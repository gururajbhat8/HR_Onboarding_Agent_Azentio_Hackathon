import os
from datetime import date, timedelta
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Output paths
DATA_DIR = os.path.join(os.path.dirname(__file__), "sample_profiles")
os.makedirs(DATA_DIR, exist_ok=True)
EXCEL_PATH = os.path.join(DATA_DIR, "candidates_50_employees.xlsx")
CSV_PATH = os.path.join(DATA_DIR, "candidates_50_employees.csv")

# Master data for generation
FIRST_NAMES = [
    "Aarav", "Aditi", "Akash", "Ananya", "Arjun", "Bhavna", "Chetan", "Deepa",
    "Dev", "Divya", "Gaurav", "Harsh", "Isha", "Ishaan", "Karan", "Kavya",
    "Madhav", "Manish", "Meera", "Mohit", "Naveen", "Neha", "Nikhil", "Nisha",
    "Pranav", "Pooja", "Rahul", "Rhea", "Rishi", "Ritu", "Rohan", "Sanjana",
    "Saurabh", "Shreya", "Siddharth", "Simran", "Sneha", "Tanvi", "Tarun", "Uma",
    "Varun", "Vidya", "Vikram", "Yash", "Zoya", "Aamir", "Farhan", "Kareena",
    "Kabir", "Zara"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Mehta", "Iyer", "Rao", "Nair", "Kulkarni",
    "Deshmukh", "Pillai", "Chopra", "Reddy", "Gupta", "Bose", "Menon", "Joshi",
    "Bhat", "Sen", "Bhattacharya", "Malhotra", "Kapoor", "Mukherjee", "Agarwal", "Saxena",
    "Das", "Pandey", "Mishra", "Trivedi", "Banerjee", "Singh", "Fernandes", "Dsouza",
    "Shetty", "Hegde", "Kamath", "Pai", "Prabhu", "Somani", "Jain", "Bansal",
    "Mittal", "Goyal", "Singhania", "Tiwari", "Dubey", "Shukla", "Pandit", "Ranganathan",
    "Subramanian", "Swaminathan"
]

DEPARTMENTS_CONFIG = [
    {
        "department": "Engineering",
        "manager_email": "ananya.roy@azentio.com",
        "roles": [
            ("Senior Software Engineer", "L4"),
            ("Software Engineer", "L2"),
            ("Frontend Developer", "L2"),
            ("Backend Architect", "L5"),
            ("DevOps Engineer", "L3"),
            ("QA Automation Engineer", "L2"),
            ("Data Engineer", "L3"),
            ("Machine Learning Engineer", "L3")
        ]
    },
    {
        "department": "Product",
        "manager_email": "priya.sharma@azentio.com",
        "roles": [
            ("Product Manager", "L3"),
            ("Senior Product Manager", "L4"),
            ("UI/UX Designer", "L2"),
            ("Lead Product Designer", "L4"),
            ("Product Operations Specialist", "L2")
        ]
    },
    {
        "department": "Finance",
        "manager_email": "suresh.nair@azentio.com",
        "roles": [
            ("Financial Analyst", "L2"),
            ("Senior Accountant", "L3"),
            ("Billing Specialist", "L1"),
            ("Finance Manager", "L4")
        ]
    },
    {
        "department": "Information Technology",
        "manager_email": "rahul.verma@azentio.com",
        "roles": [
            ("Cloud Infrastructure Engineer", "L3"),
            ("IT Support Specialist", "L2"),
            ("Systems Administrator", "L3"),
            ("Network Security Engineer", "L4")
        ]
    },
    {
        "department": "Human Resources",
        "manager_email": "priya.sharma@azentio.com",
        "roles": [
            ("HR Specialist", "L2"),
            ("Talent Acquisition Lead", "L3"),
            ("HR Operations Executive", "L2")
        ]
    },
    {
        "department": "Compliance",
        "manager_email": "deepak.mehta@azentio.com",
        "roles": [
            ("Compliance Officer", "L3"),
            ("Risk Analyst", "L2"),
            ("Regulatory Affairs Specialist", "L3")
        ]
    }
]

LOCATIONS = ["Bengaluru", "Mumbai", "Pune", "Chennai", "Hyderabad", "Dubai", "Singapore"]

def generate_records():
    records = []
    base_date = date(2026, 11, 10)
    
    for i in range(50):
        fn = FIRST_NAMES[i % len(FIRST_NAMES)]
        ln = LAST_NAMES[i % len(LAST_NAMES)]
        full_name = f"{fn} {ln}"
        clean_name = f"{fn.lower()}.{ln.lower()}"
        
        # Dept distribution
        dept_cfg = DEPARTMENTS_CONFIG[i % len(DEPARTMENTS_CONFIG)]
        dept = dept_cfg["department"]
        mgr = dept_cfg["manager_email"]
        role_tuple = dept_cfg["roles"][i % len(dept_cfg["roles"])]
        role_name, grade = role_tuple
        
        loc = LOCATIONS[i % len(LOCATIONS)]
        
        emp_code = f"AZ-EMP-{200 + i + 1:03d}"
        email = f"{clean_name}@candidate.com"
        
        phone_prefix = "+971 50" if loc == "Dubai" else ("+65 9" if loc == "Singapore" else "+91 98")
        phone = f"{phone_prefix}{i:02d} {10000 + i * 137}"
        
        joining = base_date + timedelta(days=(i * 2) % 45)
        
        records.append({
            "employee_code": emp_code,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "role": role_name,
            "grade": grade,
            "department": dept,
            "location": loc,
            "manager_email": mgr,
            "joining_date": joining.strftime("%Y-%m-%d"),
            "onboarding_status": "Initiated"
        })
    return records

def create_excel_with_styling(records):
    df = pd.DataFrame(records)
    
    # Save CSV copy
    df.to_csv(CSV_PATH, index=False)
    
    # Save styled Excel
    with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="New_Joiners", index=False)
        worksheet = writer.sheets["New_Joiners"]
        
        # Azentio Brand Colors
        # Navy: 0B192C, Mint: 00DF8F
        header_fill = PatternFill(start_color="0B192C", end_color="0B192C", fill_type="solid")
        header_font = Font(name="Segoe UI", size=11, bold=True, color="00DF8F")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
        thin_border = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0")
        )
        
        # Style headers
        for col_idx in range(1, len(df.columns) + 1):
            cell = worksheet.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
            cell.border = thin_border
            worksheet.row_dimensions[1].height = 28
            
        # Style data rows (alternating light fill)
        alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
        row_font = Font(name="Segoe UI", size=10, color="1E293B")
        
        for row_idx in range(2, len(df) + 2):
            worksheet.row_dimensions[row_idx].height = 20
            fill = alt_fill if row_idx % 2 == 0 else white_fill
            for col_idx in range(1, len(df.columns) + 1):
                cell = worksheet.cell(row=row_idx, column=col_idx)
                cell.fill = fill
                cell.font = row_font
                cell.border = thin_border
                if col_idx in [1, 6, 10, 11]:  # code, grade, date, status
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")
                    
        # Auto-adjust column width
        for col in worksheet.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                max_len = max(max_len, len(val_str))
            worksheet.column_dimensions[col_letter].width = max(max_len + 4, 12)

    print(f"[OK] Successfully created Excel file with {len(records)} records at:\n  {EXCEL_PATH}")
    print(f"[OK] Successfully created CSV backup at:\n  {CSV_PATH}")

if __name__ == "__main__":
    records = generate_records()
    create_excel_with_styling(records)
