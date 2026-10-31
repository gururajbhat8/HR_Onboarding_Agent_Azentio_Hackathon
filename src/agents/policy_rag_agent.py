import os
import re
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from src.database.models import EmployeeModel, TaskModel
from src.database.repository import TaskRepository, DocumentRepository, EmployeeRepository
from src.services.vector_store import VectorStoreService

load_dotenv()

class PolicyRAGAgent:
    """Autonomous AI HR Assistant providing grounded policy answers, candidate data intelligence, and onboarding tracking."""

    @classmethod
    def _call_groq_llm(cls, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Invoke Groq Cloud with primary model cascade. Returns None only if ALL models fail."""
        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        if not groq_key or groq_key == "your_groq_api_key_here":
            return None

        primary_model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
        fallback_model = os.getenv("FALLBACK_MODEL", "openai/gpt-oss-120b")

        for model_to_try in [primary_model, fallback_model, "openai/gpt-oss-20b"]:
            try:
                from groq import Groq
                client = Groq(api_key=groq_key)
                response = client.chat.completions.create(
                    model=model_to_try,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=900
                )
                text = response.choices[0].message.content
                if text and text.strip():
                    return text.strip()
                # Model returned empty — try next
            except Exception:
                continue
        return None  # All models failed — caller must use deterministic fallback

    @classmethod
    def ask(
        cls,
        query: str,
        employee: EmployeeModel,
        session: Session
    ) -> Dict[str, Any]:
        """Intelligent agentic router that resolves entities, intent, and dispatches to appropriate reasoning engine."""
        q_clean = query.strip()
        q_lower = q_clean.lower()

        # ------------------------------------------------------------------
        # 1. INTENT: Agent Identity & LLM Model Capabilities
        # ------------------------------------------------------------------
        identity_patterns = [
            "which llm", "what llm", "which model", "what model", 
            "who are you", "what are you", "what can you do", "introduce yourself",
            "your capabilities", "how do you work", "help me"
        ]
        if any(p in q_lower for p in identity_patterns):
            active_model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
            llm_reply = cls._call_groq_llm(
                system_prompt=(
                    f"You are the official Azentio Autonomous AI HR Onboarding Agent. "
                    f"You are powered by Groq Cloud LPU inference using model '{active_model}' "
                    f"and Pinecone Serverless Vector Database (index: azentio-hr-policies) for enterprise policy retrieval. "
                    f"When asked about your identity or capabilities, clearly state your model name ({active_model}) "
                    f"and describe your three core capabilities: "
                    f"(1) Real-time candidate onboarding & document status intelligence, "
                    f"(2) Grounded company policy Q&A with zero hallucinations from official HR handbooks, "
                    f"(3) Task dependency tracking and IT provisioning unblocking. "
                    f"Be concise, professional, and use markdown formatting."
                ),
                user_prompt=query
            )
            if not llm_reply:
                # Minimal deterministic fallback only if Groq API is truly unavailable
                llm_reply = (
                    f"I am the **Azentio Autonomous AI HR Onboarding Agent** — LLM service is temporarily unavailable. "
                    f"Please check your GROQ_API_KEY configuration."
                )
            return {
                "answer": llm_reply,
                "citations": [{"document": f"Groq LPU Engine ({active_model})", "section": "Agentic Architecture"}],
                "escalation": "priya.sharma@azentio.com"
            }

        # ------------------------------------------------------------------
        # 2. INTENT: Candidate Entity Search (e.g. "update in Aditi verma")
        # ------------------------------------------------------------------
        # Check if the query specifically references an employee in the system
        target_employee = employee
        all_emps = EmployeeRepository.get_all_employees(session)
        for cand in all_emps:
            cand_first = cand.full_name.split()[0].lower() if cand.full_name else ""
            cand_full = cand.full_name.lower() if cand.full_name else ""
            if (cand_full and cand_full in q_lower) or (cand_first and len(cand_first) > 3 and cand_first in q_lower.split()):
                target_employee = cand
                break

        # Check candidate status & progress indicators
        candidate_indicators = [
            "update", "status", "progress", "candidate", "profile", "document", "submission",
            "pan", "aadhaar", "passport", "degree", "laptop", "blocked", "approved", "rejected",
            "correction", "feedback", "remarks", "checklist", "joining", "manager", "when will",
            "did hr", "has hr", "unblock"
        ]
        is_candidate_query = (target_employee != employee) or any(k in q_lower for k in candidate_indicators)

        # Also check if it's explicitly a policy question
        policy_indicators = [
            "leave", "casual leave", "earned leave", "probation", "sick leave",
            "insurance", "medical", "opd", "hospital", "coverage", "benefits",
            "relocation", "travel", "per-diem", "cab", "uber", "expense",
            "laptop policy", "mfa", "password", "github access", "aws access", "device",
            "posh", "sexual harassment", "ethics", "whistleblower", "conduct", "nda",
            "appraisal", "notice period", "wfh", "work from home", "hybrid"
        ]
        is_policy_query = any(k in q_lower for k in policy_indicators)

        # Route priority:
        if is_candidate_query and not (is_policy_query and target_employee == employee):
            return cls._handle_candidate_status_query(query, target_employee, session)

        if is_policy_query:
            return cls._handle_policy_query(query, target_employee)

        # Default fallback: check policies first; if no relevant chunk, handle candidate query
        return cls._handle_policy_query(query, target_employee)

    @classmethod
    def _handle_candidate_status_query(
        cls,
        query: str,
        employee: EmployeeModel,
        session: Session
    ) -> Dict[str, Any]:
        """Synthesize candidate status, document verification ledger, and task blockers using live DB & Groq LLM."""
        from datetime import date
        today = date.today()
        days_left = (employee.joining_date - today).days if employee.joining_date else 0
        countdown_str = f"{days_left} days remaining until joining" if days_left > 0 else "Joining date reached"

        # 1. Profile Context
        profile_info = (
            f"Candidate Name: {employee.full_name}\n"
            f"Employee Code: {employee.employee_code}\n"
            f"Role & Grade: {employee.role} ({employee.grade})\n"
            f"Department: {employee.department}\n"
            f"Location: {employee.location}\n"
            f"Joining Date: {employee.joining_date} ({countdown_str})\n"
            f"Reporting Manager: {employee.manager_email}\n"
            f"Official Email: {employee.email}"
        )

        # 2. Document Verification History
        docs = DocumentRepository.get_documents_for_employee(session, employee.id)
        doc_lines = []
        if docs:
            for d in docs:
                status_str = "Accepted" if d.status == "Accepted" else ("Correction Requested" if d.status == "Correction Requested" else "Pending Review")
                reason_str = f" [HR Remarks: {d.rejection_reason}]" if d.rejection_reason else " [Compliant]"
                doc_lines.append(f"- {d.document_type} ({d.file_name}): {status_str}{reason_str}")
        else:
            doc_lines.append("- No documents submitted yet.")

        # 3. Tasks & Bottlenecks
        tasks = TaskRepository.get_tasks_for_employee(session, employee.id)
        if not tasks:
            tasks = TaskRepository.generate_and_save_checklist(session, employee.id)

        completed = [t for t in tasks if t.status == "Completed"]
        blocked = [t for t in tasks if t.status == "Blocked"]
        pending = [t for t in tasks if t.status == "Pending"]

        blocked_lines = []
        for bt in blocked:
            prereq = next((t for t in tasks if t.task_code == bt.prerequisite_task), None)
            prereq_title = prereq.title if prereq else (bt.prerequisite_task or "Identity Verification")
            prereq_owner = prereq.owner_email if prereq else "priya.sharma@azentio.com"
            blocked_lines.append(f"- {bt.title} is BLOCKED on '{prereq_title}' (Owner: {prereq_owner})")

        total_tasks = len(tasks)
        pct_done = int((len(completed) / total_tasks * 100)) if total_tasks > 0 else 0

        candidate_record_text = (
            f"=== CANDIDATE PROFILE ===\n{profile_info}\n\n"
            f"=== ONBOARDING PROGRESS ===\n"
            f"Progress: {len(completed)}/{total_tasks} milestones completed ({pct_done}% readiness)\n"
            f"Completed Tasks: {', '.join([t.title for t in completed]) if completed else 'None'}\n"
            f"Pending Tasks: {', '.join([t.title for t in pending]) if pending else 'None'}\n\n"
            f"=== DOCUMENT VERIFICATION LEDGER ===\n" + "\n".join(doc_lines) + "\n\n"
            f"=== ACTIVE BLOCKERS & BOTTLENECKS ===\n" + ("\n".join(blocked_lines) if blocked_lines else "None. No tasks currently blocked.")
        )

        system_prompt = (
            f"You are the official Azentio Autonomous AI HR Assistant.\n"
            f"Answer the user's question about candidate {employee.full_name} clearly and concisely using the provided live records.\n"
            f"Rules:\n"
            f"1. State the candidate's role, department, and joining date.\n"
            f"2. Summarize document verification statuses (Accepted, Correction Requested, Pending) and quote HR feedback.\n"
            f"3. Highlight any blocked tasks (especially Laptop Provisioning) and state the prerequisite needed to unblock it.\n"
            f"4. Format cleanly with markdown bullet points and emojis."
        )

        llm_reply = cls._call_groq_llm(
            system_prompt=system_prompt,
            user_prompt=f"Candidate Records:\n{candidate_record_text}\n\nUser Question: {query}"
        )

        if not llm_reply:
            # Deterministic synthesis fallback — only when Groq API is completely unavailable
            doc_bullets = "\n".join(doc_lines)
            blocker_bullets = "\n".join(blocked_lines) if blocked_lines else "None. No tasks currently blocked."
            llm_reply = (
                f"### Onboarding Status for **{employee.full_name}**\n\n"
                f"* **Role**: {employee.role} ({employee.grade}) • **Department**: {employee.department} • **Location**: {employee.location}\n"
                f"* **Joining Date**: {employee.joining_date} ({countdown_str})\n"
                f"* **Readiness Progress**: {pct_done}% ({len(completed)} of {total_tasks} milestones)\n\n"
                f"**Document Verification:**\n{doc_bullets}\n\n"
                f"**Blockers:**\n{blocker_bullets}\n\n"
                f"⚠️ *Live LLM unavailable — showing raw database records. Contact HR: priya.sharma@azentio.com*"
            )

        return {
            "answer": llm_reply,
            "citations": [{"document": "Azentio Live Candidate Database & Decision Ledger", "section": f"Profile & Status ({employee.employee_code})"}],
            "escalation": employee.manager_email or "priya.sharma@azentio.com"
        }

    @classmethod
    def _handle_policy_query(cls, query: str, employee: EmployeeModel) -> Dict[str, Any]:
        """Perform grounded semantic retrieval over official handbooks via Pinecone Vector DB and synthesize with Groq LLM."""
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
        context_str = "\n\n".join([f"[{c['document_title']} - {c['section']}]:\n{c['content']}" for c in chunks])

        system_prompt = (
            "You are the official Azentio Autonomous AI HR Assistant.\n"
            "Answer the query truthfully and accurately using ONLY the provided official policy context.\n"
            "Rules:\n"
            "1. Strictly cite the official Document Title and Section.\n"
            "2. If the context does not contain the answer, say 'I cannot find that in the official Azentio policy handbooks.' Never hallucinate numbers or clauses.\n"
            f"3. Tailor appropriately for an employee located in {employee.location} with role {employee.role}."
        )

        llm_reply = cls._call_groq_llm(
            system_prompt=system_prompt,
            user_prompt=f"Policy Handbook Context:\n{context_str}\n\nUser Question: {query}"
        )

        citations = [{"document": c["document_title"], "section": c["section"]} for c in chunks]

        if not llm_reply:
            # Deterministic fallback
            llm_reply = (
                f"According to **{top_chunk['document_title']}** ({top_chunk['section']}):\n\n"
                f"{top_chunk['content']}\n\n"
                f"*(This policy applies to your role as {employee.role} in {employee.location})*"
            )

        return {
            "answer": llm_reply,
            "citations": citations,
            "escalation": "priya.sharma@azentio.com"
        }
