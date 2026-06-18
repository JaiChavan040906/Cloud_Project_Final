# Hospital Event Simulation — Backend

## Project Overview

AWS-Based Hospital Event Simulation and Care Coordination System.  
An event-driven hospital operations platform built with FastAPI + SQLite + AWS services.

Roles: **Receptionist**, **Nurse**, **Doctor**, **Admin**.  
Each role has dedicated endpoints and role-based access control via JWT.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (Python 3.11+) |
| Database | SQLite via SQLAlchemy 2.x |
| Auth | JWT (python-jose) + bcrypt |
| Package manager | **uv** (not pip) |
| Linter | Ruff |
| Formatter | Ruff |
| Type checker | mypy (with sqlalchemy plugin) |
| AWS SDK | boto3 (SQS, S3) |
| Docker | multi-stage uv build |

---

## Project Structure

```
app/
├── main.py              # FastAPI app, CORS, auth/login, router includes
├── config.py            # Env-based settings (DB, JWT, AWS)
├── database.py          # SQLAlchemy engine + session
├── models.py            # 8 ORM models
├── schemas.py           # Pydantic request schemas
├── auth.py              # JWT create/verify, role_required guard
├── seed.py              # Insert 4 default users
├── simulator.py         # CSV-based event simulator
├── routers/
│   ├── reception.py     # Receptionist endpoints
│   ├── admin.py         # Admin endpoints
│   ├── nurse.py         # Nurse endpoints
│   └── doctor.py        # Doctor endpoints
├── engine/
│   ├── routing.py       # Event routing (event_type → recipient roles)
│   └── risk.py          # Vitals risk evaluation
└── services/
    ├── notifications.py # Notification CRUD
    ├── sqs.py           # AWS SQS send/receive/delete
    └── s3.py            # AWS S3 upload/download/list
data/
├── hospital_events.csv  # 20 predefined simulation events
lambda/
├── handler.py           # AWS Lambda entry point (self-contained)
deploy/
├── startup.sh           # EC2 startup script
├── iam-lambda-policy.json
├── iam-ec2-policy.json
└── cloudwatch-agent.json
```

---

## Database Models (`app/models.py`)

8 tables — all use SQLAlchemy ORM with `Base = declarative_base()`.

### users
| Column | Type | Notes |
|--------|------|-------|
| id | Integer | PK |
| username | String(50) | unique |
| password | String(255) | bcrypt hash |
| role | String(20) | admin, doctor, nurse, reception |

### patients
| Column | Type | Notes |
|--------|------|-------|
| id | Integer | PK |
| patient_id | String(20) | unique, business key |
| name | String(100) | |
| age | Integer | |
| gender | String(10) | |
| department | String(50) | default "General" |
| ward | String(50) | |
| assigned_doctor | String(100) | |
| assigned_nurse | String(100) | |
| status | String(20) | Registered, Checked In, Admitted, Discharged |

### appointments
| Column | Type | Notes |
|--------|------|-------|
| id | Integer | PK |
| appointment_id | String(20) | unique |
| patient_id | String(20) | |
| date | String | |
| time | String | |
| status | String(20) | default "Scheduled" |

### events
| Column | Type | Notes |
|--------|------|-------|
| id | Integer | PK |
| event_id | String(20) | unique |
| event_type | String(50) | e.g. PatientRegistered |
| patient_id | String(20) | |
| description | Text | |
| timestamp | DateTime | auto UTC |
| status | String(20) | default "Pending" |

### alerts
| Column | Type | Notes |
|--------|------|-------|
| id | Integer | PK |
| alert_id | String(20) | unique |
| patient_id | String(20) | |
| severity | String(20) | Normal, Warning, Critical |
| message | Text | |
| created_at | DateTime | auto UTC |
| status | String(20) | default "Active" |

### reviews
| Column | Type | Notes |
|--------|------|-------|
| id | Integer | PK |
| review_id | String(20) | unique |
| patient_id | String(20) | |
| doctor_id | String(20) | |
| review_note | Text | |
| review_status | String(20) | default "Pending" |

