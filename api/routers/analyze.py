import os
import uuid
import threading
import logging

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from api.models import JobStatus, AnalysisStatus
from api.job_store import job_store
from api.app_registry import registry

router = APIRouter()
logger = logging.getLogger("api.analyze")

# Serialize analysis runs to avoid InstruMateLog singleton conflicts
_analysis_lock = threading.Lock()

OUTPUT_DIR = os.environ.get("INSTRUMATE_OUTPUT_DIR", "./output")
TMP_DIR = os.environ.get("INSTRUMATE_TMP_DIR", "./tmp")
UPLOAD_DIR = os.environ.get("INSTRUMATE_UPLOAD_DIR", "./data/uploads")
TOOLS_DIR = os.environ.get("INSTRUMATE_TOOLS_DIR", "./tools")
INPUT_DIR = os.environ.get("INSTRUMATE_INPUT_DIR", "./input")

MAX_UPLOAD_SIZE = int(os.environ.get("MAX_UPLOAD_SIZE", str(200 * 1024 * 1024)))


def _run_analysis(job_id: str, apk_path: str, analyzer_keys: list[str]):
    """Run static analysis synchronously in a background thread."""
    with _analysis_lock:
        try:
            job_store.update(job_id, status=AnalysisStatus.RUNNING)

            # Lazy imports to avoid device-dependent import chains
            from pymate.common.app import App
            from pymate.instrumate.instrumate import InstruMate, STATIC_ANALYZERS

            java_home = os.environ.get("JAVA_HOME")
            jdk8_home = os.environ.get("JDK8_HOME")

            app = App(apk_base_path=apk_path)

            static_analyzers = []
            for key in analyzer_keys:
                if key in STATIC_ANALYZERS:
                    static_analyzers.append(STATIC_ANALYZERS[key])
                else:
                    logger.warning(f"Unknown analyzer: {key}")

            if not static_analyzers:
                raise ValueError(
                    f"No valid analyzers found in: {analyzer_keys}. "
                    f"Available: {list(STATIC_ANALYZERS.keys())}"
                )

            instrumate = InstruMate(
                config_dir=INPUT_DIR,
                tmp_dir=TMP_DIR,
                output_dir=OUTPUT_DIR,
                tools_dir=TOOLS_DIR,
                original_apps=[app],
                static_analyzers=static_analyzers,
                variant_makers=[],
                append_to_existing=True,
                jdk8_path=jdk8_home,
                jdk_path=java_home,
            )
            instrumate.make_variants()

            registry.refresh()
            job_store.update(
                job_id,
                status=AnalysisStatus.COMPLETED,
                app_id=app.get_app_id(),
                message=f"Analysis completed for {app.get_package_name()}",
            )
        except Exception as e:
            logger.exception(f"Analysis failed for job {job_id}")
            job_store.update(
                job_id,
                status=AnalysisStatus.FAILED,
                message=str(e),
            )


@router.post("/analyze", response_model=JobStatus)
async def analyze_apk(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    analyzers: str = "basic,content++",
):
    """Upload an APK file and start static analysis.

    **analyzers** -- comma-separated list. Available:
    `basic`, `callgraph`, `andex`, `content`, `content+`, `content++`,
    `possible_modifications`.

    Returns a job ID; poll `GET /api/analyze/{job_id}` for status.
    """
    if not file.filename or not file.filename.endswith(".apk"):
        raise HTTPException(status_code=400, detail="File must be an .apk")

    job_id = str(uuid.uuid4())
    upload_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(upload_dir, exist_ok=True)
    apk_path = os.path.join(upload_dir, file.filename)

    # Stream upload in chunks with size limit
    total_size = 0
    with open(apk_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)  # 1 MB chunks
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_UPLOAD_SIZE:
                f.close()
                os.remove(apk_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds maximum upload size of {MAX_UPLOAD_SIZE} bytes",
                )
            f.write(chunk)

    analyzer_keys = [a.strip() for a in analyzers.split(",")]

    job = job_store.create(
        job_id=job_id,
        status=AnalysisStatus.PENDING,
        message=f"Queued analysis with analyzers: {analyzer_keys}",
        job_type="analysis",
    )

    background_tasks.add_task(_run_analysis, job_id, apk_path, analyzer_keys)
    return job


@router.get("/analyze/{job_id}", response_model=JobStatus)
async def get_analysis_status(job_id: str):
    """Check the status of an analysis job."""
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
