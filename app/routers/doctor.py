from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import role_required
from app.database import get_db
from app.models import Alert, Event, Medication, Patient, Review, User
from app.routers import apply_search, apply_sort, build_paginated_response
from app.schemas import (
    MedicationIdResponse,
    PaginatedAlertsResponse,
    PaginatedReviewsResponse,
    PatientHistoryResponse,
    PatientIdResponse,
    PrescriptionCreate,
    ReviewCreate,
    ReviewIdResponse,
)
from app.services.event_bus import build_event_payload, publish_event

router = APIRouter()


@router.get(
    "/reviews/queue",
    response_model=PaginatedReviewsResponse,
    summary="List Pending Reviews",
    description=(
        "Return the doctor review queue with filtering, searching, sorting, and pagination support. "
        "Doctor and Admin users use this endpoint to find patient reviews that still need attention."
    ),
)
def review_queue(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by review, patient, doctor ID, or note"),
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("doctor", "admin")),
):
    query = db.query(Review)
    query = query.filter(Review.review_status == status) if status else query.filter(Review.review_status == "Pending")
    query = apply_search(query, search, [Review.review_id, Review.patient_id, Review.doctor_id, Review.review_note])
    query = apply_sort(
        query,
        sort_by,
        sort_order,
        {
            "review_id": Review.review_id,
            "patient_id": Review.patient_id,
            "doctor_id": Review.doctor_id,
            "review_status": Review.review_status,
        },
        [Review.review_id.asc()],
    )
    return build_paginated_response(query, page, limit)


@router.get(
    "/patients/critical",
    response_model=PaginatedAlertsResponse,
    summary="List Critical Patients",
    description=(
        "Return critical patient alerts for Doctor and Admin users with optional filters, search, sorting, and "
        "pagination. This endpoint highlights patients that may require immediate physician review."
    ),
)
def critical_patients(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by patient ID or message"),
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("doctor", "admin")),
):
    query = db.query(Alert).filter(Alert.severity == "Critical")
    query = query.filter(Alert.status == status) if status else query.filter(Alert.status == "Active")
    query = apply_search(query, search, [Alert.patient_id, Alert.message])
    query = apply_sort(
        query,
        sort_by,
        sort_order,
        {
            "alert_id": Alert.alert_id,
            "patient_id": Alert.patient_id,
            "severity": Alert.severity,
            "status": Alert.status,
            "created_at": Alert.created_at,
        },
        [Alert.created_at.desc(), Alert.alert_id.asc()],
    )
    return build_paginated_response(query, page, limit)


@router.get(
    "/patients/{patient_id}/history",
    response_model=PatientHistoryResponse,
    summary="Get Patient History",
    description=(
        "Return the full patient record along with related events, reviews, and medications. "
        "Doctor and Admin users use this endpoint to review the complete clinical timeline before taking action."
    ),
)
def patient_history(
    patient_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("doctor", "admin")),
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    events = db.query(Event).filter(Event.patient_id == patient_id).order_by(Event.timestamp).all()
    reviews = db.query(Review).filter(Review.patient_id == patient_id).all()
    medications = db.query(Medication).filter(Medication.patient_id == patient_id).all()
    return {"patient": patient, "events": events, "reviews": reviews, "medications": medications}


@router.post(
    "/prescriptions",
    response_model=MedicationIdResponse,
    summary="Prescribe Medication",
    description=(
        "Create a medication record for an existing patient. This endpoint is restricted to Doctor and Admin roles "
        "and emits a MedicationPrescribed event when the prescription is successfully recorded."
    ),
)
def prescribe_medicine(
    data: PrescriptionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("doctor", "admin")),
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

    publish_event(
        db,
        build_event_payload(
            event,
            actor_role=cast(str, user.role),
            source="api",
            metadata={"medication_id": data.medication_id, "medicine_name": data.medicine_name},
        ),
    )

    return {"message": "Medicine prescribed", "medication_id": data.medication_id}


@router.post(
    "/reviews",
    response_model=ReviewIdResponse,
    summary="Submit Patient Review",
    description=(
        "Create a patient review note and persist it in the review queue. This endpoint is available to Doctor and "
        "Admin roles and emits a PatientReviewed event for the workflow audit trail."
    ),
)
def submit_review(
    data: ReviewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("doctor", "admin")),
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

    publish_event(
        db,
        build_event_payload(
            event,
            actor_role=cast(str, user.role),
            source="api",
            metadata={"review_id": data.review_id, "review_status": data.review_status},
        ),
    )

    return {"message": "Review submitted", "review_id": data.review_id}


@router.put(
    "/discharge/{patient_id}/approve",
    response_model=PatientIdResponse,
    summary="Approve Discharge",
    description=(
        "Approve discharge for an admitted patient and transition the patient into the discharged state. "
        "This endpoint is restricted to Doctor and Admin roles and emits a DischargeApproved event."
    ),
)
def approve_discharge(
    patient_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("doctor", "admin")),
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

    publish_event(
        db,
        build_event_payload(
            event,
            actor_role=cast(str, user.role),
            source="api",
            metadata={"patient_status": patient.status},
        ),
    )

    return {"message": "Discharge approved", "patient_id": patient_id}
