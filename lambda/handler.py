import json

from app.database import SessionLocal
from app.engine.routing import get_recipients
from app.services.notifications import create_notification


def lambda_handler(event: dict, context) -> dict:
    print(f"Received event batch: {json.dumps(event)}")

    processed = 0
    db = SessionLocal()
    try:
        for record in event.get("Records", []):
            body = json.loads(record["body"])
            event_id = body.get("event_id", "")
            event_type = body.get("event_type", "")
            description = body.get("description", "")

            recipients = get_recipients(event_type)
            for role in recipients:
                create_notification(
                    db,
                    role,
                    f"{event_type}: {description}",
                    source_event_id=event_id,
                )

            processed += 1
            print(f"Processed {event_id} for recipients {recipients}")

        return {
            "statusCode": 200,
            "body": json.dumps({"processed": processed}),
        }
    finally:
        db.close()
