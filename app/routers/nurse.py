from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import role_required
from app.database import get_db
from app.models import Alert, Event, Medication, Patient, User
from app.routers import apply_search, apply_sort, build_paginated_response
from app.schemas import MedicationIdResponse, PatientIdResponse, VitalsRecord, VitalsResponse

# All endpoints require nurse or admin role
router = APIRouter(dependencies=[Depends(role_required("nurse", "admin"))])


# ─── Assigned Patients ──────────────────────────────────────────────────────
# Returns patients where assigned_nurse matches the logged-in nurse's username.


@router.get("/patients/assigned")
def assigned_patients(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by patient ID, name, or department"),
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("nurse", "admin")),
):
    query = db.query(Patient).filter(Patient.assigned_nurse == user.username)
    if status:
        query = query.filter(Patient.status == status)
    query = apply_search(query, search, [Patient.patient_id, Patient.name, Patient.department])
    query = apply_sort(
        query,
        sort_by,
        sort_order,
        {
            "patient_id": Patient.patient_id,
            "name": Patient.name,
            "department": Patient.department,
            "status": Patient.status,
        },
        [Patient.name.asc(), Patient.patient_id.asc()],
    )
    return build_paginated_response(query, page, limit)


# ─── Record Vitals ──────────────────────────────────────────────────────────
# Validates the patient exists, then evaluates heart rate / SpO2 / temp /
# blood sugar against thresholds. Returns severity (Normal / Warning / Critical)
# with a list of abnormal findings. Creates alerts for abnormal readings.


@router.post("/vitals", response_model=VitalsResponse)
def record_vitals(
    data: VitalsRecord, db: Session = Depends(get_db), user: User = Depends(role_required("nurse", "admin"))
):
    patient = db.query(Patient).filter(Patient.patient_id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    hr = data.heart_rate
    spo2 = data.oxygen_level
    temp = data.temperature
    sugar = data.blood_sugar

    reasons = []
    if hr > 100 or hr < 60:
        reasons.append(f"Heart rate abnormal: {hr}")
    if spo2 < 95:
        reasons.append(f"Low oxygen: {spo2}%")
    if temp > 100.4:
        reasons.append(f"Fever: {temp}°F")
    if sugar > 140:
        reasons.append(f"High blood sugar: {sugar}")

    severity = "Normal"
    if len(reasons) >= 2:
        severity = "Critical"
    elif len(reasons) == 1:
        severity = "Warning"

    event_type = "VitalsRecorded"
    if severity != "Normal":
        event_type = (
            "CriticalAlertGenerated"
            if severity == "Critical"
            else "HighSugarDetected"
            if "sugar" in str(reasons).lower()
            else "WarningAlertGenerated"
        )
        alert = Alert(
            alert_id=f"ALT-{data.patient_id}-{Event.id if hasattr(Event, 'id') else 0}",
            patient_id=data.patient_id,
            severity=severity,
            message="; ".join(reasons),
        )
        db.add(alert)

    event = Event(
        event_id=f"EVT-{data.patient_id}-VTL",
        event_type=event_type,
        patient_id=data.patient_id,
        description=f"Vitals recorded: {'; '.join(reasons) if reasons else 'All normal'}",
    )
    db.add(event)
    db.commit()
    return {"severity": severity, "reasons": reasons}


# ─── Active Alerts ──────────────────────────────────────────────────────────


@router.get("/alerts")
def get_alerts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by patient ID, severity, or message"),
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("nurse", "admin")),
):
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status)
    else:
        query = query.filter(Alert.status == "Active")
    query = apply_search(query, search, [Alert.patient_id, Alert.message, Alert.severity])
    query = apply_sort(
        query,
        sort_by,
        sort_order,
        {
            "alert_id": Alert.alert_id,
            "patient_id": Alert.patient_id,
            "severity": Alert.severity,
            "status": Alert.status,
            "created_at": Alert.created_at,
        },
        [Alert.created_at.desc(), Alert.alert_id.asc()],
    )
    return build_paginated_response(query, page, limit)


# ─── Medication Queue ───────────────────────────────────────────────────────
# Returns all medications with status "Prescribed" (not yet administered).


@router.get("/medications/queue")
def medication_queue(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by medication, patient ID, or medicine name"),
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("nurse", "admin")),
):
    query = db.query(Medication)
    if status:
        query = query.filter(Medication.status == status)
    else:
        query = query.filter(Medication.status == "Prescribed")
    query = apply_search(query, search, [Medication.medication_id, Medication.patient_id, Medication.medicine_name])
    query = apply_sort(
        query,
        sort_by,
        sort_order,
        {
            "medication_id": Medication.medication_id,
            "patient_id": Medication.patient_id,
            "medicine_name": Medication.medicine_name,
            "status": Medication.status,
        },
        [Medication.medicine_name.asc(), Medication.medication_id.asc()],
    )
    return build_paginated_response(query, page, limit)


# ─── Administer Medication ──────────────────────────────────────────────────
# Marks a medication as Administered. Validates existence and prevents
# double-administration. Emits a MedicationAdministered event.


@router.put("/medications/{medication_id}/administer", response_model=MedicationIdResponse)
def administer_medication(
    medication_id: str, db: Session = Depends(get_db), user: User = Depends(role_required("nurse", "admin"))
):
    med = db.query(Medication).filter(Medication.medication_id == medication_id).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")
    if med.status == cast(str, "Administered"):
        raise HTTPException(status_code=400, detail="Medication already administered")
    med.status = cast(str, "Administered")
    event = Event(
        event_id=f"EVT-{medication_id}-MED",
        event_type="MedicationAdministered",
        patient_id=med.patient_id,
        description=f"Medication {med.medicine_name} administered",
    )
    db.add(event)
    db.commit()
    return {"message": "Medication administered", "medication_id": medication_id}


# ─── Complete Checkup ───────────────────────────────────────────────────────
# Logs that a nurse completed a checkup for a patient.


@router.put("/checkups/{patient_id}/complete", response_model=PatientIdResponse)
def complete_checkup(
    patient_id: str, db: Session = Depends(get_db), user: User = Depends(role_required("nurse", "admin"))
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    event = Event(
        event_id=f"EVT-{patient_id}-CHKUP",
        event_type="CheckupCompleted",
        patient_id=patient_id,
        description="Nurse checkup completed",
    )
    db.add(event)
    db.commit()
    return {"message": "Checkup completed", "patient_id": patient_id}
