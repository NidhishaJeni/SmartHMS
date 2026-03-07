"""
Main routes for SmartHMS.
Handles all user dashboards and functionality.
"""

import os
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Cookie
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
import qrcode
from io import BytesIO
import base64

from app.database import get_db
from app.models import (
    User, Hospital, Patient, Appointment, Visit, Alert,
    Doctor, Nurse, Department, Vitals, LabTest, LabReport, Treatment, Bed, HospitalRequest
)
from app.ai.health_risk import assess_health_risk, quick_risk_assessment, DISEASE_CATEGORIES
from app.utils.auth import get_current_user, role_required

router = APIRouter(tags=["Main"])
templates = Jinja2Templates(directory="templates")


# Helper function to get current user from cookies or query params
def get_user_from_cookies(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get user from cookies or query params for template rendering."""
    # Try to get token from query parameter first
    token = request.query_params.get("token")
    
    # Try to get token from cookie
    if not token:
        token = request.cookies.get("access_token")
    
    if token:
        from app.utils.auth import decode_token
        payload = decode_token(token)
        if payload:
            username = payload.get("sub")
            if username:
                user = db.query(User).filter(User.username == username).first()
                return user
    
    # Fallback to cookie-based username
    username = request.cookies.get("username")
    if username:
        user = db.query(User).filter(User.username == username).first()
        return user
    return None


# =============================================================================
# Landing Page & Public Routes
# =============================================================================

@router.get("/staff/profile/create")
async def create_staff_profile_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("doctor", "nurse", "lab_tech"))
):
    """Create staff profile page for doctors, nurses, and lab techs."""
    hospitals = db.query(Hospital).filter(Hospital.is_active == True).order_by(Hospital.name).all()
    
    staff = None
    doctor = None
    
    if user.role == "doctor":
        staff = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    elif user.role == "nurse":
        staff = db.query(Nurse).filter(Nurse.user_id == user.id).first()
    
    return templates.TemplateResponse("create_staff_profile.html", {
        "request": request,
        "user": user,
        "staff": staff,
        "doctor": doctor,
        "hospitals": hospitals
    })


@router.post("/staff/profile/create")
async def create_staff_profile(
    request: Request,
    full_name: str = Form(...),
    specialization: str = Form(""),
    license_number: str = Form(...),
    phone: str = Form(""),
    hospital_id: int = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("doctor", "nurse", "lab_tech"))
):
    """Create or update staff profile."""
    if user.role == "doctor":
        staff = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        if staff:
            staff.full_name = full_name
            staff.specialization = specialization
            staff.license_number = license_number
            staff.phone = phone
            staff.hospital_id = hospital_id
        else:
            staff = Doctor(
                user_id=user.id,
                hospital_id=hospital_id,
                full_name=full_name,
                specialization=specialization,
                license_number=license_number,
                phone=phone
            )
            db.add(staff)
    elif user.role == "nurse":
        staff = db.query(Nurse).filter(Nurse.user_id == user.id).first()
        if staff:
            staff.full_name = full_name
            staff.license_number = license_number
            staff.phone = phone
            staff.hospital_id = hospital_id
        else:
            staff = Nurse(
                user_id=user.id,
                hospital_id=hospital_id,
                full_name=full_name,
                license_number=license_number,
                phone=phone
            )
            db.add(staff)
    
    db.commit()
    
    # Redirect based on role
    if user.role == "nurse":
        return RedirectResponse(url=f"/nurse/dashboard?token={request.query_params.get('token', '')}", status_code=status.HTTP_302_FOUND)
    elif user.role == "doctor":
        return RedirectResponse(url=f"/doctor/dashboard?token={request.query_params.get('token', '')}", status_code=status.HTTP_302_FOUND)
    elif user.role == "lab_tech":
        return RedirectResponse(url=f"/lab/dashboard?token={request.query_params.get('token', '')}", status_code=status.HTTP_302_FOUND)
    
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


@router.get("/")
async def index(request: Request, db: Session = Depends(get_db)):
    """Home/landing page."""
    hospitals = db.query(Hospital).filter(Hospital.is_active == True).order_by(Hospital.name).all()
    total_patients = db.query(Patient).count()
    total_hospitals = db.query(Hospital).filter(Hospital.is_active == True).count()
    total_appointments = db.query(Appointment).count()
    high_risk_visits = db.query(Visit).filter(Visit.prediction == "High Risk").count()
    
    # Get user from cookies if logged in
    user = None
    username = request.cookies.get("username")
    if username:
        user = db.query(User).filter(User.username == username).first()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "hospitals": hospitals,
        "total_patients": total_patients,
        "total_hospitals": total_hospitals,
        "total_appointments": total_appointments,
        "high_risk_visits": high_risk_visits
    })


# =============================================================================
# Hospital Registration Request Routes
# =============================================================================

@router.get("/hospital/register")
async def hospital_register_page(request: Request):
    """Hospital registration page."""
    return templates.TemplateResponse("hospital_register.html", {
        "request": request
    })


@router.post("/hospital/request")
async def submit_hospital_request(
    request: Request,
    hospital_name: str = Form(...),
    address: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    contact_person: str = Form(...),
    total_beds: int = Form(...),
    db: Session = Depends(get_db)
):
    """Submit hospital registration request."""
    # Check if hospital already exists
    existing = db.query(Hospital).filter(Hospital.name == hospital_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Hospital with this name already exists")
    
    # Check for pending request
    pending = db.query(HospitalRequest).filter(
        HospitalRequest.hospital_name == hospital_name,
        HospitalRequest.status == "Pending"
    ).first()
    if pending:
        raise HTTPException(status_code=400, detail="A request for this hospital is already pending")
    
    # Create request
    hospital_request = HospitalRequest(
        hospital_name=hospital_name,
        address=address,
        phone=phone,
        email=email,
        contact_person=contact_person,
        total_beds=total_beds,
        status="Pending"
    )
    db.add(hospital_request)
    db.commit()
    
    return RedirectResponse(url="/hospital/register?success=true", status_code=status.HTTP_302_FOUND)


@router.get("/admin/hospital-requests")
async def admin_hospital_requests(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("admin"))
):
    """Admin: View all hospital registration requests."""
    pending_requests = db.query(HospitalRequest).filter(
        HospitalRequest.status == "Pending"
    ).order_by(HospitalRequest.requested_at.desc()).all()
    
    processed_requests = db.query(HospitalRequest).filter(
        HospitalRequest.status != "Pending"
    ).order_by(HospitalRequest.requested_at.desc()).limit(20).all()
    
    return templates.TemplateResponse("hospital_requests.html", {
        "request": request,
        "user": user,
        "pending_requests": pending_requests,
        "processed_requests": processed_requests
    })


@router.post("/admin/hospital-request/{request_id}/approve")
async def approve_hospital_request(
    request_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("admin"))
):
    """Admin: Approve hospital registration request."""
    hospital_request = db.query(HospitalRequest).filter(HospitalRequest.id == request_id).first()
    if not hospital_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Create the hospital
    hospital = Hospital(
        name=hospital_request.hospital_name,
        address=hospital_request.address,
        phone=hospital_request.phone,
        email=hospital_request.email,
        total_beds=hospital_request.total_beds,
        available_beds=hospital_request.total_beds,
        is_active=True,
        approved=True
    )
    db.add(hospital)
    
    # Update request status
    hospital_request.status = "Approved"
    hospital_request.processed_at = datetime.utcnow()
    hospital_request.processed_by = user.id
    db.commit()
    
    return RedirectResponse(url="/admin/hospital-requests", status_code=status.HTTP_302_FOUND)


@router.post("/admin/hospital-request/{request_id}/reject")
async def reject_hospital_request(
    request_id: int,
    request: Request,
    admin_notes: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("admin"))
):
    """Admin: Reject hospital registration request."""
    hospital_request = db.query(HospitalRequest).filter(HospitalRequest.id == request_id).first()
    if not hospital_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    hospital_request.status = "Rejected"
    hospital_request.admin_notes = admin_notes
    hospital_request.processed_at = datetime.utcnow()
    hospital_request.processed_by = user.id
    db.commit()
    
    return RedirectResponse(url="/admin/hospital-requests", status_code=status.HTTP_302_FOUND)


# =============================================================================
# Patient Routes
# =============================================================================

@router.get("/patient/dashboard")
async def patient_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("patient"))
):
    """Patient dashboard."""
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    
    if not patient:
        return RedirectResponse(url="/profile/create", status_code=status.HTTP_302_FOUND)
    
    visits = db.query(Visit).filter(Visit.patient_id == patient.id).order_by(desc(Visit.created_at)).limit(5).all()
    appointments = db.query(Appointment).filter(Appointment.patient_id == patient.id).order_by(desc(Appointment.id)).limit(5).all()
    alerts = db.query(Alert).filter(Alert.patient_id == patient.id).order_by(desc(Alert.timestamp)).limit(10).all()
    
    return templates.TemplateResponse("patient_dashboard.html", {
        "request": request,
        "user": user,
        "patient": patient,
        "visits": visits,
        "appointments": appointments,
        "alerts": alerts
    })


@router.get("/profile/create")
async def create_profile_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("patient"))
):
    """Create patient profile page."""
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    return templates.TemplateResponse("create_profile.html", {
        "request": request,
        "user": user,
        "patient": patient
    })


@router.post("/profile/create")
async def create_profile(
    request: Request,
    full_name: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
    phone: str = Form(""),
    address: str = Form(""),
    date_of_birth: str = Form(""),
    blood_type: str = Form(""),
    emergency_contact: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("patient"))
):
    """Create or update patient profile."""
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    
    if patient:
        patient.full_name = full_name
        patient.age = age
        patient.gender = gender
        patient.phone = phone
        patient.address = address
        patient.date_of_birth = date_of_birth
        patient.blood_type = blood_type
        patient.emergency_contact = emergency_contact
    else:
        patient = Patient(
            user_id=user.id,
            full_name=full_name,
            age=age,
            gender=gender,
            phone=phone,
            address=address,
            date_of_birth=date_of_birth,
            blood_type=blood_type,
            emergency_contact=emergency_contact
        )
        db.add(patient)
    
    db.commit()
    return RedirectResponse(url="/patient/dashboard", status_code=status.HTTP_302_FOUND)


@router.get("/hospitals")
async def hospitals_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_user_from_cookies)
):
    """List all hospitals."""
    hospitals = db.query(Hospital).filter(Hospital.is_active == True).order_by(Hospital.name).all()
    return templates.TemplateResponse("hospitals.html", {
        "request": request,
        "user": user,
        "hospitals": hospitals
    })


@router.get("/book")
async def book_appointment_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("patient"))
):
    """Book appointment page."""
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        return RedirectResponse(url="/profile/create", status_code=status.HTTP_302_FOUND)
    
    hospitals = db.query(Hospital).filter(Hospital.is_active == True).order_by(Hospital.name).all()
    departments = db.query(Department).all()
    doctors = db.query(Doctor).filter(Doctor.is_available == True).all()
    
    return templates.TemplateResponse("book.html", {
        "request": request,
        "user": user,
        "hospitals": hospitals,
        "departments": departments,
        "doctors": doctors
    })


@router.post("/book")
async def book_appointment(
    request: Request,
    hospital_id: int = Form(...),
    doctor_id: int = Form(None),
    date: str = Form(...),
    time: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("patient"))
):
    """Book an appointment."""
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        return RedirectResponse(url="/profile/create", status_code=status.HTTP_302_FOUND)
    
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    
    # Create appointment
    appointment = Appointment(
        patient_id=patient.id,
        hospital_id=hospital.id,
        doctor_id=doctor_id,
        date=date,
        time=time,
        status="Booked",
        notes=notes
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"SMARTHMS:APPOINTMENT:{appointment.id}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code
    qr_folder = os.path.join("static", "qr_codes")
    os.makedirs(qr_folder, exist_ok=True)
    filepath = os.path.join(qr_folder, f"appointment_{appointment.id}.png")
    img.save(filepath)
    appointment.qr_code = f"qr_codes/appointment_{appointment.id}.png"
    db.commit()
    
    return RedirectResponse(url=f"/appointments?booked=success&token={request.query_params.get('token', '')}", status_code=status.HTTP_302_FOUND)


@router.get("/appointments")
async def appointments_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("patient"))
):
    """View patient appointments."""
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        return RedirectResponse(url="/profile/create", status_code=status.HTTP_302_FOUND)
    
    appointments = db.query(Appointment).filter(
        Appointment.patient_id == patient.id
    ).order_by(desc(Appointment.id)).all()
    
    return templates.TemplateResponse("appointments.html", {
        "request": request,
        "user": user,
        "appointments": appointments
    })


@router.get("/scan/{appointment_id}")
async def scan_appointment_get(
    appointment_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Mark appointment as arrived via QR scan (GET method)."""
    return await scan_appointment_internal(appointment_id, request, db)


@router.post("/scan/{appointment_id}")
async def scan_appointment_post(
    appointment_id: int,
    request: Request,
    token: str = Form(None),
    db: Session = Depends(get_db)
):
    """Mark appointment as arrived via check-in button (POST method)."""
    return await scan_appointment_internal(appointment_id, request, db, token)


async def scan_appointment_internal(
    appointment_id: int,
    request: Request,
    db: Session,
    token: str = None
):
    """Internal function to mark appointment as arrived."""
    # Try to get token from query param if not provided
    if not token:
        token = request.query_params.get("token")
    
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    appointment.status = "Arrived"
    db.commit()
    
    # Redirect to patient dashboard with token
    redirect_url = f"/patient/dashboard?token={token}" if token else "/patient/dashboard"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


# =============================================================================
# Doctor Routes
# =============================================================================

@router.get("/doctor/dashboard")
async def doctor_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("doctor"))
):
    """Doctor dashboard."""
    # Get the doctor profile
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    
    filter_status = request.query_params.get("status", "all")
    filter_risk = request.query_params.get("risk", "all")
    
    # Query visits (patients who did health assessment)
    query = db.query(Visit).join(Patient).order_by(desc(Visit.risk_score), desc(Visit.created_at))
    
    if filter_status != "all":
        query = query.filter(Visit.status == filter_status)
    if filter_risk == "high":
        query = query.filter(Visit.prediction == "High Risk")
    elif filter_risk == "moderate":
        query = query.filter(Visit.prediction == "Moderate Risk")
    elif filter_risk == "low":
        query = query.filter(Visit.prediction == "Low Risk")
    
    all_visits = query.all()
    
    # Get appointments for this doctor
    appointments = []
    if doctor:
        appointments = db.query(Appointment).filter(
            Appointment.doctor_id == doctor.id
        ).order_by(Appointment.date).all()
    
    pending_count = db.query(Visit).filter(Visit.status == "Pending Review").count()
    under_treatment_count = db.query(Visit).filter(Visit.status == "Under Treatment").count()
    treated_count = db.query(Visit).filter(Visit.status == "Treated").count()
    high_risk_count = db.query(Visit).filter(Visit.prediction == "High Risk").count()
    
    return templates.TemplateResponse("doctor_dashboard.html", {
        "request": request,
        "user": user,
        "all_visits": all_visits,
        "appointments": appointments,
        "pending_count": pending_count,
        "under_treatment_count": under_treatment_count,
        "treated_count": treated_count,
        "high_risk_count": high_risk_count,
        "filter_status": filter_status,
        "filter_risk": filter_risk,
        "DISEASE_CATEGORIES": DISEASE_CATEGORIES
    })


