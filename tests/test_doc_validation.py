import os
import uuid
import pytest
from src.agents.doc_validation_agent import DocumentValidationAgent
from src.database.session import init_db, SessionLocal
from src.database.repository import EmployeeRepository, TaskRepository, DocumentRepository
from src.api.schemas.employee import EmployeeProfile
from datetime import date

def test_extract_and_evaluate_valid_pan():
    path = "data/sample_documents/PAN_Arjun_Rao_Valid.pdf"
    assert os.path.exists(path)
    with open(path, "rb") as f:
        content = f.read()

    text = DocumentValidationAgent.extract_text_from_bytes(content, "pan.pdf")
    entities = DocumentValidationAgent.parse_entities(text)
    eval_result = DocumentValidationAgent.evaluate_against_employee(entities, "Arjun Rao")

    assert eval_result["document_number"] == "ABCDE1234F"
    assert eval_result["extracted_name"] == "Arjun Rao"
    assert eval_result["match_score"] == 100
    assert eval_result["recommendation"] == "RECOMMEND_APPROVAL"

def test_extract_and_evaluate_mismatch_pan():
    path = "data/sample_documents/PAN_Mismatch_Name.pdf"
    assert os.path.exists(path)
    with open(path, "rb") as f:
        content = f.read()

    text = DocumentValidationAgent.extract_text_from_bytes(content, "mismatch.pdf")
    entities = DocumentValidationAgent.parse_entities(text)
    eval_result = DocumentValidationAgent.evaluate_against_employee(entities, "Arjun Rao")

    assert eval_result["extracted_name"] == "Arjun Kumar Verma"
    assert eval_result["match_score"] <= 40
    assert eval_result["recommendation"] == "RECOMMEND_CORRECTION"
    assert any("MISMATCH" in f for f in eval_result["flags"])

def test_expired_document_flagging():
    path = "data/sample_documents/Passport_Expired_Sample.pdf"
    assert os.path.exists(path)
    with open(path, "rb") as f:
        content = f.read()

    text = DocumentValidationAgent.extract_text_from_bytes(content, "passport.pdf")
    entities = DocumentValidationAgent.parse_entities(text)
    eval_result = DocumentValidationAgent.evaluate_against_employee(entities, "Arjun Rao")

    assert eval_result["is_expired"] is True
    assert eval_result["match_score"] <= 30
    assert eval_result["recommendation"] == "RECOMMEND_CORRECTION"

def test_document_approval_unblocks_laptop_task():
    init_db()
    with SessionLocal() as session:
        # Create test employee & tasks
        uid = uuid.uuid4().hex[:6]
        profile = EmployeeProfile(
            employee_code=f"AZ-HITL-{uid}",
            full_name="HITL Test User",
            email=f"hitl.{uid}@candidate.com",
            role="Software Engineer",
            department="Engineering",
            location="Bengaluru",
            manager_email="ananya.roy@azentio.com",
            joining_date=date(2026, 12, 1)
        )
        emp = EmployeeRepository.create_or_update_employee(session, profile)
        tasks = TaskRepository.generate_and_save_checklist(session, emp.id)
        
        id_task = next(t for t in tasks if t.task_code == "RULE-ALL-ID")
        laptop_task = next(t for t in tasks if t.task_code == "RULE-IT-LAPTOP")
        assert laptop_task.status == "Blocked"

        # Submit document
        doc = DocumentRepository.save_document(
            session=session,
            employee_id=emp.id,
            document_type="Permanent Account Number (PAN)",
            file_name="pan.pdf",
            file_path="data/uploads/pan.pdf",
            extracted_metadata={"match_score": 100},
            status="Under Review"
        )

        # HR approves document
        DocumentRepository.update_document_status(session, doc.id, "Accepted")

        # Verify ID task is completed and laptop is unblocked!
        session.refresh(id_task)
        session.refresh(laptop_task)
        assert id_task.status == "Completed"
        assert laptop_task.status == "Pending"
