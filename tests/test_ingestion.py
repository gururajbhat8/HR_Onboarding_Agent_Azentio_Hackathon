import pytest
from src.services.ingestion_service import IngestionService

SAMPLE_CSV = """employee_code,full_name,email,phone,role,grade,department,location,manager_email,joining_date,onboarding_status
AZ-301,Ankit Roy,ankit.roy@candidate.com,+91 98765 00001,Software Engineer,L2,Engineering,Bengaluru,ananya.roy@azentio.com,2026-11-20,Initiated
"""

SAMPLE_CSV_INVALID = """employee_code,full_name,email,phone,role,grade,department,location,manager_email,joining_date,onboarding_status
AZ-302,,invalid_email,,Engineer,L1,Finance,Bengaluru,priya.sharma@azentio.com,2026-11-20,Initiated
AZ-303,Bad Date,bad.date@candidate.com,,Analyst,L1,Finance,Bengaluru,priya.sharma@azentio.com,32-13-2026,Initiated
AZ-304,Bad Dept,bad.dept@candidate.com,,Analyst,L1,UnknownDept,Bengaluru,priya.sharma@azentio.com,2026-11-20,Initiated
AZ-305,Bad Mgr,bad.mgr@candidate.com,,Analyst,L1,Finance,Bengaluru,external_mgr@gmail.com,2026-11-20,Initiated
"""

SAMPLE_JSON = """[
  {
    "employee_code": "AZ-401",
    "full_name": "Meera Sen",
    "email": "meera.sen@candidate.com",
    "role": "Product Designer",
    "grade": "L3",
    "department": "Product",
    "location": "Mumbai",
    "manager_email": "priya.sharma@azentio.com",
    "joining_date": "2026-11-25"
  }
]"""

def test_parse_valid_csv():
    result = IngestionService.parse_file(SAMPLE_CSV.encode("utf-8"), "candidates.csv")
    assert result.total_records == 1
    assert result.valid_count == 1
    assert result.error_count == 0
    assert result.employees[0].full_name == "Ankit Roy"
    assert str(result.employees[0].joining_date) == "2026-11-20"

def test_parse_valid_json():
    result = IngestionService.parse_file(SAMPLE_JSON.encode("utf-8"), "candidates.json")
    assert result.total_records == 1
    assert result.valid_count == 1
    assert result.error_count == 0
    assert result.employees[0].full_name == "Meera Sen"

def test_parse_invalid_csv_catches_all_errors():
    result = IngestionService.parse_file(SAMPLE_CSV_INVALID.encode("utf-8"), "invalid.csv")
    assert result.total_records == 4
    assert result.valid_count == 0
    assert result.error_count >= 4
    
    # Check that error fields are accurately identified
    error_fields = [e.field for e in result.errors]
    assert any("email" in f for f in error_fields if f)
    assert any("department" in f for f in error_fields if f)
    assert any("manager_email" in f for f in error_fields if f)

def test_database_persistence():
    from src.database.session import init_db, SessionLocal
    from src.database.repository import EmployeeRepository
    
    init_db()
    result = IngestionService.parse_file(SAMPLE_JSON.encode("utf-8"), "candidates.json")
    with SessionLocal() as session:
        for emp in result.employees:
            EmployeeRepository.create_or_update_employee(session, emp)
        saved = EmployeeRepository.get_all_employees(session)
        assert len(saved) >= 1
        assert any(e.full_name == "Meera Sen" for e in saved)
