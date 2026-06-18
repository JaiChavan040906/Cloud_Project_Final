from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import role_required
from app.database import get_db
from app.models import Alert, Event, Patient, Review, User
from app.routers import apply_pagination, apply_search, pagination_params

router = APIRouter(dependencies=[Depends(role_required("admin"))])


@router.get("/admin/summary")
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
def list_admissions(
    status: str | None = None,
    search: str | None = None,
    pagination: tuple[int, int] = Depends(pagination_params),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("admin")),
):
    page, limit = pagination
    query = db.query(Patient).filter(Patient.status == "Admission Requested")
    if status:
        query = query.filter(Patient.status == status)
    query = apply_search(query, search, [Patient.patient_id, Patient.name, Patient.department])
    query = query.order_by(Patient.name.asc(), Patient.patient_id.asc())
    return apply_pagination(query, page, limit).all()


@router.put("/admissions/{patient_id}/approve")
def approve_admission(patient_id: str, db: Session = Depends(get_db), user: User = Depends(role_required("admin"))):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.status = "Admitted"
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
def critical_patients(
    status: str | None = None,
    search: str | None = None,
    pagination: tuple[int, int] = Depends(pagination_params),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("admin")),
):
    page, limit = pagination
    query = db.query(Alert).filter(Alert.severity == "Critical")
    if status:
        query = query.filter(Alert.status == status)
    else:
        query = query.filter(Alert.status == "Active")
    query = apply_search(query, search, [Alert.patient_id, Alert.message])
    query = query.order_by(Alert.created_at.desc(), Alert.alert_id.asc())
    return apply_pagination(query, page, limit).all()


@router.get("/admin/alerts")
def all_alerts(
    status: str | None = None,
    search: str | None = None,
    pagination: tuple[int, int] = Depends(pagination_params),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("admin")),
):
    page, limit = pagination
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status)
    else:
        query = query.filter(Alert.status == "Active")
    query = apply_search(query, search, [Alert.patient_id, Alert.message, Alert.severity])
    query = query.order_by(Alert.created_at.desc(), Alert.alert_id.asc())
    return apply_pagination(query, page, limit).all()
