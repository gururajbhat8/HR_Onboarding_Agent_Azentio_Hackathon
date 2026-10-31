# AI-Powered HR Onboarding Agent — PostgreSQL + pgvector + LangChain RAG

A hackathon-ready starter application for employee onboarding. PostgreSQL stores normal application data **and** policy embeddings through the `pgvector` extension. There is no separate Chroma database.

## Stack

- Backend: FastAPI + SQLAlchemy
- Database: PostgreSQL 16 + pgvector
- RAG: LangChain text splitter + Gemini embeddings + Gemini chat model
- Frontend: React + Vite
- Document extraction: PyMuPDF for PDFs; plain-text extraction for TXT/MD
- Orchestration: deterministic services for checklist/document state changes. LangGraph can be added for longer-running, multi-step workflows after the core lifecycle is working.

## 1. Prerequisites

- Docker Desktop
- Python 3.11+
- Node.js 20+
- A Gemini API key (needed for policy ingestion and assistant answers)

## 2. Start PostgreSQL with pgvector

From the project root:

```bash
docker compose up -d
```

The database is available at `localhost:5432`.

Default local credentials are in `docker-compose.yml`. Change them before using this outside a local demo.

## 3. Start the backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env
# macOS/Linux: cp .env.example .env
```

Add your Gemini key to `backend/.env`:

```env
GEMINI_API_KEY=your_key_here
```

Then run:

```bash
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

On startup the app enables the PostgreSQL `vector` extension, creates tables, and inserts a few example checklist rules if the rules table is empty.

## 4. Start the frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (normally http://localhost:5173).

## 5. Try the demo

1. Add an employee, or import `sample_data/employees.csv` from the API docs (`POST /employees/import`).
2. Generate that employee's checklist (`POST /employees/{employee_id}/generate-checklist`).
3. Upload an employee document (`POST /employees/{employee_id}/documents`).
4. HR can update its status using `PATCH /documents/{document_id}/status`.
5. Upload an approved policy PDF/TXT/MD (`POST /policies/upload`).
6. Ask a policy question in the frontend or through `POST /assistant/ask`.

Example assistant request:

```json
{
  "question": "What documents should I submit before joining?",
  "top_k": 5
}
```

The response contains an answer and the policy chunks used as sources.

## 6. How the RAG pipeline works

```text
HR uploads policy PDF/TXT/MD
        |
        v
Extract text (PyMuPDF for PDF)
        |
        v
Split text into overlapping chunks (LangChain)
        |
        v
Gemini embedding model converts each chunk to a vector
        |
        v
Store chunk + metadata + vector in PostgreSQL/pgvector
        |
Employee asks a question
        |
        v
Embed the question with the same embedding model
        |
        v
pgvector cosine-distance search retrieves relevant chunks
        |
        v
Gemini answers using only the retrieved policy context
        |
        v
Return answer + source titles/page numbers
```

## 7. Important implementation notes

- The vector column is configured for **768 dimensions**. The same embedding model and dimension must be used for both policy chunks and questions.
- The default embedding model is configurable with `EMBEDDING_MODEL`; the default chat model is configurable with `LLM_MODEL`.
- Checklist generation uses Python rules, not an LLM. This makes requirements repeatable and explainable.
- Document upload status is a workflow state. An uploaded PAN/passport/etc. is **not** automatically verified as authentic. HR/compliance must make the final decision.
- The sample file validation checks extension and file size. It is not a complete malware scanner, OCR verification system, or identity-verification service.
- The assistant is instructed to answer only from retrieved policy context. Still, test it with adversarial and out-of-policy questions before a demo.
- Only upload synthetic/demo employee information to a hackathon environment. Real employee identity documents require access controls, encryption, retention rules, audit logging, and an approved privacy/security review.
- This is a hackathon MVP, not a production HR platform. Add authentication, role-based authorization, audit logs, private object storage, antivirus scanning, migrations, retries, monitoring, and robust validation before production use.

## 8. Main API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/employees` | Create employee |
| POST | `/employees/import` | Import CSV/XLSX/JSON |
| GET | `/employees` | List employees |
| POST | `/employees/{id}/generate-checklist` | Apply onboarding rules |
| GET | `/employees/{id}/tasks` | View employee checklist |
| POST | `/employees/{id}/documents` | Upload employee document |
| PATCH | `/documents/{id}/status` | HR updates document status |
| POST | `/policies/upload` | Ingest policy and save vectors |
| POST | `/assistant/ask` | RAG policy question answering |
| GET | `/dashboard` | Onboarding summary |

## 9. Suggested next step: LangGraph

The core CRUD, rules, and RAG are deliberately separated. Once this MVP works, use LangGraph to orchestrate events such as:

`employee_created -> checklist_generated -> document_collection -> HR_review -> IT_provisioning -> orientation -> onboarding_completed`

Use conditional edges for correction requests, overdue tasks, and joining-date changes. Keep final approval and sensitive HR decisions under human control.
