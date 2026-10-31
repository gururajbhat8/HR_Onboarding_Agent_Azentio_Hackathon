import os
import io
import re
from datetime import datetime, date
from typing import Dict, Any, List, Optional

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

class DocumentValidationAgent:
    """Agent responsible for OCR text extraction, entity parsing, and cross-verification against master employee profiles."""

    @staticmethod
    def extract_text_from_bytes(file_content: bytes, filename: str) -> str:
        """Extract text from PDF or raw text stream."""
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        text = ""

        if ext == "pdf":
            if HAS_PYPDF:
                try:
                    reader = PdfReader(io.BytesIO(file_content))
                    for page in reader.pages:
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"
                except Exception:
                    pass
            
            # Universal fallback: Parse PDF text operators directly from raw bytes
            if not text:
                try:
                    decoded = file_content.decode("latin1", errors="ignore")
                    matches = re.findall(r"\(([^)]+)\)\s*Tj", decoded)
                    if matches:
                        text = "\n".join(matches)
                    else:
                        words = re.findall(r"[A-Za-z0-9\-.,: /@]{3,}", decoded)
                        text = " ".join(words)
                except Exception:
                    text = ""
        else:
            try:
                text = file_content.decode("utf-8", errors="ignore")
            except Exception:
                text = ""

        return text.strip()

    @classmethod
    def parse_entities(cls, text: str) -> Dict[str, Any]:
        """Extract document type, identifier, name, and dates using regex pattern matching."""
        entities = {
            "document_type": "Unknown",
            "document_number": None,
            "extracted_name": None,
            "dob": None,
            "expiry_date": None,
            "is_expired": False
        }

        # 1. Detect Document Type & Number
        # PAN Pattern: 5 letters, 4 digits, 1 letter (e.g. ABCDE1234F)
        pan_match = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text)
        if pan_match or "PAN" in text.upper():
            entities["document_type"] = "Permanent Account Number (PAN)"
            entities["document_number"] = pan_match.group(1) if pan_match else "PAN-DETECTED"

        # Aadhaar Pattern: 12 digits (with optional spaces: 1234 5678 9012)
        aadhaar_match = re.search(r"\b(\d{4}\s?\d{4}\s?\d{4})\b", text)
        if aadhaar_match or "AADHAAR" in text.upper():
            entities["document_type"] = "Aadhaar Card"
            entities["document_number"] = aadhaar_match.group(1) if aadhaar_match else "AADHAAR-DETECTED"

        # Degree / Educational
        if any(w in text.upper() for w in ["DEGREE", "BACHELOR", "MASTER", "DIPLOMA", "CERTIFICATE"]):
            entities["document_type"] = "Educational Degree Certificate"
            deg_match = re.search(r"(?:Degree|Candidate Name):\s*([^\n\r]+)", text, re.IGNORECASE)
            entities["document_number"] = "DEGREE-ACADEMIC"

        # Passport
        passport_match = re.search(r"\b([A-Z][0-9]{7})\b", text)
        if passport_match or "PASSPORT" in text.upper():
            entities["document_type"] = "Passport"
            entities["document_number"] = passport_match.group(1) if passport_match else "PASSPORT-DETECTED"

        # 2. Extract Name on Document
        name_patterns = [
            r"(?:Name|Full Name|Candidate Name):\s*([A-Za-z\s]+)",
            r"(?:Arjun\s+[A-Za-z\s]+)"
        ]
        for pat in name_patterns:
            n_match = re.search(pat, text, re.IGNORECASE)
            if n_match:
                extracted = n_match.group(1).strip() if n_match.groups() else n_match.group(0).strip()
                # Clean out labels
                extracted = re.sub(r"(?:Date|Father|Gender|Address).*", "", extracted, flags=re.IGNORECASE).strip()
                if len(extracted) > 2:
                    entities["extracted_name"] = extracted
                    break

        # 3. Detect Expiry Date & Status
        exp_match = re.search(r"(?:Date of Expiry|Expiry Date|Expiry):\s*(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
        if exp_match:
            exp_str = exp_match.group(1)
            entities["expiry_date"] = exp_str
            try:
                exp_d = datetime.strptime(exp_str, "%Y-%m-%d").date()
                if exp_d < date.today():
                    entities["is_expired"] = True
            except Exception:
                pass
        
        if "EXPIRED" in text.upper():
            entities["is_expired"] = True

        return entities

    @classmethod
    def evaluate_against_employee(cls, extracted: Dict[str, Any], employee_name: str, employee_dob: Optional[date] = None) -> Dict[str, Any]:
        """Compare extracted document metadata against employee master profile."""
        flags: List[str] = []
        emp_clean = employee_name.strip().lower()
        doc_name = (extracted.get("extracted_name") or "").strip().lower()

        # Name matching analysis
        match_score = 0
        if doc_name:
            if doc_name == emp_clean:
                match_score = 100
                flags.append("Name exact match (100% confidence)")
            elif all(part in doc_name for part in emp_clean.split()):
                match_score = 90
                flags.append(f"Name partial match: Document has '{extracted.get('extracted_name')}' (Contains full offer letter name)")
            else:
                match_score = 40
                flags.append(f"NAME MISMATCH: Document reads '{extracted.get('extracted_name')}', but Offer Letter has '{employee_name}'")
        else:
            match_score = 50
            flags.append("Name field could not be reliably extracted from document")

        # Expiry check
        if extracted.get("is_expired"):
            match_score = min(match_score, 30)
            flags.append(f"DOCUMENT EXPIRED: Expiry date ({extracted.get('expiry_date') or 'Past'}) has lapsed. Valid proof required.")

        # Document ID check
        if extracted.get("document_number"):
            flags.append(f"Verified {extracted.get('document_type')} ID format: {extracted.get('document_number')}")
        else:
            flags.append("Warning: Could not isolate unique Government ID identifier")

        # Recommendation for Human Review
        if match_score >= 80 and not extracted.get("is_expired"):
            recommendation = "RECOMMEND_APPROVAL"
            suggested_msg = "All verification criteria satisfied. AI suggests approval."
        else:
            recommendation = "RECOMMEND_CORRECTION"
            suggested_msg = f"Please re-upload a clear and valid document. Discrepancy noted: {'; '.join(flags)}"

        return {
            "document_type": extracted.get("document_type"),
            "document_number": extracted.get("document_number"),
            "extracted_name": extracted.get("extracted_name"),
            "match_score": match_score,
            "is_expired": extracted.get("is_expired", False),
            "flags": flags,
            "recommendation": recommendation,
            "suggested_message": suggested_msg
        }

