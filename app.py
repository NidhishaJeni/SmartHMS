from flask import Flask

from config import get_config
from extensions import db, login_manager
from models import User, Patient, Hospital, Appointment, Visit, Alert
from routes import auth_bp, main_bp, automation_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(automation_bp)

    with app.app_context():
        db.create_all()
        seed_initial_data()

    return app


def seed_initial_data():
    """
    Lightweight seed data for prototype/demo use.
    Avoids duplicates by checking for existing records.
    """
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)

    if not User.query.filter_by(username="doctor").first():
        doctor = User(username="doctor", role="doctor")
        doctor.set_password("doctor123")
        db.session.add(doctor)

    if not User.query.filter_by(username="patient").first():
        patient_user = User(username="patient", role="patient")
        patient_user.set_password("patient123")
        db.session.add(patient_user)
        db.session.flush()

        patient_profile = Patient(
            user_id=patient_user.id,
            full_name="Demo Patient",
            age=45,
            gender="Male",
            phone="+1-555-0100",
            address="123 Health Street",
        )
        db.session.add(patient_profile)

    if Hospital.query.count() == 0:
        h1 = Hospital(name="City General Hospital", total_beds=100, available_beds=60)
        h2 = Hospital(name="Sunrise Medical Center", total_beds=80, available_beds=20)
        h3 = Hospital(name="Lakeside Clinic", total_beds=40, available_beds=10)
        db.session.add_all([h1, h2, h3])

    db.session.commit()


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)

