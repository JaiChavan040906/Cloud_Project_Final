from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import role_required
from app.models import Review, Patient, Alert, Medication, Event, User
from app.schemas import PrescriptionCreate, ReviewCreate

router = APIRouter(dependencies=[Depends(role_required("doctor", "admin"))])


@router.get("/reviews/queue")
def review_queue(db: Session = Depends(get_db), user: User = Depends(role_required("doctor", "admin"))):
    return db.query(Review).filter(Review.review_status == "Pending").all()


@router.get("/patients/critical")
def critical_patients(db: Session = Depends(get_db), user: User = Depends(role_required("doctor", "admin"))):
    return db.query(Alert).filter(Alert.severity == "Critical", Alert.status == "Active").all()


@router.get("/patients/{patient_id}/history")
def patient_history(patient_id: str, db: Session = Depends(get_db), user: User = Depends(role_required("doctor", "admin"))):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    events = db.query(Event).filter(Event.patient_id == patient_id).order_by(Event.timestamp).all()
    reviews = db.query(Review).filter(Review.patient_id == patient_id).all()
    medications = db.query(Medication).filter(Medication.patient_id == patient_id).all()
    return {"patient": patient, "events": events, "reviews": reviews, "medications": medications}


@router.post("/prescriptions")
def prescribe_medicine(data: PrescriptionCreate, db: Session = Depends(get_db), user: User = Depends(role_required("doctor", "admin"))):
    med = Medication(**data.model_dump())
    db.add(med)
    event = Event(event_id=f"EVT-{data.medication_id}-PRES", event_type="MedicationPrescribed", patient_id=data.patient_id, description=f"{data.medicine_name} prescribed")
    db.add(event)
    db.commit()
    return {"message": "Medicine prescribed", "medication_id": data.medication_id}


@router.post("/reviews")
def submit_review(data: ReviewCreate, db: Session = Depends(get_db), user: User = Depends(role_required("doctor", "admin"))):
    review = Review(**data.model_dump())
    db.add(review)
    event = Event(event_id=f"EVT-{data.review_id}-REV", event_type="PatientReviewed", patient_id=data.patient_id, description="Doctor reviewed patient")
    db.add(event)
    db.commit()
    return {"message": "Review submitted", "review_id": data.review_id}


@router.put("/discharge/{patient_id}/approve")
def approve_discharge(patient_id: str, db: Session = Depends(get_db), user: User = Depends(role_required("doctor", "admin"))):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.status = "Discharged"
    event = Event(event_id=f"EVT-{patient_id}-DCH", event_type="DischargeApproved", patient_id=patient_id, description="Discharge approved")
    db.add(event)
    db.commit()
    return {"message": "Discharge approved", "patient_id": patient_id}
