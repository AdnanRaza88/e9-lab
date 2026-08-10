"""E9 — single entry point.

Run the whole project with one command:

    python run.py

Starts the FastAPI backend on http://127.0.0.1:8000. The backend serves BOTH
the API and the static frontend (same origin, see backend/main.py catch_all),
so there is no separate frontend server — no port conflicts (WinError 10013
happens on reserved ports like 3000), no CORS, no API_BASE_URL mismatch.

Port can be overridden:
    E9_PORT=8001 python run.py
"""
import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"

PORT = int(os.environ.get("E9_PORT", "8000"))
URL = f"http://127.0.0.1:{PORT}"
STARTUP_WAIT = 3.0  # seconds before checking the backend survived startup


def _kill_tree(proc):
    """Terminate a process and its whole subtree (uvicorn --reload spawns a
    worker: taskkill /T on Windows, killpg on POSIX)."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def shutdown(signum=None, frame=None):
    print("\nShutting down server...")
    if backend.poll() is None:
        _kill_tree(backend)
    print("Done. Goodbye!")
    sys.exit(0)


def main():
    global backend
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass

    print("Starting backend server...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", str(PORT), "--reload"],
        cwd=str(BACKEND_DIR),
    )

    time.sleep(STARTUP_WAIT)
    if backend.poll() is not None:
        print("Failed to start backend server", file=sys.stderr)
        sys.exit(1)

    print(f"✔ E9 Smart Grading System running at {URL}")
    print(f"✔ Login page:  {URL}/login.html")
    print(f"✔ API docs:    {URL}/docs")
    print("Press Ctrl+C to stop.")

    webbrowser.open(URL + "/login.html")

    for sig in (signal.SIGINT, getattr(signal, "SIGBREAK", None), getattr(signal, "SIGTERM", None)):
        if sig is not None:
            signal.signal(sig, shutdown)

    try:
        while True:
            time.sleep(1)
            if backend.poll() is not None:
                print("Failed to start backend server", file=sys.stderr)
                shutdown()
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
