import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(10), nullable=False)
    department = Column(String(50), default="General")
    ward = Column(String(50), default="")
    assigned_doctor = Column(String(100), default="")
    assigned_nurse = Column(String(100), default="")
    status = Column(String(20), default="Registered")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(String(20), unique=True, nullable=False)
    patient_id = Column(String(20), nullable=False)
    date = Column(String(20), nullable=False)
    time = Column(String(20), nullable=False)
    status = Column(String(20), default="Scheduled")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(20), unique=True, nullable=False)
    event_type = Column(String(50), nullable=False)
    patient_id = Column(String(20), nullable=False)
    description = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(20), default="Pending")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(20), unique=True, nullable=False)
    patient_id = Column(String(20), nullable=False)
    severity = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(20), default="Active")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(String(20), unique=True, nullable=False)
    patient_id = Column(String(20), nullable=False)
    doctor_id = Column(String(20), nullable=False)
    review_note = Column(Text, default="")
    review_status = Column(String(20), default="Pending")


class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    medication_id = Column(String(20), unique=True, nullable=False)
    patient_id = Column(String(20), nullable=False)
    medicine_name = Column(String(100), nullable=False)
    prescribed_by = Column(String(100), nullable=False)
    status = Column(String(20), default="Prescribed")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String(20), unique=True, nullable=False)
    recipient_role = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), default="Unread")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
