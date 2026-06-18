THRESHOLDS = {
    "heart_rate": {"low": 60, "high": 100},
    "spo2": {"low": 95, "high": 100},
    "temperature": {"low": 97.0, "high": 100.4},
    "blood_sugar": {"low": 70, "high": 140},
    "bp_systolic": {"low": 90, "high": 140},
    "bp_diastolic": {"low": 60, "high": 90},
}


def evaluate_vitals(
    heart_rate: int,
    bp_systolic: int,
    bp_diastolic: int,
    spo2: float,
    temperature: float,
    blood_sugar: float,
) -> dict:
    reasons = []

    if heart_rate < THRESHOLDS["heart_rate"]["low"] or heart_rate > THRESHOLDS["heart_rate"]["high"]:
        reasons.append(f"Heart rate abnormal: {heart_rate} bpm")

    if spo2 < THRESHOLDS["spo2"]["low"]:
        reasons.append(f"Low oxygen level: {spo2}%")

    if temperature < THRESHOLDS["temperature"]["low"] or temperature > THRESHOLDS["temperature"]["high"]:
        reasons.append(f"Temperature abnormal: {temperature}°F")

    if blood_sugar < THRESHOLDS["blood_sugar"]["low"] or blood_sugar > THRESHOLDS["blood_sugar"]["high"]:
        reasons.append(f"Blood sugar abnormal: {blood_sugar} mg/dL")

    if bp_systolic < THRESHOLDS["bp_systolic"]["low"] or bp_systolic > THRESHOLDS["bp_systolic"]["high"]:
        reasons.append(f"BP systolic abnormal: {bp_systolic}")

    if bp_diastolic < THRESHOLDS["bp_diastolic"]["low"] or bp_diastolic > THRESHOLDS["bp_diastolic"]["high"]:
        reasons.append(f"BP diastolic abnormal: {bp_diastolic}")

    num_issues = len(reasons)

    if num_issues >= 2:
        status = "critical"
    elif num_issues == 1:
        status = "warning"
    else:
        status = "normal"

    return {
        "status": status,
        "reasons": reasons,
        "severity_score": num_issues,
    }
