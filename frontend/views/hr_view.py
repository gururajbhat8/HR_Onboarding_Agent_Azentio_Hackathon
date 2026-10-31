import streamlit as st
import pandas as pd
from datetime import datetime
from src.database.session import SessionLocal
from src.database.repository import EmployeeRepository, TaskRepository, DocumentRepository
from src.agents.policy_rag_agent import PolicyRAGAgent

def render_hr_view():
    """Render the HR Operations & Verification Console perspective."""
    user = st.session_state.get("user", {})

    with SessionLocal() as session:
        employees = EmployeeRepository.get_all_employees(session)
        pending_docs = DocumentRepository.get_all_pending_documents(session)

        # Aggregate Metrics
        total_candidates = len(employees)
        ready_count = 0
        blocked_candidates = 0

        for emp in employees:
            tasks = TaskRepository.get_tasks_for_employee(session, emp.id)
            if tasks:
                if all(t.status == "Completed" for t in tasks):
                    ready_count += 1
                if any(t.status == "Blocked" for t in tasks):
                    blocked_candidates += 1

        # HR Header Banner
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #0B192C 0%, #1E293B 100%); border-radius: 16px; padding: 22px 28px; color: white; margin-bottom: 24px; border: 1px solid rgba(0, 223, 143, 0.3);">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div>
                    <span style="background: rgba(0, 223, 143, 0.2); color: #00DF8F; border: 1px solid #00DF8F; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">
                        HR OPERATIONS CONSOLE (HITL)
                    </span>
                    <h2 style="color: #FFFFFF; margin: 8px 0 4px 0; font-size: 26px; font-weight: 700;">
                        Welcome back, {user.get('full_name', 'HR Lead')} 👋
                    </h2>
                    <p style="color: #94A3B8; margin: 0; font-size: 14px;">
                        Manage candidate document verification, unblock cross-functional dependencies, and track Day-1 enterprise readiness.
                    </p>
                </div>
                <div style="background: rgba(255, 255, 255, 0.05); padding: 12px 20px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1); text-align: right;">
                    <div style="font-size: 12px; color: #94A3B8;">Awaiting Document Review</div>
                    <div style="font-size: 24px; color: #00DF8F; font-weight: 700;">{len(pending_docs)} Pending</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # High-level Metrics Cards
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Candidates", total_candidates)
        m2.metric("Pending Doc Reviews", len(pending_docs), delta=f"{len(pending_docs)} awaiting HR" if pending_docs else "All verified", delta_color="inverse")
        m3.metric("Blocked on Prereqs", blocked_candidates, delta=f"{blocked_candidates} at risk" if blocked_candidates else "None", delta_color="inverse")
        m4.metric("100% Day-1 Ready", ready_count, delta=f"{(ready_count/total_candidates*100):.0f}% ready" if total_candidates > 0 else "0%")

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        hr_tabs = st.tabs([
            "🛡️ Document Verification Queue (HITL)",
            "📋 Candidate Pipeline & Checklists",
            "🤖 HR Policy & SLA Copilot"
        ])

        # -------------------------------------------------------------
        # TAB 1: HR VERIFICATION CONSOLE (HITL)
        # -------------------------------------------------------------
        with hr_tabs[0]:
            st.subheader("Human-in-the-Loop Document Verification Queue")
            st.caption("AI pre-screens uploaded candidate proofs and highlights discrepancies or expiry. HR retains final compliance authority.")

            if not pending_docs:
                st.success("🎉 All candidate documents have been reviewed! No items pending in the verification queue.")
            else:
                st.info(f"Showing **{len(pending_docs)}** document(s) requiring review. Approving an identity document automatically completes the onboarding requirement and unblocks IT Laptop provisioning.")

                for doc in pending_docs:
                    emp = EmployeeRepository.get_employee_by_id(session, doc.employee_id)
                    emp_name = emp.full_name if emp else "Unknown Candidate"
                    emp_role = emp.role if emp else "Role N/A"

                    meta = doc.extracted_metadata or {}
                    score = meta.get("match_score", 0)
                    findings = meta.get("findings", [])
                    extracted = meta.get("extracted", {})

                    score_color = "#15803D" if score >= 80 else ("#B45309" if score >= 50 else "#B91C1C")
                    score_bg = "#DCFCE7" if score >= 80 else ("#FEF3C7" if score >= 50 else "#FEE2E2")
                    score_border = "#86EFAC" if score >= 80 else ("#FCD34D" if score >= 50 else "#FCA5A5")

                    with st.container():
                        st.markdown(f"""
                        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 18px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
                            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #F1F5F9; padding-bottom: 10px; margin-bottom: 12px;">
                                <div>
                                    <span style="font-size: 17px; font-weight: 700; color: #0B192C;">{emp_name}</span>
                                    <span style="color: #64748B; font-size: 13px; margin-left: 8px;">({emp_role})</span>
                                    <div style="font-size: 12px; color: #94A3B8; margin-top: 2px;">
                                        Document: <strong>{doc.document_type}</strong> • File: <code>{doc.file_name}</code> • Uploaded: {doc.uploaded_at.strftime('%Y-%m-%d %H:%M') if doc.uploaded_at else ''}
                                    </div>
                                </div>
                                <div>
                                    <span style="background: {score_bg}; color: {score_color}; border: 1px solid {score_border}; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 13px;">
                                        AI MATCH SCORE: {score}%
                                    </span>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        c_left, c_right = st.columns([1, 1])

                        with c_left:
                            st.markdown("**AI Extraction & Verification Findings:**")
                            if findings:
                                for f in findings:
                                    if "✅" in f:
                                        st.markdown(f"<span style='color: #15803D;'>{f}</span>", unsafe_allow_html=True)
                                    elif "⚠️" in f:
                                        st.markdown(f"<span style='color: #B45309; font-weight: 600;'>{f}</span>", unsafe_allow_html=True)
                                    elif "❌" in f:
                                        st.markdown(f"<span style='color: #B91C1C; font-weight: 600;'>{f}</span>", unsafe_allow_html=True)
                                    else:
                                        st.markdown(f)
                            else:
                                st.caption("No specific findings extracted.")

                            if extracted:
                                st.markdown("<div style='margin-top: 8px;'>", unsafe_allow_html=True)
                                if "name" in extracted and extracted["name"]:
                                    st.markdown(f"• **Extracted Name on Document**: `{extracted['name']}`")
                                if "identifier" in extracted and extracted["identifier"]:
                                    st.markdown(f"• **Extracted Identifier**: `{extracted['identifier']}`")
                                if "expiry_date" in extracted and extracted["expiry_date"]:
                                    st.markdown(f"• **Document Expiry**: `{extracted['expiry_date']}`")
                                st.markdown("</div>", unsafe_allow_html=True)

                        with c_right:
                            st.markdown("**Human-in-the-Loop Decision:**")
                            default_rejection = "; ".join([f for f in findings if "❌" in f or "⚠️" in f])
                            feedback = st.text_area(
                                "Feedback / Correction Reason (editable):",
                                value=default_rejection or "Document verified per Azentio Hiring Policy v2.4",
                                key=f"hr_feedback_{doc.id}",
                                height=80
                            )

                            b_col1, b_col2 = st.columns(2)
                            if b_col1.button("Approve & Accept ✓", key=f"approve_{doc.id}", type="primary", use_container_width=True):
                                DocumentRepository.update_document_status(
                                    session=session,
                                    doc_id=doc.id,
                                    new_status="Accepted",
                                    rejection_reason=feedback or "Document verified per Azentio Hiring Policy v2.4",
                                    verified_by=user.get("full_name", "HR Operations")
                                )
                                st.success(f"✅ Approved {doc.document_type} for {emp_name}. Synced to Pinecone Vector DB and notified candidate!")
                                st.rerun()

                            if b_col2.button("Request Correction ❌", key=f"reject_{doc.id}", use_container_width=True):
                                DocumentRepository.update_document_status(
                                    session=session,
                                    doc_id=doc.id,
                                    new_status="Correction Requested",
                                    rejection_reason=feedback,
                                    verified_by=user.get("full_name", "HR Operations")
                                )
                                st.warning(f"⚠️ Requested correction for {emp_name}. Synced to Pinecone Vector DB and notified candidate!")
                                st.rerun()

                        st.markdown("<hr style='margin: 16px 0; border: none; border-top: 1px dashed #CBD5E1;'>", unsafe_allow_html=True)

            # -------------------------------------------------------------
            # BOTTOM DECISION HISTORY LEDGER TABLE
            # -------------------------------------------------------------
            st.markdown("---")
            st.markdown("#### 📜 Verification & Decision History Ledger")
            st.caption("Live audit log of reviewed candidate documents. All decisions and remarks are synchronized with Pinecone Vector DB and candidate notifications.")

            reviewed_docs = DocumentRepository.get_reviewed_documents_history(session)
            if reviewed_docs:
                history_rows = []
                for rd in reviewed_docs:
                    remp = EmployeeRepository.get_employee_by_id(session, rd.employee_id)
                    history_rows.append({
                        "Candidate Name": remp.full_name if remp else "N/A",
                        "Role / Dept": f"{remp.role} ({remp.department})" if remp else "N/A",
                        "Document Type": rd.document_type,
                        "Decision Status": "✅ Accepted" if rd.status == "Accepted" else "⚠️ Correction Requested",
                        "Decision Remarks / Reason": rd.rejection_reason or "Verified per Azentio Hiring Policy v2.4",
                        "Reviewed Timestamp": rd.verified_at.strftime("%Y-%m-%d %H:%M") if rd.verified_at else "N/A",
                        "Vector Sync Status": "⚡ Synced to Pinecone",
                        "File Name": rd.file_name
                    })
                st.dataframe(pd.DataFrame(history_rows), use_container_width=True)
            else:
                st.info("No documents reviewed yet. Newly approved or rejected documents will appear in this history table immediately.")

        # -------------------------------------------------------------
        # TAB 2: PIPELINE & CHECKLISTS
        # -------------------------------------------------------------
        with hr_tabs[1]:
            st.subheader("Candidate Pipeline & Role Checklists")
            st.caption("Inspect live tasks, track bottlenecks, and view unblocking cascades across all candidates.")

            if not employees:
                st.info("No candidates in the system. Use the Admin portal to ingest candidates.")
            else:
                emp_options = {f"{e.full_name} ({e.role} - {e.department})": e.id for e in employees}
                selected_label = st.selectbox("Select Candidate to Inspect:", options=list(emp_options.keys()))
                sel_emp_id = emp_options[selected_label]
                selected_emp = EmployeeRepository.get_employee_by_id(session, sel_emp_id)

                emp_tasks = TaskRepository.get_tasks_for_employee(session, sel_emp_id)
                if not emp_tasks:
                    emp_tasks = TaskRepository.generate_and_save_checklist(session, sel_emp_id)

                tc1, tc2, tc3 = st.columns(3)
                c_comp = len([t for t in emp_tasks if t.status == "Completed"])
                c_pend = len([t for t in emp_tasks if t.status == "Pending"])
                c_block = len([t for t in emp_tasks if t.status == "Blocked"])

                tc1.metric("Completed Tasks", c_comp)
                tc2.metric("Pending Tasks", c_pend)
                tc3.metric("Blocked Tasks", c_block)

                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

                for t in emp_tasks:
                    badge_style = "background: #DCFCE7; color: #15803D;" if t.status == "Completed" else ("background: #FEE2E2; color: #B91C1C;" if t.status == "Blocked" else "background: #FEF9C3; color: #854D0E;")
                    st.markdown(f"""
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong>{t.title}</strong>
                            <div style="font-size: 12px; color: #64748B;">Category: {t.category} • Owner: {t.owner_email} • Due: {t.due_date}</div>
                        </div>
                        <div>
                            <span style="{badge_style} padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;">{t.status}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # -------------------------------------------------------------
        # TAB 3: HR POLICY & CANDIDATE COPILOT
        # -------------------------------------------------------------
        with hr_tabs[2]:
            st.subheader("Autonomous HR Copilot & Candidate Data Intelligence")
            st.caption("Ask questions about candidate verification status, onboarding bottlenecks, or query company policy handbooks with live LLM inference.")

            # Live Agent Architecture Badge
            st.markdown("""
            <div style="background: rgba(0, 223, 143, 0.08); border: 1px solid rgba(0, 223, 143, 0.3); border-radius: 10px; padding: 10px 16px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="display: inline-block; width: 10px; height: 10px; background: #00DF8F; border-radius: 50%; box-shadow: 0 0 8px #00DF8F;"></span>
                    <span style="font-size: 13px; font-weight: 700; color: #0B192C;">Live Agent Engine Active</span>
                    <span style="color: #64748B; font-size: 12px;">• Groq Cloud LLM (openai/gpt-oss-120b)</span>
                    <span style="color: #64748B; font-size: 12px;">• Pinecone Vector DB (azentio-hr-policies)</span>
                </div>
                <span style="background: #0B192C; color: #00DF8F; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;">Zero Hallucinations</span>
            </div>
            """, unsafe_allow_html=True)

            # Candidate Context Selector for HR
            emp_map = {f"{e.full_name} ({e.role} - {e.department})": e for e in employees}
            selected_emp_key = st.selectbox(
                "Focus Candidate Context (or leave default for general inquiries):",
                options=list(emp_map.keys()) if emp_map else ["No candidates loaded"],
                key="hr_agent_emp_select"
            )
            focused_emp = emp_map.get(selected_emp_key) if emp_map else None

            # Quick Prompt Pills for HR
            hr_p1, hr_p2, hr_p3, hr_p4 = st.columns(4)
            if hr_p1.button("📊 Candidate Status & Data", key="hr_pill_1", use_container_width=True):
                st.session_state["hr_active_query"] = f"What is the complete onboarding status and document verification state for {focused_emp.full_name if focused_emp else 'the selected candidate'}?"
            if hr_p2.button("⚠️ Blockers & Bottlenecks", key="hr_pill_2", use_container_width=True):
                st.session_state["hr_active_query"] = f"Which tasks are currently blocked for {focused_emp.full_name if focused_emp else 'this candidate'} and what is required to unblock them?"
            if hr_p3.button("🏖️ Probation Leave Rules", key="hr_pill_3", use_container_width=True):
                st.session_state["hr_active_query"] = "What is the policy for leave entitlements during the 6-month probation period?"
            if hr_p4.button("🏥 Medical Insurance Policy", key="hr_pill_4", use_container_width=True):
                st.session_state["hr_active_query"] = "What are the group medical health insurance coverage limits and family benefits?"

            # HR Chat State
            if "hr_chat_history" not in st.session_state:
                st.session_state["hr_chat_history"] = []

            default_hr_q = st.session_state.pop("hr_active_query", "")
            hr_user_query = st.chat_input("Ask HR Copilot about candidate status or company policies...", key="hr_copilot_input")
            query_to_run_hr = hr_user_query or default_hr_q

            if query_to_run_hr and focused_emp:
                st.session_state["hr_chat_history"].append({"role": "user", "content": query_to_run_hr})

                with st.spinner("HR Copilot consulting live candidate database and Pinecone vector store..."):
                    resp = PolicyRAGAgent.ask(query=query_to_run_hr, employee=focused_emp, session=session)

                st.session_state["hr_chat_history"].append({
                    "role": "assistant",
                    "content": resp["answer"],
                    "citations": resp.get("citations", []),
                    "escalation": resp.get("escalation")
                })

            # Render Chat History
            for msg in reversed(st.session_state["hr_chat_history"]):
                if msg["role"] == "user":
                    st.chat_message("user").write(msg["content"])
                else:
                    with st.chat_message("assistant"):
                        st.markdown(msg["content"])
                        if msg.get("citations"):
                            for c in msg["citations"]:
                                st.caption(f"📖 **Source Citation**: *{c['document']}* — Section: {c['section']}")
                        if msg.get("escalation"):
                            st.caption(f"🚨 **Escalation Path**: {msg['escalation']}")

