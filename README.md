# E9 — Lab Report Rubric Scorer

Evidence-backed grading with one specialist AI agent per rubric criterion.

## Structure

```
e9-lab/
├── backend/       FastAPI + Groq agents + SQLAlchemy
├── frontend/      Liquid-glass dashboard (Score / Rubrics / History)
├── landing/       Public marketing page
├── migrations/    Alembic
├── Procfile
└── alembic.ini
```

## Quick start

```bash
cd backend
pip install -r requirements.txt
export GROQ_API_KEY=your_key
export JWT_SECRET_KEY=change-me
uvicorn main:app --reload
```

Open `frontend/login.html` (or serve the frontend folder).

## Deploy (Railway)

- Start command uses `Procfile`: `uvicorn main:app --host 0.0.0.0 --port $PORT --app-dir backend`
- Target port: **8080**
- Set env: `GROQ_API_KEY`, `JWT_SECRET_KEY`, optional `DATABASE_URL`, `ALLOWED_ORIGINS`

## Features

- JWT auth
- Custom rubrics (weights sum to 100)
- Parallel specialist scoring + evidence quotes
- Deterministic weighted total & letter grade
- Disagreement flags (>20 pt)
- Batch scoring + JSON export + audit log
