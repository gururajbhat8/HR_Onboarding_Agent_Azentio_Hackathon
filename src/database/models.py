import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Date, DateTime, Boolean, Integer, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from src.database.session import Base

class EmployeeModel(Base):
    """SQLAlchemy model for enterprise employee profile."""
    __tablename__ = "employees"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_code = Column(String(50), unique=True, index=True, nullable=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    role = Column(String(100), nullable=False)
    grade = Column(String(10), default="L1")
    department = Column(String(50), nullable=False)
    location = Column(String(50), nullable=False)
    manager_email = Column(String(100), nullable=False)
    joining_date = Column(Date, nullable=False)
    onboarding_status = Column(String(50), default="Draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tasks = relationship("TaskModel", back_populates="employee", cascade="all, delete-orphan")
    documents = relationship("DocumentModel", back_populates="employee", cascade="all, delete-orphan")

class TaskModel(Base):
    """SQLAlchemy model for onboarding checklist task."""
    __tablename__ = "onboarding_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=False)
    task_code = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False) # Document, IT, Compliance, Policy
    assigned_department = Column(String(50), nullable=False)
    owner_email = Column(String(100), nullable=True)
    due_date = Column(Date, nullable=False)
    relative_offset_days = Column(Integer, default=0)
    status = Column(String(50), default="Pending") # Pending, Completed, Blocked, Overdue
    rule_origin = Column(Text, nullable=True)
    prerequisite_task = Column(String(50), nullable=True)
    completed_at = Column(DateTime, nullable=True)

    employee = relationship("EmployeeModel", back_populates="tasks")

class DocumentModel(Base):
    """SQLAlchemy model for employee submitted documents."""
    __tablename__ = "document_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=False)
    document_type = Column(String(100), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(200), nullable=False)
    status = Column(String(50), default="Submitted") # Submitted, Under Review, Accepted, Correction Requested
    extracted_metadata = Column(JSON, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)

    employee = relationship("EmployeeModel", back_populates="documents")

class AuditLogModel(Base):
    """SQLAlchemy model for schedule recalculations and audit trail."""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String(36), nullable=False)
    action_type = Column(String(50), nullable=False) # DATE_SHIFT, ROLE_CHANGE, DOC_REJECT
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

