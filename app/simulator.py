import csv
import os
import uuid
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.engine.risk import evaluate_vitals
from app.engine.routing import get_recipients
from app.models import Alert, Appointment, Event, Medication, Notification, Patient, Review
from app.schemas import MessageResponse, SimulatorNextResponse, SimulatorStateResponse
from app.services.event_bus import build_event_payload, publish_event

router = APIRouter()

sim_state = {"current_step": 0}

_BUILTIN_EVENTS: list[dict[str, Any]] = [
    {"step": 1, "event_type": "PatientRegistered", "patient_id": "P101", "description": "New patient John Doe registered"},
    {"step": "2", "event_type": "AppointmentCreated", "patient_id": "P101", "description": "Follow-up appointment created"},
    {"step": "3", "event_type": "PatientCheckedIn", "patient_id": "P101", "description": "Patient John Doe checked in"},
    {"step": "4", "event_type": "PatientRegistered", "patient_id": "P102", "description": "New patient Jane Smith registered"},
    {"step": "5", "event_type": "AdmissionRequested", "patient_id": "P102", "description": "Admission requested for Jane Smith"},
    {"step": "6", "event_type": "AdmissionApproved", "patient_id": "P102", "description": "Admission approved for Jane Smith"},
    {"step": "7", "event_type": "PatientRegistered", "patient_id": "P103", "description": "New patient Bob Wilson registered"},
    {"step": "8", "event_type": "AppointmentCreated", "patient_id": "P103", "description": "Consultation appointment created"},
    {"step": "9", "event_type": "AdmissionRequested", "patient_id": "P103", "description": "Admission requested for Bob Wilson"},
    {"step": "10", "event_type": "PatientRegistered", "patient_id": "P104", "description": "New patient Alice Davis registered"},
    {"step": "11", "event_type": "VitalsRecorded", "patient_id": "P104", "description": "Routine vitals recorded"},
    {"step": "12", "event_type": "HighSugarDetected", "patient_id": "P104", "description": "High blood sugar detected - 185 mg/dL"},
    {"step": "13", "event_type": "MedicationPrescribed", "patient_id": "P104", "description": "Insulin prescribed for high blood sugar"},
    {"step": "14", "event_type": "PatientReviewed", "patient_id": "P104", "description": "Dr. Smith reviewed patient condition"},
    {"step": "15", "event_type": "PatientRegistered", "patient_id": "P105", "description": "New patient Tom Brown registered"},
    {"step": "16", "event_type": "AppointmentCreated", "patient_id": "P105", "description": "ER follow-up appointment created"},
    {"step": "17", "event_type": "VitalsRecorded", "patient_id": "P105", "description": "Abnormal vitals detected"},
    {"step": "18", "event_type": "CriticalAlertGenerated", "patient_id": "P105", "description": "CRITICAL: Heart rate 150 - Oxygen 85%"},
    {"step": "19", "event_type": "PatientReviewed", "patient_id": "P105", "description": "Dr. Carter reviewed critical patient"},
    {"step": "20", "event_type": "DischargeApproved", "patient_id": "P105", "description": "Patient Tom Brown discharged"},
]


def _load_events() -> list[dict[str, Any]]:
    csv_path = os.getenv("HOSPITAL_EVENTS_CSV")
    if csv_path:
        candidates = [csv_path]
    else:
        candidates = [
            os.path.join(os.path.dirname(__file__), "..", "data", "hospital_events.csv"),
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "hospital_events.csv"),
            "/app/data/hospital_events.csv",
            "/home/ec2-user/app/data/hospital_events.csv",
        ]
    for path in candidates:
        if os.path.exists(path):
            with open(path) as file:
                reader = csv.DictReader(file)
                return [
                    {
                        "step": int(row["step"]),
                        "event_type": row["event_type"],
                        "patient_id": row["patient_id"],
                        "description": row["description"],
                    }
                    for row in reader
                ]
    return list(_BUILTIN_EVENTS)


def _get_or_create_patient(db: Session, patient_id: str, name: str = "Unknown") -> Patient:
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        patient = Patient(
            patient_id=patient_id,
            name=name,
            age=35,
            gender="Unknown",
            department="General",
            ward="",
            assigned_doctor="doctor",
            assigned_nurse="nurse",
            status="Registered",
        )
        db.add(patient)
        db.flush()
    return patient


