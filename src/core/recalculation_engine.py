from datetime import date, timedelta, datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.database.models import EmployeeModel, TaskModel, AuditLogModel
from src.database.repository import EmployeeRepository
from src.core.rule_engine import RuleEngine

class RecalculationEngine:
    """Cascade recalculation engine that automatically reschedules SLAs and reconciles tasks on date/role changes."""

    @staticmethod
    def recalculate_joining_date(
        session: Session,
        employee_id: str,
        new_joining_date: date,
        reason: str = "Candidate requested joining date change"
    ) -> Dict[str, Any]:
        """Atomically shift all task deadlines when joining date changes."""
        emp = EmployeeRepository.get_employee_by_id(session, employee_id)
        if not emp:
            raise ValueError("Employee not found")

        old_date = emp.joining_date
        date_delta = (new_joining_date - old_date).days
        emp.joining_date = new_joining_date

        # Fetch and shift all tasks
        stmt = select(TaskModel).where(TaskModel.employee_id == employee_id)
        tasks = list(session.execute(stmt).scalars().all())

        updated_tasks = []
        for t in tasks:
            old_due = t.due_date
            t.due_date = new_joining_date + timedelta(days=t.relative_offset_days)
            updated_tasks.append({
                "task_code": t.task_code,
                "title": t.title,
                "old_due_date": str(old_due),
                "new_due_date": str(t.due_date)
            })

        # Record immutable audit log
        audit = AuditLogModel(
            employee_id=employee_id,
            action_type="DATE_SHIFT",
            old_value=f"Joining Date: {old_date}",
            new_value=f"Joining Date: {new_joining_date} (Shift: {date_delta:+d} days)",
            reason=reason,
            timestamp=datetime.utcnow()
        )
        session.add(audit)
        session.commit()

        return {
            "employee_id": employee_id,
            "employee_name": emp.full_name,
            "old_joining_date": str(old_date),
            "new_joining_date": str(new_joining_date),
            "days_shifted": date_delta,
            "tasks_updated_count": len(updated_tasks),
            "updated_tasks": updated_tasks,
            "audit_id": audit.id
        }

    @staticmethod
    def recalculate_role_or_department(
        session: Session,
        employee_id: str,
        new_role: str,
        new_department: str,
        new_location: str,
        reason: str = "Internal role realignment"
    ) -> Dict[str, Any]:
        """Prune obsolete tasks and inject newly mandated tasks when role or department changes."""
        emp = EmployeeRepository.get_employee_by_id(session, employee_id)
        if not emp:
            raise ValueError("Employee not found")

        old_role = f"{emp.role} ({emp.department}, {emp.location})"
        emp.role = new_role
        emp.department = new_department
        emp.location = new_location

        # Compute new ideal requirements
        new_rules = RuleEngine.generate_checklist_for_employee(
            role=new_role,
            department=new_department,
            location=new_location,
            joining_date=emp.joining_date
        )
        new_rule_codes = {r["task_code"]: r for r in new_rules}

        # Fetch existing tasks
        stmt = select(TaskModel).where(TaskModel.employee_id == employee_id)
        existing_tasks = list(session.execute(stmt).scalars().all())
        existing_codes = {t.task_code: t for t in existing_tasks}

        added_tasks = []
        removed_tasks = []

        # 1. Inject new tasks that do not exist yet
        for code, rdata in new_rule_codes.items():
            if code not in existing_codes:
                task = TaskModel(
                    employee_id=employee_id,
                    task_code=rdata["task_code"],
                    title=rdata["title"],
                    category=rdata["category"],
                    assigned_department=rdata["assigned_department"],
                    owner_email=rdata["owner_email"],
                    due_date=rdata["due_date"],
                    relative_offset_days=rdata["relative_offset_days"],
                    status=rdata["status"],
                    rule_origin=f"[Role Revision] {rdata['rule_origin']}",
                    prerequisite_task=rdata["prerequisite_task"]
                )
                session.add(task)
                added_tasks.append(rdata["title"])

        # 2. Prune obsolete tasks (unless completed)
        for code, task in existing_codes.items():
            if code not in new_rule_codes and task.status != "Completed":
                removed_tasks.append(task.title)
                session.delete(task)

        # Audit log
        new_val_str = f"{new_role} ({new_department}, {new_location})"
        audit = AuditLogModel(
            employee_id=employee_id,
            action_type="ROLE_CHANGE",
            old_value=old_role,
            new_value=new_val_str,
            reason=f"{reason} (Added: {len(added_tasks)}, Removed: {len(removed_tasks)})",
            timestamp=datetime.utcnow()
        )
        session.add(audit)
        session.commit()

        return {
            "employee_id": employee_id,
            "employee_name": emp.full_name,
            "old_profile": old_role,
            "new_profile": new_val_str,
            "added_tasks": added_tasks,
            "removed_tasks": removed_tasks,
            "audit_id": audit.id
        }