### medications
| Column | Type | Notes |
|--------|------|-------|
| id | Integer | PK |
| medication_id | String(20) | unique |
| patient_id | String(20) | |
| medicine_name | String(100) | |
| prescribed_by | String(100) | |
| status | String(20) | Prescribed, Administered |

### notifications
| Column | Type | Notes |
|--------|------|-------|
| id | Integer | PK |
| notification_id | String(20) | unique |
| recipient_role | String(20) | which role should see this |
| message | Text | |
| status | String(20) | Unread, Read |
| created_at | DateTime | auto UTC |

---

## Auth System (`app/auth.py`)

- **Login:** `POST /auth/login` → returns JWT with `sub` (username) + `role`
- **Guard:** `role_required("admin", "doctor")` returns a FastAPI dependency
- **Password:** bcrypt hash via `bcrypt.hashpw` / `bcrypt.checkpw`
- **Token:** HS256, configurable expiry (default 60 min)

---

## API Endpoints

### Auth
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check |
| POST | `/auth/login` | No | Login, returns JWT |

### Receptionist (role: reception, admin)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/patients/register` | Register new patient |
| POST | `/api/appointments` | Create appointment |
| POST | `/api/patients/{patient_id}/checkin` | Check in patient |
| GET | `/api/admissions` | List admission requests |
| GET | `/api/appointments` | List all appointments |

### Admin (role: admin)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/summary` | Hospital summary counts |
| GET | `/api/admin/admissions` | Pending admissions |
| PUT | `/api/admissions/{patient_id}/approve` | Approve admission |
| GET | `/api/admin/critical` | Critical alerts |
| GET | `/api/admin/alerts` | All active alerts |

### Nurse (role: nurse, admin)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/patients/assigned` | Patients assigned to nurse |
| POST | `/api/vitals` | Record vitals + auto-risk |
| GET | `/api/alerts` | Active alerts |
| GET | `/api/medications/queue` | Prescribed medications |
| PUT | `/api/medications/{medication_id}/administer` | Administer medication |
| PUT | `/api/checkups/{patient_id}/complete` | Complete checkup |

### Doctor (role: doctor, admin)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/reviews/queue` | Pending reviews |
| GET | `/api/patients/critical` | Critical patients |
| GET | `/api/patients/{patient_id}/history` | Full patient history |
| POST | `/api/prescriptions` | Prescribe medication |
| POST | `/api/reviews` | Submit patient review |
| PUT | `/api/discharge/{patient_id}/approve` | Approve discharge |

### Simulator (no auth)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/simulator/state` | Current step / total events |
| POST | `/api/simulator/next` | Process next event |
| POST | `/api/simulator/reset` | Reset simulation |

### Notifications (no auth)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/notifications?role=X` | Get unread notifications by role |
| PUT | `/api/notifications/{id}/read` | Mark notification read |

---

## Event Routing Engine (`app/engine/routing.py`)

Maps event types to recipient roles:

```
PatientRegistered      → reception, admin
AppointmentCreated     → reception, admin
PatientCheckedIn       → reception, nurse
AdmissionRequested     → admin, reception
AdmissionApproved      → reception, nurse, doctor, admin
VitalsRecorded         → nurse, doctor
HighSugarDetected      → nurse, doctor, admin
WarningAlertGenerated  → nurse, doctor
CriticalAlertGenerated → nurse, doctor, admin
MedicationPrescribed   → nurse, doctor
MedicationAdministered → nurse, admin
PatientReviewed        → doctor, admin
CheckupCompleted       → nurse, doctor
DischargeApproved      → reception, nurse, admin
```

---

## Risk Engine (`app/engine/risk.py`)

Pure function `evaluate_vitals(hr, bp_sys, bp_dia, spo2, temp, blood_sugar)`  
Returns `{status: "normal"|"warning"|"critical", reasons: [...], severity_score: int}`.

