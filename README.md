# E9 — Lab Report Rubric Scorer

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Evidence-backed grading.** One specialist AI agent per rubric criterion, cited evidence quotes, deterministic weighted totals in Python.

## Features

- Specialist AI agents (one per rubric criterion)
- Evidence quotes with citations
- Deterministic weighted scoring in pure Python
- FastAPI backend + clean frontend dashboard
- Auth ready (JWT)

## Structure

```
e9/
├── backend/          # FastAPI + Groq agents
├── frontend/         # Dashboard + auth (static)
├── landing/          # Marketing page
├── migrations/       # Alembic
├── alembic.ini
└── Procfile
```

## Quick start (local)

```bash
cd backend
pip install -r requirements.txt
export GROQ_API_KEY=your_key
export JWT_SECRET_KEY=change-me
uvicorn main:app --reload --port 8000
```

Open `frontend/login.html` in browser (or serve the frontend folder).

## Deploy (Railway)

Single service — FastAPI serves both the API **and** the static frontend
(same origin), so one Railway service is all you need.

1. Push this repo to GitHub.
2. On [Railway](https://railway.app): **New Project → Deploy from GitHub repo**.
3. Add env vars (Variables tab):
   - `GROQ_API_KEY` — your Groq key (required for scoring)
   - `JWT_SECRET_KEY` — any long random string (auth signing)
   - `DATABASE_URL` — optional; omit to use SQLite (resets on redeploy).
     For persistent data, add a Railway Postgres plugin and it's set
     automatically (tables are created on startup).
4. Railway auto-detects the `Procfile` / `railway.json` — no build config needed.
5. Open the generated URL. Health check: `https://<app>.up.railway.app/health`.

Local dev is unaffected: `python run.py` still splits UI (:3000) and API (:8000).

---

Built with love by [AdnanRaza88](https://github.com/AdnanRaza88)
