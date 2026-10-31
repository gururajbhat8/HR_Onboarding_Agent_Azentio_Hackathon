from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from src.database.models import EmployeeModel, TaskModel, DocumentModel, AuditLogModel, UserModel, NotificationModel
from src.services.vector_store import VectorStoreService
from src.api.schemas.employee import EmployeeProfile
from src.core.rule_engine import RuleEngine

class EmployeeRepository:
    """Repository handling employee database operations."""

    @staticmethod
    def create_or_update_employee(session: Session, emp_data: EmployeeProfile) -> EmployeeModel:
        """Insert new employee or update existing by email."""
        stmt = select(EmployeeModel).where(EmployeeModel.email == emp_data.email)
        existing = session.execute(stmt).scalar_one_or_none()

        if existing:
            existing.full_name = emp_data.full_name
            existing.role = emp_data.role
            existing.grade = emp_data.grade
            existing.department = emp_data.department
            existing.location = emp_data.location
            existing.manager_email = emp_data.manager_email
            existing.joining_date = emp_data.joining_date
            existing.phone = emp_data.phone
            existing.onboarding_status = emp_data.onboarding_status
            session.commit()
            session.refresh(existing)
            return existing
        else:
            new_emp = EmployeeModel(
                employee_code=emp_data.employee_code,
                full_name=emp_data.full_name,
                email=emp_data.email,
                phone=emp_data.phone,
                role=emp_data.role,
                grade=emp_data.grade,
                department=emp_data.department,
                location=emp_data.location,
                manager_email=emp_data.manager_email,
                joining_date=emp_data.joining_date,
                onboarding_status=emp_data.onboarding_status or "Initiated"
            )
            session.add(new_emp)
            session.commit()
            session.refresh(new_emp)
            
            # Ensure candidate login account exists
            uname = new_emp.email.split("@")[0].lower()
            stmt_user = select(UserModel).where((UserModel.username == uname) | (UserModel.employee_id == new_emp.id))
            if not session.execute(stmt_user).scalar_one_or_none():
                cand_user = UserModel(
                    username=uname,
                    password="candidate123",
                    role="Candidate",
                    full_name=new_emp.full_name,
                    email=new_emp.email,
                    employee_id=new_emp.id
                )
                session.add(cand_user)
                session.commit()

            return new_emp

    @staticmethod
    def get_all_employees(session: Session) -> List[EmployeeModel]:
        """Fetch all employees ordered by joining date."""
        stmt = select(EmployeeModel).order_by(EmployeeModel.joining_date.asc())
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def get_employee_by_id(session: Session, emp_id: str) -> Optional[EmployeeModel]:
        """Fetch a single employee by primary key UUID."""
        stmt = select(EmployeeModel).where(EmployeeModel.id == emp_id)
        return session.execute(stmt).scalar_one_or_none()

class TaskRepository:
    """Repository handling onboarding checklist operations."""

    @staticmethod
    def generate_and_save_checklist(session: Session, employee_id: str) -> List[TaskModel]:
        """Generate role-appropriate tasks using RuleEngine and persist to database."""
        emp = EmployeeRepository.get_employee_by_id(session, employee_id)
        if not emp:
            return []

        # Check existing tasks
        existing_stmt = select(TaskModel).where(TaskModel.employee_id == employee_id)
        existing_tasks = list(session.execute(existing_stmt).scalars().all())
        existing_codes = {t.task_code for t in existing_tasks}

        # Generate new tasks from rules
        rule_tasks = RuleEngine.generate_checklist_for_employee(
            role=emp.role,
            department=emp.department,
            location=emp.location,
            joining_date=emp.joining_date
        )

        created_tasks = []
        for rt in rule_tasks:
            if rt["task_code"] not in existing_codes:
                task = TaskModel(
                    employee_id=employee_id,
                    task_code=rt["task_code"],
                    title=rt["title"],
                    category=rt["category"],
                    assigned_department=rt["assigned_department"],
                    owner_email=rt["owner_email"],
                    due_date=rt["due_date"],
                    relative_offset_days=rt["relative_offset_days"],
                    status=rt["status"],
                    rule_origin=rt["rule_origin"],
                    prerequisite_task=rt["prerequisite_task"]
                )
                session.add(task)
                created_tasks.append(task)

        if created_tasks:
            session.commit()

        # Return full current task list
        stmt = select(TaskModel).where(TaskModel.employee_id == employee_id).order_by(TaskModel.due_date.asc())
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def get_tasks_for_employee(session: Session, employee_id: str) -> List[TaskModel]:
        """Fetch all tasks for an employee ordered by due date."""
        stmt = select(TaskModel).where(TaskModel.employee_id == employee_id).order_by(TaskModel.due_date.asc())
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def update_task_status(session: Session, task_id: str, new_status: str) -> Optional[TaskModel]:
        """Update status of a task and automatically unblock dependent tasks when completed."""
        stmt = select(TaskModel).where(TaskModel.id == task_id)
        task = session.execute(stmt).scalar_one_or_none()
        if not task:
            return None

        task.status = new_status
        if new_status == "Completed":
            task.completed_at = datetime.utcnow()
            # Unblock any downstream task that was waiting on this task
            prereq_stmt = select(TaskModel).where(
                TaskModel.employee_id == task.employee_id,
                TaskModel.prerequisite_task == task.task_code,
                TaskModel.status == "Blocked"
            )
            blocked_tasks = session.execute(prereq_stmt).scalars().all()
            for bt in blocked_tasks:
                bt.status = "Pending"
        elif new_status == "Pending":
            task.completed_at = None

        session.commit()
        session.refresh(task)
        return task

