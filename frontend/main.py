import sys
import os

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from src.database.session import init_db
from frontend.views.login_view import render_login_view
from frontend.views.admin_dashboard import render_admin_dashboard
from frontend.views.hr_view import render_hr_view
from frontend.views.candidate_view import render_candidate_view

# Initialize database tables and seed default users
init_db()

# Configure page settings
st.set_page_config(
    page_title="Azentio HR Onboarding Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load Azentio Enterprise CSS
css_path = os.path.join(os.path.dirname(__file__), "styles", "azentio_theme.css")
if os.path.exists(css_path):
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Authentication check
current_user = st.session_state.get("user")

# -------------------------------------------------------------------------
# UN-AUTHENTICATED: RENDER LOGIN PORTAL
# -------------------------------------------------------------------------
if not current_user:
    # Render Brand Header
    st.markdown("""
    <div class="azentio-navbar">
        <div class="azentio-logo-badge">
            <div class="azentio-logo-text">azentio<span>.ai</span></div>
            <div class="azentio-pill">ENTERPRISE ONBOARDING</div>
        </div>
        <div style="color: #94A3B8; font-size: 13px;">
            Azentio Build Labs Hackathon • Multi-Role Authentication
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_login_view()
    st.stop()

# -------------------------------------------------------------------------
# AUTHENTICATED: RENDER TOP BAR & PERSPECTIVE
# -------------------------------------------------------------------------
role = current_user.get("role", "Admin")
name = current_user.get("full_name", "User")
uname = current_user.get("username", "")

role_icon = "🛡️" if role == "Admin" else ("💼" if role == "HR" else "👤")
role_color = "#00DF8F" if role == "Admin" else ("#38BDF8" if role == "HR" else "#FBBF24")

# Top Header with User Info, Perspective Switcher (for Hackathon Judges), and Sign Out
top_col1, top_col2, top_col3 = st.columns([4, 4, 2])

with top_col1:
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 12px; padding: 6px 0;">
        <span style="font-size: 24px; font-weight: 800; color: #0B192C;">azentio<span style="color: #00DF8F;">.ai</span></span>
        <span style="background: rgba(11, 25, 44, 0.08); border: 1px solid rgba(11, 25, 44, 0.15); color: #0B192C; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 700;">
            {role_icon} {role.upper()} PORTAL
        </span>
    </div>
    """, unsafe_allow_html=True)

with top_col2:
    # Fast perspective switcher for evaluation convenience
    perspectives = ["Admin", "HR", "Candidate"]
    curr_idx = perspectives.index(role) if role in perspectives else 0
    switch_to = st.selectbox(
        "Perspective Switcher (Demo Mode):",
        options=perspectives,
        index=curr_idx,
        format_func=lambda x: f"🛡️ Admin Dashboard" if x == "Admin" else (f"💼 HR Operations Console" if x == "HR" else "👤 Candidate Portal"),
        key="perspective_switcher_dropdown"
    )
    if switch_to != role:
        # Switch role seamlessly
        if switch_to == "Admin":
            st.session_state["user"] = {"id": "demo-admin", "username": "admin", "full_name": "System Administrator", "role": "Admin", "email": "admin@azentio.com"}
        elif switch_to == "HR":
            st.session_state["user"] = {"id": "demo-hr", "username": "hr1", "full_name": "Priya Sharma", "role": "HR", "email": "priya.sharma@azentio.com"}
        else:
            st.session_state["user"] = {"id": "demo-cand", "username": "arjun.rao", "full_name": "Arjun Rao", "role": "Candidate", "email": "arjun.rao@candidate.com"}
        st.rerun()

with top_col3:
    st.markdown(f"<div style='text-align: right; font-size: 13px; color: #64748B; margin-top: 4px;'><strong>{name}</strong></div>", unsafe_allow_html=True)
    if st.button("Sign Out 🚪", key="sign_out_btn", use_container_width=True):
        st.session_state.pop("user", None)
        st.session_state.pop("demo_role", None)
        st.session_state.pop("demo_user", None)
        st.session_state.pop("demo_pass", None)
        st.rerun()

st.markdown("<hr style='margin: 12px 0 20px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# PERSPECTIVE ROUTING
# -------------------------------------------------------------------------
if role == "Admin":
    render_admin_dashboard()
elif role == "HR":
    render_hr_view()
elif role == "Candidate":
    render_candidate_view()
else:
    st.error(f"Unrecognized role '{role}'. Please sign out and sign in again.")
