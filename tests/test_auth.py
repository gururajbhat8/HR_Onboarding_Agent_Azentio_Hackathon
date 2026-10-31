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
        # Test updating user details
        updated = UserRepository.update_user(
            session=session,
            user_id=custom.id,
            full_name="Updated Candidate Name",
            password="newpassword456"
        )
        assert updated is not None
        assert updated.full_name == "Updated Candidate Name"
        assert UserRepository.authenticate(session, "test.candidate.custom", "newpassword456") is not None

        # Test deleting user
        deleted = UserRepository.delete_user(session, custom.id)
        assert deleted is True
        assert UserRepository.get_user_by_id(session, custom.id) is None

        # Primary admin deletion must fail safely
        admin_del = UserRepository.delete_user(session, admin.id)
        assert admin_del is False
        assert UserRepository.get_user_by_id(session, admin.id) is not None

