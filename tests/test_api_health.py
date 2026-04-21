"""Tests for the /api/health endpoint."""


def test_health_returns_ok(test_client):
    resp = test_client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "python_version" in data
    assert isinstance(data["analyzers_available"], list)
    assert isinstance(data["variant_makers_available"], list)


def test_health_auth_enabled_false_by_default(test_client):
    resp = test_client.get("/api/health")
    data = resp.json()
    assert data["auth_enabled"] is False


def test_health_auth_enabled_when_key_set(test_client, monkeypatch):
    monkeypatch.setenv("INSTRUMATE_API_KEY", "test-secret-key")
    resp = test_client.get("/api/health")
    data = resp.json()
    assert data["auth_enabled"] is True


def test_health_virustotal_configured_field(test_client):
    resp = test_client.get("/api/health")
    data = resp.json()
    assert "virustotal_configured" in data
    assert isinstance(data["virustotal_configured"], bool)
