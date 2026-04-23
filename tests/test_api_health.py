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


def test_health_virustotal_configured_reflects_env(test_client, monkeypatch):
    monkeypatch.setenv("VT_API_KEY", "some-key")
    assert test_client.get("/api/health").json()["virustotal_configured"] is True
    monkeypatch.setenv("VT_API_KEY", "")
    assert test_client.get("/api/health").json()["virustotal_configured"] is False


def test_health_response_shape_matches_schema(test_client):
    """All HealthResponse fields are present with correct types."""
    data = test_client.get("/api/health").json()
    assert isinstance(data["status"], str)
    assert isinstance(data["java_available"], bool)
    assert isinstance(data["jdk8_available"], bool)
    assert isinstance(data["tools_available"], dict)
    assert isinstance(data["python_version"], str)
    assert isinstance(data["analyzers_available"], list)
    assert isinstance(data["variant_makers_available"], list)
    assert isinstance(data["ollama_available"], bool)


def test_health_lists_known_analyzers(test_client):
    """Core analyzers are always reported as available."""
    data = test_client.get("/api/health").json()
    assert "basic" in data["analyzers_available"]
    assert "callgraph" in data["analyzers_available"]
    assert "content++" in data["analyzers_available"]
