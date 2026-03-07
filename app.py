"""
SmartHMS - AI-Powered Multi-Hospital Healthcare Coordination Platform
Main application entry point using FastAPI.
"""

import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

# Import database and models
from app.database import engine, Base, SessionLocal, init_db
from app.models import User, Hospital, Patient, Doctor, Nurse

# Import routers
from app.routers import auth, main

# Create FastAPI app
app = FastAPI(
    title="SmartHMS",
    description="AI-Powered Multi-Hospital Healthcare Coordination Platform",
    version="2.0.0"
)

# Mount static files
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")


# =============================================================================
# App Startup Event
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    # Import all models to ensure they're registered
    from app.models import (
        User, Hospital, Patient, Appointment, Visit, Alert,
        Doctor, Nurse, Department, Vitals, LabTest, LabReport, Treatment, Bed
    )
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Seed initial data
    seed_data()


def seed_data():
    """Seed initial data for the application."""
    db = SessionLocal()
    try:
        # Check if users already exist
        admin_exists = db.query(User).filter(User.username == "admin").first()
        doctor_exists = db.query(User).filter(User.username == "doctor").first()
        patient_exists = db.query(User).filter(User.username == "patient").first()
        
        # Create admin user
        if not admin_exists:
            from app.utils.auth import get_password_hash
            admin = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                role="admin",
                is_active=True
            )
            db.add(admin)
            print("✓ Created admin user (admin/admin123)")
        
        # Create doctor user
        if not doctor_exists:
            from app.utils.auth import get_password_hash
            doctor_user = User(
                username="doctor",
                password_hash=get_password_hash("doctor123"),
                role="doctor",
                is_active=True
            )
            db.add(doctor_user)
            db.flush()
            
            # Create doctor profile
            if not db.query(Doctor).filter(Doctor.user_id == doctor_user.id).first():
                # First check if there's a hospital
                hospital = db.query(Hospital).first()
                if not hospital:
                    hospital = Hospital(
                        name="City General Hospital",
                        address="123 Health Street",
                        phone="+1-555-0100",
                        total_beds=100,
                        available_beds=60
                    )
                    db.add(hospital)
                    db.flush()
                
                doctor = Doctor(
                    user_id=doctor_user.id,
                    hospital_id=hospital.id,
                    full_name="Dr. John Smith",
                    specialization="General Medicine",
                    license_number="MD-12345"
                )
                db.add(doctor)
            print("✓ Created doctor user (doctor/doctor123)")
        
        # Create patient user
        if not patient_exists:
            from app.utils.auth import get_password_hash
            patient_user = User(
                username="patient",
                password_hash=get_password_hash("patient123"),
                role="patient",
                is_active=True
            )
            db.add(patient_user)
            db.flush()
            
            # Create patient profile
            if not db.query(Patient).filter(Patient.user_id == patient_user.id).first():
                patient = Patient(
                    user_id=patient_user.id,
                    full_name="Demo Patient",
                    age=45,
                    gender="Male",
                    phone="+1-555-0100",
                    address="123 Health Street"
                )
                db.add(patient)
            print("✓ Created patient user (patient/patient123)")
        
        # Create nurse user
        nurse_exists = db.query(User).filter(User.username == "nurse").first()
        if not nurse_exists:
            from app.utils.auth import get_password_hash
            nurse_user = User(
                username="nurse",
                password_hash=get_password_hash("nurse123"),
                role="nurse",
                is_active=True
            )
            db.add(nurse_user)
            db.flush()
            
            # Create nurse profile
            hospital = db.query(Hospital).first()
            if hospital and not db.query(Nurse).filter(Nurse.user_id == nurse_user.id).first():
                nurse = Nurse(
                    user_id=nurse_user.id,
                    hospital_id=hospital.id,
                    full_name="Nurse Jane Doe",
                    license_number="RN-12345"
                )
                db.add(nurse)
            print("✓ Created nurse user (nurse/nurse123)")
        
        # Create lab tech user
        lab_exists = db.query(User).filter(User.username == "lab").first()
        if not lab_exists:
            from app.utils.auth import get_password_hash
            lab_user = User(
                username="lab",
                password_hash=get_password_hash("lab123"),
                role="lab_tech",
                is_active=True
            )
            db.add(lab_user)
            print("✓ Created lab tech user (lab/lab123)")
        
        # Create default hospitals if none exist
        if db.query(Hospital).count() == 0:
            hospitals = [
                Hospital(name="City General Hospital", address="100 Main St", phone="+1-555-0101", total_beds=100, available_beds=60),
                Hospital(name="Sunrise Medical Center", address="200 Oak Ave", phone="+1-555-0102", total_beds=80, available_beds=20),
                Hospital(name="Lakeside Clinic", address="300 Lake Dr", phone="+1-555-0103", total_beds=40, available_beds=10)
            ]
            for h in hospitals:
                db.add(h)
            print("✓ Created default hospitals")
        
        db.commit()
        print("✓ Database seeding completed successfully")
    except Exception as e:
        print(f"Error seeding data: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


# Include routers (main.router handles the root "/" route)
app.include_router(auth.router)
app.include_router(main.router)


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SmartHMS - AI-Powered Healthcare Platform")
    print("=" * 60)
    print("Starting server...")
    print("Access the application at: http://localhost:8000")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

