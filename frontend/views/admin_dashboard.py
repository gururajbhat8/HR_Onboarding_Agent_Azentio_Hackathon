import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import pandas as pd
from src.services.ingestion_service import IngestionService
from src.database.session import SessionLocal, init_db
from src.database.repository import EmployeeRepository, AuditRepository, UserRepository
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

def _fetch_users():
    """Fetch all system users."""
    init_db()
    with SessionLocal() as session:
        users = UserRepository.get_all_users(session)
        return [
            {
                "Username": u.username,
                "Role": u.role,
                "Full Name": u.full_name,
                "Email": u.email,
                "Created At": str(u.created_at)[:19] if u.created_at else "N/A"
            }
            for u in users
        ]

def render_admin_dashboard():
    """Renders the Admin Perspective Dashboard."""
    user = st.session_state.get("user", {})

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #0B192C 0%, #1E293B 100%); border-radius: 16px; padding: 22px 28px; color: white; margin-bottom: 24px; border: 1px solid rgba(0, 223, 143, 0.3);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div>
                <span style="background: rgba(0, 223, 143, 0.2); color: #00DF8F; border: 1px solid #00DF8F; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">
                    SYSTEM ADMINISTRATOR PORTAL
                </span>
                <h2 style="color: #FFFFFF; margin: 8px 0 4px 0; font-size: 26px; font-weight: 700;">
                    Enterprise Control Center 👋
                </h2>
                <p style="color: #94A3B8; margin: 0; font-size: 14px;">
                    Logged in as: <strong style="color: #00DF8F;">{user.get('full_name', 'System Administrator')} ({user.get('username', 'admin')})</strong> • Manage batch ingestion, dynamic recalculations, audit trails, and user roles.
                </p>
            </div>
            <div style="background: rgba(255, 255, 255, 0.05); padding: 10px 18px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1); text-align: right;">
                <span style="color: #00DF8F; font-size: 14px; font-weight: 700;">Admin Mode</span>
                <div style="color: #94A3B8; font-size: 12px;">Full Governance Access</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    admin_tabs = st.tabs([
        "📥 Batch Ingestion & Pipeline",
        "🔄 Dynamic Cascade Recalculation",
        "📜 Master Audit Trail",
        "👥 User Accounts & Access Control"
    ])

    # -------------------------------------------------------------
    # TAB 1: BATCH INGESTION & PIPELINE
    # -------------------------------------------------------------
    with admin_tabs[0]:
        st.markdown("### 📥 Candidate Data Ingestion & Validation")
        st.caption("Upload new-joiner records (CSV, Excel, JSON) or load pre-built synthetic datasets.")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("#### Upload Candidate Data")
            uploaded_file = st.file_uploader(
                "Choose a CSV, Excel (.xlsx) or JSON file",
                type=["csv", "xlsx", "json"],
                help="Supported formats: .csv, .xlsx, .json with mandatory fields: full_name, email, role, department, location, manager_email, joining_date",
                key="admin_file_uploader"
            )

            if uploaded_file is not None:
                content = uploaded_file.read()
                result = IngestionService.parse_file(content, uploaded_file.name)
                
                # Save valid records
                if result.valid_count > 0:
                    _save_employees(result.employees)
                st.session_state["last_ingestion"] = result
                st.success(f"Processed '{uploaded_file.name}' successfully! ({result.valid_count} valid, {result.error_count} errors)")

        with col2:
            st.markdown("#### Quick Enterprise Datasets")
            st.write("Load pre-configured enterprise datasets for instant evaluation:")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("📊 50-Employee Excel", use_container_width=True, help="Load 50 candidate records across all 6 departments"):
                    excel_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample_profiles", "candidates_50_employees.xlsx")
                    if os.path.exists(excel_path):
                        with open(excel_path, "rb") as f:
                            res = IngestionService.parse_file(f.read(), "candidates_50_employees.xlsx")
                        _save_employees(res.employees)
                        st.session_state["last_ingestion"] = res
                        st.success(f"Loaded {res.valid_count} candidates from Excel!")
                        st.rerun()

            with c2:
                if st.button("Load Valid JSON", use_container_width=True):
                    data_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample_profiles", "candidates.json")
                    with open(data_path, "rb") as f:
                        res = IngestionService.parse_file(f.read(), "candidates.json")
                    _save_employees(res.employees)
                    st.session_state["last_ingestion"] = res
                    st.rerun()

            if st.button("Load Invalid CSV (Error Validation Test)", use_container_width=True):
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
        st.markdown("#### 👥 Enterprise Candidate Ledger")
        saved_employees = _fetch_employees()

        if saved_employees:
            df_emps = pd.DataFrame(saved_employees)
            
            # Filtering controls
            f1, f2 = st.columns(2)
            with f1:
                dept_filter = st.multiselect("Filter by Department", options=list(df_emps["Department"].unique()), default=[], key="admin_dept_filter")
            with f2:
                loc_filter = st.multiselect("Filter by Location", options=list(df_emps["Location"].unique()), default=[], key="admin_loc_filter")

            filtered_df = df_emps
            if dept_filter:
                filtered_df = filtered_df[filtered_df["Department"].isin(dept_filter)]
            if loc_filter:
                filtered_df = filtered_df[filtered_df["Location"].isin(loc_filter)]

            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.info("No candidates ingested yet. Upload a file above or click '50-Employee Excel' to initialize.")

    # -------------------------------------------------------------
    # TAB 2: CASCADE RECALCULATION ENGINE
    # -------------------------------------------------------------
    with admin_tabs[1]:
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
        else:
            st.info("Ingest candidate records first to test dynamic recalculations.")

    # -------------------------------------------------------------
    # TAB 3: AUDIT TRAIL
    # -------------------------------------------------------------
    with admin_tabs[2]:
        st.markdown("### 📜 Enterprise Audit Trail Ledger")
        st.caption("Immutable transaction log tracking all date shifts, role re-alignments, and automated task modifications.")
        audit_entries = _fetch_audit_logs()
        if audit_entries:
            st.dataframe(pd.DataFrame(audit_entries), use_container_width=True)
        else:
            st.info("No schedule modifications logged yet.")

    # -------------------------------------------------------------
    # TAB 4: USER MANAGEMENT
    # -------------------------------------------------------------
    with admin_tabs[3]:
        st.markdown("### 👥 User Accounts & Role-Based Access")
        st.caption("Review existing user credentials in SQLite, add HR managers or candidate demo accounts.")

        users_list = _fetch_users()
        df_users = pd.DataFrame(users_list) if users_list else pd.DataFrame()

        # Stats metrics
        if not df_users.empty:
            admin_count = len(df_users[df_users["Role"] == "Admin"])
            hr_count = len(df_users[df_users["Role"] == "HR"])
            cand_count = len(df_users[df_users["Role"] == "Candidate"])

            u1, u2, u3 = st.columns(3)
            u1.metric("Admin Accounts", admin_count)
            u2.metric("HR Accounts", hr_count)
            u3.metric("Candidate Accounts", cand_count)

            st.markdown("#### Registered User Ledger")
            st.dataframe(df_users, use_container_width=True)

        # Form to add new HR or Candidate
        st.markdown("---")
        st.markdown("#### ➕ Provision New User Account")
        with st.form("admin_create_user_form"):
            cu_col1, cu_col2 = st.columns(2)
            with cu_col1:
                new_u_role = st.selectbox("Role:", ["HR", "Candidate"], help="Admin is 1 dedicated user; create additional HR or Candidate users")
                new_u_name = st.text_input("Username (login ID):", placeholder="e.g. hr3 or rohan.sharma")
                new_u_pass = st.text_input("Password:", value="hr123" if new_u_role == "HR" else "candidate123", type="password")
            with cu_col2:
                new_u_full = st.text_input("Full Name:", placeholder="e.g. Rohan Sharma")
                new_u_email = st.text_input("Email:", placeholder="e.g. rohan.sharma@azentio.com")

            submit_new_u = st.form_submit_button("Create User Account ✓", use_container_width=True)

            if submit_new_u:
                if not new_u_name or not new_u_pass or not new_u_full or not new_u_email:
                    st.error("Please fill in all user account fields.")
                else:
                    with SessionLocal() as session:
                        created = UserRepository.create_user(
                            session=session,
                            username=new_u_name,
                            password=new_u_pass,
                            role=new_u_role,
                            full_name=new_u_full,
                            email=new_u_email
                        )
                        st.success(f"✅ Successfully created {created.role} user: `{created.username}`!")
                        st.rerun()
