from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import role_required
from app.database import get_db
from app.models import Appointment, Event, Patient, User
from app.routers import apply_search, apply_sort, build_paginated_response
from app.schemas import (
    AppointmentCreate,
    AppointmentIdResponse,
    PatientIdResponse,
    PatientRegister,
)

router = APIRouter()


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
def list_admissions(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by patient ID, name, or department"),
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("reception", "admin")),
):
    query = db.query(Patient).filter(Patient.status.in_(["Admission Requested", "Admitted"]))
    if status:
        query = query.filter(Patient.status == status)
    query = apply_search(query, search, [Patient.patient_id, Patient.name, Patient.department])
    query = apply_sort(
        query,
        sort_by,
        sort_order,
        {"patient_id": Patient.patient_id, "name": Patient.name, "department": Patient.department, "status": Patient.status},
        [Patient.name.asc(), Patient.patient_id.asc()],
    )
    return build_paginated_response(query, page, limit)


# ─── List Appointments ──────────────────────────────────────────────────────


@router.get("/appointments")
def list_appointments(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by appointment or patient ID"),
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("reception", "admin")),
):
    query = db.query(Appointment)
    if status:
        query = query.filter(Appointment.status == status)
    query = apply_search(query, search, [Appointment.appointment_id, Appointment.patient_id])
    query = apply_sort(
        query,
        sort_by,
        sort_order,
        {
            "appointment_id": Appointment.appointment_id,
            "patient_id": Appointment.patient_id,
            "date": Appointment.date,
            "time": Appointment.time,
            "status": Appointment.status,
        },
        [Appointment.date.asc(), Appointment.time.asc(), Appointment.appointment_id.asc()],
    )
    return build_paginated_response(query, page, limit)


@router.get("/patients")
def get_patients(
    search: str | None = Query(None, description="Search by name, patient ID, or department"),
    status: str | None = Query(None, description="Filter by status"),
    department: str | None = Query(None, description="Filter by department"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("reception", "nurse", "doctor", "admin")),
):
    query = db.query(Patient)
    if status:
        query = query.filter(Patient.status == status)
    if department:
        query = query.filter(Patient.department == department)
    query = apply_search(query, search, [Patient.patient_id, Patient.name, Patient.department])
    query = apply_sort(
        query,
        sort_by,
        sort_order,
        {"patient_id": Patient.patient_id, "name": Patient.name, "department": Patient.department, "status": Patient.status},
        [Patient.name.asc(), Patient.patient_id.asc()],
    )
    return build_paginated_response(query, page, limit)
