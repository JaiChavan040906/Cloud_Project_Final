from time import monotonic

import boto3
from botocore.config import Config
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import create_access_token, verify_password
from app.config import AWS_ENDPOINT_URL, AWS_REGION, S3_BUCKET_NAME, SQS_QUEUE_URL
from app.database import Base, engine, get_db
from app.models import User
from app.routers import admin, doctor, nurse, reception
from app.schemas import HealthResponse, LoginRequest, MessageResponse, NotificationResponse, TokenResponse
from app.services import notifications as notif_service
from app.simulator import router as simulator_router

Base.metadata.create_all(bind=engine)
APP_START_TIME = monotonic()

app = FastAPI(title="Hospital Event Simulation", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health Check",
    description=(
        "Check the availability of the API, database, SQS queue, and S3 bucket. "
        "This endpoint is public and is primarily used for local development, container health validation, "
        "and infrastructure monitoring."
    ),
)
def health():
    db_ok = False
    sqs_ok = False
    s3_ok = False

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    aws_kwargs = {"region_name": AWS_REGION, "config": Config(retries={"max_attempts": 3})}
    if AWS_ENDPOINT_URL:
        aws_kwargs["endpoint_url"] = AWS_ENDPOINT_URL

    try:
        if SQS_QUEUE_URL:
            boto3.client("sqs", **aws_kwargs).get_queue_attributes(
                QueueUrl=SQS_QUEUE_URL,
                AttributeNames=["QueueArn"],
            )
            sqs_ok = True
    except Exception:
        sqs_ok = False

    try:
        if S3_BUCKET_NAME:
            boto3.client("s3", **aws_kwargs).head_bucket(Bucket=S3_BUCKET_NAME)
            s3_ok = True
    except Exception:
        s3_ok = False

    status = "ok" if db_ok and sqs_ok and s3_ok else "degraded"
    return {
        "status": status,
        "db": db_ok,
        "sqs": sqs_ok,
        "s3": s3_ok,
        "uptime_seconds": int(monotonic() - APP_START_TIME),
    }


@app.post(
    "/auth/login",
    response_model=TokenResponse,
    tags=["Authentication"],
    summary="Authenticate User",
    description=(
        "Authenticate a user with username and password and return a JWT access token. "
        "The returned token includes the user's role and is required for all protected dashboard endpoints."
    ),
)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password):  # type: ignore[arg-type]
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username,
    }


app.include_router(reception.router, prefix="/api", tags=["Receptionist"])
app.include_router(admin.router, prefix="/api", tags=["Admin"])
app.include_router(nurse.router, prefix="/api", tags=["Nurse"])
app.include_router(doctor.router, prefix="/api", tags=["Doctor"])
app.include_router(simulator_router, prefix="/api", tags=["Simulator"])


@app.get(
    "/api/notifications",
    response_model=list[NotificationResponse],
    tags=["Notifications"],
    summary="Get Notifications by Role",
    description=(
        "Retrieve notifications currently stored for a given role. "
        "This endpoint is used by dashboard clients to render role-specific activity and alert messages."
    ),
)
def get_notifications(role: str, db: Session = Depends(get_db)):
    return notif_service.get_notifications_for_role(db, role)


@app.put(
    "/api/notifications/{notification_id}/read",
    response_model=MessageResponse,
    tags=["Notifications"],
    summary="Mark Notification as Read",
    description=(
        "Mark a single notification as read by its notification ID. "
        "This updates the stored notification state so the UI can clear unread badges or hide handled messages."
    ),
)
def read_notification(notification_id: str, db: Session = Depends(get_db)):
    notif = notif_service.mark_notification_read(db, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Marked as read"}
