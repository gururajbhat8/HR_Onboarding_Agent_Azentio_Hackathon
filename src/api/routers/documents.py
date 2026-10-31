import os
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from src.database.session import get_db
from src.database.repository import EmployeeRepository, DocumentRepository
from src.agents.doc_validation_agent import DocumentValidationAgent

router = APIRouter(prefix="/api/v1/documents", tags=["Document Verification"])

@router.post("/upload")
def upload_and_evaluate_document(
    employee_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload document, run OCR & evaluation agent, and queue for HR review."""
    emp = EmployeeRepository.get_employee_by_id(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    content = file.file.read()
    
    # Save file to uploads folder
    upload_dir = "data/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, f"{employee_id}_{file.filename}")
    with open(save_path, "wb") as f:
        f.write(content)

    # Agent OCR & entity extraction
    raw_text = DocumentValidationAgent.extract_text_from_bytes(content, file.filename)
    entities = DocumentValidationAgent.parse_entities(raw_text)
    eval_result = DocumentValidationAgent.evaluate_against_employee(entities, emp.full_name)

    # Save to database
    doc_record = DocumentRepository.save_document(
        session=db,
        employee_id=employee_id,
        document_type=eval_result["document_type"],
        file_name=file.filename,
        file_path=save_path,
        extracted_metadata=eval_result,
        status="Under Review"
    )

    return {
        "document_id": doc_record.id,
        "employee_name": emp.full_name,
        "file_name": file.filename,
        "evaluation": eval_result,
        "status": doc_record.status
    }

@router.get("/pending")
def list_pending_documents(db: Session = Depends(get_db)):
    """Retrieve documents awaiting HR review."""
    pending = DocumentRepository.get_all_pending_documents(db)
    return [
        {
            "id": d.id,
            "employee_id": d.employee_id,
            "document_type": d.document_type,
            "file_name": d.file_name,
            "status": d.status,
            "evaluation": d.extracted_metadata,
            "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None
        }
        for d in pending
    ]

@router.post("/{doc_id}/review")
def review_document(
    doc_id: str,
    action: str = Query(..., regex="^(Accepted|Correction Requested)$"),
    correction_reason: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Human-in-the-Loop decision: Approve or Request Correction."""
    doc = DocumentRepository.update_document_status(
        session=db,
        doc_id=doc_id,
        new_status=action,
        rejection_reason=correction_reason
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": doc.id,
        "status": doc.status,
        "rejection_reason": doc.rejection_reason,
        "verified_at": doc.verified_at.isoformat() if doc.verified_at else None
    }

