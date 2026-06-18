from typing import cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import role_required
from app.database import get_db
from app.models import Appointment, Event, Patient, User
from app.schemas import (
    AppointmentCreate,
    AppointmentIdResponse,
    PatientIdResponse,
    PatientRegister,
)

# All endpoints require reception or admin role
router = APIRouter(dependencies=[Depends(role_required("reception", "admin"))])


# ─── Register Patient ───────────────────────────────────────────────────────
# Creates a new patient record and emits a PatientRegistered event.
# Returns 400 if a patient with the same patient_id already exists.


@router.post("/patients/register", response_model=PatientIdResponse)
def register_patient(
    data: PatientRegister, db: Session = Depends(get_db), user: User = Depends(role_required("reception", "admin"))
):
    existing = db.query(Patient).filter(Patient.patient_id == data.patient_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Patient with this ID already exists")
    patient = Patient(**data.model_dump())
    db.add(patient)
    event = Event(
        event_id=f"EVT-{data.patient_id}-REG",
        event_type="PatientRegistered",
        patient_id=data.patient_id,
        description=f"Patient {data.name} registered",
    )
    db.add(event)
    db.commit()
    return {"message": "Patient registered", "patient_id": data.patient_id}


# ─── Create Appointment ─────────────────────────────────────────────────────
# Creates an appointment for an existing patient.
# Returns 404 if patient does not exist, 400 if appointment_id is a duplicate.


@router.post("/appointments", response_model=AppointmentIdResponse)
def create_appointment(
    data: AppointmentCreate, db: Session = Depends(get_db), user: User = Depends(role_required("reception", "admin"))
):
    patient = db.query(Patient).filter(Patient.patient_id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    existing = db.query(Appointment).filter(Appointment.appointment_id == data.appointment_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Appointment with this ID already exists")
    appointment = Appointment(**data.model_dump())
    db.add(appointment)
    event = Event(
        event_id=f"EVT-{data.appointment_id}-APT",
        event_type="AppointmentCreated",
        patient_id=data.patient_id,
        description=f"Appointment created on {data.date}",
    )
    db.add(event)
    db.commit()
    return {"message": "Appointment created", "appointment_id": data.appointment_id}


# ─── Check In Patient ───────────────────────────────────────────────────────
# Marks a patient as checked in. Returns 404 if not found, 400 if already done.


@router.post("/patients/{patient_id}/checkin", response_model=PatientIdResponse)
def checkin_patient(
    patient_id: str, db: Session = Depends(get_db), user: User = Depends(role_required("reception", "admin"))
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if patient.status == cast(str, "Checked In"):
        raise HTTPException(status_code=400, detail="Patient is already checked in")
    patient.status = cast(str, "Checked In")
    event = Event(
        event_id=f"EVT-{patient_id}-CHK",
        event_type="PatientCheckedIn",
        patient_id=patient_id,
        description="Patient checked in",
    )
    db.add(event)
    db.commit()
    return {"message": "Patient checked in", "patient_id": patient_id}


# ─── List Admissions ────────────────────────────────────────────────────────
# Returns all patients whose status is either "Admission Requested" or "Admitted".


@router.get("/admissions")
def list_admissions(db: Session = Depends(get_db), user: User = Depends(role_required("reception", "admin"))):
    return db.query(Patient).filter(Patient.status.in_(["Admission Requested", "Admitted"])).all()


# ─── List Appointments ──────────────────────────────────────────────────────


@router.get("/appointments")
def list_appointments(db: Session = Depends(get_db), user: User = Depends(role_required("reception", "admin"))):
    return db.query(Appointment).all()
