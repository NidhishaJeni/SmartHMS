"""
AI Health Risk Scoring Engine for SmartHMS.
Rule-based multi-disease risk assessment system.
"""

from typing import Dict, List, Any, Optional
import json


# Disease categories and diagnostic tests configuration
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


def calculate_bmi(weight: float, height: float) -> float:
    """Calculate BMI from weight (kg) and height (cm)."""
    if height <= 0 or weight <= 0:
        return 0
    height_m = height / 100  # Convert cm to m
    return round(weight / (height_m * height_m), 1)


def assess_health_risk(vitals: Dict[str, Any], patient_age: int = 0) -> Dict[str, Any]:
    """
    Comprehensive multi-disease risk assessment.
    Returns dict with detected conditions, risk levels, and suggested tests.
    
    Args:
        vitals: Dictionary containing all vital signs and lab values
        patient_age: Patient's age in years
    
    Returns:
        Dictionary with risk assessment results
    """
    # Add age to features for calculations
    features = {**vitals, "age": patient_age}
    
    detected_conditions = []
    all_suggested_tests = set()
    total_risk_score = 0
    primary_disease = "General"
    
    # 1. Diabetes Risk Assessment
    diabetes_score = _assess_diabetes_risk(features)
    if diabetes_score >= 40:
        detected_conditions.append({
            "disease": "Diabetes Mellitus",
            "risk_level": "High Risk" if diabetes_score >= 60 else "Moderate Risk",
            "score": min(diabetes_score, 100),
            "key_indicators": _get_diabetes_indicators(features)
        })
        all_suggested_tests.update(DISEASE_CATEGORIES["diabetes"]["tests"])
        if diabetes_score > total_risk_score:
            total_risk_score = diabetes_score
            primary_disease = "Diabetes"
    
    # 2. Cardiovascular Disease Risk Assessment
    cardio_score = _assess_cardiovascular_risk(features)
    if cardio_score >= 35:
        detected_conditions.append({
            "disease": "Cardiovascular Disease",
            "risk_level": "High Risk" if cardio_score >= 60 else "Moderate Risk",
            "score": min(cardio_score, 100),
            "key_indicators": _get_cardio_indicators(features)
        })
        all_suggested_tests.update(DISEASE_CATEGORIES["cardiovascular"]["tests"])
        if cardio_score > total_risk_score:
            total_risk_score = cardio_score
            primary_disease = "Cardiovascular"
    
    # 3. Hypertension Risk Assessment
    hypertension_score = _assess_hypertension_risk(features)
    if hypertension_score >= 40:
        detected_conditions.append({
            "disease": "Hypertension",
            "risk_level": "High Risk" if hypertension_score >= 60 else "Moderate Risk",
            "score": min(hypertension_score, 100),
            "key_indicators": _get_hypertension_indicators(features)
        })
        all_suggested_tests.update(DISEASE_CATEGORIES["hypertension"]["tests"])
        if hypertension_score > total_risk_score:
            total_risk_score = hypertension_score
            primary_disease = "Hypertension"
    
    # 4. Respiratory Disease Risk Assessment
    respiratory_score = _assess_respiratory_risk(features)
    if respiratory_score >= 35:
        detected_conditions.append({
            "disease": "Respiratory Disease",
            "risk_level": "High Risk" if respiratory_score >= 60 else "Moderate Risk",
            "score": min(respiratory_score, 100),
            "key_indicators": _get_respiratory_indicators(features)
        })
        all_suggested_tests.update(DISEASE_CATEGORIES["respiratory"]["tests"])
        if respiratory_score > total_risk_score:
            total_risk_score = respiratory_score
            primary_disease = "Respiratory"
    
    # 5. Kidney Disease Risk Assessment
    kidney_score = _assess_kidney_risk(features)
    if kidney_score >= 35:
        detected_conditions.append({
            "disease": "Kidney Disease",
            "risk_level": "High Risk" if kidney_score >= 60 else "Moderate Risk",
            "score": min(kidney_score, 100),
            "key_indicators": _get_kidney_indicators(features)
        })
        all_suggested_tests.update(DISEASE_CATEGORIES["kidney"]["tests"])
        if kidney_score > total_risk_score:
            total_risk_score = kidney_score
            primary_disease = "Kidney"
    
    # 6. Liver Disease Risk Assessment
    liver_score = _assess_liver_risk(features)
    if liver_score >= 35:
        detected_conditions.append({
            "disease": "Liver Disease",
            "risk_level": "High Risk" if liver_score >= 60 else "Moderate Risk",
            "score": min(liver_score, 100),
            "key_indicators": _get_liver_indicators(features)
        })
        all_suggested_tests.update(DISEASE_CATEGORIES["liver"]["tests"])
        if liver_score > total_risk_score:
            total_risk_score = liver_score
            primary_disease = "Liver"
    
    # 7. Anemia Risk Assessment
    anemia_score = _assess_anemia_risk(features)
    if anemia_score >= 35:
        detected_conditions.append({
            "disease": "Anemia",
            "risk_level": "High Risk" if anemia_score >= 55 else "Moderate Risk",
            "score": min(anemia_score, 100),
            "key_indicators": _get_anemia_indicators(features)
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
            "score": 0,
            "key_indicators": ["No major concerns detected"]
        })
    
    return {
        "overall_risk": overall_risk,
        "risk_score": min(total_risk_score, 100),
        "primary_disease": primary_disease,
        "detected_conditions": detected_conditions,
        "suggested_tests": list(all_suggested_tests)
    }


