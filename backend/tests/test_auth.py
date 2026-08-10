"""Tests for API auth enforcement."""
from backend.config import settings


def test_app_routes_require_jwt_when_password_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "PASSWORD", "dev")
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret")

    denied = client.get("/api/transactions/accounts")
    assert denied.status_code == 401

    login = client.post("/api/auth/login", json={"password": "dev"})
    assert login.status_code == 200
    token = login.json()["token"]

    allowed = client.get("/api/transactions/accounts", headers={"Authorization": f"Bearer {token}"})
    assert allowed.status_code == 200


def test_app_routes_open_when_password_not_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "PASSWORD", "")

    response = client.get("/api/transactions/accounts")

    assert response.status_code == 200
