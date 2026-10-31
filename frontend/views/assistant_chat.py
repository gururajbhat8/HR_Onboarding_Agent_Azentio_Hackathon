import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from src.database.session import SessionLocal, init_db
from src.database.repository import EmployeeRepository
from src.agents.policy_rag_agent import PolicyRAGAgent

def _fetch_employees():
    """Fetch candidate profiles for chat personalization."""
    init_db()
    with SessionLocal() as session:
        return EmployeeRepository.get_all_employees(session)

def _query_assistant(emp_id, query_text):
    """Run agent query."""
    init_db()
    with SessionLocal() as session:
        emp = EmployeeRepository.get_employee_by_id(session, emp_id)
        if not emp:
            return None
        return PolicyRAGAgent.ask(query_text, emp, session)

def render_assistant_chat():
    """Renders the Grounded AI Policy & Onboarding Copilot Chat View."""
    st.markdown("### 🤖 Azentio AI Policy & Onboarding Copilot")
    st.caption("Ask questions about your onboarding tasks, first-day arrangements, company policies, or leave rules. Answers are grounded in official handbooks with exact clause citations.")

    candidates = _fetch_employees()
    if not candidates:
        st.warning("No candidate records found. Please load candidates in Tab 1 first.")
        return

    # Profile Selector for Role & Location Personalization
    emp_map = {f"{c.full_name} — {c.role} ({c.department}, {c.location}) [Joins: {c.joining_date}]": c for c in candidates}
    selected_lbl = st.selectbox("Chatting as employee:", list(emp_map.keys()), key="chat_emp_select")
    current_emp = emp_map[selected_lbl]

    # Initialize chat history in session state per employee
    chat_key = f"messages_{current_emp.id}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = [
            {
                "role": "assistant",
                "content": f"Hello **{current_emp.full_name}**! Welcome to Azentio. I am your AI Onboarding Assistant. How can I help you today with your joining preparations or company policies?",
                "citations": []
            }
        ]

    # Quick Suggestion Pills for Instant Testing
    st.markdown("##### 💡 Suggested Questions (1-Click Test):")
    pills = [
        "Which documents do I need to submit before my joining date?",
        "How many casual leaves can I take during my probation period?",
        "Why is my laptop provisioning blocked and who is responsible?",
        "Where is the Bengaluru office located and what time should I arrive on Day 1?",
        "What is the medical insurance coverage for my family?"
    ]

    cols = st.columns(len(pills))
    clicked_pill = None
    for i, pill in enumerate(pills):
        with cols[i]:
            if st.button(pill, key=f"pill_{i}", use_container_width=True):
                clicked_pill = pill

    # Display Chat Messages
    st.markdown("---")
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state[chat_key]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("citations"):
                    cit_str = " • ".join([f"**{c['document']}** (*{c['section']}*)" for c in msg["citations"]])
                    st.markdown(f"""
                    <div style="background-color: #E6FBF5; border: 1px solid #00DF8F; border-radius: 8px; padding: 6px 12px; margin-top: 8px; font-size: 12px; color: #047857;">
                        📘 <strong>Official Policy Citation:</strong> {cit_str}
                    </div>
                    """, unsafe_allow_html=True)

    # Chat Input
    user_query = st.chat_input("Ask a question about onboarding, policies, benefits, or Day-1 logistics...")
    prompt_to_send = clicked_pill or user_query

    if prompt_to_send:
        # Add user query to chat history
        st.session_state[chat_key].append({"role": "user", "content": prompt_to_send, "citations": []})

        # Run Agent
        with st.spinner("Consulting official Azentio policy handbooks..."):
            res = _query_assistant(current_emp.id, prompt_to_send)

        if res:
            st.session_state[chat_key].append({
                "role": "assistant",
                "content": res["answer"],
                "citations": res.get("citations", [])
            })
        st.rerun()
