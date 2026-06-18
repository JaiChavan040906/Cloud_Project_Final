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
    PaginatedAppointmentsResponse,
    PaginatedPatientsResponse,
    PatientIdResponse,
    PatientRegister,
)
from app.services.event_bus import build_event_payload, publish_event

router = APIRouter()


@router.post(
    "/patients/register",
    response_model=PatientIdResponse,
    summary="Register a New Patient",
    description=(
        "Create a new patient record in the system. This endpoint is available to Receptionist and Admin roles "
        "and also emits a PatientRegistered event for downstream hospital workflow tracking."
    ),
)
def register_patient(
    data: PatientRegister,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("reception", "admin")),
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

    publish_event(
        db,
        build_event_payload(
            event,
            actor_role=cast(str, user.role),
            source="api",
            metadata={"patient_name": data.name},
        ),
    )

    return {"message": "Patient registered", "patient_id": data.patient_id}


@router.post(
    "/appointments",
    response_model=AppointmentIdResponse,
    summary="Create an Appointment",
    description=(
        "Create an appointment for an existing patient. This endpoint is available to Receptionist and Admin roles "
        "and emits an AppointmentCreated event so other dashboards can react to the booking."
    ),
)
def create_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("reception", "admin")),
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

    publish_event(
        db,
        build_event_payload(
            event,
            actor_role=cast(str, user.role),
            source="api",
            metadata={"appointment_id": data.appointment_id},
        ),
    )

    return {"message": "Appointment created", "appointment_id": data.appointment_id}


@router.post(
    "/patients/{patient_id}/checkin",
    response_model=PatientIdResponse,
    summary="Check In a Patient",
    description=(
        "Mark an existing patient as checked in at the reception desk. This endpoint is available to Receptionist "
        "and Admin roles and emits a PatientCheckedIn event for the care workflow."
    ),
)
def checkin_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("reception", "admin")),
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

    publish_event(
        db,
        build_event_payload(
            event,
            actor_role=cast(str, user.role),
            source="api",
            metadata={"patient_status": patient.status},
        ),
    )

    return {"message": "Patient checked in", "patient_id": patient_id}


@router.post(
    "/patients/{patient_id}/admission-request",
    response_model=PatientIdResponse,
    summary="Request Admission",
    description=(
        "Request admission for an existing patient. This sets the patient status to Admission Requested "
        "and emits an AdmissionRequested event. Available to Receptionist and Admin roles."
    ),
)
def request_admission(
    patient_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("reception", "admin")),
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if patient.status == "Admission Requested":
        raise HTTPException(status_code=400, detail="Admission already requested")
    patient.status = cast(str, "Admission Requested")
    event = Event(
        event_id=f"EVT-{patient_id}-ADMRQ",
        event_type="AdmissionRequested",
        patient_id=patient_id,
        description=f"Admission requested for patient {patient_id}",
    )
    db.add(event)
    db.commit()

    publish_event(
        db,
        build_event_payload(
            event,
            actor_role=cast(str, user.role),
            source="api",
            metadata={"patient_status": patient.status},
        ),
    )

    return {"message": "Admission requested", "patient_id": patient_id}


@router.get(
    "/admissions",
    response_model=PaginatedPatientsResponse,
    summary="List Admission Requests",
    description=(
        "List patients in the admission workflow for Receptionist and Admin roles. Results support filtering, "
        "searching, sorting, and pagination so the front desk can manage admission and check-in traffic efficiently."
    ),
)
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
        {
            "patient_id": Patient.patient_id,
            "name": Patient.name,
            "department": Patient.department,
            "status": Patient.status,
        },
        [Patient.name.asc(), Patient.patient_id.asc()],
    )
    return build_paginated_response(query, page, limit)


@router.get(
    "/appointments",
    response_model=PaginatedAppointmentsResponse,
    summary="List All Appointments",
    description=(
        "Return a paginated appointment list for Receptionist and Admin roles. The response supports filtering, "
        "searching, and sorting so staff can review the appointment book in the Swagger UI and in the frontend."
    ),
)
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


@router.get(
    "/patients",
    response_model=PaginatedPatientsResponse,
    summary="Search Patients",
    description=(
        "Search the shared patient directory across roles with optional status, department, sorting, and pagination "
        "filters. This endpoint is accessible to Receptionist, Nurse, Doctor, and Admin roles."
    ),
)
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
        {
            "patient_id": Patient.patient_id,
            "name": Patient.name,
            "department": Patient.department,
            "status": Patient.status,
        },
        [Patient.name.asc(), Patient.patient_id.asc()],
    )
    return build_paginated_response(query, page, limit)
