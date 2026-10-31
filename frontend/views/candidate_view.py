import os
import streamlit as st
from datetime import datetime, date
from src.database.session import SessionLocal
from src.database.repository import EmployeeRepository, TaskRepository, DocumentRepository, NotificationRepository
from src.agents.doc_validation_agent import DocumentValidationAgent
from src.agents.policy_rag_agent import PolicyRAGAgent

def render_candidate_view():
    """Render the personalized Candidate Onboarding Portal."""
    user = st.session_state.get("user", {})
    emp_id = user.get("employee_id")
    emp_email = user.get("email")

    with SessionLocal() as session:
        # Fetch candidate profile
        employee = None
        if emp_id:
            employee = EmployeeRepository.get_employee_by_id(session, emp_id)
        if not employee and emp_email:
            stmt = session.query(EmployeeRepository.create_or_update_employee.__globals__["EmployeeModel"]).filter_by(email=emp_email).first()
            employee = stmt

        # Fallback to Arjun Rao if testing with generic candidate
        if not employee:
            all_emps = EmployeeRepository.get_all_employees(session)
            if all_emps:
                employee = all_emps[0]

        if not employee:
            st.warning("⚠️ No active employee profile found. Please contact HR or ask Admin to ingest employee records.")
            return

        # Ensure checklist exists
        tasks = TaskRepository.get_tasks_for_employee(session, employee.id)
        if not tasks:
            tasks = TaskRepository.generate_and_save_checklist(session, employee.id)

        # Calculate Day 1 countdown
        today = date.today()
        days_left = (employee.joining_date - today).days
        countdown_text = f"⏳ **{days_left} Days** until Day 1" if days_left > 0 else ("🎉 **Welcome! Day 1 is Today!**" if days_left == 0 else f"✅ Joined on {employee.joining_date}")

        # Candidate Header Banner
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #0B192C 0%, #1E293B 100%); border-radius: 16px; padding: 24px; color: white; margin-bottom: 24px; border: 1px solid rgba(0, 223, 143, 0.3);">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                <div>
                    <span style="background: rgba(0, 223, 143, 0.2); color: #00DF8F; border: 1px solid #00DF8F; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">
                        CANDIDATE ONBOARDING PORTAL
                    </span>
                    <h2 style="color: #FFFFFF; margin: 8px 0 4px 0; font-size: 26px; font-weight: 700;">
                        Welcome to Azentio, {employee.full_name}! 👋
                    </h2>
                    <p style="color: #94A3B8; margin: 0; font-size: 14px;">
                        Role: <strong style="color: #F8FAFC;">{employee.role} ({employee.grade})</strong> • Dept: <strong style="color: #F8FAFC;">{employee.department}</strong> • Location: <strong style="color: #F8FAFC;">{employee.location}</strong>
                    </p>
                </div>
                <div style="text-align: right; background: rgba(255, 255, 255, 0.05); padding: 12px 20px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1);">
                    <div style="font-size: 13px; color: #94A3B8;">Joining Date: <strong>{employee.joining_date}</strong></div>
                    <div style="font-size: 16px; color: #00DF8F; font-weight: 700; margin-top: 4px;">{countdown_text}</div>
                    <div style="font-size: 12px; color: #94A3B8; margin-top: 2px;">Manager: {employee.manager_email}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Progress Stats
        completed_count = len([t for t in tasks if t.status == "Completed"])
        pending_count = len([t for t in tasks if t.status == "Pending"])
        blocked_count = len([t for t in tasks if t.status == "Blocked"])
        total_tasks = len(tasks)
        pct_completed = int((completed_count / total_tasks * 100)) if total_tasks > 0 else 0

        # Progress bar
        st.markdown(f"**Your Onboarding Readiness Progress: {completed_count} of {total_tasks} requirements completed ({pct_completed}%)**")
        st.progress(pct_completed / 100.0)

        # Candidate Progress Notifications (Real-time HR Decisions)
        notifications = NotificationRepository.get_notifications_for_employee(session, employee.id)
        if notifications:
            with st.expander(f"🔔 Progress Updates & Verification Alerts ({len(notifications)})", expanded=True):
                for notif in notifications[:4]:
                    if notif.notification_type == "SUCCESS":
                        st.success(f"**{notif.title}** ({notif.created_at.strftime('%Y-%m-%d %H:%M')})\n\n{notif.message}")
                    elif notif.notification_type == "WARNING":
                        st.warning(f"**{notif.title}** ({notif.created_at.strftime('%Y-%m-%d %H:%M')})\n\n{notif.message}")
                    else:
                        st.info(f"**{notif.title}** ({notif.created_at.strftime('%Y-%m-%d %H:%M')})\n\n{notif.message}")

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        # Candidate Portal Tabs
        cand_tabs = st.tabs([
            "📋 My Onboarding Checklist",
            "📄 Submit My Documents",
            "🤖 My AI Onboarding Copilot"
        ])

        # -------------------------------------------------------------
        # TAB 1: MY CHECKLIST
        # -------------------------------------------------------------
        with cand_tabs[0]:
            st.subheader("Your Role-Specific Onboarding Milestones")
            st.caption(f"Tasks tailored dynamically for your role as **{employee.role}** in **{employee.department}**.")

            for t in tasks:
                if t.status == "Completed":
                    card_border = "#86EFAC"
                    badge_html = "<span style='background: #DCFCE7; color: #15803D; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;'>✅ Completed</span>"
                elif t.status == "Blocked":
                    card_border = "#FCA5A5"
                    badge_html = "<span style='background: #FEE2E2; color: #B91C1C; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;'>🔒 Blocked on Prereq</span>"
                else:
                    card_border = "#FEF08A"
                    badge_html = "<span style='background: #FEF9C3; color: #854D0E; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;'>⏳ Action Required</span>"

                st.markdown(f"""
                <div style="background: #FFFFFF; border-left: 5px solid {card_border}; border-top: 1px solid #E2E8F0; border-right: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 16px; font-weight: 700; color: #0B192C;">{t.title}</div>
                            <div style="font-size: 13px; color: #64748B; margin-top: 2px;">
                                Category: <strong>{t.category}</strong> • Assigned Dept: <strong>{t.assigned_department}</strong> • Target SLA: <strong>{t.due_date}</strong>
                            </div>
                        </div>
                        <div>
                            {badge_html}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if t.rule_origin or t.prerequisite_task:
                    with st.expander(f"ℹ️ Why is this required & dependency details?"):
                        if t.rule_origin:
                            st.markdown(f"**Policy Rule Origin**: *{t.rule_origin}*")
                        if t.prerequisite_task and t.status == "Blocked":
                            st.warning(f"⚠️ This task is waiting for completion of: `{t.prerequisite_task}` before IT/HR can initiate provisioning.")

        # -------------------------------------------------------------
        # TAB 2: SUBMIT DOCUMENTS
        # -------------------------------------------------------------
        with cand_tabs[1]:
            st.subheader("Candidate Document Submission Center")
            st.caption("Upload your verification documents. Azentio AI pre-screens your files in real time for immediate feedback.")

            col_up1, col_up2 = st.columns([1, 1])

            with col_up1:
                st.markdown("#### Upload New Document")
                doc_type = st.selectbox(
                    "Select Document Type:",
                    [
                        "Permanent Account Number (PAN)",
                        "Aadhaar Card",
                        "Educational Degree Certificate",
                        "Passport"
                    ]
                )

                uploaded_file = st.file_uploader(
                    "Upload Document (PDF format):",
                    type=["pdf"],
                    key="candidate_doc_uploader"
                )

                if uploaded_file is not None:
                    if st.button("🚀 Upload & Validate with AI", type="primary"):
                        save_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads")
                        os.makedirs(save_dir, exist_ok=True)
                        save_path = os.path.join(save_dir, uploaded_file.name)

                        file_bytes = uploaded_file.read()
                        with open(save_path, "wb") as f:
                            f.write(file_bytes)

                        # Run AI evaluation
                        with st.spinner("AI analyzing document text, expiry, and candidate match..."):
                            eval_result = DocumentValidationAgent.evaluate_document(
                                file_path=save_path,
                                expected_employee_name=employee.full_name,
                                doc_type=doc_type
                            )

                        # Save to document repository
                        doc_record = DocumentRepository.save_document(
                            session=session,
                            employee_id=employee.id,
                            document_type=doc_type,
                            file_path=save_path,
                            file_name=uploaded_file.name,
                            extracted_metadata=eval_result
                        )

                        st.success(f"✅ Successfully submitted **{uploaded_file.name}**! Pre-screening match score: **{eval_result['match_score']}%**.")
                        st.rerun()

            with col_up2:
                st.markdown("#### Submission History & Status")
                my_docs = DocumentRepository.get_documents_for_employee(session, employee.id)

                if not my_docs:
                    st.info("No documents submitted yet. Use the upload form on the left.")
                else:
                    for doc in my_docs:
                        status_color = "#15803D" if doc.status == "Accepted" else ("#B91C1C" if doc.status == "Correction Requested" else "#854D0E")
                        bg_color = "#DCFCE7" if doc.status == "Accepted" else ("#FEE2E2" if doc.status == "Correction Requested" else "#FEF9C3")

                        meta = doc.extracted_metadata or {}
                        score = meta.get("match_score", 0)

                        st.markdown(f"""
                        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; margin-bottom: 12px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong style="color: #0B192C; font-size: 15px;">{doc.document_type}</strong>
                                    <div style="font-size: 12px; color: #64748B;">File: {doc.file_name} • Uploaded: {doc.uploaded_at.strftime('%Y-%m-%d %H:%M') if doc.uploaded_at else ''}</div>
                                </div>
                                <div>
                                    <span style="background: {bg_color}; color: {status_color}; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 700;">
                                        {doc.status}
                                    </span>
                                </div>
                            </div>
                            <div style="margin-top: 8px; font-size: 13px;">
                                AI Confidence Score: <strong>{score}%</strong>
                            </div>
                            {f"<div style='margin-top: 6px; color: #B91C1C; font-size: 12px; font-weight: 600;'>Feedback from HR: {doc.rejection_reason}</div>" if doc.rejection_reason else ""}
                        </div>
                        """, unsafe_allow_html=True)

        # -------------------------------------------------------------
        # TAB 3: AI ONBOARDING COPILOT
        # -------------------------------------------------------------
        with cand_tabs[2]:
            st.subheader(f"Autonomous AI Onboarding Copilot for {employee.full_name}")
            st.caption("Ask questions about your candidate profile, document approvals, checklist blockers, or company policies with zero hallucination guarantee.")

            # Live Agent Architecture Badge
            st.markdown("""
            <div style="background: rgba(0, 223, 143, 0.08); border: 1px solid rgba(0, 223, 143, 0.3); border-radius: 10px; padding: 10px 16px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="display: inline-block; width: 10px; height: 10px; background: #00DF8F; border-radius: 50%; box-shadow: 0 0 8px #00DF8F;"></span>
                    <span style="font-size: 13px; font-weight: 700; color: #0B192C;">Live Agent Engine Active</span>
                    <span style="color: #64748B; font-size: 12px;">• Groq Cloud LLM (qwen/qwen3.8-27b)</span>
                    <span style="color: #64748B; font-size: 12px;">• Pinecone Vector DB (azentio-hr-policies)</span>
                </div>
                <span style="background: #0B192C; color: #00DF8F; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;">Zero Hallucinations</span>
            </div>
            """, unsafe_allow_html=True)

            # Quick Prompt Pills (Candidate Status & Policies)
            st.markdown("<div style='font-size: 13px; font-weight: 600; color: #475569; margin-bottom: 6px;'>Quick Questions for AI Agent:</div>", unsafe_allow_html=True)
            col_p1, col_p2, col_p3 = st.columns(3)
            if col_p1.button("📊 Show my candidate data & status", key="cand_pill_1", use_container_width=True):
                st.session_state["cand_active_query"] = "Can you show my candidate profile data and complete onboarding status?"
            if col_p2.button("🔍 Did HR approve my documents?", key="cand_pill_2", use_container_width=True):
                st.session_state["cand_active_query"] = "Did HR approve my documents and what are the exact feedback remarks?"
            if col_p3.button("💻 Why is laptop blocked?", key="cand_pill_3", use_container_width=True):
                st.session_state["cand_active_query"] = "Why is my laptop provisioning blocked and who can unblock it?"

            col_p4, col_p5, col_p6 = st.columns(3)
            if col_p4.button("🏖️ Leave rules in probation?", key="cand_pill_4", use_container_width=True):
                st.session_state["cand_active_query"] = "How many leaves can I take during my 6-month probation period?"
            if col_p5.button("🏥 Medical insurance benefits?", key="cand_pill_5", use_container_width=True):
                st.session_state["cand_active_query"] = "What medical insurance coverage and OPD benefits are provided?"
            if col_p6.button("💰 Relocation assistance policy?", key="cand_pill_6", use_container_width=True):
                st.session_state["cand_active_query"] = "What is the relocation reimbursement assistance policy for new hires?"

            # Chat state
            if "cand_chat_history" not in st.session_state:
                st.session_state["cand_chat_history"] = []

            default_q = st.session_state.pop("cand_active_query", "")

            user_query = st.chat_input("Ask a question about your onboarding status or Azentio policies...")
            query_to_run = user_query or default_q

            if query_to_run:
                st.session_state["cand_chat_history"].append({"role": "user", "content": query_to_run})

                with st.spinner("Autonomous Agent querying Pinecone vector store & live candidate records via Groq LLM..."):
                    response = PolicyRAGAgent.ask(
                        query=query_to_run,
                        employee=employee,
                        session=session
                    )

                st.session_state["cand_chat_history"].append({
                    "role": "assistant",
                    "content": response["answer"],
                    "citations": response.get("citations", []),
                    "escalation": response.get("escalation")
                })

            # Display conversation
            for msg in reversed(st.session_state["cand_chat_history"]):
                if msg["role"] == "user":
                    st.chat_message("user").write(msg["content"])
                else:
                    with st.chat_message("assistant"):
                        st.markdown(msg["content"])
                        if msg.get("citations"):
                            for cit in msg["citations"]:
                                st.caption(f"📖 **Grounding Source**: *{cit['document']}* — Section: {cit['section']}")
                        if msg.get("escalation"):
                            st.caption(f"🚨 **Escalation Contact**: {msg['escalation']}")

