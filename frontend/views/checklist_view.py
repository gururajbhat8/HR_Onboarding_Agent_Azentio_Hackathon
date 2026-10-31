import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import pandas as pd
from datetime import datetime
from src.database.session import SessionLocal, init_db
from src.database.repository import EmployeeRepository, TaskRepository

def _fetch_employees():
    """Fetch candidate list for selection."""
    init_db()
    with SessionLocal() as session:
        return EmployeeRepository.get_all_employees(session)

def _get_or_generate_tasks(employee_id):
    """Retrieve or generate checklist for employee."""
    init_db()
    with SessionLocal() as session:
        tasks = TaskRepository.get_tasks_for_employee(session, employee_id)
        if not tasks:
            tasks = TaskRepository.generate_and_save_checklist(session, employee_id)
        return [
            {
                "id": t.id,
                "code": t.task_code,
                "title": t.title,
                "category": t.category,
                "department": t.assigned_department,
                "owner": t.owner_email,
                "due_date": str(t.due_date),
                "offset": t.relative_offset_days,
                "status": t.status,
                "rule_origin": t.rule_origin,
                "prerequisite": t.prerequisite_task,
                "completed_at": str(t.completed_at) if t.completed_at else None
            }
            for t in tasks
        ]

def _update_task(task_id, new_status):
    """Update task status in DB."""
    init_db()
    with SessionLocal() as session:
        TaskRepository.update_task_status(session, task_id, new_status)

def render_checklist_view():
    """Renders the Dynamic Role-Based Checklist Engine View."""
    st.markdown("### 📋 Dynamic Onboarding Checklist Generator")
    st.caption("Role-tailored checklist compiled by the Rule Engine with transparent rule-origin explanations and SLA due dates.")

    employees = _fetch_employees()
    if not employees:
        st.warning("No candidates found in database. Please ingest candidates in Tab 1 first.")
        return

    # Candidate selection
    options = {
        f"{e.full_name} — {e.role} ({e.department}, {e.location}) [Joins: {e.joining_date}]": e.id
        for e in employees
    }
    selected_label = st.selectbox("Select Candidate to view/generate checklist:", list(options.keys()))
    selected_emp_id = options[selected_label]
    selected_emp = next(e for e in employees if e.id == selected_emp_id)

    # Fetch tasks
    tasks = _get_or_generate_tasks(selected_emp_id)

    # Progress Summary Metrics
    total = len(tasks)
    completed = sum(1 for t in tasks if t["status"] == "Completed")
    blocked = sum(1 for t in tasks if t["status"] == "Blocked")
    pending = sum(1 for t in tasks if t["status"] == "Pending")
    pct = int((completed / total * 100)) if total > 0 else 0

    st.markdown("---")
    st.markdown(f"#### Onboarding Readiness for **{selected_emp.full_name}** ({selected_emp.role})")
    
    # Progress Bar
    st.progress(pct / 100, text=f"Overall Day-1 Readiness: {pct}% ({completed}/{total} tasks completed)")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="azentio-metric-card">
            <div class="azentio-metric-label">Total Requirements</div>
            <div class="azentio-metric-value">{total}</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="azentio-metric-card" style="border-color: #86EFAC;">
            <div class="azentio-metric-label" style="color: #15803D;">Completed</div>
            <div class="azentio-metric-value" style="color: #15803D;">{completed}</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="azentio-metric-card" style="border-color: #FED7AA;">
            <div class="azentio-metric-label" style="color: #C2410C;">Pending Action</div>
            <div class="azentio-metric-value" style="color: #C2410C;">{pending}</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="azentio-metric-card" style="border-color: #FCA5A5;">
            <div class="azentio-metric-label" style="color: #B91C1C;">Blocked on Prereq</div>
            <div class="azentio-metric-value" style="color: #B91C1C;">{blocked}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Generated Role-Specific Checklist")

    # Render each checklist task as an interactive card
    for t in tasks:
        # Category tag color
        cat_color = {
            "Document": "#0284C7",
            "IT": "#059669",
            "Compliance": "#D97706",
            "Policy": "#7C3AED"
        }.get(t["category"], "#475569")

        # Status tag
        status_bg = {
            "Completed": "#DCFCE7",
            "Pending": "#FEF3C7",
            "Blocked": "#FEE2E2"
        }.get(t["status"], "#F1F5F9")
        
        status_fg = {
            "Completed": "#15803D",
            "Pending": "#B45309",
            "Blocked": "#B91C1C"
        }.get(t["status"], "#334155")

        offset_str = f"T{t['offset']}d" if t["offset"] < 0 else (f"T+{t['offset']}d" if t["offset"] > 0 else "Day 1 (T+0)")

        with st.container():
            c1, c2, c3 = st.columns([5, 2, 2])
            with c1:
                st.markdown(f"""
                <div style="font-weight: 700; font-size: 16px; color: #0B192C;">
                    <span style="color: {cat_color}; font-weight: 600;">[{t['category'].upper()}]</span> {t['title']}
                </div>
                <div style="font-size: 13px; color: #64748B; margin-top: 2px;">
                    Assigned: <strong>{t['department']}</strong> ({t['owner']}) • Due: <strong>{t['due_date']} ({offset_str})</strong>
                </div>
                <div style="background-color: #F8FAFC; border-left: 3px solid #00DF8F; padding: 6px 12px; margin-top: 8px; border-radius: 4px; font-size: 12px; color: #334155;">
                    💡 <strong>Rule Origin:</strong> {t['rule_origin']}
                    {f" • <em>Requires prerequisite: <code>{t['prerequisite']}</code></em>" if t['prerequisite'] else ""}
                </div>
                """, unsafe_allow_html=True)

            with c2:
                st.markdown(f"""
                <div style="text-align: center; margin-top: 10px;">
                    <span style="background-color: {status_bg}; color: {status_fg}; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 13px;">
                        ● {t['status'].upper()}
                    </span>
                </div>
                """, unsafe_allow_html=True)

            with c3:
                # 1-Click Status toggle to test unblocking
                if t["status"] == "Pending":
                    if st.button("Mark Done ✔", key=f"btn_done_{t['id']}", use_container_width=True):
                        _update_task(t["id"], "Completed")
                        st.rerun()
                elif t["status"] == "Completed":
                    if st.button("Revert ↺", key=f"btn_rev_{t['id']}", use_container_width=True):
                        _update_task(t["id"], "Pending")
                        st.rerun()
                elif t["status"] == "Blocked":
                    st.caption("🔒 Locked until prerequisite is approved")

            st.markdown("<hr style='margin: 14px 0; border: none; border-top: 1px solid #E2E8F0;'/>", unsafe_allow_html=True)

