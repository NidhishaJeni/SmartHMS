import os
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
    visits = Visit.query.filter_by(patient_id=patient.id).order_by(Visit.created_at.desc()).limit(5)
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.id.desc()).limit(5)
    return render_template("patient_dashboard.html", patient=patient, visits=visits, appointments=appointments)


@main_bp.route("/doctor/dashboard")
@login_required
@role_required("doctor")
def doctor_dashboard():
    high_risk_visits = (
        Visit.query.filter_by(prediction="High Risk")
        .order_by(Visit.created_at.desc())
        .all()
    )
    return render_template("doctor_dashboard.html", high_risk_visits=high_risk_visits)


@main_bp.route("/admin/dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
    hospitals = Hospital.query.order_by(Hospital.name).all()
    total_patients = Patient.query.count()
    total_hospitals = Hospital.query.count()
    total_appointments = Appointment.query.count()
    high_risk_alerts = Alert.query.order_by(Alert.timestamp.desc()).limit(20)
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
            pregnancies = int(request.form.get("pregnancies", 0))
            glucose = float(request.form.get("glucose", 0))
            blood_pressure = float(request.form.get("blood_pressure", 0))
            skin_thickness = float(request.form.get("skin_thickness", 0))
            insulin = float(request.form.get("insulin", 0))
            bmi = float(request.form.get("bmi", 0))
            dpf = float(request.form.get("dpf", 0))
            age = int(request.form.get("age", 0))
        except ValueError:
            flash("All fields must be valid numeric values.", "danger")
            return render_template("visit.html")

        feature_dict = {
            "pregnancies": pregnancies,
            "glucose": glucose,
            "blood_pressure": blood_pressure,
            "skin_thickness": skin_thickness,
            "insulin": insulin,
            "bmi": bmi,
            "dpf": dpf,
            "age": age,
        }

        model = load_diabetes_model()
        if model is not None:
            try:
                X = [
                    [
                        pregnancies,
                        glucose,
                        blood_pressure,
                        skin_thickness,
                        insulin,
                        bmi,
                        dpf,
                        age,
                    ]
                ]
                pred = model.predict(X)[0]
                prediction_label = "High Risk" if int(pred) == 1 else "Low Risk"
            except Exception:
                prediction_label = simple_risk_scorer(feature_dict)
        else:
            prediction_label = simple_risk_scorer(feature_dict)

        visit_obj = Visit(
            patient_id=patient.id,
            pregnancies=pregnancies,
            glucose=glucose,
            blood_pressure=blood_pressure,
            skin_thickness=skin_thickness,
            insulin=insulin,
            bmi=bmi,
            dpf=dpf,
            age=age,
            prediction=prediction_label,
        )
        db.session.add(visit_obj)
        db.session.commit()

        high_risk_triggered = False
        if prediction_label == "High Risk":
            log_alert_and_notify(patient, "High Risk diabetes prediction. Doctor notified.")
            high_risk_triggered = True

        return render_template(
            "result.html",
            visit=visit_obj,
            patient=patient,
            high_risk_triggered=high_risk_triggered,
        )

    return render_template("visit.html")


@automation_bp.route("/automation/alert", methods=["POST"])
def automation_alert():
    """
    Webhook-style endpoint reserved for external automation tools (e.g. n8n).
    For now it simply acknowledges receipt; internal triggers write to alerts.log directly.
    """
    return {"status": "received", "message": "Automation hook acknowledged."}, 200