@router.get("/doctor/visit/{visit_id}")
async def doctor_visit_detail(
    request: Request,
    visit_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("doctor"))
):
    """View patient visit details."""
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    
    patient = db.query(Patient).filter(Patient.id == visit.patient_id).first()
    
    try:
        detected_conditions = json.loads(visit.predicted_conditions) if visit.predicted_conditions else []
    except:
        detected_conditions = []
    
    try:
        suggested_tests = json.loads(visit.suggested_tests) if visit.suggested_tests else []
    except:
        suggested_tests = []
    
    lab_tests = db.query(LabTest).filter(LabTest.patient_id == visit.patient_id).order_by(desc(LabTest.created_at)).all()
    treatments = db.query(Treatment).filter(Treatment.patient_id == visit.patient_id).order_by(desc(Treatment.created_at)).all()
    
    return templates.TemplateResponse("doctor_visit_detail.html", {
        "request": request,
        "user": user,
        "visit": visit,
        "patient": patient,
        "detected_conditions": detected_conditions,
        "suggested_tests": suggested_tests,
        "lab_tests": lab_tests,
        "treatments": treatments,
        "DISEASE_CATEGORIES": DISEASE_CATEGORIES
    })


@router.post("/doctor/visit/{visit_id}")
async def update_visit(
    request: Request,
    visit_id: int,
    action: str = Form(...),
    status: str = Form(None),
    diagnosis: str = Form(""),
    treatment_plan: str = Form(""),
    doctor_notes: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("doctor"))
):
    """Update visit diagnosis and treatment."""
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    
    if action == "update_status" and status:
        if status in ["Pending Review", "Under Treatment", "Treated", "Follow-up Required"]:
            visit.status = status
            visit.diagnosis = diagnosis
            visit.treatment_plan = treatment_plan
            visit.doctor_notes = doctor_notes
            visit.reviewed_by = user.id
            visit.reviewed_at = datetime.utcnow()
            db.commit()
            
            # Create alert for patient
            patient = db.query(Patient).filter(Patient.id == visit.patient_id).first()
            if patient and user:
                alert = Alert(
                    patient_id=patient.id,
                    message=f"Your visit status has been updated to: {status}"
                )
                db.add(alert)
                db.commit()
    
    return RedirectResponse(url=f"/doctor/visit/{visit_id}", status_code=status.HTTP_302_FOUND)


