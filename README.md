# SMART HOSPITAL MANAGEMENT SYSTEM (SmartHMS)

## 🏥 Enterprise-Grade AI-Powered Healthcare Platform

SmartHMS is a comprehensive full-stack Flask healthcare management system featuring **multi-disease AI prediction**, **intelligent treatment tracking**, **appointment management**, and **hospital resource optimization**. It's designed for seamless coordination between patients, doctors, and hospital administrators with advanced health risk assessment capabilities.

### ✨ Key Features

- **🤖 Multi-Disease AI Prediction Engine**: Simultaneously analyzes 8+ chronic diseases (Diabetes, Cardiovascular Disease, Hypertension, Respiratory Disease, Kidney Disease, Liver Disease, Anemia, Thyroid Disorders)
- **📊 Comprehensive Health Assessments**: Analyzes 40+ vital signs, lab values, and symptoms
- **🔍 Intelligent Risk Scoring**: Calculates 0-100 risk scores for prioritized patient care
- **📋 Smart Diagnostic Recommendations**: AI-powered test recommendations based on detected conditions
- **👨‍⚕️ Doctor Dashboard with Treatment Tracking**: View, diagnose, and manage patient care with full status tracking
- **💊 Treatment Status Management**: Pending Review → Under Treatment → Treated → Follow-up workflows
- **📱 Patient Portal with Status Updates**: Real-time treatment progress and doctor recommendations
- **🏥 Hospital Resource Optimization**: Real-time bed availability, smart booking with alternatives
- **🔐 Role-Based Access Control**: Admin, Doctor, and Patient dashboards with tailored workflows
- **📱 QR Code Appointments**: Generate and scan QR codes for contactless check-ins
- **🔔 Intelligent Alert System**: Automatic doctor notifications for high-risk patients
- **📝 Audit Logs**: Complete history of health assessments and treatments

### 🛠️ Technology Stack

| Technology | Purpose |
|-----------|---------|
| **Flask 3.0.2** | Web framework |
| **Flask-Login 0.6.3** | Authentication & session management |
| **SQLAlchemy 2.0.25** | ORM & database abstraction |
| **SQLite** | Default database (PostgreSQL-ready) |
| **Bootstrap 5** | Responsive UI framework |
| **Jinja2** | Template engine |
| **joblib 1.3.2** | ML model loading for diabetes prediction |
| **qrcode[pil] 7.4.2** | QR code generation with PIL |
| **python-dotenv** | Environment variable management |

## 📁 Project Structure

```
HMS/
├── app.py                          # Flask app factory & entry point
├── config.py                       # Environment & configuration settings
├── extensions.py                   # SQLAlchemy & LoginManager initialization
├── models.py                       # Database ORM models (40+ disease parameters)
├── routes.py                       # Blueprints, views, AI logic & webhooks
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── instance/                       # Instance-specific files (auto-created)
├── __pycache__/                    # Python cache (auto-generated)
├── models/                         # ML Models directory
│   └── diabetes_model.pkl          # (Optional) Trained diabetes ML model
├── templates/                      # Jinja2 HTML templates
│   ├── base.html                   # Base template with navbar
│   ├── index.html                  # Home page with statistics
│   ├── login.html                  # Login form
│   ├── register.html               # Registration with role selection
│   ├── create_profile.html         # Patient profile creation
│   ├── patient_dashboard.html      # Patient overview & treatment status
│   ├── doctor_dashboard.html       # Doctor's patient list with filters
│   ├── doctor_visit_detail.html    # Detailed patient diagnosis & treatment
│   ├── admin_dashboard.html        # Admin hospital & alert overview
│   ├── hospitals.html              # Hospital management (admin)
│   ├── book.html                   # Smart appointment booking
│   ├── appointments.html           # Patient's appointment list
│   ├── visit.html                  # Comprehensive health assessment form
│   └── result.html                 # Assessment results & recommendations
└── static/
    ├── css/
    │   └── style.css               # Custom styling
    └── qr_codes/                   # Generated QR codes (auto-created)
```

