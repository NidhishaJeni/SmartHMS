import os
import json
from datetime import datetime
from functools import wraps

import joblib
import qrcode
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from models import User, Patient, Hospital, Appointment, Visit, Alert


auth_bp = Blueprint("auth", __name__)
main_bp = Blueprint("main", __name__)
automation_bp = Blueprint("automation", __name__)

# ============================================================================
# Disease Categories and Diagnostic Tests Configuration
# ============================================================================

DISEASE_CATEGORIES = {
    "diabetes": {
        "name": "Diabetes Mellitus",
        "description": "High blood sugar levels due to insulin resistance or deficiency",
        "tests": ["Fasting Blood Glucose", "HbA1c Test", "Oral Glucose Tolerance Test (OGTT)", "Random Blood Sugar", "Urine Analysis"]
    },
    "cardiovascular": {
        "name": "Cardiovascular Disease",
        "description": "Heart and blood vessel conditions including coronary artery disease",
        "tests": ["ECG/EKG", "Echocardiogram", "Lipid Profile", "Cardiac Enzyme Test (Troponin)", "Stress Test", "Chest X-Ray", "CT Angiography"]
    },
    "hypertension": {
        "name": "Hypertension",
        "description": "Chronic high blood pressure",
        "tests": ["24-Hour Blood Pressure Monitoring", "Urinalysis", "Blood Chemistry Panel", "ECG", "Kidney Function Test"]
    },
    "respiratory": {
        "name": "Respiratory Disease",
        "description": "Conditions affecting the lungs and breathing",
        "tests": ["Chest X-Ray", "Pulmonary Function Test (Spirometry)", "Arterial Blood Gas (ABG)", "CT Scan Chest", "Pulse Oximetry", "Sputum Culture"]
    },
    "kidney": {
        "name": "Kidney Disease",
        "description": "Chronic kidney disease or renal dysfunction",
        "tests": ["Serum Creatinine", "Blood Urea Nitrogen (BUN)", "GFR Test", "Urinalysis", "Kidney Ultrasound", "Urine Protein Test"]
    },
    "liver": {
        "name": "Liver Disease",
        "description": "Hepatic conditions including fatty liver and cirrhosis",
        "tests": ["Liver Function Test (LFT)", "ALT/AST Levels", "Bilirubin Test", "Liver Ultrasound", "Hepatitis Panel", "Albumin Test"]
    },
    "anemia": {
        "name": "Anemia",
        "description": "Low hemoglobin or red blood cell count",
        "tests": ["Complete Blood Count (CBC)", "Iron Studies", "Vitamin B12 Level", "Folate Level", "Reticulocyte Count", "Peripheral Blood Smear"]
    },
    "thyroid": {
        "name": "Thyroid Disorder",
        "description": "Hypothyroidism or hyperthyroidism",
        "tests": ["TSH Test", "T3 and T4 Levels", "Thyroid Ultrasound", "Thyroid Antibodies Test"]
    }
}


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.role not in roles:
                flash("You do not have access to this page.", "danger")
                return redirect(url_for("main.index"))
            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator


def load_diabetes_model():
    model_path = current_app.config.get("DIABETES_MODEL_PATH")
    if model_path and os.path.exists(model_path):
        try:
            return joblib.load(model_path)
        except Exception:
            current_app.logger.warning("Failed to load diabetes model, falling back to rule-based scorer.")
    return None


def simple_risk_scorer(features):
    """
    Simple heuristic fallback if pre-trained model is not available.
    `features` is a dict with the 8 diabetes-related parameters.
    """
    score = 0
    if features["glucose"] >= 140:
        score += 2
    if features["bmi"] >= 30:
        score += 2
    if features["age"] >= 50:
        score += 1
    if features["blood_pressure"] >= 90:
        score += 1
    return "High Risk" if score >= 3 else "Low Risk"


