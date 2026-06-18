from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import role_required
from app.database import get_db
from app.models import Appointment, Event, Patient, User
from app.schemas import AppointmentCreate, PatientRegister

router = APIRouter(dependencies=[Depends(role_required("reception", "admin"))])


@router.post("/patients/register")
def register_patient(
    data: PatientRegister, db: Session = Depends(get_db), user: User = Depends(role_required("reception", "admin"))
):
    existing = db.query(Patient).filter(Patient.patient_id == data.patient_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Patient already exists")
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


@router.post("/appointments")
def create_appointment(
    data: AppointmentCreate, db: Session = Depends(get_db), user: User = Depends(role_required("reception", "admin"))
):
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


@router.post("/patients/{patient_id}/checkin")
def checkin_patient(
    patient_id: str, db: Session = Depends(get_db), user: User = Depends(role_required("reception", "admin"))
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.status = "Checked In"
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
def list_admissions(db: Session = Depends(get_db), user: User = Depends(role_required("reception", "admin"))):
    patients = db.query(Patient).filter(Patient.status.in_(["Admission Requested", "Admitted"])).all()
    return patients


@router.get("/appointments")
def list_appointments(db: Session = Depends(get_db), user: User = Depends(role_required("reception", "admin"))):
    return db.query(Appointment).all()