def _assess_diabetes_risk(features: Dict[str, Any]) -> int:
    """Assess diabetes risk score (0-100)."""
    score = 0
    glucose = features.get("glucose", 0)
    bmi = features.get("bmi", 0)
    age = features.get("age", 0)
    dpf = features.get("dpf", 0)
    insulin = features.get("insulin", 0)
    
    if glucose >= 126:
        score += 30
    elif glucose >= 100:
        score += 15
    
    if bmi >= 30:
        score += 20
    elif bmi >= 25:
        score += 10
    
    if age >= 45:
        score += 10
    
    if dpf >= 0.5:
        score += 15
    
    if insulin <= 30 and glucose >= 100:
        score += 10
    
    return score


def _get_diabetes_indicators(features: Dict[str, Any]) -> List[str]:
    """Get key indicators for diabetes."""
    indicators = []
    if features.get("glucose", 0) >= 100:
        indicators.append("High glucose")
    if features.get("bmi", 0) >= 25:
        indicators.append("Elevated BMI")
    if features.get("age", 0) >= 45:
        indicators.append("Age factor")
    if features.get("dpf", 0) >= 0.5:
        indicators.append("Family history")
    return indicators if indicators else ["Glucose levels", "BMI"]


def _assess_cardiovascular_risk(features: Dict[str, Any]) -> int:
    """Assess cardiovascular disease risk score (0-100)."""
    score = 0
    cholesterol = features.get("cholesterol", 0)
    ldl = features.get("ldl", 0)
    hdl = features.get("hdl", 100)
    bp = features.get("blood_pressure", 0)
    bmi = features.get("bmi", 0)
    age = features.get("age", 0)
    family_history = features.get("family_history", "").lower()
    
    if cholesterol >= 240:
        score += 25
    elif cholesterol >= 200:
        score += 15
    
    if ldl >= 160:
        score += 20
    
    if hdl <= 40:
        score += 15
    
    if bp >= 140:
        score += 20
    
    if features.get("chest_pain", False):
        score += 25
    
    if features.get("shortness_of_breath", False):
        score += 15
    
    if features.get("smoking", False):
        score += 15
    
    if age >= 55:
        score += 10
    
    if bmi >= 30:
        score += 10
    
    if "heart" in family_history:
        score += 15
    
    return score


