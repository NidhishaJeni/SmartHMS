"""
Database configuration and session management for SmartHMS.
Uses SQLAlchemy ORM with SQLite for development (PostgreSQL-compatible).
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database configuration
DATABASE_URL = os.environ.get(
    "SMARTHMS_DATABASE_URI",
    "sqlite:///smart_hms.db"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()


def get_db():
    """
    Dependency for getting database session.
    Used in FastAPI routes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    Called on application startup.
    """
    from app.models import User, Hospital, Patient, Appointment, Visit, Alert
    from app.models import Nurse, Doctor, Department, LabTest, LabReport, Treatment, Bed
    
    Base.metadata.create_all(bind=engine)

