import pytest

from tests.conftest import DEMO_USER

PROTECTED_GET = ["/api/me", "/api/dashboard", "/api/cases", "/api/reports", "/api/audit", "/api/operators"]


def test_health_is_public(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_login_rejects_wrong_password(client):
    r = client.post("/api/auth/login", json={"username": DEMO_USER["username"], "password": "nope"})
    assert r.status_code == 401


def test_login_rejects_unknown_user(client):
    r = client.post("/api/auth/login", json={"username": "ghost", "password": DEMO_USER["password"]})
    assert r.status_code == 401


@pytest.mark.parametrize("path", PROTECTED_GET)
def test_protected_routes_reject_missing_token(client, path):
    r = client.get(path)
    assert r.status_code in (401, 403)


@pytest.mark.parametrize("path", PROTECTED_GET)
def test_protected_routes_reject_garbage_token(client, path):
    r = client.get(path, headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code in (401, 403)


@pytest.mark.parametrize("path", PROTECTED_GET)
def test_protected_routes_accept_valid_token(client, auth, path):
    r = client.get(path, headers=auth)
    assert r.status_code == 200, r.text


def test_create_case_requires_auth(client):
    r = client.post("/api/cases", json={"title": "no token"})
    assert r.status_code in (401, 403)


def test_query_param_token_is_accepted(client, token):
    # Used by the UI for <img>/<a> links to media and PDFs.
    r = client.get("/api/me", params={"access_token": token})
    assert r.status_code == 200
