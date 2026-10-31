import uuid
import pytest
from datetime import date, timedelta
from src.core.rule_engine import RuleEngine
from src.database.session import init_db, SessionLocal
from src.database.repository import EmployeeRepository, TaskRepository
from src.api.schemas.employee import EmployeeProfile

def test_software_engineer_checklist_includes_devtools():
    joining = date(2026, 11, 15)
    tasks = RuleEngine.generate_checklist_for_employee(
        role="Senior Software Engineer",
        department="Engineering",
        location="Bengaluru",
        joining_date=joining
    )
    task_codes = [t["task_code"] for t in tasks]

    # Engineering-specific tools must be included
    assert "RULE-TECH-DEVTOOLS" in task_codes
    assert "RULE-IT-LAPTOP" in task_codes
    assert "RULE-ALL-ID" in task_codes

    # Rule origins must be present and transparent
    for t in tasks:
        assert len(t["rule_origin"]) > 10

    # Due date offset check
    id_task = next(t for t in tasks if t["task_code"] == "RULE-ALL-ID")
    assert id_task["due_date"] == joining - timedelta(days=7)

def test_financial_analyst_checklist_excludes_devtools():
    joining = date(2026, 11, 20)
    tasks = RuleEngine.generate_checklist_for_employee(
        role="Financial Analyst",
        department="Finance",
        location="Pune",
        joining_date=joining
    )
    task_codes = [t["task_code"] for t in tasks]

    # Finance must NOT have software engineering dev tools
    assert "RULE-TECH-DEVTOOLS" not in task_codes
    # But must have universal ID, Degree, InfoSec
    assert "RULE-ALL-ID" in task_codes
    assert "RULE-POLICY-INFOSEC" in task_codes

def test_task_prerequisite_unblocking():
    init_db()
    with SessionLocal() as session:
        # Create test candidate
        uid = uuid.uuid4().hex[:6]
        profile = EmployeeProfile(
            employee_code=f"AZ-TEST-{uid}",
            full_name="Test Candidate",
            email=f"test.{uid}@candidate.com",
            role="DevOps Engineer",
            department="Engineering",
            location="Bengaluru",
            manager_email="ananya.roy@azentio.com",
            joining_date=date(2026, 12, 1)
        )
        emp = EmployeeRepository.create_or_update_employee(session, profile)
        tasks = TaskRepository.generate_and_save_checklist(session, emp.id)

        # Find ID task (prerequisite) and Laptop task (dependent)
        id_task = next(t for t in tasks if t.task_code == "RULE-ALL-ID")
        laptop_task = next(t for t in tasks if t.task_code == "RULE-IT-LAPTOP")

        assert id_task.status == "Pending"
        assert laptop_task.status == "Blocked"

        # Mark ID task completed
        TaskRepository.update_task_status(session, id_task.id, "Completed")

        # Verify laptop task is now unblocked to Pending
        session.refresh(laptop_task)
        assert laptop_task.status == "Pending"

