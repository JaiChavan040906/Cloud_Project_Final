import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import boto3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hospital.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

EVENT_ROUTES = {
    "PatientRegistered": ["reception", "admin"],
    "AppointmentCreated": ["reception", "admin"],
    "PatientCheckedIn": ["reception", "nurse"],
    "AdmissionRequested": ["admin", "reception"],
    "AdmissionApproved": ["reception", "nurse", "doctor", "admin"],
    "VitalsRecorded": ["nurse", "doctor"],
    "HighSugarDetected": ["nurse", "doctor", "admin"],
    "WarningAlertGenerated": ["nurse", "doctor"],
    "CriticalAlertGenerated": ["nurse", "doctor", "admin"],
    "MedicationPrescribed": ["nurse", "doctor"],
    "MedicationAdministered": ["nurse", "admin"],
    "PatientReviewed": ["doctor", "admin"],
    "CheckupCompleted": ["nurse", "doctor"],
    "DischargeApproved": ["reception", "nurse", "admin"],
}


def _get_recipients(event_type: str) -> list[str]:
    return EVENT_ROUTES.get(event_type, [])


def _create_notification(db, role: str, message: str):
    import uuid
    from app.models import Notification
    notif = Notification(
        notification_id=f"LAMBDA-{uuid.uuid4().hex[:8].upper()}",
        recipient_role=role,
        message=message,
        status="Unread",
    )
    db.add(notif)
    db.commit()


def lambda_handler(event: dict, context) -> dict:
    print(f"Received event: {json.dumps(event)}")

    db = SessionLocal()
    try:
        for record in event.get("Records", []):
            body = json.loads(record["body"])
            event_type = body.get("event_type", "")
            patient_id = body.get("patient_id", "")
            description = body.get("description", "")

            print(f"Processing: {event_type} for {patient_id}")

            from app.models import Event as EventModel
            evt = EventModel(
                event_id=f"LMD-{patient_id}-{event_type[:3]}",
                event_type=event_type,
                patient_id=patient_id,
                description=description,
                status="Processed",
            )
            db.add(evt)
            db.commit()

            recipients = _get_recipients(event_type)
            for role in recipients:
                _create_notification(db, role, f"{event_type}: {description}")

            print(f"Routed to: {recipients}")

        return {"statusCode": 200, "body": json.dumps({"processed": len(event.get("Records", []))})}
    finally:
        db.close()
