export type UserRole = "admin" | "doctor" | "nurse" | "reception"

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  role: UserRole
  username: string
}

export interface Patient {
  id: number
  patient_id: string
  name: string
  age: number
  gender: string
  department: string
  ward: string
  assigned_doctor: string
  assigned_nurse: string
  status: string
}

export interface Appointment {
  id: number
  appointment_id: string
  patient_id: string
  date: string
  time: string
  status: string
}

export interface Event {
  id: number
  event_id: string
  event_type: string
  patient_id: string
  description: string
  timestamp: string
  status: string
}

export interface Alert {
  id: number
  alert_id: string
  patient_id: string
  severity: string
  message: string
  created_at: string
  status: string
}

export interface Review {
  id: number
  review_id: string
  patient_id: string
  doctor_id: string
  review_note: string
  review_status: string
}

export interface Medication {
  id: number
  medication_id: string
  patient_id: string
  medicine_name: string
  prescribed_by: string
  status: string
}

export interface Notification {
  id: number
  notification_id: string
  recipient_role: string
  message: string
  status: string
  created_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
}

export interface PatientHistory {
  patient: Patient
  events: Event[]
  reviews: Review[]
  medications: Medication[]
}

export interface AdminSummary {
  total_patients: number
  admissions_pending: number
  admitted: number
  critical_patients: number
  pending_reviews: number
  active_alerts: number
}

export interface VitalsRecord {
  patient_id: string
  heart_rate: number
  blood_pressure_systolic: number
  blood_pressure_diastolic: number
  oxygen_level: number
  temperature: number
  blood_sugar: number
}

export interface VitalsResponse {
  severity: string
  reasons: string[]
}

export interface SimulatorState {
  current_step: number
  total_events: number
}

export interface SimulatorNext {
  step: {
    step: number
    event_type: string
    patient_id: string
    description: string
  }
  recipients: string[]
}

export interface AuthUser {
  username: string
  role: UserRole
  token: string
}
