from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db, login_manager


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, doctor, patient

    patient = db.relationship("Patient", backref="user", uselist=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    full_name = db.Column(db.String(128), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))

    visits = db.relationship("Visit", backref="patient", lazy=True)
    appointments = db.relationship("Appointment", backref="patient", lazy=True)
    alerts = db.relationship("Alert", backref="patient", lazy=True)


class Hospital(db.Model):
    __tablename__ = "hospitals"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    total_beds = db.Column(db.Integer, nullable=False)
    available_beds = db.Column(db.Integer, nullable=False)

    appointments = db.relationship("Appointment", backref="hospital", lazy=True)


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey("hospitals.id"), nullable=False)
    date = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(32), default="Booked")  # Booked, Arrived, Completed, Cancelled
    qr_code = db.Column(db.String(255))  # relative path to QR image


class Visit(db.Model):
    __tablename__ = "visits"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)

    # Basic vitals
    pregnancies = db.Column(db.Integer, nullable=False, default=0)
    glucose = db.Column(db.Float, nullable=False, default=0)
    blood_pressure = db.Column(db.Float, nullable=False, default=0)
    skin_thickness = db.Column(db.Float, nullable=False, default=0)
    insulin = db.Column(db.Float, nullable=False, default=0)
    bmi = db.Column(db.Float, nullable=False, default=0)
    dpf = db.Column(db.Float, nullable=False, default=0)
    age = db.Column(db.Integer, nullable=False, default=0)

    # Extended vitals for comprehensive disease detection
    heart_rate = db.Column(db.Float, default=0)  # beats per minute
    respiratory_rate = db.Column(db.Float, default=0)  # breaths per minute
    oxygen_saturation = db.Column(db.Float, default=0)  # SpO2 %
    cholesterol = db.Column(db.Float, default=0)  # mg/dL
    hdl = db.Column(db.Float, default=0)  # HDL cholesterol
    ldl = db.Column(db.Float, default=0)  # LDL cholesterol
    triglycerides = db.Column(db.Float, default=0)  # mg/dL
    creatinine = db.Column(db.Float, default=0)  # kidney function
    urea = db.Column(db.Float, default=0)  # kidney function
    alt = db.Column(db.Float, default=0)  # liver enzyme
    ast = db.Column(db.Float, default=0)  # liver enzyme
    hemoglobin = db.Column(db.Float, default=0)  # g/dL
    chest_pain = db.Column(db.Boolean, default=False)
    shortness_of_breath = db.Column(db.Boolean, default=False)
    fatigue = db.Column(db.Boolean, default=False)
    swelling = db.Column(db.Boolean, default=False)
    smoking = db.Column(db.Boolean, default=False)
    family_history = db.Column(db.String(255), default="")  # comma-separated conditions

    # Prediction results - supports multiple diseases
    prediction = db.Column(db.String(32), nullable=False)  # High Risk / Moderate Risk / Low Risk
    disease_type = db.Column(db.String(64), default="General")  # Diabetes, Cardiovascular, Hypertension, etc.
    risk_score = db.Column(db.Integer, default=0)  # 0-100 score
    predicted_conditions = db.Column(db.Text, default="")  # JSON list of detected conditions
    suggested_tests = db.Column(db.Text, default="")  # JSON list of recommended diagnostic tests

    # Treatment tracking
    status = db.Column(db.String(32), default="Pending Review")  # Pending Review, Under Treatment, Treated, Follow-up Required
    doctor_notes = db.Column(db.Text, default="")
    diagnosis = db.Column(db.Text, default="")
    treatment_plan = db.Column(db.Text, default="")
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

