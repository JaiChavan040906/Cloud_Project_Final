import csv
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.engine.routing import get_recipients
from app.models import Event, Notification, Patient
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

    event = Event(
        event_id=f"SIM-{step_data['step']}-{step_data['patient_id']}",
        event_type=step_data["event_type"],
        patient_id=step_data["patient_id"],
        description=step_data["description"],
        status="Processed",
    )
    db.add(event)

    status_map = {
        "PatientCheckedIn": "Checked In",
        "AdmissionRequested": "Admission Requested",
        "AdmissionApproved": "Admitted",
        "DischargeApproved": "Discharged",
    }
    new_status = status_map.get(step_data["event_type"])
    if new_status:
        patient = db.query(Patient).filter(Patient.patient_id == step_data["patient_id"]).first()
        if patient:
            patient.status = new_status

    db.commit()

    recipients = get_recipients(step_data["event_type"])
    for role in recipients:
        create_notification(db, role, f"{step_data['event_type']}: {step_data['description']}")

    send_to_sqs(step_data)

    return {"step": step_data, "recipients": recipients}


@router.post(
    "/simulator/reset",
    response_model=MessageResponse,
    summary="Reset Simulation",
    description=(
        "Reset the simulator back to the first event and clear generated notifications. "
        "Use this endpoint before rerunning the demo flow from the beginning."
    ),
)
def reset_simulation(db: Session = Depends(get_db)):
    sim_state["current_step"] = 0
    db.query(Notification).delete()
    db.commit()
    return {"message": "Simulation reset"}
