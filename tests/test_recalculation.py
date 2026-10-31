import uuid
import pytest
from datetime import date, timedelta
from src.database.session import init_db, SessionLocal
from src.database.repository import EmployeeRepository, TaskRepository, AuditRepository
from src.core.recalculation_engine import RecalculationEngine
from src.api.schemas.employee import EmployeeProfile

def test_dynamic_date_shift_cascade():
    init_db()
    with SessionLocal() as session:
        uid = uuid.uuid4().hex[:6]
        orig_date = date(2026, 11, 15)
        new_date = date(2026, 11, 25)

        # Create candidate
        profile = EmployeeProfile(
            employee_code=f"AZ-RECALC-{uid}",
            full_name="Recalc Candidate",
            email=f"recalc.{uid}@candidate.com",
            role="Software Engineer",
            department="Engineering",
            location="Bengaluru",
            manager_email="ananya.roy@azentio.com",
            joining_date=orig_date
        )
        emp = EmployeeRepository.create_or_update_employee(session, profile)
        tasks = TaskRepository.generate_and_save_checklist(session, emp.id)
        
        # Check original due date of task with offset -7
        t_id = next(t for t in tasks if t.relative_offset_days == -7)
        assert t_id.due_date == orig_date - timedelta(days=7)

        # Trigger Cascade Recalculation: Shift forward by 10 days
        res = RecalculationEngine.recalculate_joining_date(
            session=session,
            employee_id=emp.id,
            new_joining_date=new_date,
            reason="Notice period extended by 10 days"
        )

        assert res["days_shifted"] == 10
        assert res["tasks_updated_count"] >= 4

        # Verify updated due date in DB
        session.refresh(t_id)
        assert t_id.due_date == new_date - timedelta(days=7)

        # Verify audit log was created
        audit_logs = AuditRepository.get_audit_logs_for_employee(session, emp.id)
        assert len(audit_logs) >= 1
        assert audit_logs[0].action_type == "DATE_SHIFT"
        assert "Notice period extended" in audit_logs[0].reason

def test_dynamic_role_change_reconciliation():
    init_db()
    with SessionLocal() as session:
        uid = uuid.uuid4().hex[:6]
        joining = date(2026, 11, 20)

        # Create candidate originally as Financial Analyst
        profile = EmployeeProfile(
            employee_code=f"AZ-ROLE-{uid}",
            full_name="Transfer Candidate",
            email=f"transfer.{uid}@candidate.com",
            role="Financial Analyst",
            department="Finance",
            location="Pune",
            manager_email="suresh.nair@azentio.com",
            joining_date=joining
        )
        emp = EmployeeRepository.create_or_update_employee(session, profile)
        tasks = TaskRepository.generate_and_save_checklist(session, emp.id)
        initial_codes = [t.task_code for t in tasks]
        assert "RULE-TECH-DEVTOOLS" not in initial_codes

        # Re-align role to Software Engineer in Bengaluru
        res = RecalculationEngine.recalculate_role_or_department(
            session=session,
            employee_id=emp.id,
            new_role="Senior DevOps Engineer",
            new_department="Engineering",
            new_location="Bengaluru",
            reason="Lateral transfer to Engineering team"
        )

        # Refresh tasks
        refreshed_tasks = TaskRepository.get_tasks_for_employee(session, emp.id)
        refreshed_codes = [t.task_code for t in refreshed_tasks]

        # Verify new engineering dev tools task was injected!
        assert "RULE-TECH-DEVTOOLS" in refreshed_codes
        assert any("DevOps" in t.rule_origin or "Role Revision" in t.rule_origin for t in refreshed_tasks)

        # Verify audit log was created
        audit_logs = AuditRepository.get_audit_logs_for_employee(session, emp.id)
        assert any(l.action_type == "ROLE_CHANGE" for l in audit_logs)

