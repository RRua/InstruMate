"""Tests for /api/apps/{app_id}/classify, /api/classify/{job_id},
/api/apps/{app_id}/classification, and /api/apps/{app_id}/metrics."""

import json
import os


def _stub_run(monkeypatch):
    """Replace the heavy classification background task with a no-op
    that captures arguments for inspection."""
    import api.routers.classify

    captured = {}

    def fake_run(job_id, app_id, output_dir, model):
        captured.update(
            job_id=job_id, app_id=app_id, output_dir=output_dir, model=model
        )

    monkeypatch.setattr(api.routers.classify, "_run_classification", fake_run)
    return captured


def test_classify_post_creates_job(test_client, monkeypatch):
    captured = _stub_run(monkeypatch)

    resp = test_client.post("/api/apps/abc123/classify")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    assert body["app_id"] == "abc123"
    assert body["job_id"]

    # Background task scheduled with the right args
    assert captured["app_id"] == "abc123"
    assert captured["job_id"] == body["job_id"]
    assert os.path.isfile(os.path.join(captured["output_dir"], "app.json"))


def test_classify_post_uses_query_model_override(test_client, monkeypatch):
    captured = _stub_run(monkeypatch)
    resp = test_client.post("/api/apps/abc123/classify?model=llama3")
    assert resp.status_code == 200
    assert captured["model"] == "llama3"


def test_classify_post_falls_back_to_env_model(test_client, monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2")
    captured = _stub_run(monkeypatch)
    resp = test_client.post("/api/apps/abc123/classify")
    assert resp.status_code == 200
    assert captured["model"] == "qwen2"


def test_classify_post_unknown_app_404(test_client, monkeypatch):
    _stub_run(monkeypatch)
    resp = test_client.post("/api/apps/no-such-app/classify")
    assert resp.status_code == 404


def test_classify_job_status_found(test_client):
    from api.job_store import job_store
    from api.models import AnalysisStatus

    job_store.create(
        job_id="job-classify-1",
        status=AnalysisStatus.COMPLETED,
        message="done",
        app_id="abc123",
        job_type="classification",
    )

    resp = test_client.get("/api/classify/job-classify-1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == "job-classify-1"
    assert body["status"] == "completed"
    assert body["app_id"] == "abc123"


def test_classify_job_status_unknown(test_client):
    resp = test_client.get("/api/classify/missing-job-id")
    assert resp.status_code == 404


def test_get_classification_when_present(test_client, tmp_output_dir):
    payload = {
        "security_risk_level": "low",
        "malware_likelihood": "benign",
        "confidence": 0.9,
        "reasoning": "stub",
    }
    out_dir = tmp_output_dir / "com.example.test" / "com.example.test-1.0_original"
    with open(out_dir / "classification.json", "w") as f:
        json.dump(payload, f)

    resp = test_client.get("/api/apps/abc123/classification")
    assert resp.status_code == 200
    assert resp.json() == payload


def test_get_classification_404_when_missing(test_client):
    resp = test_client.get("/api/apps/abc123/classification")
    assert resp.status_code == 404
    assert "classification" in resp.json()["detail"].lower()


def test_get_classification_404_when_app_missing(test_client):
    resp = test_client.get("/api/apps/no-such-app/classification")
    assert resp.status_code == 404


def test_get_metrics_when_present(test_client, tmp_output_dir):
    payload = {"package_name": "com.example.test", "permission_risk_score": 3}
    out_dir = tmp_output_dir / "com.example.test" / "com.example.test-1.0_original"
    with open(out_dir / "security_metrics.json", "w") as f:
        json.dump(payload, f)

    resp = test_client.get("/api/apps/abc123/metrics")
    assert resp.status_code == 200
    assert resp.json() == payload


def test_get_metrics_404_when_missing(test_client):
    resp = test_client.get("/api/apps/abc123/metrics")
    assert resp.status_code == 404


def test_get_metrics_404_when_app_missing(test_client):
    resp = test_client.get("/api/apps/no-such-app/metrics")
    assert resp.status_code == 404


# --- Additional coverage ---


def test_classify_post_defaults_to_mistral_when_nothing_set(test_client, monkeypatch):
    """With no ?model= and no OLLAMA_MODEL env, falls back to "mistral"."""
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    captured = _stub_run(monkeypatch)
    test_client.post("/api/apps/abc123/classify")
    assert captured["model"] == "mistral"


def test_classify_post_persists_job(test_client, monkeypatch):
    """The returned job_id is retrievable via GET /api/classify/{job_id}."""
    _stub_run(monkeypatch)
    job_id = test_client.post("/api/apps/abc123/classify").json()["job_id"]
    body = test_client.get(f"/api/classify/{job_id}").json()
    assert body["status"] == "pending"
    assert body["app_id"] == "abc123"


def test_classify_post_output_dir_matches_registry(test_client, monkeypatch):
    """Background task receives the registry's output_dir for the app."""
    captured = _stub_run(monkeypatch)
    from api.app_registry import registry
    expected = registry.get_output_dir("abc123")
    test_client.post("/api/apps/abc123/classify")
    assert captured["output_dir"] == expected


def test_classify_job_status_reports_failure(test_client):
    from api.job_store import job_store
    from api.models import AnalysisStatus

    job_store.create(
        job_id="job-classify-fail",
        status=AnalysisStatus.PENDING,
        job_type="classification",
    )
    job_store.update(
        "job-classify-fail",
        status=AnalysisStatus.FAILED,
        message="ollama down",
    )

    body = test_client.get("/api/classify/job-classify-fail").json()
    assert body["status"] == "failed"
    assert body["message"] == "ollama down"


def test_get_classification_returns_nested_structure(test_client, tmp_output_dir):
    """Route passes the JSON through verbatim (not reshaping it)."""
    import json
    payload = {
        "security_risk_level": "high",
        "risk_factors": [
            {"category": "permissions", "description": "dangerous", "severity": "high"}
        ],
        "recommendations": ["review network permissions"],
        "reasoning": "multiple dangerous permissions",
    }
    out_dir = tmp_output_dir / "com.example.test" / "com.example.test-1.0_original"
    with open(out_dir / "classification.json", "w") as f:
        json.dump(payload, f)

    body = test_client.get("/api/apps/abc123/classification").json()
    assert body == payload
    assert body["risk_factors"][0]["severity"] == "high"


def test_get_metrics_returns_nested_structure(test_client, tmp_output_dir):
    import json
    payload = {
        "package_name": "com.example.test",
        "permissions": {
            "total_permissions": 5,
            "dangerous_count": 2,
            "dangerous_permissions": ["READ_SMS", "SEND_SMS"],
        },
    }
    out_dir = tmp_output_dir / "com.example.test" / "com.example.test-1.0_original"
    with open(out_dir / "security_metrics.json", "w") as f:
        json.dump(payload, f)

    body = test_client.get("/api/apps/abc123/metrics").json()
    assert body == payload
    assert body["permissions"]["dangerous_count"] == 2
