from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
from src.database.session import get_db
from src.core.recalculation_engine import RecalculationEngine
from src.database.repository import AuditRepository

router = APIRouter(prefix="/api/v1/workflows", tags=["Workflow & Recalculation"])

@router.post("/recalculate-date")
def recalculate_joining_date(
    employee_id: str = Query(...),
    new_joining_date: date = Query(...),
    reason: str = Query("Joining date shift requested by candidate/HR"),
    db: Session = Depends(get_db)
):
    """Dynamically shift candidate joining date and cascade recalculate all dependent task deadlines."""
    try:
        return RecalculationEngine.recalculate_joining_date(
            session=db,
            employee_id=employee_id,
            new_joining_date=new_joining_date,
            reason=reason
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/recalculate-role")
def recalculate_role_or_department(
    employee_id: str = Query(...),
    new_role: str = Query(...),
    new_department: str = Query(...),
    new_location: str = Query(...),
    reason: str = Query("Role realignment prior to Day 1"),
    db: Session = Depends(get_db)
):
    """Reconcile tasks when role or department changes: prunes obsolete items and injects newly required ones."""
    try:
        return RecalculationEngine.recalculate_role_or_department(
            session=db,
            employee_id=employee_id,
            new_role=new_role,
            new_department=new_department,
            new_location=new_location,
            reason=reason
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/audit-logs")
def get_audit_trail(employee_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Retrieve audit history of schedule shifts and role changes."""
    if employee_id:
        logs = AuditRepository.get_audit_logs_for_employee(db, employee_id)
    else:
        logs = AuditRepository.get_all_audit_logs(db)

    return [
        {
            "id": log.id,
            "employee_id": log.employee_id,
            "action": log.action_type,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "reason": log.reason,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None
        }
        for log in logs
    ]

