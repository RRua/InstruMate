"""Tests for /api/analyze endpoints."""

import io
import os


def test_upload_non_apk_rejected(test_client):
    resp = test_client.post(
        "/api/analyze",
        files={"file": ("test.txt", b"not an apk", "text/plain")},
    )
    assert resp.status_code == 400
    assert "apk" in resp.json()["detail"].lower()


def test_upload_no_file_rejected(test_client):
    resp = test_client.post("/api/analyze")
    assert resp.status_code == 422  # validation error


def test_upload_size_limit(test_client, monkeypatch):
    """Verify files exceeding MAX_UPLOAD_SIZE are rejected with 413."""
    import api.routers.analyze
    monkeypatch.setattr(api.routers.analyze, "MAX_UPLOAD_SIZE", 100)

    large_content = b"PK\x03\x04" + b"\x00" * 200
    resp = test_client.post(
        "/api/analyze",
        files={"file": ("big.apk", large_content, "application/octet-stream")},
    )
    assert resp.status_code == 413


def test_upload_apk_creates_job(test_client, monkeypatch):
    """Happy path: a valid .apk upload returns a JobStatus and stores the file."""
    import api.routers.analyze

    captured = {}

    def fake_run(job_id, apk_path, analyzer_keys):
        captured["job_id"] = job_id
        captured["apk_path"] = apk_path
        captured["analyzers"] = analyzer_keys

    monkeypatch.setattr(api.routers.analyze, "_run_analysis", fake_run)

    resp = test_client.post(
        "/api/analyze",
        params={"analyzers": "basic,content++"},
        files={"file": ("app-debug.apk", b"PK\x03\x04dummy", "application/octet-stream")},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"]
    assert body["status"] == "pending"
    assert "basic" in body["message"]

    # Background task was scheduled with the parsed analyzer list and a real APK on disk.
    assert captured["job_id"] == body["job_id"]
    assert captured["analyzers"] == ["basic", "content++"]
    assert os.path.isfile(captured["apk_path"])
    with open(captured["apk_path"], "rb") as f:
        assert f.read().startswith(b"PK\x03\x04")


def test_get_analysis_status_found(test_client):
    """GET /api/analyze/{job_id} returns the job recorded in the store."""
    from api.job_store import job_store
    from api.models import AnalysisStatus

    job_store.create(
        job_id="job-analyze-1",
        status=AnalysisStatus.RUNNING,
        message="working",
        job_type="analysis",
    )

    resp = test_client.get("/api/analyze/job-analyze-1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == "job-analyze-1"
    assert body["status"] == "running"
    assert body["message"] == "working"


def test_get_analysis_status_unknown_job(test_client):
    resp = test_client.get("/api/analyze/does-not-exist")
    assert resp.status_code == 404


def test_upload_uses_default_analyzers_when_param_omitted(test_client, monkeypatch):
    """Without ?analyzers=, the route falls back to "basic,content++"."""
    import api.routers.analyze

    captured = {}
    monkeypatch.setattr(
        api.routers.analyze,
        "_run_analysis",
        lambda jid, p, keys: captured.setdefault("analyzers", keys),
    )

    resp = test_client.post(
        "/api/analyze",
        files={"file": ("a.apk", b"PK\x03\x04", "application/octet-stream")},
    )
    assert resp.status_code == 200
    assert captured["analyzers"] == ["basic", "content++"]


def test_upload_persists_job_in_store(test_client, monkeypatch):
    """Returned job_id is queryable via GET /api/analyze/{job_id}."""
    import api.routers.analyze
    monkeypatch.setattr(api.routers.analyze, "_run_analysis", lambda *a, **k: None)

    job_id = test_client.post(
        "/api/analyze",
        files={"file": ("a.apk", b"PK\x03\x04", "application/octet-stream")},
    ).json()["job_id"]

    resp = test_client.get(f"/api/analyze/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


def test_get_analysis_status_returns_completed_state(test_client):
    """Status field reflects the latest job_store update."""
    from api.job_store import job_store
    from api.models import AnalysisStatus

    job_store.create(job_id="job-done", status=AnalysisStatus.PENDING)
    job_store.update(
        "job-done",
        status=AnalysisStatus.COMPLETED,
        app_id="abc123",
        message="finished",
    )

    body = test_client.get("/api/analyze/job-done").json()
    assert body["status"] == "completed"
    assert body["app_id"] == "abc123"
    assert body["message"] == "finished"
