import time

import boto3
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import create_access_token, verify_password
from app.config import AWS_ENDPOINT_URL, AWS_REGION, S3_BUCKET_NAME, SQS_QUEUE_URL
from app.database import Base, SessionLocal, engine, get_db
from app.models import User
from app.routers import admin, doctor, nurse, reception
from app.schemas import LoginRequest
from app.services import notifications as notif_service
from app.simulator import router as simulator_router

Base.metadata.create_all(bind=engine)

START_TIME = time.time()

app = FastAPI(title="Hospital Event Simulation", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

internal_router = APIRouter(tags=["Internal"])


class HealthResponse(BaseModel):
    status: str
    db: bool
    sqs: bool | None = None
    s3: bool | None = None
    uptime_seconds: int
    errors: list[str] | None = None


@internal_router.get("/health", response_model=HealthResponse)
async def health_check():
    status = "ok"
    db_healthy = False
    sqs_healthy = None
    s3_healthy = None
    errors: list[str] = []

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_healthy = True
    except Exception as e:
        db_healthy = False
        errors.append(f"db: {e}")
        status = "degraded"

    if SQS_QUEUE_URL:
        try:
            sqs = boto3.client(
                "sqs",
                region_name=AWS_REGION,
                endpoint_url=AWS_ENDPOINT_URL or None,
            )
            sqs.get_queue_attributes(QueueUrl=SQS_QUEUE_URL, AttributeNames=["All"])
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
            s3 = boto3.client(
                "s3",
                region_name=AWS_REGION,
                endpoint_url=AWS_ENDPOINT_URL or None,
            )
            s3.head_bucket(Bucket=S3_BUCKET_NAME)
            s3_healthy = True
        except Exception as e:
            s3_healthy = False
            errors.append(f"s3: {e}")
            if status == "ok":
                status = "degraded"
    else:
        s3_healthy = None

    uptime_seconds = int(time.time() - START_TIME)

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


@app.post("/auth/login")
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


app.include_router(internal_router)
app.include_router(reception.router, prefix="/api", tags=["Receptionist"])
app.include_router(admin.router, prefix="/api", tags=["Admin"])
app.include_router(nurse.router, prefix="/api", tags=["Nurse"])
app.include_router(doctor.router, prefix="/api", tags=["Doctor"])
app.include_router(simulator_router, prefix="/api", tags=["Simulator"])


@app.get("/api/notifications")
def get_notifications(role: str, db: Session = Depends(get_db)):
    return notif_service.get_notifications_for_role(db, role)


@app.put("/api/notifications/{notification_id}/read")
def read_notification(notification_id: str, db: Session = Depends(get_db)):
    notif = notif_service.mark_notification_read(db, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Marked as read"}
