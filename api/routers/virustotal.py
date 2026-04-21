"""VirusTotal API router -- submit APKs and retrieve VT scan reports."""

import json
import logging
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from api.models import AnalysisStatus, JobStatus
from api.job_store import job_store
from api.app_registry import registry
from api.routers.apps import _find_apk_file
from pymate.virustotal import VTScanner

logger = logging.getLogger(__name__)
router = APIRouter()


def _run_vt_scan(job_id: str, app_id: str, apk_path: str, output_dir: str):
    """Background task: upload APK to VirusTotal and save report."""
    try:
        job_store.update(job_id, status=AnalysisStatus.RUNNING, message="Uploading to VirusTotal...")

        scanner = VTScanner()
        scanner.scan_and_save(apk_path, output_dir)

        job_store.update(job_id, status=AnalysisStatus.COMPLETED, message="VirusTotal scan complete")

    except Exception as e:
        logger.exception("VirusTotal scan failed for app %s", app_id)
        job_store.update(job_id, status=AnalysisStatus.FAILED, message=f"VirusTotal scan failed: {e}")


@router.post("/apps/{app_id}/virustotal", response_model=JobStatus)
async def submit_to_virustotal(
    app_id: str,
    background_tasks: BackgroundTasks,
):
    """Submit an APK to VirusTotal for scanning.

    Runs as a background task. Returns a job ID for polling status.
    """
    output_dir = registry.get_output_dir(app_id)
    if output_dir is None:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")

    if not os.environ.get("VT_API_KEY", ""):
        raise HTTPException(
            status_code=400,
            detail="VT_API_KEY environment variable is not configured",
        )

    apk_path = _find_apk_file(output_dir)
    if apk_path is None:
        raise HTTPException(
            status_code=400,
            detail="No APK file found for this app",
        )

    job_id = str(uuid.uuid4())
    job = job_store.create(
        job_id=job_id,
        status=AnalysisStatus.PENDING,
        message="VirusTotal scan queued",
        app_id=app_id,
        job_type="virustotal",
    )

    background_tasks.add_task(_run_vt_scan, job_id, app_id, apk_path, output_dir)

    return job


@router.get("/virustotal/{job_id}", response_model=JobStatus)
async def get_vt_job_status(job_id: str):
    """Poll VirusTotal scan job status."""
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@router.get("/apps/{app_id}/virustotal")
async def get_vt_report(app_id: str):
    """Get cached VirusTotal report from virustotal_report.json."""
    output_dir = registry.get_output_dir(app_id)
    if output_dir is None:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")

    path = os.path.join(output_dir, "virustotal_report.json")
    if not os.path.isfile(path):
        raise HTTPException(
            status_code=404,
            detail="VirusTotal report not available. Submit the app first via POST /api/apps/{app_id}/virustotal",
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