@router.post("/doctor/lab-request")
async def create_lab_request(
    request: Request,
    patient_id: int = Form(...),
    test_name: str = Form(...),
    test_type: str = Form("Blood"),
    priority: str = Form("Normal"),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("doctor"))
):
    """Create lab test request."""
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not doctor:
        raise HTTPException(status_code=400, detail="Doctor profile not found")
    
    lab_test = LabTest(
        patient_id=patient_id,
        doctor_id=doctor.id,
        test_name=test_name,
        test_type=test_type,
        priority=priority,
        notes=notes,
        status="Pending"
    )
    db.add(lab_test)
    db.commit()
    
    return RedirectResponse(url=f"/doctor/dashboard", status_code=status.HTTP_302_FOUND)


# =============================================================================
# Nurse Routes
# =============================================================================

@router.get("/nurse/dashboard")
async def nurse_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("nurse"))
):
    """Nurse dashboard."""
    nurse = db.query(Nurse).filter(Nurse.user_id == user.id).first()
    if not nurse:
        # Redirect to profile creation if no nurse profile exists
        return RedirectResponse(url=f"/staff/profile/create?token={request.query_params.get('token', '')}", status_code=status.HTTP_302_FOUND)
    
    # Get today's appointments at nurse's hospital - arrived patients
    appointments = db.query(Appointment).filter(
        Appointment.hospital_id == nurse.hospital_id,
        Appointment.status == "Arrived"
    ).order_by(Appointment.date).all()
    
    # Get recent visits created by this nurse for reference
    recent_vitals = db.query(Vitals).filter(
        Vitals.nurse_id == nurse.id
    ).order_by(Vitals.recorded_at.desc()).limit(10).all()
    
    return templates.TemplateResponse("nurse_dashboard.html", {
        "request": request,
        "user": user,
        "nurse": nurse,
        "appointments": appointments,
        "recent_vitals": recent_vitals
    })


