import os
import re
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from src.database.models import EmployeeModel, TaskModel
from src.database.repository import TaskRepository, DocumentRepository
from src.services.vector_store import VectorStoreService

load_dotenv()

class PolicyRAGAgent:
    """Autonomous AI HR Assistant providing grounded policy answers, candidate data inspection, and onboarding progress."""

    @classmethod
    def ask(
        cls,
        query: str,
        employee: EmployeeModel,
        session: Session
    ) -> Dict[str, Any]:
        """Main agent routing entry point. Intelligently routes between Candidate Data/Status Engine and Policy RAG."""
        q_lower = query.lower()

        # 1. Candidate status, profile data, documents, approvals, or blocker queries
        candidate_data_keywords = [
            "status", "progress", "candidate data", "my data", "profile", "onboarding status",
            "approved", "rejected", "correction", "feedback", "remarks", "pan", "aadhaar", 
            "passport", "degree", "verification", "did hr", "has hr", "my doc", "my submission",
            "checklist", "laptop", "blocked", "provisioning", "prerequisite", "which document",
            "what document", "my task", "milestone", "who is my manager"
        ]
        if any(k in q_lower for k in candidate_data_keywords):
            return cls._handle_candidate_status_and_data_query(query, employee, session)

        # 2. Otherwise route to Grounded Policy RAG
        return cls._handle_policy_query(query, employee)

    @classmethod
    def _handle_candidate_status_and_data_query(
        cls,
        query: str,
        employee: EmployeeModel,
        session: Session
    ) -> Dict[str, Any]:
        """Answer queries about candidate profile data, onboarding status, document approvals, and task blockers using live DB & LLM."""
        from datetime import date
        today = date.today()
        days_left = (employee.joining_date - today).days if employee.joining_date else 0
        countdown_str = f"{days_left} days remaining until joining" if days_left > 0 else "Joining date reached"

        # 1. Retrieve Candidate Profile Data
        profile_data = (
            f"- Full Name: {employee.full_name}\n"
            f"- Employee ID: {employee.id}\n"
            f"- Role & Grade: {employee.role} ({employee.grade})\n"
            f"- Department: {employee.department}\n"
            f"- Office Location: {employee.location}\n"
            f"- Official Joining Date: {employee.joining_date} ({countdown_str})\n"
            f"- Reporting Manager: {employee.manager_email}\n"
            f"- Email: {employee.email}"
        )

        # 2. Retrieve Submitted Documents & HR Decision Ledger
        docs = DocumentRepository.get_documents_for_employee(session, employee.id)
        # Also check Pinecone progress vectors
        progress_chunks = VectorStoreService.query_candidate_progress(query, candidate_id=employee.id)

        doc_summary_lines = []
        if docs:
            for d in docs:
                status_symbol = "Accepted (Approved)" if d.status == "Accepted" else ("Correction Requested" if d.status == "Correction Requested" else "Pending Review")
                reason_txt = f", HR Remarks/Reason: '{d.rejection_reason}'" if d.rejection_reason else ", HR Remarks: 'Verified and compliant'"
                meta = d.extracted_metadata or {}
                score_txt = f", AI Confidence Score: {meta.get('match_score', 0)}%"
                doc_summary_lines.append(f"• Document: {d.document_type} (File: {d.file_name}) -> Status: {status_symbol}{score_txt}{reason_txt}")
        else:
            doc_summary_lines.append("• No documents uploaded yet. (Requires PAN, Aadhaar/Passport, Degree Certificate).")

        # 3. Retrieve Live Onboarding Tasks & Dependencies
        tasks = TaskRepository.get_tasks_for_employee(session, employee.id)
        if not tasks:
            tasks = TaskRepository.generate_and_save_checklist(session, employee.id)

        task_summary_lines = []
        blocked_lines = []
        completed_count = 0
        for t in tasks:
            if t.status == "Completed":
                completed_count += 1
                task_summary_lines.append(f"• [COMPLETED] {t.title} (Category: {t.category})")
            elif t.status == "Blocked":
                prereq_task = next((pt for pt in tasks if pt.task_code == t.prerequisite_task), None)
                prereq_name = prereq_task.title if prereq_task else (t.prerequisite_task or "Prerequisite Verification")
                prereq_owner = prereq_task.owner_email if prereq_task else "hr.ops@azentio.com"
                blocked_lines.append(f"• [BLOCKED] {t.title} -> Waiting on prerequisite: '{prereq_name}' (Action Owner: {prereq_owner})")
                task_summary_lines.append(f"• [BLOCKED] {t.title} -> Waiting on '{prereq_name}'")
            else:
                task_summary_lines.append(f"• [PENDING ACTION] {t.title} (Due: {t.due_date}, Owner: {t.owner_email})")

        total_tasks = len(tasks)
        readiness_pct = int((completed_count / total_tasks * 100)) if total_tasks > 0 else 0

        # Construct comprehensive live context for LLM
        live_context = (
            f"=== CANDIDATE PROFILE DATA ===\n{profile_data}\n\n"
            f"=== DOCUMENT VERIFICATION & HR DECISION LEDGER ===\n" + "\n".join(doc_summary_lines) + "\n\n"
            f"=== ONBOARDING TASKS & READINESS ({readiness_pct}% Complete, {completed_count}/{total_tasks} tasks done) ===\n"
            + "\n".join(task_summary_lines) + "\n\n"
            + (f"=== ACTIVE BOTTLENECK DEPENDENCIES ===\n" + "\n".join(blocked_lines) if blocked_lines else "=== ACTIVE BOTTLENECK DEPENDENCIES ===\nNone. No tasks currently blocked.")
        )

        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        if groq_key and groq_key != "your_groq_api_key_here":
            try:
                from groq import Groq
                client = Groq(api_key=groq_key)
                model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

                system_prompt = (
                    "You are the official Azentio Autonomous AI HR Onboarding Agent.\n"
                    "Your role is to answer questions from candidates or HR personnel regarding candidate data, onboarding progress, document verification status, and task dependencies.\n"
                    "Rules:\n"
                    "1. Rely strictly on the provided Candidate Profile, Document Verification Ledger, and Onboarding Tasks data.\n"
                    "2. Quote exact document statuses (e.g., Accepted, Correction Requested) and specific HR remarks/feedback.\n"
                    "3. If tasks (like Laptop Provisioning) are blocked, explain exactly what prerequisite document or approval is needed and who the action owner is.\n"
                    "4. Be encouraging, clear, professional, and well-structured using markdown bullet points."
                )

                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Live Candidate Records:\n{live_context}\n\nUser Question: {query}"}
                    ],
                    temperature=0.1
                )
                return {
                    "answer": response.choices[0].message.content,
                    "citations": [{"document": "Azentio Live Candidate Database & Decision Ledger", "section": f"Profile & Status Records ({employee.id})"}],
                    "escalation": employee.manager_email or "priya.sharma@azentio.com"
                }
            except Exception:
                pass # Graceful fallback to deterministic synthesis

        # Deterministic Grounded Synthesis Fallback
        answer_parts = [
            f"### Onboarding Status & Candidate Data for **{employee.full_name}**",
            f"- **Role**: {employee.role} ({employee.grade}) • **Department**: {employee.department}",
            f"- **Location**: {employee.location} • **Joining Date**: {employee.joining_date} ({countdown_str})",
            f"- **Readiness Progress**: **{readiness_pct}%** ({completed_count} of {total_tasks} milestones completed)",
            "",
            "#### Document Verification & HR Decisions:",
            "\n".join(doc_summary_lines),
            ""
        ]

        if blocked_lines:
            answer_parts.extend([
                "#### ⚠️ Action Required / Blocked Dependencies:",
                "\n".join(blocked_lines),
                ""
            ])

        answer_parts.append(f"💡 *For questions on remarks, contact HR Operations (**priya.sharma@azentio.com**) or Manager (**{employee.manager_email}**).*")

        return {
            "answer": "\n".join(answer_parts),
            "citations": [{"document": "Azentio Live Candidate Database & Decision Ledger", "section": f"Profile & Status Records ({employee.id})"}],
            "escalation": employee.manager_email or "priya.sharma@azentio.com"
        }

    @classmethod
    def _handle_policy_query(cls, query: str, employee: EmployeeModel) -> Dict[str, Any]:
        """Perform grounded retrieval over official handbooks via Pinecone Vector DB and synthesize with Groq LLM."""
        chunks = VectorStoreService.query_policies(
            query=query,
            department=employee.department,
            location=employee.location,
            top_k=2
        )

        if not chunks:
            return {
                "answer": "I could not find an official policy clause matching your request in the Azentio HR handbooks. Please consult your HR Business Partner (priya.sharma@azentio.com).",
                "citations": [],
                "escalation": "priya.sharma@azentio.com"
            }

        top_chunk = chunks[0]
        groq_key = os.getenv("GROQ_API_KEY", "").strip()

        # Invoke Groq Cloud LLM
        if groq_key and groq_key != "your_groq_api_key_here":
            try:
                from groq import Groq
                client = Groq(api_key=groq_key)
                model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
                
                context_str = "\n\n".join([f"[{c['document_title']} - {c['section']}]:\n{c['content']}" for c in chunks])
                system_prompt = (
                    "You are the official Azentio Autonomous AI HR Assistant.\n"
                    "Answer the employee or HR query truthfully and accurately using ONLY the provided policy context.\n"
                    "Rules:\n"
                    "1. Strictly cite the official Document Title and Section.\n"
                    "2. If the context does not contain the answer, say 'I cannot find that in the official Azentio policy handbooks.' Never hallucinate numbers or clauses.\n"
                    f"3. Tailor appropriately for an employee located in {employee.location} with role {employee.role}."
                )

                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Policy Handbook Context:\n{context_str}\n\nEmployee Query: {query}"}
                    ],
                    temperature=0.1
                )
                llm_answer = response.choices[0].message.content
                citations = [{"document": c["document_title"], "section": c["section"]} for c in chunks]
                return {
                    "answer": llm_answer,
                    "citations": citations,
                    "escalation": "priya.sharma@azentio.com"
                }
            except Exception:
                pass # Fallback to deterministic synthesis

        # Deterministic Grounded Synthesis (Zero-latency fallback)
        citations = [{"document": c["document_title"], "section": c["section"]} for c in chunks]
        answer = (
            f"According to **{top_chunk['document_title']}** ({top_chunk['section']}):\n\n"
            f"{top_chunk['content']}\n\n"
            f"*(This policy applies to your role as {employee.role} in {employee.location})*"
        )

        return {
            "answer": answer,
            "citations": citations,
            "escalation": "priya.sharma@azentio.com"
        }