class DocumentRepository:
    """Repository handling document record persistence and verification statuses."""

    @staticmethod
    def save_document(
        session: Session,
        employee_id: str,
        document_type: str,
        file_name: str,
        file_path: str,
        extracted_metadata: dict,
        status: str = "Under Review"
    ) -> DocumentModel:
        """Create or update a document record."""
        stmt = select(DocumentModel).where(
            DocumentModel.employee_id == employee_id,
            DocumentModel.document_type == document_type
        )
        existing = session.execute(stmt).scalar_one_or_none()

        if existing:
            existing.file_name = file_name
            existing.file_path = file_path
            existing.extracted_metadata = extracted_metadata
            existing.status = status
            existing.uploaded_at = datetime.utcnow()
            session.commit()
            session.refresh(existing)
            return existing
        else:
            doc = DocumentModel(
                employee_id=employee_id,
                document_type=document_type,
                file_name=file_name,
                file_path=file_path,
                extracted_metadata=extracted_metadata,
                status=status
            )
            session.add(doc)
            session.commit()
            session.refresh(doc)
            return doc

    @staticmethod
    def get_documents_for_employee(session: Session, employee_id: str) -> List[DocumentModel]:
        """Fetch all documents for an employee."""
        stmt = select(DocumentModel).where(DocumentModel.employee_id == employee_id).order_by(DocumentModel.uploaded_at.desc())
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def get_all_pending_documents(session: Session) -> List[DocumentModel]:
        """Fetch all documents requiring review across all employees."""
        stmt = select(DocumentModel).where(DocumentModel.status.in_(["Submitted", "Under Review"])).order_by(DocumentModel.uploaded_at.desc())
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def get_reviewed_documents_history(session: Session) -> List[DocumentModel]:
        """Fetch all reviewed documents (Accepted or Correction Requested) for audit ledger."""
        stmt = select(DocumentModel).where(DocumentModel.status.in_(["Accepted", "Correction Requested"])).order_by(DocumentModel.verified_at.desc(), DocumentModel.uploaded_at.desc())
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def update_document_status(
        session: Session,
        doc_id: str,
        new_status: str,
        rejection_reason: Optional[str] = None,
        verified_by: str = "HR Operations"
    ) -> Optional[DocumentModel]:
        """Update review status, create candidate notifications, and sync progress with Pinecone Vector Store."""
        stmt = select(DocumentModel).where(DocumentModel.id == doc_id)
        doc = session.execute(stmt).scalar_one_or_none()
        if not doc:
            return None

        # Fetch employee for notifications & Pinecone vector indexing
        emp = session.execute(select(EmployeeModel).where(EmployeeModel.id == doc.employee_id)).scalar_one_or_none()
        emp_name = emp.full_name if emp else "Candidate"

        doc.status = new_status
        doc.rejection_reason = rejection_reason
        doc.verified_at = datetime.utcnow()

        unblocked_info = "None"
        if new_status == "Accepted":
            task_code_map = {
                "Permanent Account Number (PAN)": "RULE-ALL-ID",
                "Aadhaar Card": "RULE-ALL-ID",
                "Educational Degree Certificate": "RULE-ALL-DEGREE",
                "Passport": "RULE-ALL-ID"
            }
            target_code = task_code_map.get(doc.document_type, "RULE-ALL-ID")

            task_stmt = select(TaskModel).where(
                TaskModel.employee_id == doc.employee_id,
                TaskModel.task_code == target_code
            )
            task = session.execute(task_stmt).scalar_one_or_none()
            if task:
                TaskRepository.update_task_status(session, task.id, "Completed")
                unblocked_info = "Laptop & Workstation Provisioning unblocked (ready for IT)"

            # Create candidate progress notification
            notif = NotificationModel(
                employee_id=doc.employee_id,
                title=f"✅ Document Approved: {doc.document_type}",
                message=f"Your {doc.document_type} was approved by HR ({verified_by}). Remarks: {rejection_reason or 'Verified per Azentio Hiring Policy v2.4'}. Downstream tasks unblocked!",
                notification_type="SUCCESS"
            )
            session.add(notif)

            # Audit trail
            audit = AuditLogModel(
                employee_id=doc.employee_id,
                action_type="DOC_APPROVAL",
                old_value="Under Review",
                new_value="Accepted",
                reason=rejection_reason or "Document verified per Azentio Hiring Policy v2.4"
            )
            session.add(audit)

        elif new_status == "Correction Requested":
            unblocked_info = "Downstream dependencies remain blocked pending corrected document submission"
            # Create candidate progress notification
            notif = NotificationModel(
                employee_id=doc.employee_id,
                title=f"⚠️ Correction Required: {doc.document_type}",
                message=f"HR requested correction for your {doc.document_type}. Remarks: {rejection_reason}. Please re-upload a compliant document.",
                notification_type="WARNING"
            )
            session.add(notif)

            # Audit trail
            audit = AuditLogModel(
                employee_id=doc.employee_id,
                action_type="DOC_CORRECTION_REQUEST",
                old_value="Under Review",
                new_value="Correction Requested",
                reason=rejection_reason
            )
            session.add(audit)

        session.commit()
        session.refresh(doc)

        # Sync progress update into Pinecone Vector Store and semantic memory
        VectorStoreService.upsert_candidate_progress(
            candidate_id=doc.employee_id,
            candidate_name=emp_name,
            document_type=doc.document_type,
            status=new_status,
            reason=rejection_reason or ("Document verified per Azentio Hiring Policy v2.4" if new_status == "Accepted" else "Discrepancy flagged"),
            unblocked_tasks=unblocked_info,
            verified_by=verified_by
        )

        return doc