@router.get("/nurse/record-vitals")
async def record_vitals_page(
    request: Request,
    appointment_id: int = None,
    patient_id: int = None,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("nurse"))
):
    """Record patient vitals page."""
    patient = None
    appointment = None
    
    if appointment_id:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if appointment:
            patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()
    elif patient_id:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
    
    return templates.TemplateResponse("nurse_vitals.html", {
        "request": request,
        "user": user,
        "patient": patient,
        "appointment": appointment
    })


@router.post("/nurse/record-vitals")
async def record_vitals(
    request: Request,
    patient_id: int = Form(...),
    appointment_id: int = Form(None),
    blood_pressure_systolic: float = Form(120),
    blood_pressure_diastolic: float = Form(80),
    heart_rate: float = Form(72),
    respiratory_rate: float = Form(16),
    temperature: float = Form(98.6),
    oxygen_saturation: float = Form(98),
    weight: float = Form(0),
    height: float = Form(0),
    glucose: float = Form(0),
    cholesterol: float = Form(0),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("nurse"))
):
    """Record patient vitals."""
    nurse = db.query(Nurse).filter(Nurse.user_id == user.id).first()
    if not nurse:
        raise HTTPException(status_code=400, detail="Nurse profile not found")
    
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Calculate BMI
    bmi = 0
    if weight > 0 and height > 0:
        height_m = height / 100
        bmi = round(weight / (height_m * height_m), 1)
    
    # Quick risk assessment
    vitals_data = {
        "blood_pressure_systolic": blood_pressure_systolic,
        "heart_rate": heart_rate,
        "oxygen_saturation": oxygen_saturation,
        "bmi": bmi,
        "glucose": glucose,
        "cholesterol": cholesterol
    }
    risk_result = quick_risk_assessment(vitals_data)
    
    # Create vitals record
    vitals = Vitals(
        patient_id=patient_id,
        nurse_id=nurse.id,
        appointment_id=appointment_id,
        blood_pressure_systolic=blood_pressure_systolic,
        blood_pressure_diastolic=blood_pressure_diastolic,
        heart_rate=heart_rate,
        respiratory_rate=respiratory_rate,
        temperature=temperature,
        oxygen_saturation=oxygen_saturation,
        weight=weight,
        height=height,
        bmi=bmi,
        glucose=glucose,
        cholesterol=cholesterol,
        risk_score=risk_result["risk_score"],
        risk_level=risk_result["risk_level"]
    )
    db.add(vitals)
    
    # Create alert for high risk
    if risk_result["risk_level"] == "High Risk":
        alert = Alert(
            patient_id=patient_id,
            message=f"High risk vitals recorded. Score: {risk_result['risk_score']}",
            alert_type="Critical"
        )
        db.add(alert)
    
    # If there was an appointment, update its status to completed
    if appointment_id:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if appointment:
            appointment.status = "Completed"
    
    db.commit()
    
    return RedirectResponse(url="/nurse/dashboard", status_code=status.HTTP_302_FOUND)


