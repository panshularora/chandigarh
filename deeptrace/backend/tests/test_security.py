from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import DEFAULT_SECRET_KEY, Settings, check_secret_key, settings
from app.security import hash_password, verify_password


def test_pbkdf2_hash_and_verify():
    stored = hash_password("chandigarh2026")
    salt_hex, dk_hex = stored.split("$")
    assert len(bytes.fromhex(salt_hex)) == 16
    assert len(dk_hex) == 64
    assert "chandigarh2026" not in stored
    assert verify_password("chandigarh2026", stored) is True
    assert verify_password("wrong-password", stored) is False
    assert verify_password("", stored) is False


def test_pbkdf2_uses_random_salt():
    assert hash_password("same") != hash_password("same")


def test_verify_password_rejects_malformed_hash():
    assert verify_password("x", "not-a-valid-hash") is False


def _token(**overrides):
    payload = {"sub": "1", "username": "inspector", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    payload.update(overrides)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_alg)


def test_expired_jwt_is_rejected(client):
    expired = _token(exp=datetime.now(timezone.utc) - timedelta(seconds=5))
    r = client.get("/api/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401
    assert "expired" in r.json()["detail"].lower()


def test_unexpired_jwt_is_accepted(client):
    r = client.get("/api/me", headers={"Authorization": f"Bearer {_token()}"})
    assert r.status_code == 200
    assert r.json()["username"] == "inspector"


def test_jwt_signed_with_other_key_is_rejected(client):
    forged = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        DEFAULT_SECRET_KEY,
        algorithm="HS256",
    )
    r = client.get("/api/me", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_login_token_expires_after_jwt_hours(client):
    from tests.conftest import DEMO_USER

    token = client.post("/api/auth/login", json=DEMO_USER).json()["token"]
    claims = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_alg])
    lifetime = claims["exp"] - datetime.now(timezone.utc).timestamp()
    assert settings.jwt_hours * 3600 - 60 < lifetime <= settings.jwt_hours * 3600


# --- SECRET_KEY startup guard -------------------------------------------------

def test_guard_rejects_default_key_outside_demo_mode():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        check_secret_key(Settings(secret_key=DEFAULT_SECRET_KEY, demo_mode=False))


def test_guard_rejects_empty_key_outside_demo_mode():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        check_secret_key(Settings(secret_key="", demo_mode=False))


def test_guard_allows_default_key_in_demo_mode():
    cfg = Settings(secret_key=DEFAULT_SECRET_KEY, demo_mode=True)
    check_secret_key(cfg)
    assert cfg.secret_key == DEFAULT_SECRET_KEY


def test_guard_allows_custom_key():
    check_secret_key(Settings(secret_key="a-real-random-secret", demo_mode=False))
