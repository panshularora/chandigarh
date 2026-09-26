"""The app must refuse to start with the placeholder SECRET_KEY unless DEMO_MODE is on."""
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def _import_app(tmp_path, **env_overrides):
    env = {k: v for k, v in os.environ.items() if k not in {"SECRET_KEY", "DEMO_MODE", "VERCEL"}}
    env.update(
        {
            "DATABASE_URL": f"sqlite:///{(tmp_path / 'boot.db').as_posix()}",
            "DATA_DIR": str(tmp_path),
            "UPLOAD_DIR": str(tmp_path / "uploads"),
            "HEATMAP_DIR": str(tmp_path / "heatmaps"),
            "REPORT_DIR": str(tmp_path / "reports"),
            "LIGHT_SEED": "true",
            # An explicit empty value also overrides any developer .env file.
            "SECRET_KEY": "",
        }
    )
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


def test_startup_fails_fast_with_default_secret(tmp_path):
    from app.config import DEFAULT_SECRET_KEY

    r = _import_app(tmp_path, SECRET_KEY=DEFAULT_SECRET_KEY, DEMO_MODE="false")
    assert r.returncode != 0
    assert "SECRET_KEY" in r.stderr and "DEMO_MODE" in r.stderr
    assert not (tmp_path / "boot.db").exists(), "guard must run before the DB is created"


def test_startup_fails_fast_without_secret(tmp_path):
    r = _import_app(tmp_path)
    assert r.returncode != 0
    assert "SECRET_KEY" in r.stderr


def test_startup_allowed_in_demo_mode(tmp_path):
    r = _import_app(tmp_path, DEMO_MODE="true")
    assert r.returncode == 0, r.stderr
