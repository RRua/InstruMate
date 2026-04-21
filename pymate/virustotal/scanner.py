"""VirusTotal API v3 client for APK scanning."""

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

VT_BASE_URL = "https://www.virustotal.com/api/v3"
LARGE_FILE_THRESHOLD = 32 * 1024 * 1024  # 32 MB


class VTScanner:
    """Wraps VirusTotal API v3 for file upload, analysis polling, and report retrieval."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("VT_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "VirusTotal API key is required. "
                "Set VT_API_KEY environment variable or pass api_key."
            )
        self._headers = {"x-apikey": self.api_key}

    def upload_file(self, file_path: str) -> str:
        """Upload a file to VirusTotal and return the analysis ID.

        For files >32 MB, fetches a special upload URL first.
        """
        file_size = os.path.getsize(file_path)

        if file_size > LARGE_FILE_THRESHOLD:
            upload_url = self._get_large_upload_url()
        else:
            upload_url = f"{VT_BASE_URL}/files"

        logger.info("Uploading %s (%d bytes) to VirusTotal", file_path, file_size)
        with open(file_path, "rb") as f:
            resp = httpx.post(
                upload_url,
                headers=self._headers,
                files={"file": (os.path.basename(file_path), f)},
                timeout=60.0,
            )
        resp.raise_for_status()
        analysis_id = resp.json()["data"]["id"]
        logger.info("Upload complete — analysis ID: %s", analysis_id)
        return analysis_id

    def _get_large_upload_url(self) -> str:
        """Get a special upload URL for files >32 MB."""
        resp = httpx.get(
            f"{VT_BASE_URL}/files/upload_url",
            headers=self._headers,
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["data"]

    def get_analysis(self, analysis_id: str) -> dict:
        """Poll an analysis by ID. Returns the analysis attributes."""
        resp = httpx.get(
            f"{VT_BASE_URL}/analyses/{analysis_id}",
            headers=self._headers,
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["data"]["attributes"]

    def get_file_report(self, sha256: str) -> dict:
        """Fetch the full file report by SHA-256 hash."""
        resp = httpx.get(
            f"{VT_BASE_URL}/files/{sha256}",
            headers=self._headers,
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["data"]["attributes"]

    def scan_and_save(self, apk_path: str, output_dir: str) -> dict:
        """Upload file, wait for analysis, fetch report, and save to output_dir.

        Polls every 15 s with a 10-minute timeout.
        Returns the saved report dict.
        """
        # Compute SHA-256 before upload
        sha256 = self._sha256(apk_path)

        # Upload
        analysis_id = self.upload_file(apk_path)

        # Poll until completed (max 10 min)
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            analysis = self.get_analysis(analysis_id)
            status = analysis.get("status")
            logger.info("VT analysis %s — status: %s", analysis_id, status)
            if status == "completed":
                break
            time.sleep(15)
        else:
            raise TimeoutError(
                f"VirusTotal analysis {analysis_id} did not complete within 10 minutes"
            )

        # Fetch full file report
        file_report = self.get_file_report(sha256)
        stats = file_report.get("last_analysis_stats", {})
        results = file_report.get("last_analysis_results", {})

        detected = stats.get("malicious", 0) + stats.get("suspicious", 0)
        total = sum(stats.values())

        report = {
            "analysis_id": analysis_id,
            "sha256": sha256,
            "scan_date": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
            "detection_ratio": f"{detected}/{total}",
            "results": {
                engine: {
                    "category": info.get("category"),
                    "result": info.get("result"),
                }
                for engine, info in results.items()
            },
            "permalink": f"https://www.virustotal.com/gui/file/{sha256}",
        }

        # Save
        report_path = os.path.join(output_dir, "virustotal_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info("VT report saved to %s", report_path)

        return report

    @staticmethod
    def _sha256(file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
