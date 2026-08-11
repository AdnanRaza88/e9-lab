@echo off
REM E9 - Lab Report Rubric Scorer - local start script
cd /d %~dp0

if not exist .venv (
    echo [E9] Creating virtual environment...
    python -m venv .venv
)

echo [E9] Installing requirements...
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

echo [E9] Starting server on http://127.0.0.1:8000 ...
echo [E9] NOTE: set GROQ_API_KEY env var before running to enable AI scoring
.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --reload --port 8000
