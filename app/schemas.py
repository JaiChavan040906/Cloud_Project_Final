from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(..., examples=["admin"])
    password: str = Field(..., examples=["admin123"])

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "username": "admin",
                    "password": "admin123",
                }
            ]
        }
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str


class PatientRegister(BaseModel):
    patient_id: str = Field(..., examples=["P001"])
    name: str = Field(..., examples=["John Doe"])
    age: int = Field(..., examples=[30])
    gender: str = Field(..., examples=["Male"])
    department: str = Field(default="General", examples=["Cardiology"])
    ward: str = Field(default="", examples=["A1"])

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "patient_id": "P001",
                    "name": "John Doe",
                    "age": 30,
                    "gender": "Male",
                    "department": "Cardiology",
                    "ward": "A1",
                }
            ]
        }
    )


class AppointmentCreate(BaseModel):
    appointment_id: str = Field(..., examples=["APT001"])
    patient_id: str = Field(..., examples=["P001"])
    date: str = Field(..., examples=["2026-06-18"])
    time: str = Field(..., examples=["09:30"])

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "appointment_id": "APT001",
                    "patient_id": "P001",
                    "date": "2026-06-18",
                    "time": "09:30",
                }
            ]
        }
    )


class VitalsRecord(BaseModel):
    patient_id: str = Field(..., examples=["P001"])
    heart_rate: int = Field(..., examples=[75])
    blood_pressure_systolic: int = Field(..., examples=[120])
    blood_pressure_diastolic: int = Field(..., examples=[80])
    oxygen_level: float = Field(..., examples=[98.0])
    temperature: float = Field(..., examples=[98.6])
    blood_sugar: float = Field(..., examples=[100.0])

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "patient_id": "P001",
                    "heart_rate": 75,
                    "blood_pressure_systolic": 120,
                    "blood_pressure_diastolic": 80,
                    "oxygen_level": 98.0,
                    "temperature": 98.6,
                    "blood_sugar": 100.0,
                }
            ]
        }
    )

    @field_validator("heart_rate")
    @classmethod
    def validate_heart_rate(cls, value: int) -> int:
        if value < 0 or value > 300:
            raise ValueError("Heart rate must be between 0 and 300 bpm")
        return value

    @field_validator("blood_pressure_systolic")
    @classmethod
    def validate_bp_systolic(cls, value: int) -> int:
        if value < 0 or value > 300:
            raise ValueError("Systolic BP must be between 0 and 300")
        return value

    @field_validator("blood_pressure_diastolic")
    @classmethod
    def validate_bp_diastolic(cls, value: int) -> int:
        if value < 0 or value > 200:
            raise ValueError("Diastolic BP must be between 0 and 200")
        return value

    @field_validator("oxygen_level")
    @classmethod
    def validate_spo2(cls, value: float) -> float:
        if value < 0 or value > 100:
            raise ValueError("Oxygen level must be between 0 and 100")
        return value

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, value: float) -> float:
        if value < 90 or value > 110:
            raise ValueError("Temperature must be between 90 and 110 F")
        return value

    @field_validator("blood_sugar")
    @classmethod
    def validate_blood_sugar(cls, value: float) -> float:
        if value < 0 or value > 1000:
            raise ValueError("Blood sugar must be between 0 and 1000 mg/dL")
        return value


class PrescriptionCreate(BaseModel):
    medication_id: str = Field(..., examples=["MED001"])
    patient_id: str = Field(..., examples=["P001"])
    medicine_name: str = Field(..., examples=["Metformin"])
    prescribed_by: str = Field(..., examples=["doctor"])

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "medication_id": "MED001",
                    "patient_id": "P001",
                    "medicine_name": "Metformin",
                    "prescribed_by": "doctor",
                }
            ]
        }
    )


class ReviewCreate(BaseModel):
    review_id: str = Field(..., examples=["REV001"])
    patient_id: str = Field(..., examples=["P001"])
    doctor_id: str = Field(..., examples=["doctor"])
    review_note: str = Field(..., examples=["Patient is stable and can continue observation."])
    review_status: str = Field(default="Completed", examples=["Completed"])

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "review_id": "REV001",
                    "patient_id": "P001",
                    "doctor_id": "doctor",
                    "review_note": "Patient is stable and can continue observation.",
                    "review_status": "Completed",
                }
            ]
        }
    )


class AdmissionApprove(BaseModel):
    patient_id: str = Field(..., examples=["P001"])


class SimulatorEvent(BaseModel):
    step: int = Field(..., examples=[1])
    event_type: str = Field(..., examples=["PatientRegistered"])
    patient_id: str = Field(..., examples=["P001"])
    description: str = Field(..., examples=["Patient John Doe registered"])


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
    db: bool
    sqs: bool | None = None
    s3: bool | None = None
    uptime_seconds: int
    errors: list[str] | None = None


class AdminSummaryResponse(BaseModel):
    total_patients: int
    admissions_pending: int
    admitted: int
    critical_patients: int
    pending_reviews: int
    active_alerts: int


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: str
    name: str
    age: int
    gender: str
    department: str
    ward: str
    assigned_doctor: str
    assigned_nurse: str
    status: str


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appointment_id: str
    patient_id: str
    date: str
    time: str
    status: str


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    event_type: str
    patient_id: str
    description: str
    timestamp: datetime
    status: str


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_id: str
    patient_id: str
    severity: str
    message: str
    created_at: datetime
    status: str


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    review_id: str
    patient_id: str
    doctor_id: str
    review_note: str
    review_status: str


class MedicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    medication_id: str
    patient_id: str
    medicine_name: str
    prescribed_by: str
    status: str


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    notification_id: str
    recipient_role: str
    message: str
    status: str
    created_at: datetime


class PaginatedPatientsResponse(BaseModel):
    items: list[PatientResponse]
    total: int
    page: int
    limit: int


class PaginatedAppointmentsResponse(BaseModel):
    items: list[AppointmentResponse]
    total: int
    page: int
    limit: int


class PaginatedAlertsResponse(BaseModel):
    items: list[AlertResponse]
    total: int
    page: int
    limit: int


class PaginatedMedicationsResponse(BaseModel):
    items: list[MedicationResponse]
    total: int
    page: int
    limit: int


class PaginatedReviewsResponse(BaseModel):
    items: list[ReviewResponse]
    total: int
    page: int
    limit: int


class PatientHistoryResponse(BaseModel):
    patient: PatientResponse
    events: list[EventResponse]
    reviews: list[ReviewResponse]
    medications: list[MedicationResponse]


class SimulatorStateResponse(BaseModel):
    current_step: int
    total_events: int


class SimulatorNextResponse(BaseModel):
    step: SimulatorEvent
    recipients: list[str]