def _get_cardio_indicators(features: Dict[str, Any]) -> List[str]:
    """Get key indicators for cardiovascular disease."""
    indicators = []
    if features.get("cholesterol", 0) >= 200:
        indicators.append("Cholesterol levels")
    if features.get("blood_pressure", 0) >= 120:
        indicators.append("Blood pressure")
    if features.get("chest_pain", False):
        indicators.append("Chest pain")
    if features.get("smoking", False):
        indicators.append("Smoking history")
    return indicators if indicators else ["Cardiac markers", "Lifestyle factors"]


def _assess_hypertension_risk(features: Dict[str, Any]) -> int:
    """Assess hypertension risk score (0-100)."""
    score = 0
    bp = features.get("blood_pressure", 0)
    age = features.get("age", 0)
    bmi = features.get("bmi", 0)
    family_history = features.get("family_history", "").lower()
    
    if bp >= 140:
        score += 40
    elif bp >= 130:
        score += 25
    elif bp >= 120:
        score += 10
    
    if age >= 50:
        score += 15
    
    if bmi >= 30:
        score += 15
    
    if features.get("smoking", False):
        score += 10
    
    if "hypertension" in family_history or "blood pressure" in family_history:
        score += 15
    
    return score


def _get_hypertension_indicators(features: Dict[str, Any]) -> List[str]:
    """Get key indicators for hypertension."""
    indicators = []
    if features.get("blood_pressure", 0) >= 120:
        indicators.append("Elevated blood pressure")
    if features.get("age", 0) >= 50:
        indicators.append("Age factor")
    if features.get("bmi", 0) >= 25:
        indicators.append("Weight")
    if features.get("smoking", False):
        indicators.append("Lifestyle")
    return indicators if indicators else ["Blood pressure", "Age"]


def _assess_respiratory_risk(features: Dict[str, Any]) -> int:
    """Assess respiratory disease risk score (0-100)."""
    score = 0
    spo2 = features.get("oxygen_saturation", 100)
    rr = features.get("respiratory_rate", 0)
    
    if spo2 <= 92:
        score += 35
    elif spo2 <= 95:
        score += 20
    
    if rr >= 24:
        score += 25
    elif rr >= 20:
        score += 10
    
    if features.get("shortness_of_breath", False):
        score += 25
    
    if features.get("smoking", False):
        score += 20
    
    if features.get("fatigue", False):
        score += 10
    
    return score


def _get_respiratory_indicators(features: Dict[str, Any]) -> List[str]:
    """Get key indicators for respiratory disease."""
    indicators = []
    if features.get("oxygen_saturation", 100) < 95:
        indicators.append("Low oxygen saturation")
    if features.get("shortness_of_breath", False):
        indicators.append("Breathing issues")
    if features.get("smoking", False):
        indicators.append("Smoking history")
    return indicators if indicators else ["Oxygen levels", "Breathing"]


def _assess_kidney_risk(features: Dict[str, Any]) -> int:
    """Assess kidney disease risk score (0-100)."""
    score = 0
    creatinine = features.get("creatinine", 0)
    urea = features.get("urea", 0)
    bp = features.get("blood_pressure", 0)
    glucose = features.get("glucose", 0)
    
    if creatinine >= 1.5:
        score += 35
    elif creatinine >= 1.2:
        score += 20
    
    if urea >= 45:
        score += 25
    elif urea >= 25:
        score += 10
    
    if features.get("swelling", False):
        score += 20
    
    if bp >= 140:
        score += 15
    
    if glucose >= 126:
        score += 10
    
    return score


def _get_kidney_indicators(features: Dict[str, Any]) -> List[str]:
    """Get key indicators for kidney disease."""
    indicators = []
    if features.get("creatinine", 0) >= 1.2:
        indicators.append("Elevated creatinine")
    if features.get("urea", 0) >= 25:
        indicators.append("High urea")
    if features.get("swelling", False):
        indicators.append("Edema")
    return indicators if indicators else ["Kidney function markers"]


