import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import pandas as pd
from src.services.ingestion_service import IngestionService
from src.database.session import SessionLocal, init_db
from src.database.repository import EmployeeRepository, AuditRepository
from src.core.recalculation_engine import RecalculationEngine
from src.api.schemas.employee import VALID_DEPARTMENTS, VALID_LOCATIONS

def _save_employees(employees):
    """Save parsed employees to SQLite/PostgreSQL."""
    init_db()
    with SessionLocal() as session:
        for emp in employees:
            EmployeeRepository.create_or_update_employee(session, emp)

def _fetch_employees():
    """Fetch all saved employees from database."""
    init_db()
    with SessionLocal() as session:
        emps = EmployeeRepository.get_all_employees(session)
        return [
            {
                "Code": e.employee_code,
                "Name": e.full_name,
                "Role": e.role,
                "Grade": e.grade,
                "Department": e.department,
                "Location": e.location,
                "Manager": e.manager_email,
                "Joining Date": str(e.joining_date),
                "Status": e.onboarding_status
            }
            for e in emps
        ]

def _fetch_raw_employees():
    """Fetch raw employee model objects."""
    init_db()
    with SessionLocal() as session:
        return EmployeeRepository.get_all_employees(session)

def _recalculate_date(employee_id, new_date, reason):
    """Run dynamic date shift recalculation."""
    init_db()
    with SessionLocal() as session:
        return RecalculationEngine.recalculate_joining_date(session, employee_id, new_date, reason)

def _recalculate_role(employee_id, new_role, new_dept, new_loc, reason):
    """Run dynamic role change recalculation."""
    init_db()
    with SessionLocal() as session:
        return RecalculationEngine.recalculate_role_or_department(session, employee_id, new_role, new_dept, new_loc, reason)

def _fetch_audit_logs():
    """Fetch audit trail."""
    init_db()
    with SessionLocal() as session:
        logs = AuditRepository.get_all_audit_logs(session)
        return [
            {
                "Timestamp": str(l.timestamp)[:19],
                "Action": l.action_type,
                "Old Value": l.old_value,
                "New Value": l.new_value,
                "Reason / Details": l.reason
            }
            for l in logs
        ]

