from typing import cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import role_required
from app.database import get_db
from app.models import Appointment, Event, Patient, User
from app.routers import apply_pagination, apply_search, pagination_params
from app.schemas import (
    AppointmentCreate,
    AppointmentIdResponse,
    PatientIdResponse,
    PatientRegister,
)

router = APIRouter()


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


@router.get("/admissions")
def list_admissions(
    status: str | None = None,
    search: str | None = None,
    pagination: tuple[int, int] = Depends(pagination_params),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("reception", "admin")),
):
    page, limit = pagination
    query = db.query(Patient).filter(Patient.status.in_(["Admission Requested", "Admitted"]))
    if status:
        query = query.filter(Patient.status == status)
    query = apply_search(query, search, [Patient.patient_id, Patient.name, Patient.department])
    query = query.order_by(Patient.name.asc(), Patient.patient_id.asc())
    return apply_pagination(query, page, limit).all()


@router.get("/appointments")
def list_appointments(
    status: str | None = None,
    search: str | None = None,
    pagination: tuple[int, int] = Depends(pagination_params),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("reception", "admin")),
):
    page, limit = pagination
    query = db.query(Appointment)
    if status:
        query = query.filter(Appointment.status == status)
    query = apply_search(query, search, [Appointment.appointment_id, Appointment.patient_id])
    query = query.order_by(Appointment.date.asc(), Appointment.time.asc(), Appointment.appointment_id.asc())
    return apply_pagination(query, page, limit).all()


@router.get("/patients")
def get_patients(
    status: str | None = None,
    search: str | None = None,
    pagination: tuple[int, int] = Depends(pagination_params),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("reception", "nurse", "doctor", "admin")),
):
    page, limit = pagination
    query = db.query(Patient)
    if status:
        query = query.filter(Patient.status == status)
    query = apply_search(query, search, [Patient.patient_id, Patient.name, Patient.department])
    query = query.order_by(Patient.name.asc(), Patient.patient_id.asc())
    return apply_pagination(query, page, limit).all()
