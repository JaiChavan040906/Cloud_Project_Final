from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.engine.routing import get_recipients
from app.models import Event
from app.services.notifications import create_notification
from app.services.sqs import send_to_sqs


def build_event_payload(
    event: Event,
    *,
    actor_role: str,
    source: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "patient_id": event.patient_id,
        "description": event.description,
        "source": source,
        "actor_role": actor_role,
        "timestamp": datetime.now(UTC).isoformat(),
        "metadata": metadata or {},
    }


def publish_event(db: Session, payload: dict[str, Any]) -> bool:
    sent = send_to_sqs(payload)
    if sent:
        return True

    message = f"{payload['event_type']}: {payload['description']}"
    for role in get_recipients(str(payload["event_type"])):
        create_notification(
            db,
            role,
            message,
            source_event_id=str(payload["event_id"]),
        )
    return False