## 🗄️ Database Schema - Enhanced Visit Model

### User Model
- `id` (int, primary key)
- `username` (str, unique)
- `password_hash` (str)
- `role` (str: 'admin', 'doctor', 'patient')

### Patient Model
- `id`, `user_id`, `full_name`, `age`, `gender`, `phone`, `address`

### Hospital Model
- `id`, `name`, `total_beds`, `available_beds`

### Appointment Model
- `id`, `patient_id`, `hospital_id`, `date`, `status`, `qr_code`

### Visit Model (Comprehensive Disease Detection)

**BASIC VITALS (Diabetes)**
- `pregnancies`, `glucose`, `blood_pressure`, `skin_thickness`
- `insulin`, `bmi`, `dpf`, `age`

**EXTENDED VITALS**
- `heart_rate`, `respiratory_rate`, `oxygen_saturation`  
- `cholesterol`, `hdl`, `ldl`, `triglycerides`
- `creatinine`, `urea`, `alt`, `ast`, `hemoglobin`

**SYMPTOMS & RISK FACTORS**
- `chest_pain`, `shortness_of_breath`, `fatigue`
- `swelling`, `smoking`, `family_history`

**AI PREDICTIONS & RECOMMENDATIONS**
- `prediction` (High/Moderate/Low Risk)
- `disease_type` (primary detected disease)
- `risk_score` (0-100 composite score)
- `predicted_conditions` (JSON: detected conditions list)
- `suggested_tests` (JSON: diagnostic test recommendations)

