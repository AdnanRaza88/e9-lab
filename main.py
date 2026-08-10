"""Root shim so uvicorn `main:app` works whether Railway's root directory is
repo root (/) or /backend. Imports the real app from backend/ and makes the
backend dir importable (backend modules use flat imports like `import errors`)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from backend.main import app

__all__ = ["app"]
