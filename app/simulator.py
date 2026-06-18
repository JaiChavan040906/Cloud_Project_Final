import csv
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.engine.routing import get_recipients
from app.models import Event, Notification
from app.services.notifications import create_notification
from app.services.sqs import send_to_sqs

router = APIRouter(tags=["Simulator"])

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "hospital_events.csv")

sim_state = {"current_step": 0}


def _load_events():
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH) as f:
        reader = csv.DictReader(f)
        return [
            {
                "step": int(r["step"]),
                "event_type": r["event_type"],
                "patient_id": r["patient_id"],
                "description": r["description"],
            }
            for r in reader
        ]


@router.get("/simulator/state")
def get_state():
    return {"current_step": sim_state["current_step"], "total_events": len(_load_events())}


@router.post("/simulator/next")
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
    db.commit()

    recipients = get_recipients(step_data["event_type"])
    for role in recipients:
        create_notification(db, role, f"{step_data['event_type']}: {step_data['description']}")

    send_to_sqs(step_data)

    return {"step": step_data, "recipients": recipients}


@router.post("/simulator/reset")
def reset_simulation(db: Session = Depends(get_db)):
    sim_state["current_step"] = 0
    db.query(Notification).delete()
    db.commit()
    return {"message": "Simulation reset"}