class NotificationRepository:
    """Repository handling candidate notifications."""

    @staticmethod
    def get_notifications_for_employee(session: Session, employee_id: str) -> List[NotificationModel]:
        """Fetch all notifications for employee ordered by latest."""
        stmt = select(NotificationModel).where(NotificationModel.employee_id == employee_id).order_by(NotificationModel.created_at.desc())
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def create_notification(session: Session, employee_id: str, title: str, message: str, notification_type: str = "INFO") -> NotificationModel:
        """Create new progress notification."""
        notif = NotificationModel(
            employee_id=employee_id,
            title=title,
            message=message,
            notification_type=notification_type
        )
        session.add(notif)
        session.commit()
        session.refresh(notif)
        return notif

    @staticmethod
    def mark_all_as_read(session: Session, employee_id: str) -> None:
        """Mark all notifications as read."""
        stmt = select(NotificationModel).where(NotificationModel.employee_id == employee_id)
        notifs = list(session.execute(stmt).scalars().all())
        for n in notifs:
            n.is_read = True
        session.commit()

class AuditRepository:
    """Repository handling audit log ledger queries."""

    @staticmethod
    def get_audit_logs_for_employee(session: Session, employee_id: str) -> List[AuditLogModel]:
        """Fetch audit trail for specific employee."""
        stmt = select(AuditLogModel).where(AuditLogModel.employee_id == employee_id).order_by(AuditLogModel.timestamp.desc())
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def get_all_audit_logs(session: Session) -> List[AuditLogModel]:
        """Fetch all enterprise audit trail entries."""
        stmt = select(AuditLogModel).order_by(AuditLogModel.timestamp.desc())
        return list(session.execute(stmt).scalars().all())