**TREATMENT TRACKING** ⭐ NEW
- `status` (Pending Review → Under Treatment → Treated → Follow-up Required)
- `diagnosis` (doctor's clinical diagnosis)
- `treatment_plan` (prescribed treatment)
- `doctor_notes` (additional notes for patient)
- `reviewed_by` (doctor ID)
- `reviewed_at` (review timestamp)

### Alert Model
- `id`, `patient_id`, `message`, `timestamp`

---

## 🎯 Supported Diseases & Analysis

The AI engine predicts risk for 8+ diseases:

| Disease | Key Indicators | Recommended Tests |
|---------|---|---|
| **Diabetes Mellitus** | Glucose ≥126, High BMI, Low Insulin | Fasting Glucose, HbA1c, OGTT, Urinalysis |
| **Cardiovascular Disease** | High Cholesterol, Chest Pain, High BP | ECG, Echo, Stress Test, Troponin |
| **Hypertension** | Systolic ≥140, Age ≥50, Obesity | 24h BP Monitor, ECG, Kidney Function |
| **Respiratory Disease** | Low SpO2, High RR, Shortness of Breath | Chest X-Ray, Spirometry, ABG, CT Chest |
| **Kidney Disease** | High Creatinine, Urea, Swelling | Creatinine, BUN, GFR, Urinalysis, Ultrasound |
| **Liver Disease** | High ALT/AST, Obesity, Fatigue | LFTs, Bilirubin, Ultrasound, Hepatitis Panel |
| **Anemia** | Low Hemoglobin, Fatigue, SOB | CBC, Iron Studies, B12, Folate, Reticulocyte |
| **Thyroid Disorder** | (Expandable) | TSH, T3/T4, Ultrasound, Antibodies |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- Virtual environment (recommended)

### Quick Start

#### 1. Navigate to Project
```bash
cd path/to/HMS
```

#### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. (Optional) Add Pre-trained ML Model
```bash
mkdir -p models
# Place your diabetes_model.pkl in the models/ directory
# Model expects: [pregnancies, glucose, blood_pressure, skin_thickness, insulin, bmi, dpf, age]
# Output: 0 (Low Risk) or 1 (High Risk)
```

#### 5. Run Application
```bash
python app.py
```

#### 6. Access Web Interface
```
http://localhost:5000
```

### Demo Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Doctor | `doctor` | `doctor123` |
| Patient | `patient` | `patient123` |

---

## 📊 Enhanced Workflows (v2.0)

### 👨‍⚕️ Doctor Treatment Management

**Step-by-Step Process:**
1. Doctor logs into dashboard
2. Reviews patient queue with status filters
3. Selects patient to view detailed assessment
4. Reviews detected conditions & risk scores
5. Enters diagnosis based on AI recommendations
6. Creates treatment plan
7. Adds doctor notes
8. Updates patient status
9. Patient automatically notified

### 🏥 Comprehensive Health Assessment

Patients now enter 40+ data points instead of just 8:
- **Diabetes parameters** (glucose, insulin, BMI, glucose)
- **Cardiovascular markers** (cholesterol, HDL, LDL, blood pressure)
- **Respiratory values** (oxygen saturation, respiratory rate)
- **Kidney function** (creatinine, urea)
- **Liver function** (ALT, AST)
- **Blood composition** (hemoglobin)
- **Symptoms & risk factors** (chest pain, breathing issues, family history)

### 📱 Patient Status Tracking

New patient portal features:
- See doctor's diagnosis
- View treatment plan
- Read doctor's notes
- Track treatment status in real-time
- Know when to follow-up

---

## 🔐 Security & Configuration

**Environment Variables:**
```bash
SMARTHMS_DATABASE_URI=sqlite:///hms.db
SMARTHMS_SECRET_KEY=your-secret-key
SMARTHMS_MODEL_PATH=models/diabetes_model.pkl
SMARTHMS_ALERTS_LOG_PATH=instance/alerts.log
```

**Security Features:**
✅ Werkzeug password hashing  
✅ Session-based authentication  
✅ Role-based access control (RBAC)  
✅ Server-side input validation  
✅ SQLAlchemy ORM (SQL injection prevention)  

---

## 🌐 API Endpoints

**/Authentication:**
- `POST /register` - Register new user
- `POST /login` - Login user
- `GET /logout` - Logout user

**/Patient:**
- `GET /patient/dashboard` - Patient overview
- `GET /profile/create` - Create patient profile
- `POST /visit` - Submit health assessment
- `GET /visit` - Health assessment form
- `POST /book` - Book appointment
- `GET /appointments` - View appointments
- `GET /scan/<id>` - Mark as arrived (QR scan)

**/Doctor:**
- `GET /doctor/dashboard` - Patient list with filters
- `GET /doctor/visit/<id>` - Detailed patient view
- `POST /doctor/visit/<id>` - Update diagnosis & treatment

**/Admin:**
- `GET /admin/dashboard` - System overview
- `GET /hospitals` - Hospital management
- `POST /hospitals` - Add/edit hospitals

**Other:**
- `GET /` - Home page
- `POST /automation/alert` - Webhook endpoint
---
## 📈 Performance & Scalability

- **Database:** SQLite (dev) → PostgreSQL (production)
- **ML Model:** Heuristic-based disease detection (no external APIs)
- **Caching:** Ready for Flask-Caching integration
- **Deployment:** Docker, Heroku, AWS-ready
---
## 📝 Version History
**v2.0.0 (Current - March 3, 2026)**
- ✨ Multi-disease AI prediction engine (8+ diseases)
- ✨ Comprehensive health assessment (40+ parameters)
- ✨ Doctor treatment management system
- ✨ Patient status tracking workflows
- ✨ Enhanced doctor dashboard with filters
- ✨ Diagnostic test recommendations
- ✨ Fixed Query object length issue in admin dashboard
- 📚 Comprehensive documentation
**v1.0.0 (Initial)**
- Diabetes risk prediction
- Hospital management
- Appointment booking with QR codes
- Patient dashboards
- Alert system

---
**Last Updated:** March 3, 2026  
**Status:** Active Development  
**Maintainer:** SmartHMS Development Team
