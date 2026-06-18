from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str


class PatientRegister(BaseModel):
    patient_id: str
    name: str
    age: int
    gender: str
    department: str = "General"
    ward: str = ""


class AppointmentCreate(BaseModel):
    appointment_id: str
    patient_id: str
    date: str
    time: str


class VitalsRecord(BaseModel):
    patient_id: str
    heart_rate: int
    blood_pressure_systolic: int
    blood_pressure_diastolic: int
    oxygen_level: float
    temperature: float
    blood_sugar: float


class PrescriptionCreate(BaseModel):
    medication_id: str
    patient_id: str
    medicine_name: str
    prescribed_by: str


class ReviewCreate(BaseModel):
    review_id: str
    patient_id: str
    doctor_id: str
    review_note: str
    review_status: str = "Completed"


class AdmissionApprove(BaseModel):
    patient_id: str


class SimulatorEvent(BaseModel):
    step: int
    event_type: str
    patient_id: str
    description: str
