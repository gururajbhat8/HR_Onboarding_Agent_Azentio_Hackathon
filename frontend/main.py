import sys
import os

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from frontend.views.admin_dashboard import render_admin_dashboard
from frontend.views.checklist_view import render_checklist_view
from frontend.views.document_view import render_document_view
from frontend.views.assistant_chat import render_assistant_chat

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

# Render Azentio Header Navbar
st.markdown("""
<div class="azentio-navbar">
    <div class="azentio-logo-badge">
        <div class="azentio-logo-text">azentio<span>.ai</span></div>
        <div class="azentio-pill">HR ONBOARDING AGENT</div>
    </div>
    <div style="color: #94A3B8; font-size: 14px;">
        Build Labs Day 2026 • Exora Business Park
    </div>
</div>
""", unsafe_allow_html=True)

# Navigation Tabs
tabs = st.tabs([
    "📥 Ingestion & Candidate Pipeline",
    "📋 Dynamic Role Checklists",
    "📄 Document Verification & OCR",
    "🤖 Grounded Policy Copilot"
])

with tabs[0]:
    render_admin_dashboard()

with tabs[1]:
    render_checklist_view()

with tabs[2]:
    render_document_view()

with tabs[3]:
    render_assistant_chat()

