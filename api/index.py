"""Vercel Python entrypoint — FastAPI app lives under deeptrace/backend."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "deeptrace" / "backend"))

from app.main import app  # noqa: E402, F401
