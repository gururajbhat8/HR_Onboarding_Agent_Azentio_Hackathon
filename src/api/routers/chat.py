from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from src.database.session import get_db
from src.database.repository import EmployeeRepository
from src.agents.policy_rag_agent import PolicyRAGAgent

router = APIRouter(prefix="/api/v1/chat", tags=["AI Conversational Assistant"])

class ChatRequest(BaseModel):
    employee_id: str
    query: str

class CitationItem(BaseModel):
    document: str
    section: str

class ChatResponse(BaseModel):
    answer: str
    citations: List[CitationItem] = []
    escalation: Optional[str] = None

@router.post("/ask", response_model=ChatResponse)
def ask_assistant(req: ChatRequest, db: Session = Depends(get_db)):
    """Grounded AI Policy & Onboarding Assistant query endpoint."""
    emp = EmployeeRepository.get_employee_by_id(db, req.employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    result = PolicyRAGAgent.ask(
        query=req.query,
        employee=emp,
        session=db
    )
    return result

