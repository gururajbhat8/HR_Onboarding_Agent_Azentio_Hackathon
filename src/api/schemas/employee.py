from datetime import date
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

# Supported departments and locations
VALID_DEPARTMENTS = ["Engineering", "Product", "Human Resources", "Finance", "Information Technology", "Compliance"]
VALID_LOCATIONS = ["Bengaluru", "Mumbai", "Pune", "Chennai", "Hyderabad", "Dubai", "Singapore"]

class EmployeeProfile(BaseModel):
    """Employee onboarding profile schema."""
    employee_code: Optional[str] = Field(default=None, description="Auto-generated or custom employee ID")
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=20)
    role: str = Field(..., min_length=2, max_length=100)
    grade: str = Field("L1", max_length=10)
    department: str = Field(...)
    location: str = Field(...)
    manager_email: EmailStr
    joining_date: date
    onboarding_status: str = Field("Draft", max_length=50)

    @field_validator("manager_email")
    @classmethod
    def validate_manager_email(cls, v: EmailStr) -> EmailStr:
        s = str(v).lower()
        if not s.endswith("@azentio.com"):
            raise ValueError(f"Manager email '{v}' must be an internal corporate address (@azentio.com)")
        return v

    @field_validator("department")
    @classmethod
    def validate_department(cls, v: str) -> str:
        clean = v.strip()
        if clean not in VALID_DEPARTMENTS:
            raise ValueError(f"Invalid department '{clean}'. Must be one of: {', '.join(VALID_DEPARTMENTS)}")
        return clean

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: str) -> str:
        clean = v.strip()
        if clean not in VALID_LOCATIONS:
            raise ValueError(f"Invalid location '{clean}'. Must be one of: {', '.join(VALID_LOCATIONS)}")
        return clean

class DepartmentOwner(BaseModel):
    """Department task owner schema."""
    department: str
    owner_name: str
    owner_email: EmailStr
    function: str

class ValidationErrorDetail(BaseModel):
    """Details for ingestion validation error."""
    row_number: int
    field: Optional[str] = None
    message: str
    raw_data: Optional[dict] = None

class IngestionResult(BaseModel):
    """Summary result of data ingestion."""
    total_records: int
    valid_count: int
    error_count: int
    errors: List[ValidationErrorDetail] = []
    employees: List[EmployeeProfile] = []