def render_admin_dashboard():
    """Renders the HR Ingestion & Candidate Management Dashboard."""
    st.markdown("### 📥 Employee Data Ingestion & Validation")
    st.caption("Upload new-joiner records (CSV, Excel, JSON) or load pre-built synthetic datasets.")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("#### Upload Candidate Data")
        uploaded_file = st.file_uploader(
            "Choose a CSV, Excel or JSON file",
            type=["csv", "xlsx", "json"],
            help="Supported formats: .csv, .xlsx, .json with mandatory fields: full_name, email, role, department, location, manager_email, joining_date"
        )

        if uploaded_file is not None:
            content = uploaded_file.read()
            result = IngestionService.parse_file(content, uploaded_file.name)
            
            # Save valid records
            if result.valid_count > 0:
                _save_employees(result.employees)
            st.session_state["last_ingestion"] = result
            st.success(f"Processed '{uploaded_file.name}' successfully!")

    with col2:
        st.markdown("#### Quick Synthetic Demo")
        st.write("Load pre-configured enterprise datasets for instant testing:")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Load Valid Data", use_container_width=True):
                data_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample_profiles", "candidates.json")
                with open(data_path, "rb") as f:
                    res = IngestionService.parse_file(f.read(), "candidates.json")
                _save_employees(res.employees)
                st.session_state["last_ingestion"] = res
                st.rerun()

        with c2:
            if st.button("Load Invalid (Test)", use_container_width=True):
                err_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample_profiles", "candidates_with_errors.csv")
                with open(err_path, "rb") as f:
                    res = IngestionService.parse_file(f.read(), "candidates_with_errors.csv")
                if res.valid_count > 0:
                    _save_employees(res.employees)
                st.session_state["last_ingestion"] = res
                st.rerun()

    # Ingestion Summary Metrics
    if "last_ingestion" in st.session_state:
        res = st.session_state["last_ingestion"]
        st.markdown("---")
        st.markdown("#### Latest Ingestion Validation Report")
        
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f"""
            <div class="azentio-metric-card">
                <div class="azentio-metric-label">Total Records Evaluated</div>
                <div class="azentio-metric-value">{res.total_records}</div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="azentio-metric-card" style="border-color: #86EFAC;">
                <div class="azentio-metric-label" style="color: #15803D;">Valid Records Saved</div>
                <div class="azentio-metric-value" style="color: #15803D;">{res.valid_count}</div>
            </div>
            """, unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
            <div class="azentio-metric-card" style="border-color: #FCA5A5;">
                <div class="azentio-metric-label" style="color: #B91C1C;">Validation Errors Caught</div>
                <div class="azentio-metric-value" style="color: #B91C1C;">{res.error_count}</div>
            </div>
            """, unsafe_allow_html=True)

        if res.error_count > 0:
            with st.expander(f"⚠️ View {res.error_count} Validation Errors Detected", expanded=True):
                err_rows = [
                    {"Row #": e.row_number, "Field": e.field or "N/A", "Error Description": e.message}
                    for e in res.errors
                ]
                st.dataframe(pd.DataFrame(err_rows), use_container_width=True)

    # Ingested Candidates Table
    st.markdown("---")
    st.markdown("#### 👥 Onboarding Pipeline Database")
    saved_employees = _fetch_employees()

    if saved_employees:
        df_emps = pd.DataFrame(saved_employees)
        
        # Filtering controls
        f1, f2 = st.columns(2)
        with f1:
            dept_filter = st.multiselect("Filter by Department", options=list(df_emps["Department"].unique()), default=[])
        with f2:
            loc_filter = st.multiselect("Filter by Location", options=list(df_emps["Location"].unique()), default=[])

        filtered_df = df_emps
        if dept_filter:
            filtered_df = filtered_df[filtered_df["Department"].isin(dept_filter)]
        if loc_filter:
            filtered_df = filtered_df[filtered_df["Location"].isin(loc_filter)]

        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.info("No candidates ingested yet. Upload a file above or click 'Load Valid Data' to initialize.")

    # -------------------------------------------------------------
    # SCENARIO 4: DYNAMIC CHANGE MANAGEMENT & CASCADE ENGINE
    # -------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🔄 Dynamic Change Management & Recalculation Engine")
    st.caption("Azentio Cascade Engine: When joining dates shift or roles are revised, tasks and SLAs are automatically recalculated without manual HR intervention.")

    raw_candidates = _fetch_raw_employees()
    if raw_candidates:
        cand_map = {f"{c.full_name} ({c.role}, {c.department}) [Joins: {c.joining_date}]": c for c in raw_candidates}
        selected_cand_lbl = st.selectbox("Select Candidate to Modify:", list(cand_map.keys()), key="recalc_cand_select")
        c_target = cand_map[selected_cand_lbl]

        col_chg1, col_chg2 = st.columns(2)

        # Action 1: Joining Date Shift
        with col_chg1:
            st.markdown(f"#### 📅 Shift Joining Date")
            st.markdown(f"Current Joining Date: **`{c_target.joining_date}`**")
            new_date = st.date_input("Select New Target Date:", value=c_target.joining_date, key=f"dt_pick_{c_target.id}")
            shift_reason = st.text_input("Reason for Date Modification:", value="Candidate notice period extended by 10 days", key="dt_reason")

            if st.button("Apply Date Shift & Cascade Recalculate ⚡", use_container_width=True):
                if new_date != c_target.joining_date:
                    res = _recalculate_date(c_target.id, new_date, shift_reason)
                    st.success(f"✅ Recalculated! Shifted {res['tasks_updated_count']} task deadlines by {res['days_shifted']:+d} days.")
                    with st.expander("View Recalculated Task Deadlines", expanded=True):
                        st.dataframe(pd.DataFrame(res["updated_tasks"]), use_container_width=True)
                    st.rerun()
                else:
                    st.warning("Please choose a different date than the current joining date.")

        # Action 2: Role / Department Revision
        with col_chg2:
            st.markdown(f"#### 💼 Revise Role & Department")
            st.markdown(f"Current: **`{c_target.role}`** in **`{c_target.department}`**")
            new_role_title = st.text_input("New Role Title:", value="Lead Systems Architect", key="role_title_input")
            
            dept_idx = VALID_DEPARTMENTS.index(c_target.department) if c_target.department in VALID_DEPARTMENTS else 0
            new_dept_val = st.selectbox("New Department:", VALID_DEPARTMENTS, index=dept_idx, key="role_dept_input")
            
            loc_idx = VALID_LOCATIONS.index(c_target.location) if c_target.location in VALID_LOCATIONS else 0
            new_loc_val = st.selectbox("New Location:", VALID_LOCATIONS, index=loc_idx, key="role_loc_input")
            role_reason = st.text_input("Reason for Role Change:", value="Promoted to Lead Systems Architect prior to Day 1", key="role_reason")

            if st.button("Apply Role Re-alignment ⚡", use_container_width=True):
                res = _recalculate_role(c_target.id, new_role_title, new_dept_val, new_loc_val, role_reason)
                st.success(f"✅ Role updated to '{new_role_title}'! Injected {len(res['added_tasks'])} new tasks and pruned {len(res['removed_tasks'])} obsolete tasks.")
                st.rerun()

    # Immutable Audit Trail Table
    st.markdown("---")
    st.markdown("#### 📜 Enterprise Audit Trail Ledger")
    st.caption("Immutable transaction log tracking all date shifts, role re-alignments, and automated task modifications.")
    audit_entries = _fetch_audit_logs()
    if audit_entries:
        st.dataframe(pd.DataFrame(audit_entries), use_container_width=True)
    else:
        st.info("No schedule modifications logged yet.")
