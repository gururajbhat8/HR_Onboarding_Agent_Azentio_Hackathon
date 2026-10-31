import io
import os
import json
import pandas as pd
from typing import Union, List, Dict, Any
from pydantic import ValidationError
from src.api.schemas.employee import EmployeeProfile, ValidationErrorDetail, IngestionResult

class IngestionService:
    """Service to parse and validate candidate onboarding data from CSV, Excel, and JSON."""

    @staticmethod
    def load_department_owners() -> List[str]:
        """Load registered department manager emails."""
        try:
            path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "rules", "department_owners.json")
            with open(path, "r") as f:
                data = json.load(f)
                return [d["owner_email"].lower() for d in data if "owner_email" in d]
        except Exception:
            return ["ananya.roy@azentio.com", "priya.sharma@azentio.com", "suresh.nair@azentio.com", "rahul.verma@azentio.com"]

    @classmethod
    def parse_file(cls, file_content: Union[bytes, str], filename: str) -> IngestionResult:
        """Parse raw content from CSV, XLSX, or JSON and return validated IngestionResult."""
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        raw_records: List[Dict[str, Any]] = []

        try:
            if ext == "json":
                if isinstance(file_content, bytes):
                    file_content = file_content.decode("utf-8")
                parsed = json.loads(file_content)
                raw_records = parsed if isinstance(parsed, list) else [parsed]
            
            elif ext in ["csv", "txt"]:
                if isinstance(file_content, str):
                    file_content = file_content.encode("utf-8")
                df = pd.read_csv(io.BytesIO(file_content))
                # Fill NaN with None
                df = df.where(pd.notnull(df), None)
                raw_records = df.to_dict(orient="records")

            elif ext in ["xlsx", "xls"]:
                if isinstance(file_content, str):
                    file_content = file_content.encode("utf-8")
                df = pd.read_excel(io.BytesIO(file_content))
                df = df.where(pd.notnull(df), None)
                raw_records = df.to_dict(orient="records")
            else:
                return IngestionResult(
                    total_records=0, valid_count=0, error_count=1,
                    errors=[ValidationErrorDetail(row_number=0, field="file_type", message=f"Unsupported format '{ext}'. Must be CSV, Excel, or JSON.")]
                )
        except Exception as e:
            return IngestionResult(
                total_records=0, valid_count=0, error_count=1,
                errors=[ValidationErrorDetail(row_number=0, field="file_parser", message=f"Failed to read file: {str(e)}")]
            )

        return cls.validate_records(raw_records)

    @classmethod
    def validate_records(cls, records: List[Dict[str, Any]]) -> IngestionResult:
        """Validate list of raw dictionaries against EmployeeProfile schema."""
        valid_employees: List[EmployeeProfile] = []
        errors: List[ValidationErrorDetail] = []
        known_managers = cls.load_department_owners()

        for idx, record in enumerate(records, start=1):
            # Clean string values and handle date formatting
            cleaned = {}
            for k, v in record.items():
                if v is None:
                    cleaned[k] = None
                elif isinstance(v, str):
                    cleaned[k] = v.strip() if v.strip() != "" else None
                else:
                    if hasattr(v, "strftime"):
                        cleaned[k] = v.strftime("%Y-%m-%d")
                    else:
                        cleaned[k] = v

            # Validate against Pydantic schema
            try:
                emp = EmployeeProfile(**cleaned)
                valid_employees.append(emp)
            except ValidationError as ve:
                for err in ve.errors():
                    field_name = ".".join(str(loc) for loc in err["loc"])
                    msg = err["msg"]
                    errors.append(ValidationErrorDetail(
                        row_number=idx,
                        field=field_name,
                        message=msg,
                        raw_data=cleaned
                    ))
            except Exception as ex:
                errors.append(ValidationErrorDetail(
                    row_number=idx,
                    field="general",
                    message=str(ex),
                    raw_data=cleaned
                ))

        return IngestionResult(
            total_records=len(records),
            valid_count=len(valid_employees),
            error_count=len(errors),
            errors=errors,
            employees=valid_employees
        )
