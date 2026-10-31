from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from src.database.session import get_db
from src.database.repository import TaskRepository, EmployeeRepository

router = APIRouter(prefix="/api/v1/tasks", tags=["Onboarding Tasks & Checklists"])

@router.post("/generate/{employee_id}")
def generate_checklist(employee_id: str, db: Session = Depends(get_db)):
    """Generate role-appropriate onboarding checklist for candidate."""
    emp = EmployeeRepository.get_employee_by_id(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    tasks = TaskRepository.generate_and_save_checklist(db, employee_id)
    return {
        "employee_id": employee_id,
        "employee_name": emp.full_name,
        "role": emp.role,
        "department": emp.department,
        "total_tasks": len(tasks),
        "tasks": [
            {
                "id": t.id,
                "task_code": t.task_code,
                "title": t.title,
                "category": t.category,
                "assigned_department": t.assigned_department,
                "owner_email": t.owner_email,
                "due_date": t.due_date.isoformat(),
                "relative_offset_days": t.relative_offset_days,
                "status": t.status,
                "rule_origin": t.rule_origin,
                "prerequisite_task": t.prerequisite_task,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None
            }
            for t in tasks
        ]
    }

@router.get("/{employee_id}")
def get_candidate_tasks(employee_id: str, db: Session = Depends(get_db)):
    """Retrieve checklist tasks for candidate."""
    tasks = TaskRepository.get_tasks_for_employee(db, employee_id)
    return [
        {
            "id": t.id,
            "task_code": t.task_code,
            "title": t.title,
            "category": t.category,
            "assigned_department": t.assigned_department,
            "owner_email": t.owner_email,
            "due_date": t.due_date.isoformat(),
            "relative_offset_days": t.relative_offset_days,
            "status": t.status,
            "rule_origin": t.rule_origin,
            "prerequisite_task": t.prerequisite_task,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None
        }
        for t in tasks
    ]

@router.patch("/{task_id}/status")
def update_task_status(task_id: str, status: str = Query(..., regex="^(Pending|Completed|Blocked|Overdue)$"), db: Session = Depends(get_db)):
    """Update task status. Marking 'Completed' automatically unblocks dependent tasks."""
    task = TaskRepository.update_task_status(db, task_id, status)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "id": task.id,
        "task_code": task.task_code,
        "title": task.title,
        "status": task.status,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None
    }

