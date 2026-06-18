import uuid

from sqlalchemy.orm import Session

from app.models import Notification


def create_notification(db: Session, recipient_role: str, message: str) -> Notification:
    notif = Notification(
        notification_id=f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
        recipient_role=recipient_role,
        message=message,
        status="Unread",
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def get_notifications_for_role(db: Session, role: str) -> list[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.recipient_role == role, Notification.status == "Unread")
        .order_by(Notification.created_at.desc())
        .all()
    )


def mark_notification_read(db: Session, notification_id: str) -> Notification | None:
    notif = db.query(Notification).filter(Notification.notification_id == notification_id).first()
    if notif:
        notif.status = "Read"
        db.commit()
    return notif
