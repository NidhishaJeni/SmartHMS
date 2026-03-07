"""
Database models for SmartHMS.
All models are PostgreSQL-compatible and use SQLAlchemy ORM.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    """User authentication model with role-based access."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, index=True)  # admin, hospital_admin, doctor, nurse, lab_tech, patient
    email = Column(String(128), unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="user", uselist=False)
    doctor = relationship("Doctor", back_populates="user", uselist=False)
    nurse = relationship("Nurse", back_populates="user", uselist=False)


class Hospital(Base):
    """Hospital entity with bed management."""
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, unique=True)
    address = Column(String(255))
    phone = Column(String(20))
    email = Column(String(128))
    total_beds = Column(Integer, nullable=False, default=0)
    available_beds = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=True)
    approved = Column(Boolean, default=True)  # Platform admin approval
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    appointments = relationship("Appointment", back_populates="hospital")
    departments = relationship("Department", back_populates="hospital")
    doctors = relationship("Doctor", back_populates="hospital")
    nurses = relationship("Nurse", back_populates="hospital")
    beds = relationship("Bed", back_populates="hospital")


class Department(Base):
    """Hospital departments."""
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    description = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    hospital = relationship("Hospital", back_populates="departments")
    doctors = relationship("Doctor", back_populates="department")
    treatments = relationship("Treatment", back_populates="department")


class Doctor(Base):
    """Doctor profile linked to user and hospital."""
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    full_name = Column(String(128), nullable=False)
    specialization = Column(String(128))
    license_number = Column(String(64))
    phone = Column(String(20))
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="doctor")
    hospital = relationship("Hospital", back_populates="doctors")
    department = relationship("Department", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctor")
    visits = relationship("Visit", back_populates="doctor")
    lab_requests = relationship("LabTest", back_populates="doctor")


class Nurse(Base):
    """Nurse profile linked to user and hospital."""
    __tablename__ = "nurses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    full_name = Column(String(128), nullable=False)
    license_number = Column(String(64))
    phone = Column(String(20))
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="nurse")
    hospital = relationship("Hospital", back_populates="nurses")
    vitals = relationship("Vitals", back_populates="nurse")


class Patient(Base):
    """Patient profile linked to user."""
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    full_name = Column(String(128), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(10), nullable=False)
    phone = Column(String(20))
    address = Column(String(255))
    date_of_birth = Column(String(20))
    blood_type = Column(String(5))
    allergies = Column(Text)
    emergency_contact = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")
    visits = relationship("Visit", back_populates="patient")
    vitals = relationship("Vitals", back_populates="patient")
    alerts = relationship("Alert", back_populates="patient")
    lab_reports = relationship("LabReport", back_populates="patient")


