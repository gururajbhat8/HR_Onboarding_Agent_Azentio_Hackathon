from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database.session import get_db
from src.database.repository import EmployeeRepository
from src.services.ingestion_service import IngestionService
from src.api.schemas.employee import IngestionResult, VALID_DEPARTMENTS, VALID_LOCATIONS

router = APIRouter(prefix="/api/v1/ingestion", tags=["Data Ingestion"])

@router.post("/upload", response_model=IngestionResult)
def upload_candidate_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and validate candidate file (CSV, Excel, or JSON). Valid records are saved to the database."""
    content = file.file.read()
    result = IngestionService.parse_file(content, file.filename)

    # Persist valid records
    for emp in result.employees:
        EmployeeRepository.create_or_update_employee(db, emp)

    return result

@router.post("/load-sample", response_model=IngestionResult)
def load_sample_dataset(
    dataset_type: str = "valid", # "valid" or "with_errors"
    db: Session = Depends(get_db)
):
    """1-Click loader for synthetic candidate datasets."""
    file_path = "data/sample_profiles/candidates.json" if dataset_type == "valid" else "data/sample_profiles/candidates_with_errors.csv"
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        filename = file_path.split("/")[-1]
        result = IngestionService.parse_file(content, filename)
        
        # Save valid employees
        for emp in result.employees:
            EmployeeRepository.create_or_update_employee(db, emp)
            
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Sample file {file_path} not found")

@router.get("/employees")
def list_ingested_employees(db: Session = Depends(get_db)):
    """Retrieve all ingested candidate profiles."""
    employees = EmployeeRepository.get_all_employees(db)
    return [
        {
            "id": e.id,
            "employee_code": e.employee_code,
            "full_name": e.full_name,
            "email": e.email,
            "phone": e.phone,
            "role": e.role,
            "grade": e.grade,
            "department": e.department,
            "location": e.location,
            "manager_email": e.manager_email,
            "joining_date": e.joining_date.isoformat() if e.joining_date else None,
            "onboarding_status": e.onboarding_status,
            "created_at": e.created_at.isoformat() if e.created_at else None
        }
        for e in employees
    ]

@router.get("/metadata")
def get_org_metadata():
    """Retrieve valid departments and locations for UI filters."""
    return {
        "departments": VALID_DEPARTMENTS,
        "locations": VALID_LOCATIONS
    }
