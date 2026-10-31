import streamlit as st
from src.database.session import SessionLocal, init_db
from src.database.repository import UserRepository

def render_login_view():
    """Render the enterprise production login portal."""
    init_db()

    st.markdown("""
    <div style="text-align: center; margin-top: 20px; margin-bottom: 25px;">
        <div style="font-size: 34px; font-weight: 800; color: #0B192C; letter-spacing: -0.5px;">
            azentio<span style="color: #00DF8F;">.ai</span>
        </div>
        <p style="color: #64748B; font-size: 15px; margin-top: 4px;">
            Enterprise Onboarding & Workforce Lifecycle Platform
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_center, col_r = st.columns([1, 2, 1])

    with col_center:
        role_options = ["Admin", "HR", "Candidate"]

        selected_role = st.radio(
            "Select Portal Access:",
            options=role_options,
            index=0,
            horizontal=True,
            format_func=lambda x: f"🛡️ Admin" if x == "Admin" else (f"💼 HR Operations" if x == "HR" else f"👤 Candidate")
        )

        with st.container(border=True):
            if selected_role == "Admin":
                st.markdown("<div style='font-size: 18px; font-weight: 700; color: #0B192C;'>Administrator Login</div>", unsafe_allow_html=True)
                st.caption("Access the batch ingestion engine, dynamic cascade recalculations, and system audit trail.")
                user_placeholder = "Enter admin username or email"

            elif selected_role == "HR":
                st.markdown("<div style='font-size: 18px; font-weight: 700; color: #0B192C;'>HR Operations Login</div>", unsafe_allow_html=True)
                st.caption("Access the document verification queue (HITL), candidate pipeline, and SLA management.")
                user_placeholder = "e.g. hr1 or priya.sharma@azentio.com"

            else:
                st.markdown("<div style='font-size: 18px; font-weight: 700; color: #0B192C;'>Candidate Portal Login</div>", unsafe_allow_html=True)
                st.caption("Access your personalized onboarding checklist, document uploads, and policy assistant.")
                user_placeholder = "e.g. arjun.rao or arjun.rao@candidate.com"

            with st.form("azentio_enterprise_login_form"):
                input_username = st.text_input("Username or Corporate Email:", placeholder=user_placeholder)
                input_password = st.text_input("Password:", placeholder="••••••••", type="password")
                
                st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
                submitted = st.form_submit_button(f"Sign In as {selected_role} →", use_container_width=True)

                if submitted:
                    if not input_username.strip() or not input_password.strip():
                        st.error("Please enter both username/email and password.")
                    else:
                        with SessionLocal() as session:
                            user = UserRepository.authenticate(
                                session=session,
                                username=input_username.strip(),
                                password=input_password.strip(),
                                expected_role=selected_role
                            )

                            if user:
                                st.session_state["user"] = {
                                    "id": user.id,
                                    "username": user.username,
                                    "full_name": user.full_name,
                                    "role": user.role,
                                    "email": user.email,
                                    "employee_id": user.employee_id
                                }
                                st.rerun()
                            else:
                                st.error(f"Authentication failed: Invalid credentials for {selected_role} access.")
