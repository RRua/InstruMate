"""Tests for /api/apps/{app_id}/virustotal (POST + GET) and
/api/virustotal/{job_id}."""

import json
import os


def _stub_run(monkeypatch):
    import api.routers.virustotal

    captured = {}

    def fake_run(job_id, app_id, apk_path, output_dir):
        captured.update(
            job_id=job_id,
            app_id=app_id,
            apk_path=apk_path,
            output_dir=output_dir,
        )

    monkeypatch.setattr(api.routers.virustotal, "_run_vt_scan", fake_run)
    return captured


def test_post_vt_creates_job(test_client, monkeypatch):
    monkeypatch.setenv("VT_API_KEY", "fake-key")
    captured = _stub_run(monkeypatch)

    resp = test_client.post("/api/apps/abc123/virustotal")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    assert body["app_id"] == "abc123"
    assert body["job_id"]

    assert captured["app_id"] == "abc123"
    assert captured["job_id"] == body["job_id"]
    assert os.path.isfile(captured["apk_path"])
    assert captured["apk_path"].endswith(".apk")


def test_post_vt_unknown_app_404(test_client, monkeypatch):
    monkeypatch.setenv("VT_API_KEY", "fake-key")
    _stub_run(monkeypatch)
    resp = test_client.post("/api/apps/no-such-app/virustotal")
    assert resp.status_code == 404


def test_post_vt_missing_api_key_400(test_client, monkeypatch):
    monkeypatch.setenv("VT_API_KEY", "")
    _stub_run(monkeypatch)
    resp = test_client.post("/api/apps/abc123/virustotal")
    assert resp.status_code == 400
    assert "vt_api_key" in resp.json()["detail"].lower()


def test_post_vt_no_apk_file_400(test_client, tmp_output_dir, monkeypatch):
    """If the app's APK is gone, VT submission should report a 400."""
    monkeypatch.setenv("VT_API_KEY", "fake-key")
    _stub_run(monkeypatch)

    apk = tmp_output_dir / "com.example.test" / "com.example.test-1.0_original" / "installers" / "test.apk"
    apk.unlink()

    resp = test_client.post("/api/apps/abc123/virustotal")
    assert resp.status_code == 400
    assert "apk" in resp.json()["detail"].lower()


def test_get_vt_job_status_found(test_client):
    from api.job_store import job_store
    from api.models import AnalysisStatus

    job_store.create(
        job_id="job-vt-1",
        status=AnalysisStatus.RUNNING,
        message="uploading",
        app_id="abc123",
        job_type="virustotal",
    )
    resp = test_client.get("/api/virustotal/job-vt-1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == "job-vt-1"
    assert body["status"] == "running"


def test_get_vt_job_status_unknown(test_client):
    resp = test_client.get("/api/virustotal/missing")
    assert resp.status_code == 404


def test_get_vt_report_when_present(test_client, tmp_output_dir):
    payload = {"data": {"attributes": {"last_analysis_stats": {"malicious": 0}}}}
    out_dir = tmp_output_dir / "com.example.test" / "com.example.test-1.0_original"
    with open(out_dir / "virustotal_report.json", "w") as f:
        json.dump(payload, f)

    resp = test_client.get("/api/apps/abc123/virustotal")
    assert resp.status_code == 200
    assert resp.json() == payload


def test_get_vt_report_404_when_missing(test_client):
    resp = test_client.get("/api/apps/abc123/virustotal")
    assert resp.status_code == 404


def test_get_vt_report_404_when_app_missing(test_client):
    resp = test_client.get("/api/apps/no-such-app/virustotal")
    assert resp.status_code == 404


# --- Additional coverage ---


def test_post_vt_persists_job(test_client, monkeypatch):
    from api.job_store import job_store

    monkeypatch.setenv("VT_API_KEY", "fake-key")
    _stub_run(monkeypatch)

    job_id = test_client.post("/api/apps/abc123/virustotal").json()["job_id"]
    stored = job_store.get(job_id)
    assert stored is not None
    assert stored.app_id == "abc123"
    assert stored.status.value == "pending"


def test_post_vt_finds_apk_in_installers(test_client, monkeypatch):
    """_find_apk_file should prefer installers/*.apk."""
    monkeypatch.setenv("VT_API_KEY", "fake-key")
    captured = _stub_run(monkeypatch)
    test_client.post("/api/apps/abc123/virustotal")
    assert captured["apk_path"].endswith("installers/test.apk")


def test_get_vt_job_status_reports_failure(test_client):
    from api.job_store import job_store
    from api.models import AnalysisStatus

    job_store.create(
        job_id="vt-fail",
        status=AnalysisStatus.PENDING,
        app_id="abc123",
        job_type="virustotal",
    )
    job_store.update(
        "vt-fail",
        status=AnalysisStatus.FAILED,
        message="quota exceeded",
    )

    body = test_client.get("/api/virustotal/vt-fail").json()
    assert body["status"] == "failed"
    assert body["message"] == "quota exceeded"
    assert body["app_id"] == "abc123"


def test_get_vt_report_returns_nested_structure(test_client, tmp_output_dir):
    import json
    payload = {
        "data": {
            "attributes": {
                "last_analysis_stats": {
                    "malicious": 3,
                    "suspicious": 1,
                    "harmless": 60,
                }
            }
        }
    }
    out_dir = tmp_output_dir / "com.example.test" / "com.example.test-1.0_original"
    with open(out_dir / "virustotal_report.json", "w") as f:
        json.dump(payload, f)

    body = test_client.get("/api/apps/abc123/virustotal").json()
    assert body == payload
    assert body["data"]["attributes"]["last_analysis_stats"]["malicious"] == 3
