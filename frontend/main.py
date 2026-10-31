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
# UN-AUTHENTICATED: RENDER ENTERPRISE LOGIN PORTAL
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
            Azentio Build Labs Hackathon
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_login_view()
    st.stop()

# -------------------------------------------------------------------------
# AUTHENTICATED: RENDER PRODUCTION HEADER & PERSPECTIVE
# -------------------------------------------------------------------------
role = current_user.get("role", "Admin")
name = current_user.get("full_name", "User")
email = current_user.get("email", "")

role_icon = "🛡️" if role == "Admin" else ("💼" if role == "HR" else "👤")
portal_title = f"{role.upper()} PORTAL"

top_col1, top_col2 = st.columns([7, 3])

with top_col1:
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 14px; padding: 4px 0;">
        <span style="font-size: 26px; font-weight: 800; color: #0B192C;">azentio<span style="color: #00DF8F;">.ai</span></span>
        <span style="background: rgba(11, 25, 44, 0.08); border: 1px solid rgba(11, 25, 44, 0.15); color: #0B192C; padding: 5px 14px; border-radius: 14px; font-size: 13px; font-weight: 700;">
            {role_icon} {portal_title}
        </span>
    </div>
    """, unsafe_allow_html=True)

with top_col2:
    col_u_info, col_u_btn = st.columns([2, 1])
    with col_u_info:
        st.markdown(f"""
        <div style="text-align: right; padding-top: 2px;">
            <div style="font-size: 14px; color: #0B192C; font-weight: 700;">{name}</div>
            <div style="font-size: 12px; color: #64748B;">{email}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_u_btn:
        if st.button("Sign Out 🚪", key="sign_out_btn", use_container_width=True):
            st.session_state.clear()
            st.rerun()

st.markdown("<hr style='margin: 10px 0 22px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

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