class UserRepository:
    """Repository handling authentication, role segregation, and user accounts."""

    @staticmethod
    def authenticate(session: Session, username: str, password: str, expected_role: Optional[str] = None) -> Optional[UserModel]:
        """Verify username, password, and optional expected role."""
        u_clean = username.strip().lower()
        stmt = select(UserModel).where(UserModel.username == u_clean)
        user = session.execute(stmt).scalar_one_or_none()
        if not user:
            # Also allow login with email as username
            stmt_email = select(UserModel).where(UserModel.email == u_clean)
            user = session.execute(stmt_email).scalar_one_or_none()
        
        if not user:
            return None
        
        if user.password != password:
            return None
            
        if expected_role and user.role.lower() != expected_role.lower():
            return None
            
        return user

    @staticmethod
    def get_user_by_username(session: Session, username: str) -> Optional[UserModel]:
        """Fetch user by username or email."""
        u_clean = username.strip().lower()
        stmt = select(UserModel).where((UserModel.username == u_clean) | (UserModel.email == u_clean))
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_users_by_role(session: Session, role: str) -> List[UserModel]:
        """List all users having a given role."""
        stmt = select(UserModel).where(UserModel.role == role).order_by(UserModel.username)
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def get_all_users(session: Session) -> List[UserModel]:
        """List all registered users in the system."""
        stmt = select(UserModel).order_by(UserModel.role, UserModel.username)
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def create_user(
        session: Session,
        username: str,
        password: str,
        role: str,
        full_name: str,
        email: str,
        employee_id: Optional[str] = None
    ) -> UserModel:
        """Create a new user account."""
        u_clean = username.strip().lower()
        stmt = select(UserModel).where(UserModel.username == u_clean)
        existing = session.execute(stmt).scalar_one_or_none()
        if existing:
            existing.password = password
            existing.role = role
            existing.full_name = full_name
            existing.email = email
            existing.employee_id = employee_id
            session.commit()
            session.refresh(existing)
            return existing

        user = UserModel(
            username=u_clean,
            password=password,
            role=role,
            full_name=full_name,
            email=email,
            employee_id=employee_id
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    @staticmethod
    def get_user_by_id(session: Session, user_id: str) -> Optional[UserModel]:
        """Fetch user by primary key ID."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def delete_user(session: Session, user_id: str) -> bool:
        """Delete user account with safety check against primary admin."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        user = session.execute(stmt).scalar_one_or_none()
        if not user or user.username.lower() == "admin":
            return False
        session.delete(user)
        session.commit()
        return True

    @staticmethod
    def update_user(
        session: Session,
        user_id: str,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        role: Optional[str] = None,
        password: Optional[str] = None
    ) -> Optional[UserModel]:
        """Modify existing user account details."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        user = session.execute(stmt).scalar_one_or_none()
        if not user:
            return None

        if full_name is not None and full_name.strip():
            user.full_name = full_name.strip()
        if email is not None and email.strip():
            user.email = email.strip()
        if role is not None and role.strip():
            # Prevent demoting the primary admin
            if user.username.lower() == "admin":
                user.role = "Admin"
            else:
                user.role = role.strip()
        if password is not None and password.strip():
            user.password = password.strip()

        session.commit()
        session.refresh(user)
        return user

    @classmethod
    def seed_default_users(cls, session: Session) -> None:
        """Seed default admin, HR team, and candidate users if not present."""
        # 1. Admin account
        cls.create_user(
            session=session,
            username="admin",
            password="admin123",
            role="Admin",
            full_name="System Administrator",
            email="admin@azentio.com"
        )

        # 2. HR Team accounts
        cls.create_user(
            session=session,
            username="hr1",
            password="hr123",
            role="HR",
            full_name="Priya Sharma",
            email="priya.sharma@azentio.com"
        )
        cls.create_user(
            session=session,
            username="hr2",
            password="hr123",
            role="HR",
            full_name="Ananya Roy",
            email="ananya.roy@azentio.com"
        )

        # 3. Candidate accounts for existing employees
        stmt_emps = select(EmployeeModel)
        employees = list(session.execute(stmt_emps).scalars().all())
        for emp in employees:
            uname = emp.email.split("@")[0].lower()
            stmt_user = select(UserModel).where((UserModel.username == uname) | (UserModel.employee_id == emp.id))
            cand_user = session.execute(stmt_user).scalar_one_or_none()
            if not cand_user:
                cls.create_user(
                    session=session,
                    username=uname,
                    password="candidate123",
                    role="Candidate",
                    full_name=emp.full_name,
                    email=emp.email,
                    employee_id=emp.id
                )
