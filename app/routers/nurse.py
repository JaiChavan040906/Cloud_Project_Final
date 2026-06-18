from typing import cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import role_required
from app.database import get_db
from app.models import Alert, Event, Medication, Patient, User
from app.schemas import MedicationIdResponse, PatientIdResponse, VitalsRecord, VitalsResponse

router = APIRouter(dependencies=[Depends(role_required("nurse", "admin"))])


@router.get("/patients/assigned")
def assigned_patients(db: Session = Depends(get_db), user: User = Depends(role_required("nurse", "admin"))):
    return db.query(Patient).filter(Patient.assigned_nurse == user.username).all()


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


@router.get("/alerts")
def get_alerts(db: Session = Depends(get_db), user: User = Depends(role_required("nurse", "admin"))):
    return db.query(Alert).filter(Alert.status == "Active").all()


@router.get("/medications/queue")
def medication_queue(db: Session = Depends(get_db), user: User = Depends(role_required("nurse", "admin"))):
    return db.query(Medication).filter(Medication.status == "Prescribed").all()


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
