from pydantic import BaseModel, field_validator

# ─── Auth ───────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str


# ─── Receptionist Request Models ────────────────────────────────────────────


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


# ─── Vitals Request with Range Validation ───────────────────────────────────
# All vitals fields have field_validator decorators that reject out-of-range
# values before the request reaches the router handler.


class VitalsRecord(BaseModel):
    patient_id: str
    heart_rate: int
    blood_pressure_systolic: int
    blood_pressure_diastolic: int
    oxygen_level: float
    temperature: float
    blood_sugar: float

    @field_validator("heart_rate")
    @classmethod
    def validate_heart_rate(cls, v: int) -> int:
        if v < 0 or v > 300:
            raise ValueError("Heart rate must be between 0 and 300 bpm")
        return v

    @field_validator("blood_pressure_systolic")
    @classmethod
    def validate_bp_systolic(cls, v: int) -> int:
        if v < 0 or v > 300:
            raise ValueError("Systolic BP must be between 0 and 300")
        return v

    @field_validator("blood_pressure_diastolic")
    @classmethod
    def validate_bp_diastolic(cls, v: int) -> int:
        if v < 0 or v > 200:
            raise ValueError("Diastolic BP must be between 0 and 200")
        return v

    @field_validator("oxygen_level")
    @classmethod
    def validate_spo2(cls, v: float) -> float:
        if v < 0 or v > 100:
            raise ValueError("Oxygen level must be between 0 and 100")
        return v

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if v < 90 or v > 110:
            raise ValueError("Temperature must be between 90 and 110 °F")
        return v

    @field_validator("blood_sugar")
    @classmethod
    def validate_blood_sugar(cls, v: float) -> float:
        if v < 0 or v > 1000:
            raise ValueError("Blood sugar must be between 0 and 1000 mg/dL")
        return v


# ─── Doctor Request Models ──────────────────────────────────────────────────


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


# ─── Simulator ──────────────────────────────────────────────────────────────


class SimulatorEvent(BaseModel):
    step: int
    event_type: str
    patient_id: str
    description: str


# ─── Standard Response Models ───────────────────────────────────────────────
# Every endpoint uses one of these as its response_model so Swagger/OpenAPI
# documents the exact return shape and clients know what to expect.


class MessageResponse(BaseModel):
    message: str


class PatientIdResponse(BaseModel):
    message: str
    patient_id: str


class AppointmentIdResponse(BaseModel):
    message: str
    appointment_id: str


class MedicationIdResponse(BaseModel):
    message: str
    medication_id: str


class ReviewIdResponse(BaseModel):
    message: str
    review_id: str


class VitalsResponse(BaseModel):
    severity: str
    reasons: list[str]


class HealthResponse(BaseModel):
    status: str


class AdminSummaryResponse(BaseModel):
    total_patients: int
    admissions_pending: int
    admitted: int
    critical_patients: int
    pending_reviews: int
    active_alerts: int
