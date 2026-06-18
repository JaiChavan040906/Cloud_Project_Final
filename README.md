# Hospital Event Simulation

AWS-Based Hospital Event Simulation and Care Coordination System.  
An event-driven hospital operations platform built with FastAPI + SQLite + React.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.11+) |
| Database | SQLite via SQLAlchemy 2.x |
| Auth | JWT (python-jose) + bcrypt |
| Frontend | React 19 + TypeScript + Vite |
| Styling | Tailwind CSS v4 + shadcn/ui |
| Package manager | **uv** (backend), **npm** (frontend) |
| AWS SDK | boto3 (SQS, S3) |

## How to Run

### 1. Start the Backend

```bash
# From the project root
uv run uvicorn app.main:app --reload --port 8000
```

The backend runs on **http://localhost:8000**.

### 2. Seed Default Users (first time only)

```bash
uv run python -m app.seed
```

### 3. Start the Frontend

```bash
cd frontend
npm run dev
```

The frontend runs on **http://localhost:5173** and proxies API requests to the backend.

### 4. Open the App

Navigate to **http://localhost:5173** — you'll see the role selection login page.

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

Each event creates real database records (patients, appointments, alerts, medications, reviews).

## Available Scripts

### Backend (root)

```bash
npm run seed        # Seed default users
npm run check       # format:check + lint + typecheck
npm run format      # ruff format .
npm run lint        # ruff check .
npm run typecheck   # mypy app/
```

### Frontend (frontend/)

```bash
npm run dev         # Start Vite dev server
npm run build       # TypeScript check + production build
npm run lint        # ESLint
```

## Project Structure

```
app/                    # FastAPI backend
├── main.py
├── routers/            # Role-based API routes
├── engine/             # Event routing & risk evaluation
└── services/           # SQS, S3, notifications

frontend/src/           # React frontend
├── pages/              # Login, Admin, Simulator
├── components/         # Shared UI components
├── layouts/            # Dashboard layout
├── context/            # Auth context
├── api/                # Axios client
└── types/              # TypeScript types

data/
└── hospital_events.csv # 20 simulation events

deploy/                 # AWS deployment scripts
lambda/                 # AWS Lambda handler
```
