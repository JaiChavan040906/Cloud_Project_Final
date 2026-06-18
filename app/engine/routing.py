EVENT_ROUTES = {
    "PatientRegistered": ["reception", "admin"],
    "AppointmentCreated": ["reception", "admin"],
    "PatientCheckedIn": ["reception", "nurse"],
    "AdmissionRequested": ["admin", "reception"],
    "AdmissionApproved": ["reception", "nurse", "doctor", "admin"],
    "VitalsRecorded": ["nurse", "doctor"],
    "HighSugarDetected": ["nurse", "doctor", "admin"],
    "WarningAlertGenerated": ["nurse", "doctor"],
    "CriticalAlertGenerated": ["nurse", "doctor", "admin"],
    "MedicationPrescribed": ["nurse", "doctor"],
    "MedicationAdministered": ["nurse", "admin"],
    "PatientReviewed": ["doctor", "nurse", "admin"],
    "CheckupCompleted": ["nurse", "doctor"],
    "DischargeApproved": ["reception", "nurse", "admin"],
}


def get_recipients(event_type: str) -> list[str]:
    return EVENT_ROUTES.get(event_type, [])
