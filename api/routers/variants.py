import os
import threading
import logging
import uuid
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException
from api.models import VariantCreateRequest, JobStatus, AnalysisStatus, AppSummary
from api.job_store import job_store
from api.app_registry import registry

router = APIRouter()
logger = logging.getLogger("api.variants")

_variant_lock = threading.Lock()

OUTPUT_DIR = os.environ.get("INSTRUMATE_OUTPUT_DIR", "./output")
TMP_DIR = os.environ.get("INSTRUMATE_TMP_DIR", "./tmp")
TOOLS_DIR = os.environ.get("INSTRUMATE_TOOLS_DIR", "./tools")
INPUT_DIR = os.environ.get("INSTRUMATE_INPUT_DIR", "./input")


def _run_variant_creation(
    job_id: str, app_id: str, maker_keys: list[str], spec_levels: list[str]
):
    """Create instrumented variants in a background thread."""
    with _variant_lock:
        try:
            job_store.update(job_id, status=AnalysisStatus.RUNNING)

            from pymate.common.app import App
            from pymate.instrumate.instrumate import (
                InstruMate,
                STATIC_ANALYZERS,
                parse_variant_makers,
            )

            app_dir = registry.get_output_dir(app_id)
            if app_dir is None:
                raise ValueError(f"App {app_id} not found in output directory")

            app = App.load_from_dir(app_dir)

            java_home = os.environ.get("JAVA_HOME")
            jdk8_home = os.environ.get("JDK8_HOME")

            static_analyzers = [
                STATIC_ANALYZERS["basic"],
                STATIC_ANALYZERS["content++"],
            ]
            variant_makers = parse_variant_makers(maker_keys)

            instrumate = InstruMate(
                config_dir=INPUT_DIR,
                tmp_dir=TMP_DIR,
                output_dir=OUTPUT_DIR,
                tools_dir=TOOLS_DIR,
                original_apps=[app],
                static_analyzers=static_analyzers,
                variant_makers=variant_makers,
                append_to_existing=True,
                jdk8_path=jdk8_home,
                jdk_path=java_home,
                specs_modify_manifest="manifest" in spec_levels,
                specs_modify_resources="resources" in spec_levels,
                specs_modify_behaviour="instrumentation" in spec_levels,
            )
            n_variants = instrumate.make_variants() or 0

            registry.refresh()
            job_store.update(
                job_id,
                status=AnalysisStatus.COMPLETED,
                message=(
                    f"Produced {n_variants} variant(s) for "
                    f"{app.get_package_name()}"
                ),
            )
        except Exception as e:
            logger.exception(f"Variant creation failed for job {job_id}")
            job_store.update(
                job_id,
                status=AnalysisStatus.FAILED,
                message=str(e),
            )


@router.post("/apps/{app_id}/variants", response_model=JobStatus)
async def create_variants(
    app_id: str,
    request: VariantCreateRequest,
    background_tasks: BackgroundTasks,
):
    """Create instrumented variants for an analyzed app.

    **variant_makers** -- list of makers: `zip`, `apkeditor`, `apktool`,
    `acvtool`, `androlog`, `aspectj`, `fridagadget`, `imcoverage`.

    **variant_specs** -- modification levels: `signature`, `manifest`,
    `resources`, `instrumentation`.
    """
    app_dir = registry.get_output_dir(app_id)
    if app_dir is None:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")

    job_id = str(uuid.uuid4())
    job = job_store.create(
        job_id=job_id,
        status=AnalysisStatus.PENDING,
        app_id=app_id,
        message=f"Queued variant creation: makers={request.variant_makers}",
        job_type="variants",
    )

    background_tasks.add_task(
        _run_variant_creation,
        job_id,
        app_id,
        request.variant_makers,
        request.variant_specs,
    )
    return job


@router.get("/apps/{app_id}/variants", response_model=List[AppSummary])
async def list_variants(app_id: str):
    """List all instrumented variants for a given app."""
    entry = registry.get(app_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")

    target_package = entry["app_data"].get("package_name")
    if not target_package:
        return []

    variants = []
    pkg_dir = os.path.join(OUTPUT_DIR, target_package)
    if os.path.isdir(pkg_dir):
        for vdir_name in os.listdir(pkg_dir):
            vdir = os.path.join(pkg_dir, vdir_name)
            app_json = os.path.join(vdir, "app.json")
            if os.path.isfile(app_json):
                import json
                with open(app_json, "r") as f:
                    data = json.load(f)
                if data.get("variant_info") is not None:
                    variants.append(
                        AppSummary(
                            app_id=data.get("app_id", "unknown"),
                            package_name=data.get("package_name", "unknown"),
                            version_name=data.get("app_version_name"),
                            version_code=data.get("app_version_code"),
                            is_variant=True,
                            output_dir=vdir,
                        )
                    )
    return variants