Thresholds:
- Heart rate: 60–100 bpm
- SpO2: ≥95%
- Temperature: 97.0–100.4°F
- Blood sugar: 70–140 mg/dL
- BP systolic: 90–140
- BP diastolic: 60–90

Status = `critical` if ≥2 issues, `warning` if 1 issue, else `normal`.

---

## Coding Conventions

- **Line length:** 120
- **Quotes:** double quotes
- **Indent:** spaces (4)
- **Imports:** sorted (ruff I rule), stdlib → third-party → local
- **Type hints:** required on all function signatures
- **No `# type: ignore`** unless absolutely necessary and justified

### Run checks before committing:
```bash
npm run check    # format:check + lint + typecheck
```

---

## Available Scripts

```bash
npm run dev            # uvicorn with --reload
npm start              # uvicorn production
npm run format         # ruff format .
npm run format:check   # ruff format --check .
npm run lint           # ruff check .
npm run lint:fix       # ruff check --fix .
npm run typecheck      # mypy app/
npm run typecheck:strict  # mypy --strict app/
npm run check          # format:check + lint + typecheck
npm run seed           # Insert 4 default users
npm run sync           # uv sync
npm run build          # docker compose build
npm run up             # docker compose up -d
npm run down           # docker compose down
```

---

## How to Run

```bash
uv sync                  # Install dependencies
uv run python -m app.seed  # Seed default users
uv run uvicorn app.main:app --reload --port 8000  # Dev server
```

Default users: `admin/admin123`, `doctor/doctor123`, `nurse/nurse123`, `reception/reception123`

---

## Pending Issues

These issues are assigned for implementation in order.  
Branch from `main`, do NOT touch files outside your issue scope.

### Person A

| Branch | Files to Touch | Task |
|--------|---------------|------|
| `feat/validation-error-handling` | `app/schemas.py`, `app/routers/*.py` | Add Pydantic response models to all endpoints. Add consistent 404/400 errors for missing resources. Validate vitals ranges (HR 0-300, SpO2 0-100, etc.) |
| `feat/unit-tests` | `tests/test_risk.py`, `tests/test_routing.py`, `tests/conftest.py`, `tests/__init__.py` | Pytest with SQLite in-memory. Test `evaluate_vitals()` (normal/warning/critical), test `get_recipients()` coverage, test `create_access_token()` + `verify_password()`, test `hash_password()` round-trip |
| `feat/api-docs` | `app/main.py`, `app/routers/*.py`, `app/schemas.py` | Add `summary=` and `description=` to every route. Add `examples` to Pydantic request models. Add `response_model` to every endpoint. Swagger groups should be clean |
| `feat/health-probe` | `app/main.py` | `GET /health` returns `{status, db, sqs, s3, uptime}`. Ping DB with `SELECT 1`. Attempt SQS get-queue-attributes. Attempt S3 head-bucket. Return 503 if DB is down |

### Person B

| Branch | Files to Touch | Task |
|--------|---------------|------|
| `feat/filter-sort-paginate` | `app/routers/*.py` | Add query params: `?status=X&search=Y&page=1&limit=20` to list endpoints. Add `GET /patients` for general patient search. `get_patients` with name/ID/department search. Sort by `created_at` or name |
| `feat/integration-tests` | `tests/test_api.py` | FastAPI `TestClient`. Test login with valid/invalid creds. Test each endpoint returns correct status codes. Test role-based access (reception can't POST to doctor endpoints, etc.). Test missing resource returns 404 |
| `chore/env-config` | `app/config.py`, `.env.example` | Create `.env.example` with every config var + comment. Add `LOG_LEVEL` (default INFO). Verify `python-dotenv` loads `.env` at startup |
| `chore/docker-localstack` | `docker-compose.yml` | Add init container for localstack that creates SQS queue + S3 bucket on startup. Add volume for persistence. Test with `docker compose up` |
