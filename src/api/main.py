from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database.session import init_db
from src.api.routers import ingestion, tasks, documents, workflows, chat

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    init_db()
    yield

app = FastAPI(
    title="Azentio HR Onboarding Agent API",
    description="Autonomous Enterprise Employee Lifecycle Automation API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(ingestion.router)
app.include_router(tasks.router)
app.include_router(documents.router)
app.include_router(workflows.router)
app.include_router(chat.router)

@app.get("/health", tags=["System"])
async def health_check():
    """System health check endpoint."""
    return {"status": "healthy", "service": "Azentio HR Onboarding API", "version": "1.0.0"}