def run_simulation_to_completion(db: Session) -> None:
    """Process all CSV events into the database. Used by seed script."""
    events = _load_events()
    for step_data in events:
        event_id = f"SIM-{step_data['step']}-{step_data['patient_id']}"
        event = Event(
            event_id=event_id,
            event_type=step_data["event_type"],
            patient_id=step_data["patient_id"],
            description=step_data["description"],
            status="Processed",
        )
        db.add(event)

        event_type = step_data["event_type"]
        patient_id = step_data["patient_id"]

        if event_type == "PatientRegistered":
            name = step_data["description"].replace("New patient ", "").replace(" registered", "")
            _get_or_create_patient(db, patient_id, name)

        elif event_type == "AppointmentCreated":
            _get_or_create_patient(db, patient_id)
            appointment = Appointment(
                appointment_id=f"APT-SIM-{step_data['step']}",
                patient_id=patient_id,
                date="2026-06-18",
                time="10:00",
                status="Scheduled",
            )
            db.add(appointment)

        elif event_type == "AdmissionRequested":
            patient = _get_or_create_patient(db, patient_id)
            patient.status = cast(str, "Admission Requested")

        elif event_type == "AdmissionApproved":
            patient = _get_or_create_patient(db, patient_id)
            patient.status = cast(str, "Admitted")

        elif event_type == "PatientCheckedIn":
            patient = _get_or_create_patient(db, patient_id)
            patient.status = cast(str, "Checked In")

        elif event_type == "DischargeApproved":
            patient = _get_or_create_patient(db, patient_id)
            patient.status = cast(str, "Discharged")

        elif event_type == "VitalsRecorded":
            _get_or_create_patient(db, patient_id)
            result = evaluate_vitals(115, 120, 80, 97.0, 98.6, 100.0)
            alert = Alert(
                alert_id=f"ALT-SIM-{uuid.uuid4().hex[:8].upper()}",
                patient_id=patient_id,
                severity=result["status"].capitalize(),
                message=f"Vitals: HR 115, BP 120/80, SpO2 97%, Temp 98.6, Sugar 100 — {', '.join(result['reasons'])}",
                status="Active",
            )
            db.add(alert)

        elif event_type == "HighSugarDetected":
            _get_or_create_patient(db, patient_id)
            alert = Alert(
                alert_id=f"ALT-SIM-{uuid.uuid4().hex[:8].upper()}",
                patient_id=patient_id,
                severity="Warning",
                message="High blood sugar detected: 185 mg/dL",
                status="Active",
            )
            db.add(alert)

        elif event_type == "CriticalAlertGenerated":
            _get_or_create_patient(db, patient_id)
            alert = Alert(
                alert_id=f"ALT-SIM-{uuid.uuid4().hex[:8].upper()}",
                patient_id=patient_id,
                severity="Critical",
                message=f"CRITICAL: Heart rate 135 - Oxygen 88% — {step_data['description']}",
                status="Active",
            )
            db.add(alert)

        elif event_type == "MedicationPrescribed":
            _get_or_create_patient(db, patient_id)
            medication = Medication(
                medication_id=f"MED-SIM-{step_data['step']}",
                patient_id=patient_id,
                medicine_name="Insulin",
                prescribed_by="doctor",
                status="Prescribed",
            )
            db.add(medication)

        elif event_type == "PatientReviewed":
            _get_or_create_patient(db, patient_id)
            review_status = "Pending" if step_data["step"] % 2 == 0 else "Completed"
            review = Review(
                review_id=f"REV-SIM-{step_data['step']}",
                patient_id=patient_id,
                doctor_id="doctor",
                review_note=step_data["description"],
                review_status=review_status,
            )
            db.add(review)

    db.commit()
    sim_state["current_step"] = len(events)


@router.get(
    "/simulator/state",
    response_model=SimulatorStateResponse,
    summary="Get Simulator State",
    description=(
        "Return the current simulator step and the total number of predefined hospital events. "
        "This endpoint powers the simulator dashboard so users can see how far the demo has progressed."
    ),
)
def get_state(db: Session = Depends(get_db)):
    processed = db.query(Event).filter(Event.event_id.like("SIM-%")).count()
    sim_state["current_step"] = processed
    return {"current_step": processed, "total_events": len(_load_events())}


