import uuid
import pytest
from datetime import date
from src.database.session import init_db, SessionLocal
from src.database.repository import EmployeeRepository, TaskRepository
from src.api.schemas.employee import EmployeeProfile
from src.services.vector_store import VectorStoreService
from src.agents.policy_rag_agent import PolicyRAGAgent

def test_vector_store_retrieves_probation_leave_policy():
    chunks = VectorStoreService.query_policies("How many casual leaves can I take during probation?")
    assert len(chunks) >= 1
    top = chunks[0]
    assert "Leave" in top["document_title"]
    assert "probation" in top["content"].lower()
    assert "1 day per completed month" in top["content"]

def test_vector_store_retrieves_office_address():
    chunks = VectorStoreService.query_policies("Where is the Bengaluru office located?")
    assert len(chunks) >= 1
    contents = " ".join([c["content"] for c in chunks])
    assert "Exora Business Park" in contents
    assert "Marathahalli" in contents

def test_policy_rag_agent_answers_with_citations():
    init_db()
    with SessionLocal() as session:
        uid = uuid.uuid4().hex[:6]
        profile = EmployeeProfile(
            employee_code=f"AZ-RAG-{uid}",
            full_name="RAG Candidate",
            email=f"rag.{uid}@candidate.com",
            role="Software Engineer",
            department="Engineering",
            location="Bengaluru",
            manager_email="ananya.roy@azentio.com",
            joining_date=date(2026, 11, 20)
        )
        emp = EmployeeRepository.create_or_update_employee(session, profile)

        res = PolicyRAGAgent.ask(
            query="How many leaves do I get during probation?",
            employee=emp,
            session=session
        )

        assert "1 day per completed month" in res["answer"] or "probation" in res["answer"].lower()
        assert len(res["citations"]) >= 1
        assert any("Leave" in c["document"] for c in res["citations"])

def test_policy_rag_agent_escalates_blocked_tasks():
    init_db()
    with SessionLocal() as session:
        uid = uuid.uuid4().hex[:6]
        profile = EmployeeProfile(
            employee_code=f"AZ-ESC-{uid}",
            full_name="Escalate Candidate",
            email=f"esc.{uid}@candidate.com",
            role="Senior Software Engineer",
            department="Engineering",
            location="Bengaluru",
            manager_email="ananya.roy@azentio.com",
            joining_date=date(2026, 11, 25)
        )
        emp = EmployeeRepository.create_or_update_employee(session, profile)
        TaskRepository.generate_and_save_checklist(session, emp.id)

        res = PolicyRAGAgent.ask(
            query="Why is my laptop provisioning blocked?",
            employee=emp,
            session=session
        )

        assert "BLOCKED" in res["answer"]
        assert "Identity" in res["answer"]
        assert res["escalation"] is not None
        assert "@azentio.com" in res["escalation"]
