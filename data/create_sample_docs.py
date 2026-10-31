import os

def create_simple_pdf(filepath: str, title: str, fields: dict):
    """Generates a valid, readable PDF file containing structured text fields."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Build text stream
    lines = [f"--- {title.upper()} ---", ""]
    for k, v in fields.items():
        lines.append(f"{k}: {v}")
    lines.append("")
    lines.append("CONFIDENTIAL - AZENTIO ONBOARDING VERIFICATION")

    # Construct simple PDF 1.4
    content_lines = []
    y = 700
    for line in lines:
        content_lines.append(f"BT /F1 12 Tf 50 {y} Td ({line}) Tj ET")
        y -= 25
    stream_data = "\n".join(content_lines).encode("latin1")

    pdf_parts = [
        b"%PDF-1.4\n",
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
        f"4 0 obj\n<< /Length {len(stream_data)} >>\nstream\n".encode("latin1"),
        stream_data,
        b"\nendstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        b"xref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n0000000234 00000 n \n0000000350 00000 n \n",
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n440\n%%EOF\n"
    ]

    with open(filepath, "wb") as f:
        for part in pdf_parts:
            f.write(part)
    print(f"Created: {filepath}")

def generate_all_samples():
    docs = [
        ("data/sample_documents/PAN_Arjun_Rao_Valid.pdf", "Income Tax Department - PAN Card", {
            "Permanent Account Number": "ABCDE1234F",
            "Name": "Arjun Rao",
            "Father Name": "Ramesh Rao",
            "Date of Birth": "1994-08-15",
            "Document Type": "Permanent Account Number (PAN)"
        }),
        ("data/sample_documents/Aadhaar_Arjun_Rao_Valid.pdf", "Unique Identification Authority of India - Aadhaar", {
            "Aadhaar Number": "9876 5432 1098",
            "Full Name": "Arjun Rao",
            "Gender": "Male",
            "Date of Birth": "1994-08-15",
            "Address": "No 42, 4th Cross, Indiranagar, Bengaluru, Karnataka - 560038"
        }),
        ("data/sample_documents/Degree_Arjun_Rao_Valid.pdf", "University Degree Certificate", {
            "Candidate Name": "Arjun Rao",
            "Degree": "Bachelor of Technology in Computer Science & Engineering",
            "Institution": "National Institute of Technology",
            "Passing Year": "2016",
            "Grade": "First Class with Distinction"
        }),
        ("data/sample_documents/PAN_Mismatch_Name.pdf", "Income Tax Department - PAN Card (Discrepancy)", {
            "Permanent Account Number": "XYZPK9988G",
            "Name": "Arjun Kumar Verma", # Intentionally mismatched name to show mismatch detection!
            "Father Name": "Suresh Verma",
            "Date of Birth": "1994-08-15",
            "Document Type": "PAN Card"
        }),
        ("data/sample_documents/Passport_Expired_Sample.pdf", "Passport (Expired Sample)", {
            "Passport Number": "Z1234567",
            "Name": "Arjun Rao",
            "Date of Issue": "2014-01-10",
            "Date of Expiry": "2024-01-09", # Expired date to show expiry validation!
            "Status": "EXPIRED"
        })
    ]

    for path, title, fields in docs:
        create_simple_pdf(path, title, fields)

if __name__ == "__main__":
    generate_all_samples()

