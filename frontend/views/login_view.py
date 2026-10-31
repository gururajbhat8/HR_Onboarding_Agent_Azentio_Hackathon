import streamlit as st
from src.database.session import SessionLocal, init_db
from src.database.repository import UserRepository, EmployeeRepository

def render_login_view():
    """Render the Azentio role-based authentication portal."""
    init_db()

    st.markdown("""
    <div style="text-align: center; margin-top: 10px; margin-bottom: 25px;">
        <h1 style="color: #0B192C; font-weight: 800; font-size: 32px; margin-bottom: 6px;">
            Azentio Onboarding Portal
        </h1>
        <p style="color: #64748B; font-size: 15px;">
            Autonomous Multi-Perspective Lifecycle Management • Choose your role to sign in
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Centered container for login card
    col_l, col_center, col_r = st.columns([1, 2, 1])

    with col_center:
        # Quick Demo Login Banner for hackathon judges
        with st.expander("🔑 Quick Demo Credentials (1-Click Fill)", expanded=True):
            st.markdown("<small style='color: #64748B;'>Click any role below to pre-populate credentials for evaluation:</small>", unsafe_allow_html=True)
            col_d1, col_d2, col_d3 = st.columns(3)
            
            if col_d1.button("🛡️ Admin", use_container_width=True, help="Username: admin | Pass: admin123"):
                st.session_state["demo_role"] = "Admin"
                st.session_state["demo_user"] = "admin"
                st.session_state["demo_pass"] = "admin123"
                st.rerun()

            if col_d2.button("💼 HR Team", use_container_width=True, help="Username: hr1 | Pass: hr123"):
                st.session_state["demo_role"] = "HR"
                st.session_state["demo_user"] = "hr1"
                st.session_state["demo_pass"] = "hr123"
                st.rerun()

            if col_d3.button("👤 Candidate", use_container_width=True, help="Username: arjun.rao | Pass: candidate123"):
                st.session_state["demo_role"] = "Candidate"
                st.session_state["demo_user"] = "arjun.rao"
                st.session_state["demo_pass"] = "candidate123"
                st.rerun()

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        # Retrieve any demo prefill
        demo_role = st.session_state.get("demo_role", "Admin")
        demo_user = st.session_state.get("demo_user", "admin")
        demo_pass = st.session_state.get("demo_pass", "admin123")

        role_options = ["Admin", "HR", "Candidate"]
        default_index = role_options.index(demo_role) if demo_role in role_options else 0

        # Tabbed login interface for the 3 perspectives
        selected_role = st.radio(
            "Select Portal Perspective:",
            options=role_options,
            index=default_index,
            horizontal=True,
            format_func=lambda x: f"🛡️ Admin Portal" if x == "Admin" else (f"💼 HR Operations" if x == "HR" else f"👤 Candidate Portal")
        )

        st.markdown("<div style='background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 16px; padding: 24px; box-shadow: 0 4px 16px rgba(0,0,0,0.04); margin-top: 10px;'>", unsafe_allow_html=True)

        if selected_role == "Admin":
            st.info("🛡️ **Admin Portal Access**: Ingest candidate batches, trigger cascade recalculations, manage users, and view system audit trails.")
            username_val = demo_user if demo_role == "Admin" else "admin"
            password_val = demo_pass if demo_role == "Admin" else "admin123"

        elif selected_role == "HR":
            st.info("💼 **HR Operations Access**: Review document submissions in the HITL console, track candidate readiness, and manage task blockers.")
            username_val = demo_user if demo_role == "HR" else "hr1"
            password_val = demo_pass if demo_role == "HR" else "hr123"

        else: # Candidate
            st.info("👤 **Candidate Portal Access**: View your personalized onboarding checklist, upload required documents, and chat with the Grounded Policy Copilot.")
            username_val = demo_user if demo_role == "Candidate" else "arjun.rao"
            password_val = demo_pass if demo_role == "Candidate" else "candidate123"

        # Login Form
        with st.form("azentio_login_form"):
            input_username = st.text_input("Username or Corporate Email:", value=username_val)
            input_password = st.text_input("Password:", value=password_val, type="password")
            submitted = st.form_submit_button(f"Sign In as {selected_role} →", use_container_width=True)

            if submitted:
                if not input_username or not input_password:
                    st.error("Please enter both username and password.")
                else:
                    with SessionLocal() as session:
                        user = UserRepository.authenticate(
                            session=session,
                            username=input_username,
                            password=input_password,
                            expected_role=selected_role
                        )

                        if user:
                            # Save authenticated user in session state
                            st.session_state["user"] = {
                                "id": user.id,
                                "username": user.username,
                                "full_name": user.full_name,
                                "role": user.role,
                                "email": user.email,
                                "employee_id": user.employee_id
                            }
                            st.success(f"Welcome, {user.full_name}! Redirecting to {user.role} Dashboard...")
                            st.rerun()
                        else:
                            st.error(f"Invalid credentials for {selected_role} role. Please check username/password or use the Quick Demo buttons above.")

        st.markdown("</div>", unsafe_allow_html=True)