def comprehensive_disease_predictor(features):
    """
    Comprehensive multi-disease risk assessment.
    Returns dict with detected conditions, risk levels, and suggested tests.
    """
    detected_conditions = []
    all_suggested_tests = set()
    total_risk_score = 0
    primary_disease = "General"
    
    # 1. Diabetes Risk Assessment
    diabetes_score = 0
    if features.get("glucose", 0) >= 126:
        diabetes_score += 30
    elif features.get("glucose", 0) >= 100:
        diabetes_score += 15
    if features.get("bmi", 0) >= 30:
        diabetes_score += 20
    elif features.get("bmi", 0) >= 25:
        diabetes_score += 10
    if features.get("age", 0) >= 45:
        diabetes_score += 10
    if features.get("dpf", 0) >= 0.5:
        diabetes_score += 15
    if features.get("insulin", 0) <= 30 and features.get("glucose", 0) >= 100:
        diabetes_score += 10
    
    if diabetes_score >= 40:
        detected_conditions.append({
            "disease": "Diabetes Mellitus",
            "risk_level": "High Risk" if diabetes_score >= 60 else "Moderate Risk",
            "score": min(diabetes_score, 100),
            "key_indicators": ["High glucose", "Elevated BMI", "Age factor"]
        })
        all_suggested_tests.update(DISEASE_CATEGORIES["diabetes"]["tests"])
        if diabetes_score > total_risk_score:
            total_risk_score = diabetes_score
            primary_disease = "Diabetes"
    
    # 2. Cardiovascular Disease Risk Assessment
    cardio_score = 0
    if features.get("cholesterol", 0) >= 240:
        cardio_score += 25
    elif features.get("cholesterol", 0) >= 200:
        cardio_score += 15
    if features.get("ldl", 0) >= 160:
        cardio_score += 20
    if features.get("hdl", 0) <= 40:
        cardio_score += 15
    if features.get("blood_pressure", 0) >= 140:
        cardio_score += 20
    if features.get("chest_pain", False):
        cardio_score += 25
    if features.get("shortness_of_breath", False):
        cardio_score += 15
    if features.get("smoking", False):
        cardio_score += 15
    if features.get("age", 0) >= 55:
        cardio_score += 10
    if features.get("bmi", 0) >= 30:
        cardio_score += 10
    if "heart" in features.get("family_history", "").lower():
        cardio_score += 15
    
    if cardio_score >= 35:
        detected_conditions.append({
            "disease": "Cardiovascular Disease",
            "risk_level": "High Risk" if cardio_score >= 60 else "Moderate Risk",
            "score": min(cardio_score, 100),
            "key_indicators": ["Cholesterol levels", "Blood pressure", "Symptoms"]
        })
        all_suggested_tests.update(DISEASE_CATEGORIES["cardiovascular"]["tests"])
        if cardio_score > total_risk_score:
            total_risk_score = cardio_score
            primary_disease = "Cardiovascular"
    
    # 3. Hypertension Risk Assessment
    hypertension_score = 0
    bp = features.get("blood_pressure", 0)
    if bp >= 140:
        hypertension_score += 40
    elif bp >= 130:
        hypertension_score += 25
    elif bp >= 120:
        hypertension_score += 10
    if features.get("age", 0) >= 50:
        hypertension_score += 15
    if features.get("bmi", 0) >= 30:
        hypertension_score += 15
    if features.get("smoking", False):
        hypertension_score += 10
    if "hypertension" in features.get("family_history", "").lower():
        hypertension_score += 15
    
    if hypertension_score >= 40:
        detected_conditions.append({
            "disease": "Hypertension",
            "risk_level": "High Risk" if hypertension_score >= 60 else "Moderate Risk",
            "score": min(hypertension_score, 100),
            "key_indicators": ["Elevated blood pressure", "Age", "Lifestyle"]
        })
        all_suggested_tests.update(DISEASE_CATEGORIES["hypertension"]["tests"])
        if hypertension_score > total_risk_score:
            total_risk_score = hypertension_score
            primary_disease = "Hypertension"
    
    # 4. Respiratory Disease Risk Assessment
    respiratory_score = 0
    if features.get("oxygen_saturation", 100) <= 92:
        respiratory_score += 35
    elif features.get("oxygen_saturation", 100) <= 95:
        respiratory_score += 20
    if features.get("respiratory_rate", 0) >= 24:
        respiratory_score += 25
    elif features.get("respiratory_rate", 0) >= 20:
        respiratory_score += 10
    if features.get("shortness_of_breath", False):
        respiratory_score += 25
    if features.get("smoking", False):
        respiratory_score += 20
    if features.get("fatigue", False):
        respiratory_score += 10
    
    if respiratory_score >= 35:
        detected_conditions.append({
            "disease": "Respiratory Disease",
            "risk_level": "High Risk" if respiratory_score >= 60 else "Moderate Risk",
            "score": min(respiratory_score, 100),
            "key_indicators": ["Low oxygen saturation", "Breathing issues", "Smoking history"]
        })
        all_suggested_tests.update(DISEASE_CATEGORIES["respiratory"]["tests"])
        if respiratory_score > total_risk_score:
            total_risk_score = respiratory_score
            primary_disease = "Respiratory"
    
    # 5. Kidney Disease Risk Assessment
    kidney_score = 0
    if features.get("creatinine", 0) >= 1.5:
        kidney_score += 35
    elif features.get("creatinine", 0) >= 1.2:
        kidney_score += 20
    if features.get("urea", 0) >= 45:
        kidney_score += 25
    elif features.get("urea", 0) >= 25:
        kidney_score += 10
    if features.get("swelling", False):
        kidney_score += 20
    if features.get("blood_pressure", 0) >= 140:
        kidney_score += 15
    if features.get("glucose", 0) >= 126:  # Diabetes affects kidneys
        kidney_score += 10
    
    if kidney_score >= 35:
        detected_conditions.append({
            "disease": "Kidney Disease",
            "risk_level": "High Risk" if kidney_score >= 60 else "Moderate Risk",
            "score": min(kidney_score, 100),
            "key_indicators": ["Elevated creatinine", "High urea", "Edema"]
        })
        all_suggested_tests.update(DISEASE_CATEGORIES["kidney"]["tests"])
        if kidney_score > total_risk_score:
            total_risk_score = kidney_score
            primary_disease = "Kidney"
    
    # 6. Liver Disease Risk Assessment
    liver_score = 0
    if features.get("alt", 0) >= 56:
        liver_score += 30
    elif features.get("alt", 0) >= 40:
        liver_score += 15
    if features.get("ast", 0) >= 48:
        liver_score += 30
    elif features.get("ast", 0) >= 35:
        liver_score += 15
    if features.get("bmi", 0) >= 30:  # Fatty liver risk
        liver_score += 15
    if features.get("fatigue", False):
        liver_score += 10
    
    if liver_score >= 35:
        detected_conditions.append({
            "disease": "Liver Disease",
            "risk_level": "High Risk" if liver_score >= 60 else "Moderate Risk",
            "score": min(liver_score, 100),
            "key_indicators": ["Elevated liver enzymes", "BMI", "Fatigue"]
        })
        all_suggested_tests.update(DISEASE_CATEGORIES["liver"]["tests"])
        if liver_score > total_risk_score:
            total_risk_score = liver_score
            primary_disease = "Liver"
    
    # 7. Anemia Risk Assessment
    anemia_score = 0
    hemoglobin = features.get("hemoglobin", 14)  # Default to normal
    if hemoglobin > 0:
        if hemoglobin <= 8:
            anemia_score += 50
        elif hemoglobin <= 10:
            anemia_score += 35
        elif hemoglobin <= 12:
            anemia_score += 20
    if features.get("fatigue", False):
        anemia_score += 20
    if features.get("shortness_of_breath", False):
        anemia_score += 15
    
    if anemia_score >= 35:
        detected_conditions.append({
            "disease": "Anemia",
            "risk_level": "High Risk" if anemia_score >= 55 else "Moderate Risk",
            "score": min(anemia_score, 100),
            "key_indicators": ["Low hemoglobin", "Fatigue", "Breathing difficulty"]
        })
        all_suggested_tests.update(DISEASE_CATEGORIES["anemia"]["tests"])
        if anemia_score > total_risk_score:
            total_risk_score = anemia_score
            primary_disease = "Anemia"
    
    # Determine overall risk level
    if total_risk_score >= 60:
        overall_risk = "High Risk"
    elif total_risk_score >= 35:
        overall_risk = "Moderate Risk"
    else:
        overall_risk = "Low Risk"
    
    # If no specific conditions detected, provide general health check
    if not detected_conditions:
        all_suggested_tests = {"Complete Blood Count (CBC)", "Basic Metabolic Panel", "Lipid Profile", "Urinalysis"}
        detected_conditions.append({
            "disease": "General Health Check",
            "risk_level": "Low Risk",
            "score": total_risk_score,
            "key_indicators": ["No major concerns detected"]
        })
    
    return {
        "overall_risk": overall_risk,
        "risk_score": min(total_risk_score, 100),
        "primary_disease": primary_disease,
        "detected_conditions": detected_conditions,
        "suggested_tests": list(all_suggested_tests)
    }