def _assess_liver_risk(features: Dict[str, Any]) -> int:
    """Assess liver disease risk score (0-100)."""
    score = 0
    alt = features.get("alt", 0)
    ast = features.get("ast", 0)
    bmi = features.get("bmi", 0)
    
    if alt >= 56:
        score += 30
    elif alt >= 40:
        score += 15
    
    if ast >= 48:
        score += 30
    elif ast >= 35:
        score += 15
    
    if bmi >= 30:
        score += 15
    
    if features.get("fatigue", False):
        score += 10
    
    return score


def _get_liver_indicators(features: Dict[str, Any]) -> List[str]:
    """Get key indicators for liver disease."""
    indicators = []
    if features.get("alt", 0) >= 40:
        indicators.append("Elevated ALT")
    if features.get("ast", 0) >= 35:
        indicators.append("Elevated AST")
    if features.get("bmi", 0) >= 25:
        indicators.append("BMI")
    return indicators if indicators else ["Liver enzymes"]


def _assess_anemia_risk(features: Dict[str, Any]) -> int:
    """Assess anemia risk score (0-100)."""
    score = 0
    hemoglobin = features.get("hemoglobin", 14)
    
    if hemoglobin > 0:
        if hemoglobin <= 8:
            score += 50
        elif hemoglobin <= 10:
            score += 35
        elif hemoglobin <= 12:
            score += 20
    
    if features.get("fatigue", False):
        score += 20
    
    if features.get("shortness_of_breath", False):
        score += 15
    
    return score


def _get_anemia_indicators(features: Dict[str, Any]) -> List[str]:
    """Get key indicators for anemia."""
    indicators = []
    if features.get("hemoglobin", 14) < 12:
        indicators.append("Low hemoglobin")
    if features.get("fatigue", False):
        indicators.append("Fatigue")
    if features.get("shortness_of_breath", False):
        indicators.append("Breathing difficulty")
    return indicators if indicators else ["Blood count"]


def quick_risk_assessment(vitals: Dict[str, Any], patient_age: int = 0) -> Dict[str, Any]:
    """
    Quick simplified risk assessment for vitals recorded by nurses.
    Uses basic vital signs to determine risk level.
    """
    score = 0
    indicators = []
    
    # Blood pressure assessment
    bp_sys = vitals.get("blood_pressure_systolic", 0)
    if bp_sys >= 140:
        score += 30
        indicators.append("High blood pressure")
    elif bp_sys >= 130:
        score += 15
        indicators.append("Elevated blood pressure")
    
    # Heart rate assessment
    hr = vitals.get("heart_rate", 0)
    if hr > 100:
        score += 15
        indicators.append("Elevated heart rate")
    elif hr < 60:
        score += 10
        indicators.append("Low heart rate")
    
    # Oxygen saturation
    spo2 = vitals.get("oxygen_saturation", 0)
    if spo2 < 90:
        score += 30
        indicators.append("Low oxygen saturation")
    elif spo2 < 95:
        score += 15
        indicators.append("Reduced oxygen saturation")
    
    # BMI assessment
    bmi = vitals.get("bmi", 0)
    if bmi >= 30:
        score += 15
        indicators.append("Obesity")
    elif bmi >= 25:
        score += 10
        indicators.append("Overweight")
    
    # Glucose assessment
    glucose = vitals.get("glucose", 0)
    if glucose >= 126:
        score += 25
        indicators.append("High glucose")
    elif glucose >= 100:
        score += 10
        indicators.append("Elevated glucose")
    
    # Cholesterol
    cholesterol = vitals.get("cholesterol", 0)
    if cholesterol >= 240:
        score += 20
        indicators.append("High cholesterol")
    elif cholesterol >= 200:
        score += 10
        indicators.append("Borderline cholesterol")
    
    # Determine risk level
    if score >= 50:
        risk_level = "High Risk"
    elif score >= 25:
        risk_level = "Moderate Risk"
    else:
        risk_level = "Low Risk"
    
    return {
        "risk_score": min(score, 100),
        "risk_level": risk_level,
        "indicators": indicators if indicators else ["All vitals within normal range"]
    }

