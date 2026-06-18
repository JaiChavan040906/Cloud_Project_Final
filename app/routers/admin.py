from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import role_required
from app.database import get_db
from app.models import Alert, Event, Patient, Review, User
from app.routers import apply_search, apply_sort, build_paginated_response
from app.schemas import AdminSummaryResponse, PatientIdResponse

# All endpoints require admin role only
router = APIRouter(dependencies=[Depends(role_required("admin"))])


# ─── Hospital Summary ───────────────────────────────────────────────────────
# Returns aggregate counts used by the admin dashboard — total patients,
# pending admissions, admitted count, critical alerts, pending reviews.


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


# ─── Pending Admissions ─────────────────────────────────────────────────────


@router.get("/admin/admissions")
def list_admissions(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by patient ID, name, or department"),
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("admin")),
):
    query = db.query(Patient).filter(Patient.status == "Admission Requested")
    if status:
        query = query.filter(Patient.status == status)
    query = apply_search(query, search, [Patient.patient_id, Patient.name, Patient.department])
    query = apply_sort(
        query,
        sort_by,
        sort_order,
        {
            "patient_id": Patient.patient_id,
            "name": Patient.name,
            "department": Patient.department,
            "status": Patient.status,
        },
        [Patient.name.asc(), Patient.patient_id.asc()],
    )
    return build_paginated_response(query, page, limit)


# ─── Approve Admission ──────────────────────────────────────────────────────
# Transitions a patient from "Admission Requested" to "Admitted".
# Validates that the patient exists and is actually requesting admission.
# Emits an AdmissionApproved event.


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


# ─── Critical & Active Alerts ───────────────────────────────────────────────


@router.get("/admin/critical")
def critical_patients(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by patient ID or message"),
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("admin")),
):
    query = db.query(Alert).filter(Alert.severity == "Critical")
    if status:
        query = query.filter(Alert.status == status)
    else:
        query = query.filter(Alert.status == "Active")
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


@router.get("/admin/alerts")
def all_alerts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by patient ID, severity, or message"),
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    db: Session = Depends(get_db),
    user: User = Depends(role_required("admin")),
):
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status)
    else:
        query = query.filter(Alert.status == "Active")
    query = apply_search(query, search, [Alert.patient_id, Alert.message, Alert.severity])
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
