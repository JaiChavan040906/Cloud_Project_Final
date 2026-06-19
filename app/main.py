import os
from time import monotonic
from typing import cast

import boto3
from botocore.config import Config
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, verify_password
from app.config import AWS_ENDPOINT_URL, AWS_REGION, S3_BUCKET_NAME, SQS_QUEUE_URL
from app.database import Base, SessionLocal, engine, get_db
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

internal_router = APIRouter(tags=["Internal"])


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
    status = "ok"
    db_healthy = False
    sqs_healthy = None
    s3_healthy = None
    errors: list[str] = []

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        db_healthy = True
    except Exception as e:
        db_healthy = False
        errors.append(f"db: {e}")
        status = "degraded"

    aws_kwargs = {"region_name": AWS_REGION, "config": Config(retries={"max_attempts": 3})}
    if AWS_ENDPOINT_URL:
        aws_kwargs["endpoint_url"] = AWS_ENDPOINT_URL

    if SQS_QUEUE_URL:
        try:
            boto3.client("sqs", **aws_kwargs).get_queue_attributes(
                QueueUrl=SQS_QUEUE_URL,
                AttributeNames=["QueueArn"],
            )
            sqs_healthy = True
        except Exception as e:
            sqs_healthy = False
            errors.append(f"sqs: {e}")
            if status == "ok":
                status = "degraded"
    else:
        sqs_healthy = None

    if S3_BUCKET_NAME:
        try:
            boto3.client("s3", **aws_kwargs).head_bucket(Bucket=S3_BUCKET_NAME)
            s3_healthy = True
        except Exception as e:
            s3_healthy = False
            errors.append(f"s3: {e}")
            if status == "ok":
                status = "degraded"
    else:
        s3_healthy = None

    uptime_seconds = int(monotonic() - APP_START_TIME)

    result = HealthResponse(
        status=status,
        db=db_healthy,
        sqs=sqs_healthy,
        s3=s3_healthy,
        uptime_seconds=uptime_seconds,
        errors=errors or None,
    )

    if not db_healthy:
        return JSONResponse(status_code=503, content=result.model_dump(exclude_none=True))

    return result


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
    if not user or not verify_password(req.password, str(user.password)):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username,
    }


# Role hierarchy: which roles a given role is allowed to view notifications for
ROLE_HIERARCHY: dict[str, list[str]] = {
    "admin": ["admin", "doctor", "nurse", "reception"],
    "doctor": ["doctor", "admin"],
    "nurse": ["nurse", "admin"],
    "reception": ["reception", "admin"],
}

app.include_router(internal_router)
app.include_router(reception.router, prefix="/api", tags=["Receptionist"])
app.include_router(admin.router, prefix="/api", tags=["Admin"])
app.include_router(nurse.router, prefix="/api", tags=["Nurse"])
app.include_router(doctor.router, prefix="/api", tags=["Doctor"])
app.include_router(simulator_router, prefix="/api", tags=["Simulator"])


@app.get(
    "/api/notifications",
    response_model=list[NotificationResponse],
    tags=["Notifications"],
    summary="Get Notifications for Current User",
    description=(
        "Retrieve notifications for a specific role. "
        "The authenticated user must have access to the requested role. "
        "If no role is specified, the user's own role is used. "
        "This endpoint is used by dashboard clients to render role-specific activity and alert messages."
    ),
)
def get_notifications(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    role: str | None = Query(default=None, description="Dashboard role to fetch notifications for"),
):
    target_role = role if role else cast(str, user.role)
    allowed = ROLE_HIERARCHY.get(cast(str, user.role), [cast(str, user.role)])
    if target_role not in allowed:
        raise HTTPException(status_code=403, detail="Not authorized for this role's notifications")
    return notif_service.get_notifications_for_role(db, target_role)


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
def read_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    role: str | None = Query(default=None, description="Dashboard role to scope the notification to"),
):
    target_role = role if role else cast(str, user.role)
    allowed = ROLE_HIERARCHY.get(cast(str, user.role), [cast(str, user.role)])
    if target_role not in allowed:
        raise HTTPException(status_code=403, detail="Not authorized for this role's notifications")
    notif = notif_service.mark_notification_read(db, notification_id, target_role)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Marked as read"}


frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