def log_alert_and_notify(patient, message):
    alerts_log_path = current_app.config["ALERTS_LOG_PATH"]
    os.makedirs(os.path.dirname(alerts_log_path), exist_ok=True)

    timestamp = datetime.utcnow().isoformat()
    line = f"{timestamp} | PATIENT_ID={patient.id} | {message}\n"
    with open(alerts_log_path, "a", encoding="utf-8") as f:
        f.write(line)

    alert = Alert(patient_id=patient.id, message=message)
    db.session.add(alert)
    db.session.commit()

    # Fire internal automation webhook to keep architecture automation-ready.
    try:
        client = current_app.test_client()
        client.post(
            "/automation/alert",
            json={"patient_id": patient.id, "message": message},
        )
    except Exception:
        current_app.logger.warning("Failed to trigger automation webhook endpoint.")


def generate_qr_for_appointment(appointment):
    qr_folder = os.path.join(current_app.root_path, "static", "qr_codes")
    os.makedirs(qr_folder, exist_ok=True)
    scan_url = url_for("main.scan_appointment", appointment_id=appointment.id, _external=True)
    img = qrcode.make(scan_url)
    filename = f"appointment_{appointment.id}.png"
    filepath = os.path.join(qr_folder, filename)
    img.save(filepath)
    appointment.qr_code = f"qr_codes/{filename}"
    db.session.commit()


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "").strip()

        if not username or not password or role not in {"admin", "doctor", "patient"}:
            flash("Please provide username, password, and valid role.", "danger")
            return render_template("register.html")

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "warning")
            return render_template("register.html")

        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash("Invalid username or password.", "danger")
            return render_template("login.html")

        login_user(user)
        flash("Logged in successfully.", "success")

        if user.role == "admin":
            return redirect(url_for("main.admin_dashboard"))
        if user.role == "doctor":
            return redirect(url_for("main.doctor_dashboard"))
        return redirect(url_for("main.patient_dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


@main_bp.route("/")
def index():
    hospitals = Hospital.query.order_by(Hospital.name).all()
    total_patients = Patient.query.count()
    total_hospitals = Hospital.query.count()
    total_appointments = Appointment.query.count()
    high_risk_visits = Visit.query.filter_by(prediction="High Risk").count()
    return render_template(
        "index.html",
        hospitals=hospitals,
        total_patients=total_patients,
        total_hospitals=total_hospitals,
        total_appointments=total_appointments,
        high_risk_visits=high_risk_visits,
    )


@main_bp.route("/patient/dashboard")
@login_required
@role_required("patient")
def patient_dashboard():
    patient = current_user.patient
    visits = Visit.query.filter_by(patient_id=patient.id).order_by(Visit.created_at.desc()).limit(5).all()
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.id.desc()).limit(5).all()
    return render_template("patient_dashboard.html", patient=patient, visits=visits, appointments=appointments)


@main_bp.route("/doctor/dashboard")
@login_required
@role_required("doctor")
def doctor_dashboard():
    # Get filter parameter
    filter_status = request.args.get("status", "all")
    filter_risk = request.args.get("risk", "all")
    
    # Base query - order by risk score and creation date
    query = Visit.query.join(Patient).order_by(Visit.risk_score.desc(), Visit.created_at.desc())
    
    # Apply filters
    if filter_status != "all":
        query = query.filter(Visit.status == filter_status)
    if filter_risk == "high":
        query = query.filter(Visit.prediction == "High Risk")
    elif filter_risk == "moderate":
        query = query.filter(Visit.prediction == "Moderate Risk")
    elif filter_risk == "low":
        query = query.filter(Visit.prediction == "Low Risk")
    
    all_visits = query.all()
    
    # Statistics
    pending_count = Visit.query.filter_by(status="Pending Review").count()
    under_treatment_count = Visit.query.filter_by(status="Under Treatment").count()
    treated_count = Visit.query.filter_by(status="Treated").count()
    high_risk_count = Visit.query.filter_by(prediction="High Risk").count()
    
    return render_template(
        "doctor_dashboard.html",
        all_visits=all_visits,
        pending_count=pending_count,
        under_treatment_count=under_treatment_count,
        treated_count=treated_count,
        high_risk_count=high_risk_count,
        filter_status=filter_status,
        filter_risk=filter_risk,
        DISEASE_CATEGORIES=DISEASE_CATEGORIES,
    )


@main_bp.route("/doctor/visit/<int:visit_id>", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def doctor_view_visit(visit_id):
    visit_obj = Visit.query.get_or_404(visit_id)
    patient = visit_obj.patient
    
    # Parse JSON fields
    try:
        detected_conditions = json.loads(visit_obj.predicted_conditions) if visit_obj.predicted_conditions else []
    except:
        detected_conditions = []
    
    try:
        suggested_tests = json.loads(visit_obj.suggested_tests) if visit_obj.suggested_tests else []
    except:
        suggested_tests = []
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "update_status":
            new_status = request.form.get("status")
            diagnosis = request.form.get("diagnosis", "").strip()
            treatment_plan = request.form.get("treatment_plan", "").strip()
            doctor_notes = request.form.get("doctor_notes", "").strip()
            
            if new_status in ["Pending Review", "Under Treatment", "Treated", "Follow-up Required"]:
                visit_obj.status = new_status
                visit_obj.diagnosis = diagnosis
                visit_obj.treatment_plan = treatment_plan
                visit_obj.doctor_notes = doctor_notes
                visit_obj.reviewed_by = current_user.id
                visit_obj.reviewed_at = datetime.utcnow()
                db.session.commit()
                
                # Notify patient about status change
                if new_status == "Treated":
                    log_alert_and_notify(patient, f"Your visit has been marked as Treated by the doctor.")
                elif new_status == "Under Treatment":
                    log_alert_and_notify(patient, f"Your treatment has started. Please follow the prescribed plan.")
                elif new_status == "Follow-up Required":
                    log_alert_and_notify(patient, f"A follow-up visit is required. Please book an appointment.")
                
                flash(f"Visit status updated to '{new_status}'.", "success")
        
        return redirect(url_for("main.doctor_view_visit", visit_id=visit_id))
    
    return render_template(
        "doctor_visit_detail.html",
        visit=visit_obj,
        patient=patient,
        detected_conditions=detected_conditions,
        suggested_tests=suggested_tests,
        DISEASE_CATEGORIES=DISEASE_CATEGORIES,
    )


@main_bp.route("/admin/dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
    hospitals = Hospital.query.order_by(Hospital.name).all()
    total_patients = Patient.query.count()
    total_hospitals = Hospital.query.count()
    total_appointments = Appointment.query.count()
    high_risk_alerts = Alert.query.order_by(Alert.timestamp.desc()).limit(20).all()
    return render_template(
        "admin_dashboard.html",
        hospitals=hospitals,
        total_patients=total_patients,
        total_hospitals=total_hospitals,
        total_appointments=total_appointments,
        high_risk_alerts=high_risk_alerts,
    )


@main_bp.route("/profile/create", methods=["GET", "POST"])
@login_required
@role_required("patient")
def create_profile():
    if current_user.patient:
        flash("Profile already exists. You can update it below.", "info")

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        if not full_name or not age or gender not in {"Male", "Female", "Other"}:
            flash("Please provide full name, age, and gender.", "danger")
            return render_template("create_profile.html", patient=current_user.patient)

        try:
            age_val = int(age)
        except ValueError:
            flash("Age must be a valid number.", "danger")
            return render_template("create_profile.html", patient=current_user.patient)

        patient = current_user.patient or Patient(user_id=current_user.id, full_name=full_name, age=age_val, gender=gender)
        patient.full_name = full_name
        patient.age = age_val
        patient.gender = gender
        patient.phone = phone
        patient.address = address

        db.session.add(patient)
        db.session.commit()
        flash("Profile saved successfully.", "success")
        return redirect(url_for("main.patient_dashboard"))

    return render_template("create_profile.html", patient=current_user.patient)


@main_bp.route("/hospitals", methods=["GET", "POST"])
@login_required
def hospitals_view():
    if request.method == "POST" and current_user.role == "admin":
        name = request.form.get("name", "").strip()
        total_beds = request.form.get("total_beds", "").strip()
        available_beds = request.form.get("available_beds", "").strip()
        if not name or not total_beds or not available_beds:
            flash("Please provide hospital name and bed counts.", "danger")
        else:
            try:
                total = int(total_beds)
                available = int(available_beds)
            except ValueError:
                flash("Bed counts must be valid integers.", "danger")
                return redirect(url_for("main.hospitals_view"))

            hospital_id = request.form.get("hospital_id")
            if hospital_id:
                hospital = Hospital.query.get(int(hospital_id))
                if hospital:
                    hospital.name = name
                    hospital.total_beds = total
                    hospital.available_beds = available
                    flash("Hospital updated.", "success")
            else:
                hospital = Hospital(name=name, total_beds=total, available_beds=available)
                db.session.add(hospital)
                flash("Hospital added.", "success")
            db.session.commit()

    hospitals = Hospital.query.order_by(Hospital.name).all()
    return render_template("hospitals.html", hospitals=hospitals)


@main_bp.route("/book", methods=["GET", "POST"])
@login_required
@role_required("patient")
def book_appointment():
    patient = current_user.patient
    if not patient:
        flash("Please create your patient profile before booking.", "warning")
        return redirect(url_for("main.create_profile"))

    hospitals = Hospital.query.order_by(Hospital.name).all()
    recommendation = None

    if request.method == "POST":
        hospital_id = request.form.get("hospital_id")
        date = request.form.get("date", "").strip()

        if not hospital_id or not date:
            flash("Please select a hospital and date.", "danger")
            return render_template("book.html", hospitals=hospitals, recommendation=recommendation)

        hospital = Hospital.query.get(int(hospital_id))
        if not hospital:
            flash("Selected hospital not found.", "danger")
            return render_template("book.html", hospitals=hospitals, recommendation=recommendation)

        if hospital.available_beds <= 0:
            alt = Hospital.query.order_by(Hospital.available_beds.desc()).first()
            if alt and alt.available_beds > 0 and alt.id != hospital.id:
                recommendation = alt
                flash(
                    "No beds available at selected hospital. We recommend another hospital with availability.",
                    "warning",
                )
            else:
                flash("No beds available in any hospital at the moment.", "danger")
            return render_template("book.html", hospitals=hospitals, recommendation=recommendation)

        appointment = Appointment(
            patient_id=patient.id,
            hospital_id=hospital.id,
            date=date,
            status="Booked",
        )
        db.session.add(appointment)
        hospital.available_beds -= 1
        db.session.commit()

        generate_qr_for_appointment(appointment)

        flash("Appointment booked successfully. Doctor Notified.", "success")
        return redirect(url_for("main.appointments_view"))

    return render_template("book.html", hospitals=hospitals, recommendation=recommendation)


@main_bp.route("/appointments")
@login_required
@role_required("patient")
def appointments_view():
    patient = current_user.patient
    appointments = (
        Appointment.query.filter_by(patient_id=patient.id)
        .order_by(Appointment.id.desc())
        .all()
    )
    return render_template("appointments.html", appointments=appointments)


@main_bp.route("/scan/<int:appointment_id>")
def scan_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = "Arrived"
    db.session.commit()
    flash("Appointment marked as Arrived.", "success")
    return redirect(url_for("main.index"))


@main_bp.route("/visit", methods=["GET", "POST"])
@login_required
@role_required("patient")
def visit():
    patient = current_user.patient
    if not patient:
        flash("Please create your patient profile before recording a visit.", "warning")
        return redirect(url_for("main.create_profile"))

    if request.method == "POST":
        try:
            # Basic vitals (original)
            pregnancies = int(request.form.get("pregnancies", 0))
            glucose = float(request.form.get("glucose", 0))
            blood_pressure = float(request.form.get("blood_pressure", 0))
            skin_thickness = float(request.form.get("skin_thickness", 0))
            insulin = float(request.form.get("insulin", 0))
            bmi = float(request.form.get("bmi", 0))
            dpf = float(request.form.get("dpf", 0))
            age = int(request.form.get("age", 0))
            
            # Extended vitals for comprehensive assessment
            heart_rate = float(request.form.get("heart_rate", 0))
            respiratory_rate = float(request.form.get("respiratory_rate", 0))
            oxygen_saturation = float(request.form.get("oxygen_saturation", 98))
            cholesterol = float(request.form.get("cholesterol", 0))
            hdl = float(request.form.get("hdl", 0))
            ldl = float(request.form.get("ldl", 0))
            triglycerides = float(request.form.get("triglycerides", 0))
            creatinine = float(request.form.get("creatinine", 0))
            urea = float(request.form.get("urea", 0))
            alt = float(request.form.get("alt", 0))
            ast = float(request.form.get("ast", 0))
            hemoglobin = float(request.form.get("hemoglobin", 0))
            
            # Symptoms (boolean)
            chest_pain = request.form.get("chest_pain") == "on"
            shortness_of_breath = request.form.get("shortness_of_breath") == "on"
            fatigue = request.form.get("fatigue") == "on"
            swelling = request.form.get("swelling") == "on"
            smoking = request.form.get("smoking") == "on"
            family_history = request.form.get("family_history", "").strip()
            
        except ValueError:
            flash("All numeric fields must be valid numbers.", "danger")
            return render_template("visit.html")

        # Build comprehensive feature dictionary
        feature_dict = {
            "pregnancies": pregnancies,
            "glucose": glucose,
            "blood_pressure": blood_pressure,
            "skin_thickness": skin_thickness,
            "insulin": insulin,
            "bmi": bmi,
            "dpf": dpf,
            "age": age,
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
            "family_history": family_history,
        }

        # Run comprehensive disease prediction
        prediction_result = comprehensive_disease_predictor(feature_dict)
        prediction_label = prediction_result["overall_risk"]
        
        # Also try ML model for diabetes specifically if available
        model = load_diabetes_model()
        if model is not None and glucose > 0:
            try:
                X = [[pregnancies, glucose, blood_pressure, skin_thickness, insulin, bmi, dpf, age]]
                pred = model.predict(X)[0]
                if int(pred) == 1 and prediction_label != "High Risk":
                    prediction_label = "High Risk"
                    prediction_result["risk_score"] = max(prediction_result["risk_score"], 60)
            except Exception:
                pass

        visit_obj = Visit(
            patient_id=patient.id,
            # Basic vitals
            pregnancies=pregnancies,
            glucose=glucose,
            blood_pressure=blood_pressure,
            skin_thickness=skin_thickness,
            insulin=insulin,
            bmi=bmi,
            dpf=dpf,
            age=age,
            # Extended vitals
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
            # Prediction results
            prediction=prediction_label,
            disease_type=prediction_result["primary_disease"],
            risk_score=prediction_result["risk_score"],
            predicted_conditions=json.dumps(prediction_result["detected_conditions"]),
            suggested_tests=json.dumps(prediction_result["suggested_tests"]),
            status="Pending Review",
        )
        db.session.add(visit_obj)
        db.session.commit()

        high_risk_triggered = False
        if prediction_label in ["High Risk", "Moderate Risk"]:
            conditions_list = [c["disease"] for c in prediction_result["detected_conditions"]]
            message = f"{prediction_label} detected for: {', '.join(conditions_list)}. Doctor notified."
            log_alert_and_notify(patient, message)
            high_risk_triggered = True

        return render_template(
            "result.html",
            visit=visit_obj,
            patient=patient,
            high_risk_triggered=high_risk_triggered,
            prediction_result=prediction_result,
        )

    return render_template("visit.html")


@automation_bp.route("/automation/alert", methods=["POST"])
def automation_alert():
    """
    Webhook-style endpoint reserved for external automation tools (e.g. n8n).
    For now it simply acknowledges receipt; internal triggers write to alerts.log directly.
    """
    return {"status": "received", "message": "Automation hook acknowledged."}, 200

