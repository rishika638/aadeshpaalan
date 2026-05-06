# AadeshPaalan

Court judgment compliance execution system (Karnataka Govt). This repository contains:
- `backend/`: FastAPI + async SQLAlchemy + Alembic + OCR/LLM extraction services
- `frontend/`: React 18 + TypeScript + Tailwind + React Query + React Router v6

## Prerequisites
- Docker Desktop (Windows) **running** (for `docker compose`)
- Node.js 20+ (optional, for running frontend outside Docker)
- Python 3.11 (optional, for running backend outside Docker)

## Configure environment
Copy `.env.example` to `.env` and fill:
- `ANTHROPIC_API_KEY`
- `JWT_SECRET`
- NIC SMTP values if you want alert sending

This repo includes a dev `.env` with placeholders; replace them before production.

## Run with Docker (recommended)
From `d:\Court\aadeshpaalan`:

```bash
docker compose up --build
```

Then (in another terminal) run migrations and seed:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python /app/seed.py
```

Endpoints:
- Backend: `http://localhost:8000/healthz`
- Frontend: `http://localhost:5173`

Login emails (seeded):
- `reviewer@karnataka.gov.in`
- `officer@karnataka.gov.in`
- `admin@karnataka.gov.in`

## Local run (without Docker)
Backend:

```bash
cd backend
python -m pip install -r requirements.txt
set DATABASE_URL=postgresql+asyncpg://...
set JWT_SECRET=...
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
set VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

