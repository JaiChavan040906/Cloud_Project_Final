from typing import cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import role_required
from app.database import get_db
from app.models import Alert, Event, Patient, Review, User
from app.schemas import AdminSummaryResponse, PatientIdResponse

router = APIRouter(dependencies=[Depends(role_required("admin"))])


@router.get("/admin/summary", response_model=AdminSummaryResponse)
def admin_summary(db: Session = Depends(get_db), user: User = Depends(role_required("admin"))):
    total_patients = db.query(Patient).count()
    admissions = db.query(Patient).filter(Patient.status == "Admission Requested").count()
    admitted = db.query(Patient).filter(Patient.status == "Admitted").count()
    critical = db.query(Alert).filter(Alert.severity == "Critical", Alert.status == "Active").count()
    pending_reviews = db.query(Review).filter(Review.review_status == "Pending").count()
    active_alerts = db.query(Alert).filter(Alert.status == "Active").count()
    return {
        "total_patients": total_patients,
        "admissions_pending": admissions,
        "admitted": admitted,
        "critical_patients": critical,
        "pending_reviews": pending_reviews,
        "active_alerts": active_alerts,
    }


@router.get("/admin/admissions")
def list_admissions(db: Session = Depends(get_db), user: User = Depends(role_required("admin"))):
    return db.query(Patient).filter(Patient.status == "Admission Requested").all()


@router.put("/admissions/{patient_id}/approve", response_model=PatientIdResponse)
def approve_admission(patient_id: str, db: Session = Depends(get_db), user: User = Depends(role_required("admin"))):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if patient.status != "Admission Requested":
        raise HTTPException(status_code=400, detail="Patient has not requested admission")
    patient.status = cast(str, "Admitted")
    event = Event(
        event_id=f"EVT-{patient_id}-ADM",
        event_type="AdmissionApproved",
        patient_id=patient_id,
        description="Admission approved",
    )
    db.add(event)
    db.commit()
    return {"message": "Admission approved", "patient_id": patient_id}


@router.get("/admin/critical")
def critical_patients(db: Session = Depends(get_db), user: User = Depends(role_required("admin"))):
    return db.query(Alert).filter(Alert.severity == "Critical", Alert.status == "Active").all()


@router.get("/admin/alerts")
def all_alerts(db: Session = Depends(get_db), user: User = Depends(role_required("admin"))):
    return db.query(Alert).filter(Alert.status == "Active").all()
