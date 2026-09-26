"""Test setup: point the app at a throwaway SQLite DB and data dir *before* it is imported.

app.config reads its settings at import time and app.main seeds the database on import,
so the environment has to be in place first. No network access is needed.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="deeptrace-tests-"))
os.environ.update(
    {
        "SECRET_KEY": "test-secret-key-not-the-default-0123456789",
        "DEMO_MODE": "false",
        "DATABASE_URL": f"sqlite:///{(_TMP / 'test.db').as_posix()}",
        "DATA_DIR": str(_TMP),
        "UPLOAD_DIR": str(_TMP / "uploads"),
        "HEATMAP_DIR": str(_TMP / "heatmaps"),
        "REPORT_DIR": str(_TMP / "reports"),
        "LIGHT_SEED": "true",
        "XAI_API_KEY": "",
        "FRONTEND_DIST": str(_TMP / "no-frontend"),
    }
)
os.environ.pop("VERCEL", None)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

DEMO_USER = {"username": "inspector", "password": "chandigarh2026"}


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def token(client: TestClient) -> str:
    r = client.post("/api/auth/login", json=DEMO_USER)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="session")
def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def db():
    from app.database import SessionLocal

    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
