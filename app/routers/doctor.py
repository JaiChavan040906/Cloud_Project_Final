from typing import cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import role_required
from app.database import get_db
from app.models import Alert, Event, Medication, Patient, Review, User
from app.routers import apply_pagination, apply_search, pagination_params
from app.schemas import MedicationIdResponse, PatientIdResponse, PrescriptionCreate, ReviewCreate, ReviewIdResponse

# All endpoints require doctor or admin role
router = APIRouter(dependencies=[Depends(role_required("doctor", "admin"))])


# ─── Review Queue ───────────────────────────────────────────────────────────
# Returns all reviews with status "Pending" awaiting doctor action.


@router.get("/reviews/queue")
def review_queue(
    status: str | None = None,
    search: str | None = None,
    pagination: tuple[int, int] = Depends(pagination_params),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("doctor", "admin")),
):
    page, limit = pagination
    query = db.query(Review)
    if status:
        query = query.filter(Review.review_status == status)
    else:
        query = query.filter(Review.review_status == "Pending")
    query = apply_search(query, search, [Review.review_id, Review.patient_id, Review.doctor_id, Review.review_note])
    query = query.order_by(Review.review_id.asc())
    return apply_pagination(query, page, limit).all()


# ─── Critical Patients ──────────────────────────────────────────────────────
# Returns all active alerts with Critical severity.


@router.get("/patients/critical")
def critical_patients(
    status: str | None = None,
    search: str | None = None,
    pagination: tuple[int, int] = Depends(pagination_params),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("doctor", "admin")),
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


# ─── Patient History ────────────────────────────────────────────────────────
# Returns full patient record plus all related events, reviews, and medications.


@router.get("/patients/{patient_id}/history")
def patient_history(
    patient_id: str, db: Session = Depends(get_db), user: User = Depends(role_required("doctor", "admin"))
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    events = db.query(Event).filter(Event.patient_id == patient_id).order_by(Event.timestamp).all()
    reviews = db.query(Review).filter(Review.patient_id == patient_id).all()
    medications = db.query(Medication).filter(Medication.patient_id == patient_id).all()
    return {"patient": patient, "events": events, "reviews": reviews, "medications": medications}


# ─── Prescribe Medication ───────────────────────────────────────────────────
# Validates patient exists, checks for duplicate medication_id, then creates
# a Medication record with status "Prescribed". Emits MedicationPrescribed event.


@router.post("/prescriptions", response_model=MedicationIdResponse)
def prescribe_medicine(
    data: PrescriptionCreate, db: Session = Depends(get_db), user: User = Depends(role_required("doctor", "admin"))
):
    patient = db.query(Patient).filter(Patient.patient_id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    existing = db.query(Medication).filter(Medication.medication_id == data.medication_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Medication with this ID already exists")
    med = Medication(**data.model_dump())
    db.add(med)
    event = Event(
        event_id=f"EVT-{data.medication_id}-PRES",
        event_type="MedicationPrescribed",
        patient_id=data.patient_id,
        description=f"{data.medicine_name} prescribed",
    )
    db.add(event)
    db.commit()
    return {"message": "Medicine prescribed", "medication_id": data.medication_id}


# ─── Submit Review ──────────────────────────────────────────────────────────
# Validates patient exists, checks for duplicate review_id, then creates a
# review record. Emits PatientReviewed event.


@router.post("/reviews", response_model=ReviewIdResponse)
def submit_review(
    data: ReviewCreate, db: Session = Depends(get_db), user: User = Depends(role_required("doctor", "admin"))
):
    patient = db.query(Patient).filter(Patient.patient_id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    existing = db.query(Review).filter(Review.review_id == data.review_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Review with this ID already exists")
    review = Review(**data.model_dump())
    db.add(review)
    event = Event(
        event_id=f"EVT-{data.review_id}-REV",
        event_type="PatientReviewed",
        patient_id=data.patient_id,
        description="Doctor reviewed patient",
    )
    db.add(event)
    db.commit()
    return {"message": "Review submitted", "review_id": data.review_id}


# ─── Approve Discharge ──────────────────────────────────────────────────────
# Validates patient exists and is admitted. Transitions to "Discharged".
# Emits DischargeApproved event.


@router.put("/discharge/{patient_id}/approve", response_model=PatientIdResponse)
def approve_discharge(
    patient_id: str, db: Session = Depends(get_db), user: User = Depends(role_required("doctor", "admin"))
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if patient.status != "Admitted":
        raise HTTPException(status_code=400, detail="Patient must be admitted before discharge")
    patient.status = cast(str, "Discharged")
    event = Event(
        event_id=f"EVT-{patient_id}-DCH",
        event_type="DischargeApproved",
        patient_id=patient_id,
        description="Discharge approved",
    )
    db.add(event)
    db.commit()
    return {"message": "Discharge approved", "patient_id": patient_id}
