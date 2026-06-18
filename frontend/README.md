# Frontend — Hospital Event Simulation

React 19 + TypeScript + Vite + Tailwind CSS v4 + shadcn/ui.

## Setup

```bash
npm install
```

## Development

```bash
npm run dev
```

Runs on **http://localhost:5173**. Make sure the backend is running on port 8000 — the Vite dev server proxies `/api`, `/auth`, and `/health` requests to `http://localhost:8000`.

## Build

```bash
npm run build     # tsc + vite build
npm run lint      # ESLint
```

## Project Structure

```
src/
├── pages/          # Login, Admin, Simulator
├── components/     # PaginatedTable, SeverityBadge, StatsCard + shadcn/ui
├── layouts/        # DashboardLayout (sidebar + header)
├── context/        # AuthContext (login/logout/JWT)
├── api/            # Axios client with JWT interceptor
├── hooks/          # useDebounce
├── types/          # TypeScript interfaces
└── lib/            # cn() utility
```

## Default Users

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Doctor | `doctor` | `doctor123` |
| Nurse | `nurse` | `nurse123` |
| Receptionist | `reception` | `reception123` |
