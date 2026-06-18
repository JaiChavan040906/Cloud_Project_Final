import json
import os
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hospital.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String(20), unique=True)
    recipient_role = Column(String(20))
    message = Column(Text)
    status = Column(String(20), default="Unread")
    created_at = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(20), unique=True)
    event_type = Column(String(50))
    patient_id = Column(String(20))
    description = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="Pending")


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


def _create_notification(db, role, message):
    notif = Notification(
        notification_id=f"LMD-{uuid.uuid4().hex[:8].upper()}",
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

            evt = Event(
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

        return {
            "statusCode": 200,
            "body": json.dumps({"processed": len(event.get("Records", []))}),
        }
    finally:
        db.close()
