import csv
import os
import uuid
from typing import cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.engine.routing import get_recipients
from app.engine.risk import evaluate_vitals
from app.models import Alert, Appointment, Event, Medication, Notification, Patient, Review
from app.schemas import MessageResponse, SimulatorNextResponse, SimulatorStateResponse
from app.services.notifications import create_notification
from app.services.sqs import send_to_sqs

router = APIRouter()

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "hospital_events.csv")

sim_state = {"current_step": 0}


def _load_events():
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH) as file:
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
            assigned_doctor="",
            assigned_nurse="",
            status="Registered",
        )
        db.add(patient)
        db.flush()
    return patient


@router.get(
    "/simulator/state",
    response_model=SimulatorStateResponse,
    summary="Get Simulator State",
    description=(
        "Return the current simulator step and the total number of predefined hospital events. "
        "This endpoint powers the simulator dashboard so users can see how far the demo has progressed."
    ),
)
def get_state():
    return {"current_step": sim_state["current_step"], "total_events": len(_load_events())}


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
        medication = (
            db.query(Medication)
            .filter(Medication.patient_id == patient_id, Medication.status == "Prescribed")
            .first()
        )
        if medication:
            medication.status = cast(str, "Administered")

    elif event_type == "PatientReviewed":
        patient = _get_or_create_patient(db, patient_id)
        review = Review(
            review_id=f"REV-SIM-{step_data['step']}",
            patient_id=patient_id,
            doctor_id="doctor",
            review_note=step_data["description"],
            review_status="Completed",
        )
        db.add(review)

    db.commit()

    recipients = get_recipients(event_type)
    for role in recipients:
        create_notification(db, role, f"{event_type}: {step_data['description']}")

    send_to_sqs(step_data)

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
