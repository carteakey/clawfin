"""Tests for AI provider settings."""


def test_ai_api_key_override_is_write_only(client, db, monkeypatch):
    from backend.config import settings
    from backend.db.models import AppConfig

    monkeypatch.setattr(settings, "PASSWORD", "")
    monkeypatch.setattr(settings, "AI_API_KEY", "")
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret")

    saved = client.put("/api/settings/ai/flags", json={"api_key": "sk-test"})
    assert saved.status_code == 200
    stored = db.query(AppConfig).filter(AppConfig.key == "ai_api_key_override").first()
    assert stored is not None
    assert stored.value.startswith("enc:")
    assert "sk-test" not in stored.value

    flags = client.get("/api/settings/ai/flags")
    assert flags.status_code == 200
    assert flags.json()["has_api_key"] is True
    assert "sk-test" not in str(flags.json())

    cleared = client.put("/api/settings/ai/flags", json={"clear_api_key": True})
    assert cleared.status_code == 200

    flags = client.get("/api/settings/ai/flags")
    assert flags.json()["has_api_key"] is False