class Appointment(Base):
    """Appointment linking patient, doctor, and hospital."""
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=True)
    date = Column(String(32), nullable=False)
    time = Column(String(16))
    status = Column(String(32), default="Booked")  # Booked, Arrived, Completed, Cancelled
    qr_code = Column(String(255))  # relative path to QR image
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    hospital = relationship("Hospital", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")


class Vitals(Base):
    """Patient vitals recorded by nurses."""
    __tablename__ = "vitals"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    nurse_id = Column(Integer, ForeignKey("nurses.id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    
    # Vital signs
    blood_pressure_systolic = Column(Float, default=0)  # mmHg
    blood_pressure_diastolic = Column(Float, default=0)  # mmHg
    heart_rate = Column(Float, default=0)  # bpm
    respiratory_rate = Column(Float, default=0)  # breaths/min
    temperature = Column(Float, default=0)  # Fahrenheit
    oxygen_saturation = Column(Float, default=0)  # SpO2 %
    weight = Column(Float, default=0)  # kg
    height = Column(Float, default=0)  # cm
    bmi = Column(Float, default=0)
    glucose = Column(Float, default=0)  # mg/dL
    cholesterol = Column(Float, default=0)  # mg/dL
    
    # Risk assessment
    risk_score = Column(Integer, default=0)
    risk_level = Column(String(20), default="Low Risk")  # Low Risk, Moderate Risk, High Risk
    
    notes = Column(Text)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="vitals")
    nurse = relationship("Nurse", back_populates="vitals")


class Visit(Base):
    """Patient visit record with AI health assessment."""
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    
    # Basic vitals (for diabetes assessment)
    pregnancies = Column(Integer, default=0)
    glucose = Column(Float, default=0)
    blood_pressure = Column(Float, default=0)
    skin_thickness = Column(Float, default=0)
    insulin = Column(Float, default=0)
    bmi = Column(Float, default=0)
    dpf = Column(Float, default=0)
    age = Column(Integer, default=0)
    
    # Extended vitals
    heart_rate = Column(Float, default=0)
    respiratory_rate = Column(Float, default=0)
    oxygen_saturation = Column(Float, default=0)
    cholesterol = Column(Float, default=0)
    hdl = Column(Float, default=0)
    ldl = Column(Float, default=0)
    triglycerides = Column(Float, default=0)
    creatinine = Column(Float, default=0)
    urea = Column(Float, default=0)
    alt = Column(Float, default=0)
    ast = Column(Float, default=0)
    hemoglobin = Column(Float, default=0)
    
    # Symptoms
    chest_pain = Column(Boolean, default=False)
    shortness_of_breath = Column(Boolean, default=False)
    fatigue = Column(Boolean, default=False)
    swelling = Column(Boolean, default=False)
    smoking = Column(Boolean, default=False)
    family_history = Column(String(255), default="")
    
    # AI prediction results
    prediction = Column(String(32), default="Low Risk")  # High Risk, Moderate Risk, Low Risk
    disease_type = Column(String(64), default="General")
    risk_score = Column(Integer, default=0)
    predicted_conditions = Column(Text, default="")  # JSON list
    suggested_tests = Column(Text, default="")  # JSON list
    
    # Treatment
    status = Column(String(32), default="Pending Review")
    diagnosis = Column(Text, default="")
    treatment_plan = Column(Text, default="")
    doctor_notes = Column(Text, default="")
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="visits")
    doctor = relationship("Doctor", back_populates="visits")


class LabTest(Base):
    """Lab test requests from doctors."""
    __tablename__ = "lab_tests"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    test_name = Column(String(128), nullable=False)
    test_type = Column(String(64))  # Blood, Urine, Imaging, etc.
    priority = Column(String(20), default="Normal")  # Normal, Urgent, Emergency
    status = Column(String(32), default="Pending")  # Pending, In Progress, Completed, Cancelled
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    patient = relationship("Patient")
    doctor = relationship("Doctor", back_populates="lab_requests")
    reports = relationship("LabReport", back_populates="lab_test")


class LabReport(Base):
    """Lab test reports uploaded by lab technicians."""
    __tablename__ = "lab_reports"

    id = Column(Integer, primary_key=True, index=True)
    lab_test_id = Column(Integer, ForeignKey("lab_tests.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    technician_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    report_file = Column(String(255))  # relative path to report file
    findings = Column(Text)
    recommendations = Column(Text)
    is_abnormal = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    lab_test = relationship("LabTest", back_populates="reports")
    patient = relationship("Patient", back_populates="lab_reports")


class Treatment(Base):
    """Treatment plans created by doctors."""
    __tablename__ = "treatments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    
    diagnosis = Column(Text, nullable=False)
    treatment_plan = Column(Text, nullable=False)
    medications = Column(Text)  # JSON list
    dosage = Column(String(255))
    frequency = Column(String(128))
    duration = Column(String(64))
    status = Column(String(32), default="Active")  # Active, Completed, Cancelled
    start_date = Column(String(20))
    end_date = Column(String(20))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    department = relationship("Department", back_populates="treatments")


class Bed(Base):
    """Bed management for hospitals."""
    __tablename__ = "beds"

    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    ward = Column(String(64))
    room_number = Column(String(16))
    bed_number = Column(String(16))
    bed_type = Column(String(32))  # General, ICU, Private, Ward
    status = Column(String(32), default="Available")  # Available, Occupied, Maintenance, Reserved
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    hospital = relationship("Hospital", back_populates="beds")


class Alert(Base):
    """Patient alerts for high-risk conditions."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    message = Column(String(255), nullable=False)
    alert_type = Column(String(32), default="Warning")  # Info, Warning, Critical
    is_read = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="alerts")


class HospitalRequest(Base):
    """Hospital registration requests from hospital admins."""
    __tablename__ = "hospital_requests"

    id = Column(Integer, primary_key=True, index=True)
    hospital_name = Column(String(128), nullable=False)
    address = Column(String(255))
    phone = Column(String(20))
    email = Column(String(128))
    contact_person = Column(String(128))
    total_beds = Column(Integer, default=0)
    status = Column(String(32), default="Pending")  # Pending, Approved, Rejected
    admin_notes = Column(Text)
    requested_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    processed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

