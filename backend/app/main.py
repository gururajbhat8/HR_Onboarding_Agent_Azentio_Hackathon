from pathlib import Path
from datetime import date, datetime, timedelta
import json
import shutil
import uuid

import pandas as pd
from fastapi import FastAPI, Depends, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db, initialize_database
from .models import Employee, OnboardingRule, ChecklistTask, EmployeeDocument, PolicyDocument
from .schemas import EmployeeCreate, EmployeeOut, DocumentStatusUpdate, AskRequest
from .rag import ingest_policy, answer_policy_question

app = FastAPI(title="AI HR Onboarding Agent", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_ROOT = Path(settings.upload_dir)
EMPLOYEE_UPLOADS = UPLOAD_ROOT / "employee_docs"
POLICY_UPLOADS = UPLOAD_ROOT / "policies"
EMPLOYEE_UPLOADS.mkdir(parents=True, exist_ok=True)
POLICY_UPLOADS.mkdir(parents=True, exist_ok=True)

ALLOWED_EMPLOYEE_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
ALLOWED_POLICY_EXTENSIONS = {".pdf", ".txt", ".md"}
DOCUMENT_STATUSES = {"Not Submitted", "Submitted", "Under Review", "Accepted", "Correction Requested"}


@app.on_event("startup")
def startup():
    initialize_database()
    from .db import SessionLocal
    with SessionLocal() as db:
        if db.scalar(select(func.count(OnboardingRule.id))) == 0:
            seed_rules = [
                OnboardingRule(
                    rule_name="all_identity_documents", department="ALL", role="ALL",
                    task_title="Submit identity and address documents", task_type="Document",
                    owner_team="HR", due_days_from_joining=-3,
                    explanation="This rule applies to every employee, regardless of department or role."
                ),
                OnboardingRule(
                    rule_name="all_background_verification", department="ALL", role="ALL",
                    task_title="Complete background verification", task_type="Verification",
                    owner_team="Compliance", due_days_from_joining=-1,
                    explanation="Background verification is required for all employees before joining/system access."
                ),
                OnboardingRule(
                    rule_name="all_policy_acknowledgement", department="ALL", role="ALL",
                    task_title="Acknowledge company policies", task_type="Activity",
                    owner_team="HR", due_days_from_joining=0,
                    explanation="Every employee must acknowledge the applicable company policies."
                ),
                OnboardingRule(
                    rule_name="engineering_laptop_email", department="Engineering", role="ALL",
                    task_title="Provision laptop and company email", task_type="IT Provisioning",
                    owner_team="IT", due_days_from_joining=0,
                    explanation="This rule applies because the employee belongs to Engineering."
                ),
                OnboardingRule(
                    rule_name="engineering_github", department="Engineering", role="ALL",
                    task_title="Provision GitHub access", task_type="IT Access",
                    owner_team="IT", due_days_from_joining=0,
                    explanation="Engineering employees need GitHub access for development work."
                ),
                OnboardingRule(
                    rule_name="hr_hrms", department="HR", role="ALL",
                    task_title="Provision HRMS access", task_type="IT Access",
                    owner_team="IT", due_days_from_joining=0,
                    explanation="This rule applies because the employee belongs to HR."
                ),
            ]
            db.add_all(seed_rules)
            db.commit()


@app.get("/health")
def health():
    return {"status": "ok", "database": "PostgreSQL + pgvector"}


@app.post("/employees", response_model=EmployeeOut)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(Employee).where(
        (Employee.employee_code == payload.employee_code) | (Employee.email == payload.email)
    ))
    if existing:
        raise HTTPException(409, "Employee code or email already exists.")
    employee = Employee(**payload.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@app.get("/employees", response_model=list[EmployeeOut])
def list_employees(db: Session = Depends(get_db)):
    return list(db.scalars(select(Employee).order_by(Employee.joining_date)).all())


@app.post("/employees/import")
async def import_employees(file: UploadFile = File(...), db: Session = Depends(get_db)):
    suffix = Path(file.filename or "").suffix.lower()
    raw = await file.read()
    try:
        if suffix == ".csv":
            from io import BytesIO
            frame = pd.read_csv(BytesIO(raw))
            records = frame.where(pd.notnull(frame), None).to_dict(orient="records")
        elif suffix in {".xlsx", ".xls"}:
            from io import BytesIO
            frame = pd.read_excel(BytesIO(raw))
            records = frame.where(pd.notnull(frame), None).to_dict(orient="records")
        elif suffix == ".json":
            records = json.loads(raw.decode("utf-8"))
            if isinstance(records, dict):
                records = records.get("employees", [records])
        else:
            raise HTTPException(400, "Upload a CSV, XLSX, or JSON file.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"Could not parse file: {exc}")

    required = {"employee_code", "name", "email", "role", "department", "location", "joining_date"}
    imported, errors = 0, []
    for row_no, row in enumerate(records, start=2):
        try:
            # A savepoint isolates a bad row without rolling back previously valid rows.
            with db.begin_nested():
                missing = [key for key in required if row.get(key) in (None, "")]
                if missing:
                    raise ValueError("Missing fields: " + ", ".join(sorted(missing)))
                row["joining_date"] = pd.to_datetime(row["joining_date"]).date()
                payload = EmployeeCreate(**row)
                duplicate = db.scalar(select(Employee).where(
                    (Employee.employee_code == payload.employee_code) | (Employee.email == payload.email)
                ))
                if duplicate:
                    raise ValueError("Employee code or email already exists")
                db.add(Employee(**payload.model_dump()))
                db.flush()
            imported += 1
        except Exception as exc:
            errors.append({"row": row_no, "error": str(exc)})
    db.commit()
    return {"imported": imported, "errors": errors}


@app.post("/employees/{employee_id}/generate-checklist")
def generate_checklist(employee_id: int, db: Session = Depends(get_db)):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found.")
    rules = db.scalars(select(OnboardingRule).where(OnboardingRule.active.is_(True))).all()
    created = []
    for rule in rules:
        department_match = rule.department == "ALL" or rule.department.casefold() == employee.department.casefold()
        role_match = rule.role == "ALL" or rule.role.casefold() == employee.role.casefold()
        if department_match and role_match:
            exists = db.scalar(select(ChecklistTask).where(
                ChecklistTask.employee_id == employee.id,
                ChecklistTask.rule_id == rule.id,
            ))
            if not exists:
                task = ChecklistTask(
                    employee_id=employee.id,
                    rule_id=rule.id,
                    title=rule.task_title,
                    task_type=rule.task_type,
                    owner_team=rule.owner_team,
                    due_date=employee.joining_date + timedelta(days=rule.due_days_from_joining),
                    status="Pending",
                    rule_explanation=rule.explanation,
                )
                db.add(task)
                created.append(task.title)
    db.commit()
    return {"employee_id": employee.id, "created_count": len(created), "created_tasks": created}


@app.get("/employees/{employee_id}/tasks")
def get_employee_tasks(employee_id: int, db: Session = Depends(get_db)):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found.")
    tasks = db.scalars(select(ChecklistTask).where(
        ChecklistTask.employee_id == employee_id
    ).order_by(ChecklistTask.due_date)).all()
    today = date.today()
    return [{
        "id": t.id, "title": t.title, "task_type": t.task_type, "owner_team": t.owner_team,
        "due_date": t.due_date.isoformat(), "status": t.status,
        "rule_explanation": t.rule_explanation,
        "overdue": t.status not in {"Completed", "Accepted"} and t.due_date < today,
    } for t in tasks]


@app.post("/employees/{employee_id}/documents")
async def upload_employee_document(
    employee_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found.")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EMPLOYEE_EXTENSIONS:
        raise HTTPException(400, "Allowed employee document formats: PDF, PNG, JPG, JPEG.")
    content = await file.read()
    if not content or len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(400, f"File is empty or exceeds {settings.max_upload_mb} MB.")
    safe_name = f"{employee_id}_{uuid.uuid4().hex}{suffix}"
    destination = EMPLOYEE_UPLOADS / safe_name
    destination.write_bytes(content)
    document = EmployeeDocument(
        employee_id=employee_id,
        document_type=document_type,
        original_filename=file.filename or safe_name,
        stored_path=str(destination),
        status="Submitted",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return {"id": document.id, "document_type": document.document_type, "status": document.status}


@app.patch("/documents/{document_id}/status")
def update_document_status(
    document_id: int,
    payload: DocumentStatusUpdate,
    db: Session = Depends(get_db),
):
    if payload.status not in DOCUMENT_STATUSES:
        raise HTTPException(400, f"Status must be one of: {', '.join(sorted(DOCUMENT_STATUSES))}")
    document = db.get(EmployeeDocument, document_id)
    if not document:
        raise HTTPException(404, "Document not found.")
    document.status = payload.status
    document.review_note = payload.review_note
    db.commit()
    return {"id": document.id, "status": document.status, "review_note": document.review_note}


@app.post("/policies/upload")
async def upload_policy(
    title: str = Form(...),
    approved: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_POLICY_EXTENSIONS:
        raise HTTPException(400, "Policy formats supported: PDF, TXT, MD.")
    content = await file.read()
    if not content or len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(400, f"File is empty or exceeds {settings.max_upload_mb} MB.")
    safe_name = f"{uuid.uuid4().hex}{suffix}"
    destination = POLICY_UPLOADS / safe_name
    destination.write_bytes(content)
    policy = PolicyDocument(
        title=title,
        original_filename=file.filename or safe_name,
        stored_path=str(destination),
        approved=approved,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    try:
        chunk_count = ingest_policy(db, policy)
    except Exception as exc:
        db.delete(policy)
        db.commit()
        destination.unlink(missing_ok=True)
        raise HTTPException(400, f"Policy ingestion failed: {exc}")
    return {
        "policy_id": policy.id,
        "title": policy.title,
        "approved": policy.approved,
        "chunks_created": chunk_count,
        "message": "Policy text was embedded and stored in PostgreSQL/pgvector.",
    }


@app.post("/assistant/ask")
def ask_policy(payload: AskRequest, db: Session = Depends(get_db)):
    try:
        return answer_policy_question(db, payload.question, payload.top_k)
    except Exception as exc:
        raise HTTPException(500, str(exc))


@app.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    employees = db.scalars(select(Employee)).all()
    tasks = db.scalars(select(ChecklistTask)).all()
    today = date.today()
    completed = sum(t.status in {"Completed", "Accepted"} for t in tasks)
    overdue = sum(t.status not in {"Completed", "Accepted"} and t.due_date < today for t in tasks)
    pending = sum(t.status not in {"Completed", "Accepted"} and t.due_date >= today for t in tasks)
    return {
        "employee_count": len(employees),
        "task_count": len(tasks),
        "completed": completed,
        "pending": pending,
        "overdue": overdue,
        "employees": [{
            "id": e.id, "name": e.name, "role": e.role, "department": e.department,
            "location": e.location, "joining_date": e.joining_date.isoformat(),
        } for e in employees],
    }
