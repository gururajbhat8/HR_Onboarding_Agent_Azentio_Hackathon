import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import pandas as pd
from src.database.session import SessionLocal, init_db
from src.database.repository import EmployeeRepository, DocumentRepository, TaskRepository
from src.agents.doc_validation_agent import DocumentValidationAgent

def _fetch_candidates():
    """Fetch all candidates from database."""
    init_db()
    with SessionLocal() as session:
        return EmployeeRepository.get_all_employees(session)

def _process_and_save_doc(employee_id, filename, file_bytes):
    """Run AI evaluation and save document record."""
    init_db()
    with SessionLocal() as session:
        emp = EmployeeRepository.get_employee_by_id(session, employee_id)
        if not emp:
            return None

        # Save to uploads folder
        upload_dir = os.path.join(PROJECT_ROOT, "data", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{employee_id}_{filename}")
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # Agent extraction & evaluation
        text = DocumentValidationAgent.extract_text_from_bytes(file_bytes, filename)
        entities = DocumentValidationAgent.parse_entities(text)
        evaluation = DocumentValidationAgent.evaluate_against_employee(entities, emp.full_name)

        # Save to DB
        doc = DocumentRepository.save_document(
            session=session,
            employee_id=employee_id,
            document_type=evaluation["document_type"],
            file_name=filename,
            file_path=file_path,
            extracted_metadata=evaluation,
            status="Under Review"
        )
        return doc, evaluation

def _fetch_pending_reviews():
    """Fetch documents needing HR decision."""
    init_db()
    with SessionLocal() as session:
        docs = DocumentRepository.get_all_pending_documents(session)
        items = []
        for d in docs:
            emp = EmployeeRepository.get_employee_by_id(session, d.employee_id)
            items.append({
                "doc_id": d.id,
                "emp_name": emp.full_name if emp else "Unknown",
                "emp_role": emp.role if emp else "",
                "doc_type": d.document_type,
                "file_name": d.file_name,
                "status": d.status,
                "evaluation": d.extracted_metadata or {},
                "uploaded_at": str(d.uploaded_at)
            })
        return items

def _fetch_all_docs_for_emp(employee_id):
    """Fetch submission history for candidate."""
    init_db()
    with SessionLocal() as session:
        docs = DocumentRepository.get_documents_for_employee(session, employee_id)
        return [
            {
                "Document": d.document_type,
                "File": d.file_name,
                "Status": d.status,
                "Feedback / Reason": d.rejection_reason or "N/A",
                "Uploaded": str(d.uploaded_at)
            }
            for d in docs
        ]

def _review_doc(doc_id, action, reason=None):
    """Apply HR review decision."""
    init_db()
    with SessionLocal() as session:
        DocumentRepository.update_document_status(session, doc_id, action, reason)

def render_document_view():
    """Renders Candidate Document Portal and HR Human-in-the-Loop Review Console."""
    st.markdown("### 📄 Pre-Joining Document Verification & Human-in-the-Loop Review")
    st.caption("AI-powered OCR extraction and semantic profile cross-referencing with HR approval oversight.")

    candidates = _fetch_candidates()
    if not candidates:
        st.warning("No candidates found. Please load candidate data in Tab 1 first.")
        return

    subtabs = st.tabs(["📤 Candidate Document Portal", "🔍 HR Verification Queue (Human-in-the-Loop)"])

    # -------------------------------------------------------------
    # SUBTAB 1: CANDIDATE PORTAL
    # -------------------------------------------------------------
    with subtabs[0]:
        st.markdown("#### Candidate Upload Center")
        
        c_opts = {f"{c.full_name} ({c.role}, {c.location})": c.id for c in candidates}
        selected_cand_label = st.selectbox("I am logging in as:", list(c_opts.keys()))
        selected_cand_id = c_opts[selected_cand_label]
        selected_emp = next(c for c in candidates if c.id == selected_cand_id)

        col_up1, col_up2 = st.columns([3, 2])

        with col_up1:
            st.markdown("##### Upload Document (PDF / Image)")
            uploaded_file = st.file_uploader(
                "Select document proof (PAN, Aadhaar, Degree, Passport):",
                type=["pdf", "png", "jpg", "jpeg"],
                key="cand_doc_uploader"
            )

            if uploaded_file is not None:
                doc_bytes = uploaded_file.read()
                doc_res, eval_res = _process_and_save_doc(selected_cand_id, uploaded_file.name, doc_bytes)
                st.success(f"Uploaded '{uploaded_file.name}'! AI evaluation completed. Queued for HR Review.")
                st.session_state["last_eval"] = eval_res

        with col_up2:
            st.markdown("##### ⚡ 1-Click Sample Documents")
            st.caption("Test AI verification and mismatch detection instantly:")

            samples = [
                ("Valid PAN (Arjun Rao)", "PAN_Arjun_Rao_Valid.pdf"),
                ("Valid Aadhaar (Arjun Rao)", "Aadhaar_Arjun_Rao_Valid.pdf"),
                ("Valid Degree (Arjun Rao)", "Degree_Arjun_Rao_Valid.pdf"),
                ("⚠️ Mismatch PAN (Arjun K. Verma)", "PAN_Mismatch_Name.pdf"),
                ("⏰ Expired Passport Sample", "Passport_Expired_Sample.pdf")
            ]

            for btn_label, file_name in samples:
                if st.button(btn_label, use_container_width=True):
                    sample_path = os.path.join(PROJECT_ROOT, "data", "sample_documents", file_name)
                    if os.path.exists(sample_path):
                        with open(sample_path, "rb") as f:
                            doc_res, eval_res = _process_and_save_doc(selected_cand_id, file_name, f.read())
                        st.session_state["last_eval"] = eval_res
                        st.success(f"Processed sample '{file_name}'! Head over to the HR Verification Queue tab.")
                        st.rerun()

        # Display Candidate's Upload History
        st.markdown("---")
        st.markdown("##### 📋 Document Submission Tracker")
        cand_docs = _fetch_all_docs_for_emp(selected_cand_id)
        if cand_docs:
            st.dataframe(pd.DataFrame(cand_docs), use_container_width=True)
        else:
            st.info("No documents submitted yet. Use the upload box or 1-click test buttons above.")

    # -------------------------------------------------------------
    # SUBTAB 2: HR HUMAN-IN-THE-LOOP REVIEW QUEUE
    # -------------------------------------------------------------
    with subtabs[1]:
        st.markdown("#### 🛡️ HR Verification Console (Human-in-the-Loop)")
        st.caption("AI pre-screens documents and computes confidence scores. HR retains final approval authority.")

        pending_items = _fetch_pending_reviews()

        if not pending_items:
            st.info("🎉 Verification queue is clear! No documents pending HR review.")
        else:
            st.markdown(f"**{len(pending_items)} Document(s) Awaiting Review:**")

            for item in pending_items:
                ev = item["evaluation"]
                score = ev.get("match_score", 0)
                score_color = "#15803D" if score >= 80 else ("#C2410C" if score >= 50 else "#B91C1C")
                score_bg = "#DCFCE7" if score >= 80 else ("#FEF3C7" if score >= 50 else "#FEE2E2")

                with st.container():
                    st.markdown(f"""
                    <div style="background: #FFFFFF; border: 2px solid {'#86EFAC' if score >= 80 else '#FCA5A5'}; border-radius: 14px; padding: 18px; margin-bottom: 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="font-size: 18px; font-weight: 700; color: #0B192C;">{item['emp_name']}</span>
                                <span style="font-size: 14px; color: #64748B;">({item['emp_role']})</span>
                            </div>
                            <div style="background-color: {score_bg}; color: {score_color}; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 14px;">
                                AI MATCH SCORE: {score}%
                            </div>
                        </div>
                        <div style="margin-top: 10px; font-size: 14px; color: #334155;">
                            Document: <strong>{item['doc_type']}</strong> • File: <code>{item['file_name']}</code> • Uploaded: {item['uploaded_at'][:19]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    c_left, c_right = st.columns([3, 2])
                    with c_left:
                        st.markdown("**AI Extraction & Verification Findings:**")
                        flags = ev.get("flags", [])
                        for flg in flags:
                            icon = "✅" if ("match" in flg.lower() or "verified" in flg.lower()) and "mismatch" not in flg.lower() else "⚠️"
                            st.write(f"{icon} {flg}")

                        ext_name = ev.get("extracted_name") or "N/A"
                        doc_num = ev.get("document_number") or "N/A"
                        st.markdown(f"• **Extracted Name on Document:** `{ext_name}`")
                        st.markdown(f"• **Extracted Identifier Number:** `{doc_num}`")

                    with c_right:
                        st.markdown("**Human-in-the-Loop Decision:**")
                        
                        # AI Recommended message
                        corr_msg = st.text_area(
                            "Feedback / Correction Reason (editable):",
                            value=ev.get("suggested_message", ""),
                            key=f"reason_{item['doc_id']}",
                            height=90
                        )

                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            if st.button("Approve & Accept ✔", key=f"appr_{item['doc_id']}", use_container_width=True):
                                _review_doc(item['doc_id'], "Accepted")
                                st.success("Document Accepted! Corresponding checklist task marked Completed and downstream items unblocked.")
                                st.rerun()
                        with btn_col2:
                            if st.button("Request Correction ❌", key=f"corr_{item['doc_id']}", use_container_width=True):
                                _review_doc(item['doc_id'], "Correction Requested", corr_msg)
                                st.warning("Correction requested and feedback logged for candidate.")
                                st.rerun()

                    st.markdown("<hr style='margin: 16px 0; border: none; border-top: 1px solid #CBD5E1;'/>", unsafe_allow_html=True)

