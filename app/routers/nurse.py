from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import role_required
from app.database import get_db
from app.models import Alert, Event, Medication, Patient, User
from app.routers import apply_search, apply_sort, build_paginated_response
from app.schemas import (
    MedicationIdResponse,
    PaginatedAlertsResponse,
    PaginatedMedicationsResponse,
    PaginatedPatientsResponse,
    PatientIdResponse,
    VitalsRecord,
    VitalsResponse,
)

router = APIRouter(dependencies=[Depends(role_required("nurse", "admin"))])


@router.get(
    "/patients/assigned",
    response_model=PaginatedPatientsResponse,
    summary="Get Assigned Patients",
    description=(
        "Return the paginated patient list assigned to the current Nurse user, or all matching records for Admin. "
        "This endpoint supports search, filters, and sorting so staff can quickly find patients in their queue."
    ),
)
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


@router.post(
    "/vitals",
    response_model=VitalsResponse,
    summary="Record Patient Vitals",
    description=(
        "Record vital signs for an existing patient. The values are evaluated by the risk engine, which may create "
        "warning or critical alerts and store a corresponding event. Only Nurse and Admin roles can access this endpoint."
    ),
)
def record_vitals(
    data: VitalsRecord,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("nurse", "admin")),
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
        reasons.append(f"Fever: {temp}Â°F")
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


@router.get(
    "/alerts",
    response_model=PaginatedAlertsResponse,
    summary="List Active Alerts",
    description=(
        "Return the nurse-facing alert feed with optional filters, search, sorting, and pagination. "
        "This endpoint helps Nurse and Admin users monitor active warning and critical patient alerts."
    ),
)
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
    query = query.filter(Alert.status == status) if status else query.filter(Alert.status == "Active")
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


@router.get(
    "/medications/queue",
    response_model=PaginatedMedicationsResponse,
    summary="List Medication Queue",
    description=(
        "Return prescribed medications awaiting administration, with optional filtering, searching, sorting, and "
        "pagination. Nurse and Admin users use this queue to track medication tasks."
    ),
)
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
    query = query.filter(Medication.status == status) if status else query.filter(Medication.status == "Prescribed")
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


@router.put(
    "/medications/{medication_id}/administer",
    response_model=MedicationIdResponse,
    summary="Administer Medication",
    description=(
        "Mark a prescribed medication as administered for a patient. This endpoint is restricted to Nurse and Admin "
        "roles and emits a MedicationAdministered event when the action succeeds."
    ),
)
def administer_medication(
    medication_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("nurse", "admin")),
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


@router.put(
    "/checkups/{patient_id}/complete",
    response_model=PatientIdResponse,
    summary="Complete Patient Checkup",
    description=(
        "Record that a nurse has completed a patient checkup. This endpoint is available to Nurse and Admin roles "
        "and logs a CheckupCompleted event for downstream dashboards."
    ),
)
def complete_checkup(
    patient_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("nurse", "admin")),
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
