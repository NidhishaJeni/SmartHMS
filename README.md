SMART HOSPITAL MANAGEMENT SYSTEM (SmartHMS)
===========================================

Overview
--------

SmartHMS is a full-stack Flask prototype for hospital coordination, intelligent appointment booking, AI-based diabetes risk prediction, and automation-ready alerting.

It uses:
- Flask + Flask-Login + Flask-SQLAlchemy
- SQLite (upgradeable to PostgreSQL)
- Jinja2 templates + Bootstrap 5
- Pre-trained Logistic Regression model loaded with joblib (or heuristic fallback)
- QR codes for appointments via `qrcode`

Folder Structure
----------------

```text
HMS/
├─ app.py                 # Flask app factory and entry point
├─ config.py              # Configuration (dev/prod, DB, model path, alerts path)
├─ extensions.py          # SQLAlchemy + LoginManager instances
├─ models.py              # SQLAlchemy ORM models
├─ routes.py              # Blueprints, views, AI logic, automation, QR
├─ requirements.txt
├─ alerts.log             # Created automatically on first High-Risk alert
├─ models/
│  └─ diabetes_model.pkl  # (Optional) Logistic Regression model file
├─ templates/
│  ├─ base.html
│  ├─ index.html
│  ├─ login.html
│  ├─ register.html
│  ├─ patient_dashboard.html
│  ├─ doctor_dashboard.html
│  ├─ admin_dashboard.html
│  ├─ create_profile.html
│  ├─ hospitals.html
│  ├─ book.html
│  ├─ appointments.html
│  ├─ visit.html
│  └─ result.html
└─ static/
   ├─ css/
   │  └─ style.css
   └─ qr_codes/           # Generated QR images for appointments
```

Database Models
---------------

- `User`: `id`, `username`, `password_hash`, `role`
- `Patient`: `id`, `user_id`, `full_name`, `age`, `gender`, `phone`, `address`
- `Hospital`: `id`, `name`, `total_beds`, `available_beds`
- `Appointment`: `id`, `patient_id`, `hospital_id`, `date`, `status`, `qr_code`
- `Visit`: `id`, `patient_id`, `pregnancies`, `glucose`, `blood_pressure`, `skin_thickness`, `insulin`, `bmi`, `dpf`, `age`, `prediction`, `created_at`
- `Alert`: `id`, `patient_id`, `message`, `timestamp`

Seed Data (for quick testing)
-----------------------------

On first run, `app.py` seeds:

- Admin user: `admin / admin123`
- Doctor user: `doctor / doctor123`
- Patient user: `patient / patient123` with a sample patient profile
- Three demo hospitals with different bed capacities

Running the Application
-----------------------

1. Create and activate a virtual environment (recommended):

```bash
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. (Optional) Place your trained Logistic Regression diabetes model:

- Create a `models` folder next to `app.py` if it does not exist.
- Save the pickled model as `diabetes_model.pkl` inside that folder.
- The model should accept 8 features in this order:
  `[pregnancies, glucose, blood_pressure, skin_thickness, insulin, bmi, dpf, age]`
- Prediction is expected as `0` (Low Risk) or `1` (High Risk).

If the file is missing or fails to load, SmartHMS automatically falls back to a simple heuristic scorer.

4. Run the app:

```bash
python app.py
```

5. Open the browser:

- Navigate to `http://127.0.0.1:5000/`
- Login using the demo credentials above or register a new account.

Key Flows
---------

- **Authentication**: Registration with role selection (Admin / Doctor / Patient), secure password hashing, session-based login, role-based dashboards.
- **Patient Module**: Create/update profile, view AI prediction history and appointments from the patient dashboard.
- **Hospital Module**: Admin can add/edit hospitals and bed counts; home page and admin dashboard show live bed availability.
- **Smart Booking System**:
  - Checks `available_beds` before confirming appointment.
  - If no beds, recommends the hospital with the highest availability (if any).
  - Decrements `available_beds` upon successful booking.
  - Generates a QR code (`/static/qr_codes/...`) for each appointment.
  - `/scan/<appointment_id>` marks appointment as `Arrived`.
- **AI Risk Prediction**:
  - `/visit` accepts the 8 diabetes-related parameters.
  - Uses joblib-loaded model if available, otherwise a heuristic scorer.
  - Stores each `Visit` in the database and shows a detailed `result.html` view.
- **Intelligent Alert System**:
  - For `High Risk` predictions:
    - Appends an entry to `alerts.log`.
    - Creates an `Alert` row in the database.
    - Internally POSTs to `/automation/alert` (webhook-style endpoint).
    - Shows a prominent “Doctor Notified” banner on the result page.
  - Admin dashboard lists recent high-risk alerts.

Scalability Notes
-----------------

- Database URL, secret key, model path, and alerts log path are configured in `config.py` and can be overridden via environment variables:
  - `SMARTHMS_SECRET_KEY`
  - `SMARTHMS_DATABASE_URI` (e.g. PostgreSQL URI)
  - `SMARTHMS_MODEL_PATH`
  - `SMARTHMS_ALERTS_LOG_PATH`
- Ready for external workflow tools (e.g. n8n) via the `/automation/alert` webhook endpoint.

Security & Validation
---------------------

- Passwords are stored using Werkzeug’s secure hashing.
- Inputs are validated server-side for all core flows (registration, profiles, visits, booking).
- No sensitive secrets are hard-coded; they can be supplied via environment variables.

