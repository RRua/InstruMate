"""Tests for /api/analyze endpoints."""

import io


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