@router.post(
    "/simulator/next",
    response_model=SimulatorNextResponse,
    summary="Process Next Event",
    description=(
        "Process the next event from the simulation CSV, persist it as a hospital event, and route notifications "
        "to the affected roles. The event is also sent to SQS when queue integration is configured."
    ),
)
def next_event(db: Session = Depends(get_db)):
    events = _load_events()
    if sim_state["current_step"] >= len(events):
        raise HTTPException(status_code=400, detail="All events processed. Reset to start over.")

    step_data = events[sim_state["current_step"]]
    sim_state["current_step"] += 1

    event_id = f"SIM-{step_data['step']}-{step_data['patient_id']}"
    existing = db.query(Event).filter(Event.event_id == event_id).first()
    if existing:
        db.delete(existing)
        db.flush()
    event = Event(
        event_id=event_id,
        event_type=step_data["event_type"],
        patient_id=step_data["patient_id"],
        description=step_data["description"],
        status="Processed",
    )
    db.add(event)

    event_type = step_data["event_type"]
    patient_id = step_data["patient_id"]

    if event_type == "PatientRegistered":
        name = step_data["description"].replace("New patient ", "").replace(" registered", "")
        _get_or_create_patient(db, patient_id, name)

    elif event_type == "AppointmentCreated":
        patient = _get_or_create_patient(db, patient_id)
        appointment = Appointment(
            appointment_id=f"APT-SIM-{step_data['step']}",
            patient_id=patient_id,
            date="2026-06-18",
            time="10:00",
            status="Scheduled",
        )
        db.add(appointment)

    elif event_type == "AdmissionRequested":
        patient = _get_or_create_patient(db, patient_id)
        patient.status = cast(str, "Admission Requested")

    elif event_type == "AdmissionApproved":
        patient = _get_or_create_patient(db, patient_id)
        patient.status = cast(str, "Admitted")

    elif event_type == "PatientCheckedIn":
        patient = _get_or_create_patient(db, patient_id)
        patient.status = cast(str, "Checked In")

    elif event_type == "DischargeApproved":
        patient = _get_or_create_patient(db, patient_id)
        patient.status = cast(str, "Discharged")

    elif event_type == "VitalsRecorded":
        patient = _get_or_create_patient(db, patient_id)
        result = evaluate_vitals(115, 120, 80, 97.0, 98.6, 100.0)
        alert = Alert(
            alert_id=f"ALT-SIM-{uuid.uuid4().hex[:8].upper()}",
            patient_id=patient_id,
            severity=result["status"].capitalize(),
            message=f"Vitals: HR 115, BP 120/80, SpO2 97%, Temp 98.6, Sugar 100 — {', '.join(result['reasons'])}",
            status="Active",
        )
        db.add(alert)

    elif event_type == "HighSugarDetected":
        patient = _get_or_create_patient(db, patient_id)
        alert = Alert(
            alert_id=f"ALT-SIM-{uuid.uuid4().hex[:8].upper()}",
            patient_id=patient_id,
            severity="Warning",
            message="High blood sugar detected: 185 mg/dL",
            status="Active",
        )
        db.add(alert)

    elif event_type == "CriticalAlertGenerated":
        patient = _get_or_create_patient(db, patient_id)
        alert = Alert(
            alert_id=f"ALT-SIM-{uuid.uuid4().hex[:8].upper()}",
            patient_id=patient_id,
            severity="Critical",
            message=f"CRITICAL: Heart rate 135 - Oxygen 88% — {step_data['description']}",
            status="Active",
        )
        db.add(alert)

    elif event_type == "MedicationPrescribed":
        patient = _get_or_create_patient(db, patient_id)
        medication = Medication(
            medication_id=f"MED-SIM-{step_data['step']}",
            patient_id=patient_id,
            medicine_name="Insulin",
            prescribed_by="doctor",
            status="Prescribed",
        )
        db.add(medication)

    elif event_type == "MedicationAdministered":
        existing_medication: Medication | None = (
            db.query(Medication)
            .filter(Medication.patient_id == patient_id, Medication.status == "Prescribed")
            .first()
        )
        if existing_medication:
            existing_medication.status = cast(str, "Administered")

    elif event_type == "PatientReviewed":
        patient = _get_or_create_patient(db, patient_id)
        review_status = "Pending" if step_data["step"] % 2 == 0 else "Completed"
        review = Review(
            review_id=f"REV-SIM-{step_data['step']}",
            patient_id=patient_id,
            doctor_id="doctor",
            review_note=step_data["description"],
            review_status=review_status,
        )
        db.add(review)

    db.commit()

    recipients = get_recipients(event_type)
    publish_event(
        db,
        build_event_payload(
            event,
            actor_role="simulator",
            source="simulator",
            metadata={"step": step_data["step"]},
        ),
    )

    return {"step": step_data, "recipients": recipients}


@router.post(
    "/simulator/previous",
    response_model=SimulatorNextResponse,
    summary="Process Previous Event",
    description="Go back one step by undoing the last processed event and its notification.",
)
def previous_event(db: Session = Depends(get_db)):
    if sim_state["current_step"] <= 0:
        raise HTTPException(status_code=400, detail="No events to undo.")

    sim_state["current_step"] -= 1
    events = _load_events()
    step_data = events[sim_state["current_step"]]

    event_id = f"SIM-{step_data['step']}-{step_data['patient_id']}"
    event = db.query(Event).filter(Event.event_id == event_id).first()
    if event:
        db.delete(event)

    db.query(Notification).filter(
        Notification.message.ilike(f"{step_data['event_type']}: {step_data['description']}%")
    ).delete(synchronize_session=False)
    db.commit()

    recipients = get_recipients(step_data["event_type"])

    return {"step": step_data, "recipients": recipients}


@router.post(
    "/simulator/reset",
    response_model=MessageResponse,
    summary="Reset Simulation",
    description=(
        "Reset the simulator back to the first event and clear generated data. "
        "Use this endpoint before rerunning the demo flow from the beginning."
    ),
)
def reset_simulation(db: Session = Depends(get_db)):
    sim_state["current_step"] = 0
    db.query(Alert).delete()
    db.query(Appointment).delete()
    db.query(Event).delete()
    db.query(Medication).delete()
    db.query(Notification).delete()
    db.query(Patient).delete()
    db.query(Review).delete()
    db.commit()
    return {"message": "Simulation reset"}
