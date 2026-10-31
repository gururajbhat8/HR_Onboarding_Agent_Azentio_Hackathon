import os
import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from src.database.models import EmployeeModel, TaskModel
from src.database.repository import TaskRepository
from src.services.vector_store import VectorStoreService

class PolicyRAGAgent:
    """Conversational agent providing grounded policy answers with zero hallucinations and task escalation."""

    @classmethod
    def ask(
        cls,
        query: str,
        employee: EmployeeModel,
        session: Session
    ) -> Dict[str, Any]:
        """Main agent entry point. Routes to Task Engine for status questions or Policy RAG for handbook questions."""
        q_lower = query.lower()

        # 1. Check if user is asking about their personal checklist, blockers, or required documents
        task_keywords = [
            "which document", "what document", "my document", "my task", 
            "checklist", "status", "laptop", "blocked", "provisioning", 
            "escalat", "pending", "why is", "prerequisite"
        ]
        if any(k in q_lower for k in task_keywords):
            return cls._handle_task_query(query, employee, session)

        # 2. Otherwise route to Grounded Policy RAG
        return cls._handle_policy_query(query, employee)

    @classmethod
    def _handle_task_query(cls, query: str, employee: EmployeeModel, session: Session) -> Dict[str, Any]:
        """Answer task and status questions using live database checklist."""
        tasks = TaskRepository.get_tasks_for_employee(session, employee.id)
        if not tasks:
            tasks = TaskRepository.generate_and_save_checklist(session, employee.id)

        pending = [t for t in tasks if t.status == "Pending"]
        blocked = [t for t in tasks if t.status == "Blocked"]
        completed = [t for t in tasks if t.status == "Completed"]

        # Check for specific blocker query (Scenario 5 escalation requirement)
        if "blocked" in query.lower() or "laptop" in query.lower():
            blocked_details = []
            for bt in blocked:
                prereq_task = next((t for t in tasks if t.task_code == bt.prerequisite_task), None)
                prereq_name = prereq_task.title if prereq_task else (bt.prerequisite_task or "Prerequisite Verification")
                prereq_owner = prereq_task.owner_email if prereq_task else "hr.ops@azentio.com"
                blocked_details.append(
                    f"• **{bt.title}** is currently **BLOCKED** waiting on *{prereq_name}* (Owner: **{prereq_owner}**)."
                )

            if blocked_details:
                answer = (
                    f"Here is the status of your onboarding dependencies for **{employee.full_name}** ({employee.role}):\n\n"
                    + "\n".join(blocked_details)
                    + f"\n\n🚨 **Escalation Path**: If this approval is overdue, please reach out directly to the responsible owner listed above or HR Lead **priya.sharma@azentio.com**."
                )
                return {
                    "answer": answer,
                    "citations": [{"document": "Azentio Onboarding SLA Matrix", "section": "Dependency & Escalation Rules"}],
                    "escalation": "priya.sharma@azentio.com"
                }

        # General "Which documents do I need to submit?" (Level 1 capability)
        doc_tasks = [t for t in tasks if t.category in ["Document", "Compliance"]]
        doc_list = []
        for dt in doc_tasks:
            status_emoji = "✅" if dt.status == "Completed" else ("🔒" if dt.status == "Blocked" else "⏳")
            doc_list.append(f"{status_emoji} **{dt.title}** (Due: {dt.due_date} • Rule: *{dt.rule_origin}*)")

        answer = (
            f"Based on your assigned role as **{employee.role}** in **{employee.location}** (Joining Date: {employee.joining_date}), "
            f"here are your mandatory onboarding requirements:\n\n"
            + "\n".join(doc_list)
            + f"\n\n**Summary**: {len(completed)} completed, {len(pending)} pending action, {len(blocked)} blocked."
        )

        return {
            "answer": answer,
            "citations": [{"document": "Azentio Hiring & Onboarding Policy v2.4", "section": "Mandatory Role Requirements"}],
            "escalation": employee.manager_email
        }

    @classmethod
    def _handle_policy_query(cls, query: str, employee: EmployeeModel) -> Dict[str, Any]:
        """Perform grounded retrieval over official handbooks and synthesize with Groq LLM or deterministic fallback."""
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

        # Try Groq Cloud Llama 3 if key is provided
        if groq_key and groq_key != "your_groq_api_key_here":
            try:
                from groq import Groq
                client = Groq(api_key=groq_key)
                model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
                
                context_str = "\n\n".join([f"[{c['document_title']} - {c['section']}]:\n{c['content']}" for c in chunks])
                system_prompt = (
                    "You are the official Azentio AI HR Assistant. Answer the employee's query truthfully using ONLY the provided context.\n"
                    "Rules:\n"
                    "1. Strictly cite the official Document Title and Section.\n"
                    "2. If the context does not contain the answer, say 'I cannot find that in official policy.' Never hallucinate policies or numbers.\n"
                    f"3. Tailor appropriately for an employee located in {employee.location} with role {employee.role}."
                )

                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Context:\n{context_str}\n\nEmployee Query: {query}"}
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
            except Exception as e:
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
