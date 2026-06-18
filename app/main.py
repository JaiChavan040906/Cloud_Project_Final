from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.auth import create_access_token, verify_password
from app.database import Base, engine, get_db
from app.models import User
from app.routers import admin, doctor, nurse, reception
from app.schemas import LoginRequest
from app.services import notifications as notif_service
from app.simulator import router as simulator_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hospital Event Simulation", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login")
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


@app.get("/api/notifications")
def get_notifications(role: str, db: Session = Depends(get_db)):
    return notif_service.get_notifications_for_role(db, role)


@app.put("/api/notifications/{notification_id}/read")
def read_notification(notification_id: str, db: Session = Depends(get_db)):
    notif = notif_service.mark_notification_read(db, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Marked as read"}
