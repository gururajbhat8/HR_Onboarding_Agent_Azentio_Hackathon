# 🚀 Azentio HR Onboarding Agent — Autonomous Multi-Agent Lifecycle Platform

<div align="center">

![Azentio Theme](https://img.shields.io/badge/Azentio-Design%20System-00DF8F?style=for-the-badge&logoColor=0B192C)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Async%20Core-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-State%20Machine-FF6F00?style=for-the-badge)
![Streamlit](https://img.shields.io/badge/Streamlit-Azentio%20UI-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Pinecone](https://img.shields.io/badge/Pinecone-Serverless%20Vector%20DB-000000?style=for-the-badge)
![Groq](https://img.shields.io/badge/Groq-Llama%203%2070B-F59E0B?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)

**An enterprise-grade, multi-agent AI system designed for Azentio Build Labs Hackathon.**  
*Automating employee onboarding, document verification, role-based checklists, IT provisioning, grounded policy assistance, and dynamic date/role recalculations.*

</div>

---

## 📌 Executive Summary

Modern enterprise employee onboarding is notoriously fragmented across HR, IT, Administration, and Compliance. Delayed document submissions, manual data chasing, and last-minute joining date shifts cause new hires to arrive on Day 1 without laptops, system credentials, or active profiles.

The **Azentio HR Onboarding Agent** is an autonomous, event-driven platform that orchestrates the entire onboarding journey. Built with a decoupled **3-tier architecture** (Streamlit Azentio UI, FastAPI microservices, and a deterministic **LangGraph state machine**), the system combines deterministic business guardrails with generative AI to ensure 100% Day-1 readiness.

---

## 🏗️ High-Level System Architecture

The complete system architecture diagram is available in [`flow_diagram.png`](./flow_diagram.png) and documented in [`flow diagram.md`](./flow%20diagram.md).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. PRESENTATION LAYER (Azentio Design System: Mint #00DF8F & Navy #0B192C)  │
│  - HR Operations Admin Console  │  New Joiner Portal  │  Policy Copilot Chat│
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Async REST / WebSocket
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 2. API & SECURITY GATEWAY (FastAPI + Pydantic v2)                            │
│  - Ingestion API (CSV/XLSX/JSON)│ Document API │ Workflow API │ Chat API    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ State Triggers & Actions
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 3. AGENTIC ORCHESTRATION LAYER (LangGraph Cyclic State Machine)             │
│  - Master Coordinator Supervisor Agent                                      │
│  - Dynamic Checklist & Rule Engine Agent                                    │
│  - OCR & Discrepancy Verification Agent                                     │
│  - IT & Systems Provisioning Agent                                          │
│  - Dynamic Cascade Recalculation Engine                                     │
│  - Grounded Zero-Hallucination Policy RAG Agent                             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Persistence & Knowledge Lookups
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 4. PERSISTENCE & VECTOR LAYER                                                │
│  - PostgreSQL / SQLite (ACID Employee & Task Ledger)                         │
│  - Pinecone Serverless (Azentio HR Handbooks & Policy Metadata Index)        │
│  - AWS S3 / Local Vault (Encrypted Document Staging)                         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Sub-second Inference
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 5. INFERENCE & CLOUD LAYER                                                   │
│  - Groq Cloud Llama-3 70B (Sub-second LLM reasoning)                        │
│  - AWS Textract / PyMuPDF OCR (Key-value document extraction)               │
│  - Docker & Docker Compose Container Topology                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Continuous Evaluation Roadmap: Level 1 Milestone Delivery

The application is structured to deliver immediate evaluation-ready results for **Level 1 (0 – 3 Hours Milestone)** while establishing the complete architectural backbone for advanced scenarios.

### Level 1 Capability Matrix

| Capability | Requirement Specification | Application Implementation |
| :--- | :--- | :--- |
| **1. Employee Data Ingestion** | Support CSV, Excel, and JSON ingestion of synthetic new joiners; validate mandatory fields, date formats, and manager/department references. | Multi-format parser validating against strict **Pydantic v2 schemas**, rejecting malformed dates or missing hierarchies before DB commit. |
| **2. Checklist Generation** | Generate role-appropriate checklists (documents, assets, training, due dates); explain the specific rule origin for each generated task. | Deterministic **Rule Engine** mapping (Role × Department × Location) to task templates with transparent `rule_origin` explanations. |
| **3. Document Tracking** | Upload documents; maintain real-time status: `Not Submitted`, `Submitted`, `Under Review`, `Accepted`, `Correction Requested`. | State-tracked document ledger with dynamic status tags and real-time candidate progress bars. |
| **4. Record & Doc Validation** | Detect missing mandatory info, expired documents, and cross-reference extracted OCR data (Name, ID, DoB) against master records. | **OCR & Verification Agent** using PyMuPDF / Textract + LLM entity cross-matching; highlights mismatches with actionable correction requests. |
| **5. Grounded Policy Assistant** | Conversational assistant answering employee queries using approved policy docs; role/location-specific; zero hallucinations; source citations. | **Pinecone Serverless RAG** with metadata filtering (Role, Dept, Location); strictly constrained prompts citing exact policy sections. |
| **6. Progress Dashboard** | Filterable HR dashboard (by joining date, dept, location, status); view completed, pending, blocked, and overdue tasks with full drill-down. | **Azentio-styled Streamlit Dashboard** featuring interactive metric cards, filterable pipeline tables, and candidate record modals. |

---

## 🔄 Core End-to-End Scenarios Handled

1. **Pre-Joining Document Collection & Correction**: Automated ingestion, OCR extraction, profile cross-checking, and clear correction guidance for rejected files.
2. **Employee Profile Creation & IT Provisioning**: Prerequisite-gated state transitions; automatically raises IT asset (laptop) and AD email requests upon document approval.
3. **Role-Specific Onboarding & Policy Acknowledgement**: Tailored onboarding decks and compliance tracking based on candidate grade and department.
4. **Dynamic Joining-Date & Role Changes (Cascade Engine)**: Atomic recalculation of dependent task deadlines, SLA offsets, and owner reassignments whenever joining dates or roles shift.
5. **Grounded Assistance & Automated Escalation**: Proactive bottleneck detection; escalates overdue tasks to department leads and provides instant, cited policy answers.

---

## 📁 Repository Directory Structure

```text
HR_Onboarding_Agent_Azentio_Hackathon/
├── .env.example                 # Standardized environment configuration template
├── .env                         # Local runtime credentials (git-ignored)
├── .gitignore                   # Enterprise ignore rules for Python, DB & uploads
├── README.md                    # Master documentation & evaluation guide
├── flow diagram.md              # Architectural specification & Mermaid diagrams
├── flow_diagram.png             # High-resolution (2600x3300) visual architecture blueprint
├── requirements.txt             # Python dependencies (FastAPI, Streamlit, LangGraph, etc.)
│
├── data/                        # Sample & Operational Data
│   ├── sample_profiles/         # Synthetic new-joiner data (CSV, XLSX, JSON)
│   ├── policies/                # Official Azentio HR policy handbooks (PDF, Markdown)
│   ├── rules/                   # Role, department & location onboarding rule matrices
│   └── uploads/                 # Local encrypted file staging directory
│
├── docker/                      # Containerization Configurations
│   ├── Dockerfile.backend       # FastAPI service container definition
│   ├── Dockerfile.frontend      # Streamlit Azentio UI container definition
│   └── docker-compose.yml       # Multi-service local orchestration
│
├── frontend/                    # Dedicated Frontend Layer (Streamlit + Azentio Theme)
│   ├── styles/                  # Azentio Enterprise CSS (Mint #00DF8F, Navy #0B192C)
│   ├── components/              # Reusable UI cards, metrics, modals & timelines
│   └── views/                   # Admin Dashboard, Joiner Portal, Policy Copilot
│
├── src/                         # Backend & Core Engine Source Code
│   │   ├── routers/             # Ingestion, Documents, Workflows, and Chat routers
│   │   └── schemas/             # Pydantic v2 request/response schemas
│   │
│   ├── core/                    # Core Business Logic & Orchestration
│   │   ├── config.py            # Typed settings & environment variables
│   │   ├── state_machine.py     # LangGraph cyclic workflow graph
│   │   ├── rule_engine.py       # Deterministic checklist generator
│   │   └── recalculation_engine.py # Dynamic date/role cascade recalculator
│   │
│   ├── agents/                  # Autonomous Agents
│   │   ├── coordinator_agent.py # Master supervisor & SLA manager
│   │   ├── doc_validation_agent.py # OCR parsing & discrepancy analyzer
│   │   ├── provisioning_agent.py # IT asset & system credential dispatcher
│   │   └── policy_rag_agent.py  # Grounded RAG with strict clause citations
│   │
│   ├── database/                # Persistence & Data Access
│   │   ├── session.py           # SQLAlchemy async session manager
│   │   ├── models.py            # Relational database models (Employees, Tasks, Docs)
│   │   └── repository.py        # Abstract repository pattern for DB operations
│   │
│   └── services/                # Cloud & External Service Adapters
│       ├── ocr_service.py       # Pluggable OCR (PyMuPDF / AWS Textract)
│       ├── vector_store.py      # Pinecone Serverless integration client
│       └── llm_provider.py      # Groq Llama-3 client with Bedrock/OpenAI fallback
│
└── tests/                       # Automated Verification Suite
    ├── test_ingestion.py        # Schema validation & multi-format parser tests
    ├── test_rule_engine.py      # Checklist generation & rule origin tests
    ├── test_recalculation.py    # Date shift cascade propagation tests
    └── test_policy_rag.py       # Groundedness & zero-hallucination tests
```

---

## 🎨 Azentio Brand Design System

The user interface strictly adheres to Azentio's corporate design language:
* **Primary Brand Accent**: Mint / Electric Emerald (`#00DF8F` / `#10B981`)
* **Deep Contrast Surface**: Midnight Navy (`#0B192C` / `#1E293B`)
* **Background & Cards**: Crisp White (`#FFFFFF`) with Light Ice Slate (`#F8FAFC`)
* **Typography & Elements**: Clean geometric sans-serif (Segoe UI / Inter), rounded pill badges (`rounded-full`), smooth cards (`rounded-2xl`), and high-contrast status tags.

---

## ⚡ Quick Start & Setup Guide

### 1. Prerequisites
* Python 3.11+
* Docker & Docker Compose (Optional for containerized run)
* Groq API Key ([console.groq.com](https://console.groq.com/keys))
* Pinecone API Key ([app.pinecone.io](https://app.pinecone.io/))

### 2. Environment Configuration
Clone the repository and configure your environment variables:
```bash
# Copy the environment template
cp .env.example .env

# Edit .env with your credentials
# Set GROQ_API_KEY, PINECONE_API_KEY, etc.
```

### 3. Installation
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Linux/macOS
.venv\Scripts\activate          # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 4. Running the Application
```bash
# Terminal 1: Start FastAPI Backend Service
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start Azentio Streamlit Portal
streamlit run frontend/main.py --server.port 8501
```

### 5. Running with Docker Compose
```bash
docker-compose -f docker/docker-compose.yml up --build
```

---

## 🧪 Verification & Continuous Testing

Run the automated test suite to verify Level 1 compliance:
```bash
# Run all tests
pytest tests/ -v

# Run ingestion validation tests
pytest tests/test_ingestion.py -v

# Run checklist rule engine tests
pytest tests/test_rule_engine.py -v
```

---

## 🏆 Hackathon Evaluation Checklist

- [x] **Repository Scaffolding & Architecture Flow Diagram**: Complete & documented.
- [x] **Level 1 Ingestion**: CSV, Excel, JSON multi-format parser with Pydantic validation.
- [x] **Level 1 Checklists**: Dynamic generation with explicit rule-origin attribution.
- [x] **Level 1 Document Lifecycle**: Upload, OCR, discrepancy checking & status tracking.
- [x] **Level 1 Conversational Assistant**: Grounded Pinecone RAG with zero hallucination.
- [x] **Level 1 Dashboard**: Filterable HR operations console with Azentio styling.
- [x] **Advanced Scenario 4**: Cascade Recalculation Engine for date & role changes.
- [x] **Advanced Scenario 2 & 3**: State-gated IT provisioning & digital policy sign-off.

