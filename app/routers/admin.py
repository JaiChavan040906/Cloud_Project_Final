from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import role_required
from app.database import get_db
from app.engine.routing import get_recipients
from app.models import Alert, Event, Patient, Review, User
from app.routers import apply_search, apply_sort, build_paginated_response
from app.schemas import AdminSummaryResponse, PaginatedAlertsResponse, PaginatedPatientsResponse, PatientIdResponse
from app.services.notifications import create_notification
from app.services.sqs import send_to_sqs

router = APIRouter()


@router.get(
    "/admin/summary",
    response_model=AdminSummaryResponse,
    summary="Get Hospital Summary",
    description=(
        "Return aggregated hospital metrics for the Admin dashboard, including patient totals, admissions, active "
        "alerts, and pending reviews. This endpoint is restricted to the Admin role."
    ),
)
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


@router.get(
    "/admin/admissions",
    response_model=PaginatedPatientsResponse,
    summary="List Pending Admissions",
    description=(
        "Return a paginated list of admission requests for the Admin role. Results can be filtered, searched, and "
        "sorted to help hospital administrators review and manage incoming admissions."
    ),
)
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


@router.put(
    "/admissions/{patient_id}/approve",
    response_model=PatientIdResponse,
    summary="Approve Admission",
    description=(
        "Approve a patient admission request and transition the patient into the admitted state. This endpoint is "
        "restricted to Admin users and emits an AdmissionApproved event for downstream dashboards."
    ),
)
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

    event_data = {
        "step": 0,
        "event_type": "AdmissionApproved",
        "patient_id": patient_id,
        "description": f"Admission approved for patient {patient_id}",
    }
    for role in get_recipients("AdmissionApproved"):
        create_notification(db, role, f"AdmissionApproved: {patient_id}")
    send_to_sqs(event_data)

    return {"message": "Admission approved", "patient_id": patient_id}


@router.get(
    "/admin/critical",
    response_model=PaginatedAlertsResponse,
    summary="List Critical Alerts",
    description=(
        "Return critical patient alerts for the Admin role with optional filtering, searching, sorting, and "
        "pagination. This helps administrators monitor severe events that may require escalation."
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
    user: User = Depends(role_required("admin")),
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
    "/admin/alerts",
    response_model=PaginatedAlertsResponse,
    summary="List All Active Alerts",
    description=(
        "Return the alert feed for administrators with optional filtering, searching, sorting, and pagination. "
        "This endpoint surfaces active issues created by the vitals risk engine and care workflow."
    ),
)
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
    query = query.filter(Alert.status == status) if status else query.filter(Alert.status == "Active")
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
