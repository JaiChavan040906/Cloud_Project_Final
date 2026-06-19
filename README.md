# Hospital Event Simulation

AWS-Based Hospital Event Simulation and Care Coordination System.  
An event-driven hospital operations platform built with FastAPI + React.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.11+) |
| Database | SQLite (default local) / PostgreSQL (Docker) via SQLAlchemy 2.x |
| Auth | JWT (python-jose) + bcrypt |
| Frontend | React 19 + TypeScript + Vite |
| Styling | Tailwind CSS v4 + shadcn/ui |
| Package manager | **uv** (backend), **npm** (frontend) |
| AWS | EC2, SQS, Lambda, S3, CloudWatch |
| AWS SDK | boto3 (SQS, S3) |

## How to Run (Local Development)

### Prerequisites

- **Python 3.11+** — [install](https://www.python.org/downloads/)
- **uv** — Python package manager ([install guide](https://docs.astral.sh/uv/#getting-started))
- **Node.js 18+** — [install](https://nodejs.org/)
- **Docker Desktop** (optional, for AWS-local stack with LocalStack)

---

### 1. Clone the Repository

```bash
git clone <repo-url>
cd Cloud_Project_Final
```

### 2. Backend Setup (uv)

Install Python dependencies and create a virtual environment:

```bash
uv sync
```

This reads `pyproject.toml` and `uv.lock` to install all backend dependencies into a `.venv` folder.

> **Note:** If this is your first time using `uv`, running `uv sync` will also auto-create the virtual environment.

### 3. Frontend Setup (npm)

```bash
cd frontend
npm install
cd ..
```

### 4. Configure Environment (Optional)

The backend works out of the box with sensible defaults (SQLite, no AWS).  
To customize, copy the example env file and edit as needed:

```bash
cp .env.example .env
```

| Variable | Default | Notes |
|----------|---------|-------|
| `DATABASE_URL` | `sqlite:///./hospital.db` | Use SQLite for local dev; PostgreSQL for Docker |
| `JWT_SECRET` | `Strong-Secret-key` | Change in production |
| `SQS_QUEUE_URL` | *(empty)* | Leave empty to skip SQS in local dev |
| `AWS_ENDPOINT_URL` | *(empty)* | Set to `http://localhost:4566` when using LocalStack |

### 5. Fix Frontend Proxy (Important for Local Dev)

The frontend's `vite.config.ts` proxies API requests to the backend. For local development, the proxy must point to `localhost:8000`:

```ts
// frontend/vite.config.ts
server: {
  proxy: {
    "/api": "http://localhost:8000",
    "/auth": "http://localhost:8000",
    "/health": "http://localhost:8000",
  },
},
```

> The file currently points to a remote AWS EC2 instance. Change it to `localhost:8000` for local development.

### 6. Seed the Database (First Time Only)

```bash
uv run python -m app.seed
```

This creates four default users (see below).

### 7. Start the Application

Terminal 1 — Backend (port 8000):

```bash
uv run uvicorn app.main:app --reload --port 8000
# or: npm run dev
```

Terminal 2 — Frontend (port 5173):

```bash
cd frontend && npm run dev
```

### 8. Open the App

Navigate to **http://localhost:5173** — you'll see the role selection login page.

---

## Run with Docker (Includes LocalStack for AWS Services)

If you want to test AWS integrations (SQS, S3) locally, use Docker Compose which starts FastAPI, PostgreSQL, and LocalStack:

```bash
docker compose up -d
```

This provisions:
- **PostgreSQL** on port 5432
- **LocalStack** on port 4566 (with SQS queue + S3 bucket auto-created)
- **FastAPI backend** on port 8000 (connected to PostgreSQL + LocalStack)

Seed the database inside the container:

```bash
docker compose exec backend uv run python -m app.seed
```

Then start the frontend separately (vite proxy should point to `http://localhost:8000`):

```bash
cd frontend && npm run dev
```

---

## Default Users

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Doctor | `doctor` | `doctor123` |
| Nurse | `nurse` | `nurse123` |
| Receptionist | `reception` | `reception123` |

## Event Simulator

The simulator steps through 20 predefined CSV events to populate the system with demo data:

1. Navigate to **http://localhost:5173/simulator** or click **Simulator** in the sidebar
2. Click **[Next Event]** to process events one at a time
3. Click **[Reset]** to start over

Each event creates real database records (patients, appointments, alerts, medications, reviews) and publishes a canonical event payload. Lambda handles stakeholder notification fan-out in AWS mode, while a local fallback keeps the app usable without AWS.

## AWS Flow

`Frontend -> FastAPI -> Database -> SQS -> Lambda -> Notifications -> role portal polling`

- `FastAPI` handles auth, role checks, validation, and core writes
- `SQS` buffers event payloads
- `Lambda` creates role-based notifications
- `S3` stores files and archives
- `CloudWatch` captures backend and Lambda logs

## Available Scripts

### Backend (root — npm scripts wrapping uv)

```bash
npm run seed            # Seed default users (uv run python -m app.seed)
npm run check           # format:check + lint + typecheck
npm run format          # ruff format .
npm run format:check    # ruff format --check .
npm run lint            # ruff check .
npm run lint:fix        # ruff check --fix .
npm run typecheck       # mypy app/
npm run sync            # uv sync
npm run dev             # Start backend (uv run fastapi dev)
npm run build           # docker compose build
npm run up              # docker compose up -d
npm run down            # docker compose down
```

### Frontend (frontend/)

```bash
npm run dev             # Start Vite dev server
npm run build           # TypeScript check + production build
npm run lint            # ESLint
```

## Project Structure

```
app/                    # FastAPI backend
├── main.py             # App entry point, CORS, auth, router includes
├── config.py           # Env-based settings (DB, JWT, AWS)
├── database.py         # SQLAlchemy engine + session
├── models.py           # 8 ORM models (users, patients, appointments, etc.)
├── schemas.py          # Pydantic request/response schemas
├── auth.py             # JWT create/verify, role_required guard
├── seed.py             # Insert 4 default users
├── simulator.py        # CSV-based event simulator
├── routers/            # Role-based API routes
│   ├── reception.py
│   ├── admin.py
│   ├── nurse.py
│   └── doctor.py
├── engine/             # Event routing & vitals risk evaluation
│   ├── routing.py
│   └── risk.py
└── services/           # SQS, S3, notifications
    ├── notifications.py
    ├── sqs.py
    └── s3.py

frontend/src/           # React frontend
├── pages/              # Login, Admin, Simulator
├── components/         # PaginatedTable, SeverityBadge, StatsCard + shadcn/ui
├── layouts/            # DashboardLayout (sidebar + header)
├── context/            # AuthContext (login/logout/JWT)
├── api/                # Axios client with JWT interceptor
├── hooks/              # useDebounce
├── types/              # TypeScript interfaces
└── lib/                # cn() utility

data/
└── hospital_events.csv # 20 predefined simulation events

deploy/                 # AWS deployment scripts & configs
├── startup.sh
├── iam-lambda-policy.json
├── iam-ec2-policy.json
├── cloudwatch-agent.json
└── init-aws.sh         # LocalStack init (creates SQS queue + S3 bucket)

lambda/                 # Standalone AWS Lambda handler
├── handler.py
└── ...

tests/                  # Pytest test suite
├── test_risk.py
├── test_routing.py
├── test_api.py
└── conftest.py
```

## Troubleshooting

- **Port already in use**: `lsof -ti:8000 | xargs kill` or change the port in the command
- **SQLite database not found**: Run `uv run python -m app.seed` to create and seed it
- **Frontend can't reach backend**: Check `frontend/vite.config.ts` — the proxy must point to `http://localhost:8000`
- **Docker permission errors**: Ensure Docker Desktop is running and you're in the `docker` group
- **uv command not found**: Install uv with `curl -LsSf https://astral.sh/uv/install.sh | sh` or `pip install uv`
