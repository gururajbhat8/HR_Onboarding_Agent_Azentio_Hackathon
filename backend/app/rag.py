from pathlib import Path
import fitz
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import settings
from .models import PolicyDocument, PolicyChunk


def _require_api_key():
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to backend/.env and restart the API.")


def get_embeddings():
    _require_api_key()
    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.gemini_api_key,
        output_dimensionality=settings.embedding_dimensions,
    )


def extract_policy_text(path: str, suffix: str):
    if suffix == ".pdf":
        pages = []
        with fitz.open(path) as pdf:
            for page_no, page in enumerate(pdf, start=1):
                txt = page.get_text("text").strip()
                if txt:
                    pages.append((page_no, txt))
        return pages
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    return [(None, text)] if text.strip() else []


def ingest_policy(db: Session, policy: PolicyDocument):
    pages = extract_policy_text(policy.stored_path, Path(policy.original_filename).suffix.lower())
    if not pages:
        raise ValueError("No extractable text found. This PDF may be scanned; OCR is not included in this MVP.")

    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150)
    records = []
    for page_no, page_text in pages:
        for chunk in splitter.split_text(page_text):
            records.append((page_no, chunk))
    if not records:
        raise ValueError("The policy did not produce any text chunks.")

    vectors = get_embeddings().embed_documents([item[1] for item in records])
    for index, ((page_no, content), vector) in enumerate(zip(records, vectors)):
        db.add(PolicyChunk(
            policy_id=policy.id,
            chunk_index=index,
            page_number=page_no,
            content=content,
            embedding=vector,
        ))
    db.commit()
    return len(records)


def answer_policy_question(db: Session, question: str, top_k: int = 5):
    _require_api_key()
    query_vector = get_embeddings().embed_query(question)
    distance = PolicyChunk.embedding.cosine_distance(query_vector)
    rows = db.execute(
        select(PolicyChunk, PolicyDocument)
        .join(PolicyDocument, PolicyChunk.policy_id == PolicyDocument.id)
        .where(PolicyDocument.approved.is_(True))
        .order_by(distance)
        .limit(top_k)
    ).all()

    if not rows:
        return {
            "answer": "I couldn't find any approved policy content to answer this question. Please contact HR.",
            "sources": [],
        }

    context_parts, sources = [], []
    for i, (chunk, policy) in enumerate(rows, start=1):
        page_label = f", page {chunk.page_number}" if chunk.page_number else ""
        context_parts.append(f"[Source {i}: {policy.title}{page_label}]\n{chunk.content}")
        sources.append({
            "policy_title": policy.title,
            "page_number": chunk.page_number,
            "chunk_id": chunk.id,
        })

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are an HR policy assistant. Answer only using the supplied approved policy excerpts. "
         "Do not invent policy rules or use outside knowledge. If the excerpts do not contain the answer, "
         "say that the approved policy information available to you does not specify it and advise the "
         "employee to contact HR. Cite supporting excerpts as [Source 1], [Source 2], etc. "
         "Do not expose unrelated personal data."),
        ("human", "Question: {question}\n\nApproved policy excerpts:\n{context}")
    ])
    llm = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.gemini_api_key,
        temperature=0,
    )
    response = llm.invoke(prompt.format_messages(
        question=question,
        context="\n\n".join(context_parts),
    ))
    return {"answer": response.content, "sources": sources}
