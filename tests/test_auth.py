import pytest
from src.database.session import init_db, SessionLocal
from src.database.repository import UserRepository

def test_user_seeding_and_authentication():
    init_db()
    with SessionLocal() as session:
        # Verify admin authentication
        admin = UserRepository.authenticate(session, "admin", "admin123", expected_role="Admin")
        assert admin is not None
        assert admin.role == "Admin"
        assert admin.full_name == "System Administrator"

        # Verify wrong password fails
        bad_pass = UserRepository.authenticate(session, "admin", "wrong_pass")
        assert bad_pass is None

        # Verify HR authentication
        hr = UserRepository.authenticate(session, "hr1", "hr123", expected_role="HR")
        assert hr is not None
        assert hr.role == "HR"
        assert hr.full_name == "Priya Sharma"

        # Verify role mismatch fails
        mismatch = UserRepository.authenticate(session, "hr1", "hr123", expected_role="Admin")
        assert mismatch is None

        # Verify creating custom candidate user
        custom = UserRepository.create_user(
            session=session,
            username="test.candidate.custom",
            password="candidate123",
            role="Candidate",
            full_name="Custom Candidate",
            email="custom.candidate@candidate.com"
        )
        assert custom.id is not None
        auth_custom = UserRepository.authenticate(session, "test.candidate.custom", "candidate123", expected_role="Candidate")
        assert auth_custom is not None
