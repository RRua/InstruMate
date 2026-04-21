"""Classification API router -- trigger and retrieve APK security classification."""

import json
import logging
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from api.models import AnalysisStatus, JobStatus
from api.job_store import job_store
from api.app_registry import registry

from pymate.classification.metrics_extractor import MetricsExtractor
from pymate.classification.llm_classifier import LLMClassifier

logger = logging.getLogger(__name__)
router = APIRouter()


def _run_classification(job_id: str, app_id: str, output_dir: str, model: str):
    """Background task: extract metrics and run LLM classification."""
    try:
        job_store.update(job_id, status=AnalysisStatus.RUNNING, message="Extracting security metrics...")

        # Stage 1 -- Metrics extraction
        extractor = MetricsExtractor(output_dir)
        metrics = extractor.extract_and_save()

        job_store.update(job_id, message="Running LLM classification...")

        # Stage 2 -- LLM classification
        classifier = LLMClassifier(model=model)
        classifier.classify_and_save(metrics, output_dir)

        job_store.update(job_id, status=AnalysisStatus.COMPLETED, message="Classification complete")

    except Exception as e:
        logger.exception("Classification failed for app %s", app_id)
        job_store.update(job_id, status=AnalysisStatus.FAILED, message=f"Classification failed: {e}")


@router.post("/apps/{app_id}/classify", response_model=JobStatus)
async def trigger_classification(
    app_id: str,
    background_tasks: BackgroundTasks,
    model: str = Query(default=None, description="Ollama model name (default: from env)"),
):
    """Trigger security classification for an analyzed app.

    Runs metrics extraction (Stage 1) and LLM classification (Stage 2)
    as a background task. Returns a job ID for polling status.
    """
    output_dir = registry.get_output_dir(app_id)
    if output_dir is None:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")

    if not os.path.isfile(os.path.join(output_dir, "app.json")):
        raise HTTPException(
            status_code=400,
            detail="App has not been analyzed yet",
        )

    job_id = str(uuid.uuid4())
    job = job_store.create(
        job_id=job_id,
        status=AnalysisStatus.PENDING,
        message="Classification queued",
        app_id=app_id,
        job_type="classification",
    )

    effective_model = model or os.environ.get("OLLAMA_MODEL", "mistral")
    background_tasks.add_task(
        _run_classification, job_id, app_id, output_dir, effective_model
    )

    return job


@router.get("/classify/{job_id}", response_model=JobStatus)
async def get_classification_job_status(job_id: str):
    """Poll classification job status."""
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@router.get("/apps/{app_id}/classification")
async def get_classification_result(app_id: str):
    """Get cached classification result from classification.json."""
    output_dir = registry.get_output_dir(app_id)
    if output_dir is None:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")

    path = os.path.join(output_dir, "classification.json")
    if not os.path.isfile(path):
        raise HTTPException(
            status_code=404,
            detail="Classification not available. Trigger classification first via POST /api/apps/{app_id}/classify",
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/apps/{app_id}/metrics")
async def get_security_metrics(app_id: str):
    """Get extracted security metrics from security_metrics.json."""
    output_dir = registry.get_output_dir(app_id)
    if output_dir is None:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")

    path = os.path.join(output_dir, "security_metrics.json")
    if not os.path.isfile(path):
        raise HTTPException(
            status_code=404,
            detail="Security metrics not available. Trigger classification first via POST /api/apps/{app_id}/classify",
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
