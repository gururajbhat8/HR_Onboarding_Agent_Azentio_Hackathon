import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./azentio_onboarding.db")
if "sqlite+aiosqlite" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")

# Standard engine with thread-safety for SQLite
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def init_db():
    """Create all database tables on startup."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for API database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