# Nurse Health Assessment Route
@router.get("/nurse/visit")
async def nurse_visit_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("nurse"))
):
    """Nurse health assessment page - for recording patient health data."""
    nurse = db.query(Nurse).filter(Nurse.user_id == user.id).first()
    if not nurse:
        raise HTTPException(status_code=400, detail="Nurse profile not found")
    
    # Get all patients
    patients = db.query(Patient).all()
    doctors = db.query(Doctor).filter(Doctor.hospital_id == nurse.hospital_id).all()
    
    return templates.TemplateResponse("nurse_visit.html", {
        "request": request,
        "user": user,
        "patients": patients,
        "doctors": doctors
    })


@router.post("/nurse/visit")
async def nurse_submit_visit(
    request: Request,
    patient_id: int = Form(...),
    doctor_id: int = Form(None),
    pregnancies: int = Form(0),
    glucose: float = Form(0),
    blood_pressure: float = Form(0),
    skin_thickness: float = Form(0),
    insulin: float = Form(0),
    bmi: float = Form(0),
    dpf: float = Form(0),
    age: int = Form(0),
    heart_rate: float = Form(0),
    respiratory_rate: float = Form(0),
    oxygen_saturation: float = Form(98),
    cholesterol: float = Form(0),
    hdl: float = Form(0),
    ldl: float = Form(0),
    triglycerides: float = Form(0),
    creatinine: float = Form(0),
    urea: float = Form(0),
    alt: float = Form(0),
    ast: float = Form(0),
    hemoglobin: float = Form(0),
    chest_pain: bool = Form(False),
    shortness_of_breath: bool = Form(False),
    fatigue: bool = Form(False),
    swelling: bool = Form(False),
    smoking: bool = Form(False),
    family_history: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("nurse"))
):
    """Submit health assessment from nurse."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Build feature dict for AI assessment
    feature_dict = {
        "pregnancies": pregnancies,
        "glucose": glucose,
        "blood_pressure": blood_pressure,
        "skin_thickness": skin_thickness,
        "insulin": insulin,
        "bmi": bmi,
        "dpf": dpf,
        "age": age or patient.age,
        "heart_rate": heart_rate,
        "respiratory_rate": respiratory_rate,
        "oxygen_saturation": oxygen_saturation,
        "cholesterol": cholesterol,
        "hdl": hdl,
        "ldl": ldl,
        "triglycerides": triglycerides,
        "creatinine": creatinine,
        "urea": urea,
        "alt": alt,
        "ast": ast,
        "hemoglobin": hemoglobin,
        "chest_pain": chest_pain,
        "shortness_of_breath": shortness_of_breath,
        "fatigue": fatigue,
        "swelling": swelling,
        "smoking": smoking,
        "family_history": family_history
    }
    
    # Run AI assessment
    prediction_result = assess_health_risk(feature_dict, patient.age)
    
    # Create visit record
    visit = Visit(
        patient_id=patient.id,
        doctor_id=doctor_id,
        pregnancies=pregnancies,
        glucose=glucose,
        blood_pressure=blood_pressure,
        skin_thickness=skin_thickness,
        insulin=insulin,
        bmi=bmi,
        dpf=dpf,
        age=patient.age,
        heart_rate=heart_rate,
        respiratory_rate=respiratory_rate,
        oxygen_saturation=oxygen_saturation,
        cholesterol=cholesterol,
        hdl=hdl,
        ldl=ldl,
        triglycerides=triglycerides,
        creatinine=creatinine,
        urea=urea,
        alt=alt,
        ast=ast,
        hemoglobin=hemoglobin,
        chest_pain=chest_pain,
        shortness_of_breath=shortness_of_breath,
        fatigue=fatigue,
        swelling=swelling,
        smoking=smoking,
        family_history=family_history,
        prediction=prediction_result["overall_risk"],
        disease_type=prediction_result["primary_disease"],
        risk_score=prediction_result["risk_score"],
        predicted_conditions=json.dumps(prediction_result["detected_conditions"]),
        suggested_tests=json.dumps(prediction_result["suggested_tests"]),
        status="Pending Review"
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    
    # Create alert for high risk
    high_risk_triggered = False
    if prediction_result["overall_risk"] in ["High Risk", "Moderate Risk"]:
        conditions_list = [c["disease"] for c in prediction_result["detected_conditions"]]
        message = f"{prediction_result['overall_risk']} detected for: {', '.join(conditions_list)}"
        alert = Alert(patient_id=patient.id, message=message)
        db.add(alert)
        db.commit()
        high_risk_triggered = True
    
    return templates.TemplateResponse("result.html", {
        "request": request,
        "user": user,
        "patient": patient,
        "visit": visit,
        "prediction_result": prediction_result,
        "high_risk_triggered": high_risk_triggered
    })


# =============================================================================
# Lab Technician Routes
# =============================================================================

@router.get("/lab/dashboard")
async def lab_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("lab_tech"))
):
    """Lab technician dashboard."""
    pending_tests = db.query(LabTest).filter(LabTest.status == "Pending").order_by(LabTest.created_at).all()
    in_progress_tests = db.query(LabTest).filter(LabTest.status == "In Progress").order_by(LabTest.created_at).all()
    completed_tests = db.query(LabTest).filter(LabTest.status == "Completed").order_by(LabTest.completed_at.desc()).limit(20).all()
    
    return templates.TemplateResponse("lab_dashboard.html", {
        "request": request,
        "user": user,
        "pending_tests": pending_tests,
        "in_progress_tests": in_progress_tests,
        "completed_tests": completed_tests
    })


@router.post("/lab/update-test")
async def update_lab_test(
    request: Request,
    test_id: int = Form(...),
    action: str = Form(...),
    findings: str = Form(""),
    recommendations: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("lab_tech"))
):
    """Update lab test status and upload report."""
    lab_test = db.query(LabTest).filter(LabTest.id == test_id).first()
    if not lab_test:
        raise HTTPException(status_code=404, detail="Lab test not found")
    
    if action == "start":
        lab_test.status = "In Progress"
    elif action == "complete":
        lab_test.status = "Completed"
        lab_test.completed_at = datetime.utcnow()
        
        # Create lab report
        report = LabReport(
            lab_test_id=lab_test.id,
            patient_id=lab_test.patient_id,
            technician_id=user.id,
            findings=findings,
            recommendations=recommendations,
            is_abnormal=bool(findings and ("abnormal" in findings.lower() or "high" in findings.lower() or "low" in findings.lower()))
        )
        db.add(report)
        
        # Notify patient
        alert = Alert(
            patient_id=lab_test.patient_id,
            message=f"Your lab test '{lab_test.test_name}' results are ready"
        )
        db.add(alert)
    
    db.commit()
    
    return RedirectResponse(url="/lab/dashboard", status_code=status.HTTP_302_FOUND)


# =============================================================================
# Admin Routes
# =============================================================================

@router.get("/admin/dashboard")
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("admin", "hospital_admin"))
):
    """Admin dashboard."""
    hospitals = db.query(Hospital).order_by(Hospital.name).all()
    total_patients = db.query(Patient).count()
    total_hospitals = db.query(Hospital).filter(Hospital.is_active == True).count()
    total_appointments = db.query(Appointment).count()
    high_risk_alerts = db.query(Alert).order_by(Alert.timestamp.desc()).limit(20).all()
    
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "user": user,
        "hospitals": hospitals,
        "total_patients": total_patients,
        "total_hospitals": total_hospitals,
        "total_appointments": total_appointments,
        "high_risk_alerts": high_risk_alerts
    })


@router.post("/admin/hospital")
async def manage_hospital(
    request: Request,
    name: str = Form(...),
    total_beds: int = Form(...),
    available_beds: int = Form(...),
    address: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    hospital_id: int = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("admin"))
):
    """Add or update hospital."""
    if hospital_id:
        hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
        if hospital:
            hospital.name = name
            hospital.total_beds = total_beds
            hospital.available_beds = available_beds
            hospital.address = address
            hospital.phone = phone
            hospital.email = email
    else:
        hospital = Hospital(
            name=name,
            total_beds=total_beds,
            available_beds=available_beds,
            address=address,
            phone=phone,
            email=email
        )
        db.add(hospital)
    
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)


@router.post("/admin/hospital/{hospital_id}/toggle")
async def toggle_hospital(
    hospital_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("admin"))
):
    """Toggle hospital active status."""
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if hospital:
        hospital.is_active = not hospital.is_active
        db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)


@router.post("/admin/hospital/{hospital_id}/approve")
async def approve_hospital(
    hospital_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("admin"))
):
    """Approve hospital onboarding."""
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if hospital:
        hospital.approved = True
        db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)


# =============================================================================
# Hospital ERP Admin Routes
# =============================================================================

@router.get("/hospital/manage")
async def hospital_manage(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("hospital_admin"))
):
    """Hospital management page."""
    hospital_admin = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not hospital_admin:
        # Try to find via nurse
        hospital_admin = db.query(Nurse).filter(Nurse.user_id == user.id).first()
    
    hospital_id = hospital_admin.hospital_id if hospital_admin else None
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first() if hospital_id else None
    
    doctors = db.query(Doctor).filter(Doctor.hospital_id == hospital_id).all() if hospital_id else []
    nurses = db.query(Nurse).filter(Nurse.hospital_id == hospital_id).all() if hospital_id else []
    departments = db.query(Department).filter(Department.hospital_id == hospital_id).all() if hospital_id else []
    beds = db.query(Bed).filter(Bed.hospital_id == hospital_id).all() if hospital_id else []
    
    return templates.TemplateResponse("hospital_manage.html", {
        "request": request,
        "user": user,
        "hospital": hospital,
        "doctors": doctors,
        "nurses": nurses,
        "departments": departments,
        "beds": beds
    })


@router.post("/hospital/manage/department")
async def manage_department(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    department_id: int = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("hospital_admin"))
):
    """Add or update department."""
    hospital_admin = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not hospital_admin:
        hospital_admin = db.query(Nurse).filter(Nurse.user_id == user.id).first()
    
    hospital_id = hospital_admin.hospital_id if hospital_admin else None
    
    if department_id:
        dept = db.query(Department).filter(Department.id == department_id).first()
        if dept:
            dept.name = name
            dept.description = description
    else:
        dept = Department(name=name, hospital_id=hospital_id, description=description)
        db.add(dept)
    
    db.commit()
    return RedirectResponse(url="/hospital/manage", status_code=status.HTTP_302_FOUND)


@router.post("/hospital/manage/bed")
async def manage_bed(
    request: Request,
    ward: str = Form(...),
    room_number: str = Form(...),
    bed_number: str = Form(...),
    bed_type: str = Form("General"),
    bed_id: int = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("hospital_admin"))
):
    """Add or update bed."""
    hospital_admin = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not hospital_admin:
        hospital_admin = db.query(Nurse).filter(Nurse.user_id == user.id).first()
    
    hospital_id = hospital_admin.hospital_id if hospital_admin else None
    
    if bed_id:
        bed = db.query(Bed).filter(Bed.id == bed_id).first()
        if bed:
            bed.ward = ward
            bed.room_number = room_number
            bed.bed_number = bed_number
            bed.bed_type = bed_type
    else:
        bed = Bed(
            hospital_id=hospital_id,
            ward=ward,
            room_number=room_number,
            bed_number=bed_number,
            bed_type=bed_type,
            status="Available"
        )
        db.add(bed)
    
    db.commit()
    return RedirectResponse(url="/hospital/manage", status_code=status.HTTP_302_FOUND)


# =============================================================================
# API Routes for Cascading Dropdowns in Booking
# =============================================================================

@router.get("/api/hospitals/{hospital_id}/categories")
async def get_hospital_categories(
    hospital_id: int,
    db: Session = Depends(get_db)
):
    """Get unique categories/specializations available at a hospital."""
    # Get unique specializations for doctors at this hospital
    doctors = db.query(Doctor).filter(
        Doctor.hospital_id == hospital_id,
        Doctor.is_available == True,
        Doctor.specialization != None,
        Doctor.specialization != ""
    ).all()
    
    # Extract unique specializations
    categories = list(set([d.specialization for d in doctors if d.specialization]))
    categories.sort()
    
    return {"categories": categories}


@router.get("/api/hospitals/{hospital_id}/categories/{category}/doctors")
async def get_hospital_category_doctors(
    hospital_id: int,
    category: str,
    db: Session = Depends(get_db)
):
    """Get doctors by hospital and category/specialization."""
    doctors = db.query(Doctor).filter(
        Doctor.hospital_id == hospital_id,
        Doctor.specialization == category,
        Doctor.is_available == True
    ).all()
    
    doctor_list = []
    for doctor in doctors:
        doctor_list.append({
            "id": doctor.id,
            "full_name": doctor.full_name,
            "specialization": doctor.specialization
        })
    
    return {"doctors": doctor_list}


# =============================================================================
# Health Assessment (Patient self-assessment)
# =============================================================================

@router.get("/visit")
async def visit_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("patient"))
):
    """Health assessment form page."""
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        return RedirectResponse(url="/profile/create", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("visit.html", {
        "request": request,
        "user": user,
        "patient": patient
    })


@router.post("/visit")
async def submit_visit(
    request: Request,
    pregnancies: int = Form(0),
    glucose: float = Form(0),
    blood_pressure: float = Form(0),
    skin_thickness: float = Form(0),
    insulin: float = Form(0),
    bmi: float = Form(0),
    dpf: float = Form(0),
    age: int = Form(0),
    heart_rate: float = Form(0),
    respiratory_rate: float = Form(0),
    oxygen_saturation: float = Form(98),
    cholesterol: float = Form(0),
    hdl: float = Form(0),
    ldl: float = Form(0),
    triglycerides: float = Form(0),
    creatinine: float = Form(0),
    urea: float = Form(0),
    alt: float = Form(0),
    ast: float = Form(0),
    hemoglobin: float = Form(0),
    chest_pain: bool = Form(False),
    shortness_of_breath: bool = Form(False),
    fatigue: bool = Form(False),
    swelling: bool = Form(False),
    smoking: bool = Form(False),
    family_history: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("patient"))
):
    """Submit health assessment."""
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        return RedirectResponse(url="/profile/create", status_code=status.HTTP_302_FOUND)
    
    # Build feature dict for AI assessment
    feature_dict = {
        "pregnancies": pregnancies,
        "glucose": glucose,
        "blood_pressure": blood_pressure,
        "skin_thickness": skin_thickness,
        "insulin": insulin,
        "bmi": bmi,
        "dpf": dpf,
        "age": age or patient.age,
        "heart_rate": heart_rate,
        "respiratory_rate": respiratory_rate,
        "oxygen_saturation": oxygen_saturation,
        "cholesterol": cholesterol,
        "hdl": hdl,
        "ldl": ldl,
        "triglycerides": triglycerides,
        "creatinine": creatinine,
        "urea": urea,
        "alt": alt,
        "ast": ast,
        "hemoglobin": hemoglobin,
        "chest_pain": chest_pain,
        "shortness_of_breath": shortness_of_breath,
        "fatigue": fatigue,
        "swelling": swelling,
        "smoking": smoking,
        "family_history": family_history
    }
    
    # Run AI assessment
    prediction_result = assess_health_risk(feature_dict, patient.age)
    
    # Create visit record
    visit = Visit(
        patient_id=patient.id,
        pregnancies=pregnancies,
        glucose=glucose,
        blood_pressure=blood_pressure,
        skin_thickness=skin_thickness,
        insulin=insulin,
        bmi=bmi,
        dpf=dpf,
        age=patient.age,
        heart_rate=heart_rate,
        respiratory_rate=respiratory_rate,
        oxygen_saturation=oxygen_saturation,
        cholesterol=cholesterol,
        hdl=hdl,
        ldl=ldl,
        triglycerides=triglycerides,
        creatinine=creatinine,
        urea=urea,
        alt=alt,
        ast=ast,
        hemoglobin=hemoglobin,
        chest_pain=chest_pain,
        shortness_of_breath=shortness_of_breath,
        fatigue=fatigue,
        swelling=swelling,
        smoking=smoking,
        family_history=family_history,
        prediction=prediction_result["overall_risk"],
        disease_type=prediction_result["primary_disease"],
        risk_score=prediction_result["risk_score"],
        predicted_conditions=json.dumps(prediction_result["detected_conditions"]),
        suggested_tests=json.dumps(prediction_result["suggested_tests"]),
        status="Pending Review"
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    
    # Create alert for high risk
    high_risk_triggered = False
    if prediction_result["overall_risk"] in ["High Risk", "Moderate Risk"]:
        conditions_list = [c["disease"] for c in prediction_result["detected_conditions"]]
        message = f"{prediction_result['overall_risk']} detected for: {', '.join(conditions_list)}"
        alert = Alert(patient_id=patient.id, message=message)
        db.add(alert)
        db.commit()
        high_risk_triggered = True
    
    return templates.TemplateResponse("result.html", {
        "request": request,
        "user": user,
        "patient": patient,
        "visit": visit,
        "prediction_result": prediction_result,
        "high_risk_triggered": high_risk_triggered
    })

