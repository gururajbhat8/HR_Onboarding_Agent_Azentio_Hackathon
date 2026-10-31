from datetime import date
from pydantic import BaseModel, ConfigDict, Field


class EmployeeCreate(BaseModel):
    employee_code: str
    name: str
    email: str
    role: str
    grade: str | None = None
    department: str
    location: str
    manager_name: str | None = None
    joining_date: date


class EmployeeOut(EmployeeCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class DocumentStatusUpdate(BaseModel):
    status: str
    review_note: str | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=3)
    top_k: int = Field(default=5, ge=1, le=10)
