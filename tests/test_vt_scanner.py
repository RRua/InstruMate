"""Tests for VTScanner with mocked HTTP calls."""

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from pymate.virustotal.scanner import VTScanner


@pytest.fixture
def scanner():
    return VTScanner(api_key="test-key-123")


def test_scanner_requires_api_key():
    with pytest.raises(ValueError, match="API key"):
        VTScanner(api_key="")


def test_scanner_init(scanner):
    assert scanner.api_key == "test-key-123"
    assert scanner._headers["x-apikey"] == "test-key-123"


@patch("pymate.virustotal.scanner.httpx.post")
def test_upload_file(mock_post, scanner, tmp_path):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"data": {"id": "analysis-abc"}}
    mock_post.return_value = mock_resp

    apk = tmp_path / "test.apk"
    apk.write_bytes(b"PK" + b"\x00" * 100)

    analysis_id = scanner.upload_file(str(apk))
    assert analysis_id == "analysis-abc"
    mock_post.assert_called_once()


@patch("pymate.virustotal.scanner.httpx.get")
def test_get_analysis(mock_get, scanner):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "data": {"attributes": {"status": "completed"}}
    }
    mock_get.return_value = mock_resp

    result = scanner.get_analysis("analysis-abc")
    assert result["status"] == "completed"


@patch("pymate.virustotal.scanner.time.sleep", return_value=None)
@patch("pymate.virustotal.scanner.httpx.get")
@patch("pymate.virustotal.scanner.httpx.post")
def test_scan_and_save(mock_post, mock_get, mock_sleep, scanner, tmp_path):
    """Full scan_and_save flow with mocked HTTP."""
    # Upload response
    upload_resp = MagicMock()
    upload_resp.raise_for_status = MagicMock()
    upload_resp.json.return_value = {"data": {"id": "analysis-xyz"}}
    mock_post.return_value = upload_resp

    # Analysis poll (completed on first call) + file report
    analysis_resp = MagicMock()
    analysis_resp.raise_for_status = MagicMock()
    analysis_resp.json.return_value = {
        "data": {"attributes": {"status": "completed"}}
    }

    file_resp = MagicMock()
    file_resp.raise_for_status = MagicMock()
    file_resp.json.return_value = {
        "data": {
            "attributes": {
                "last_analysis_stats": {
                    "malicious": 2,
                    "suspicious": 1,
                    "undetected": 60,
                    "harmless": 0,
                },
                "last_analysis_results": {
                    "EngineA": {"category": "malicious", "result": "Trojan"},
                    "EngineB": {"category": "undetected", "result": None},
                },
            }
        }
    }

    mock_get.side_effect = [analysis_resp, file_resp]

    apk = tmp_path / "app.apk"
    apk.write_bytes(b"PK" + b"\x00" * 50)

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    report = scanner.scan_and_save(str(apk), str(output_dir))

    assert report["stats"]["malicious"] == 2
    assert "3/" in report["detection_ratio"]
    assert "EngineA" in report["results"]

    # Verify file was saved
    report_path = output_dir / "virustotal_report.json"
    assert report_path.exists()
    with open(report_path) as f:
        saved = json.load(f)
    assert saved["analysis_id"] == "analysis-xyz"


@patch("pymate.virustotal.scanner.time.sleep", return_value=None)
@patch("pymate.virustotal.scanner.time.monotonic")
@patch("pymate.virustotal.scanner.httpx.get")
@patch("pymate.virustotal.scanner.httpx.post")
def test_scan_timeout(mock_post, mock_get, mock_monotonic, mock_sleep, scanner, tmp_path):
    """Verify TimeoutError when analysis never completes."""
    upload_resp = MagicMock()
    upload_resp.raise_for_status = MagicMock()
    upload_resp.json.return_value = {"data": {"id": "analysis-slow"}}
    mock_post.return_value = upload_resp

    # Always return queued
    analysis_resp = MagicMock()
    analysis_resp.raise_for_status = MagicMock()
    analysis_resp.json.return_value = {
        "data": {"attributes": {"status": "queued"}}
    }
    mock_get.return_value = analysis_resp

    # Simulate time passing beyond deadline
    mock_monotonic.side_effect = [0, 0, 601]

    apk = tmp_path / "timeout.apk"
    apk.write_bytes(b"PK" + b"\x00" * 50)

    with pytest.raises(TimeoutError):
        scanner.scan_and_save(str(apk), str(tmp_path))
