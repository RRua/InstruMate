import os
import sys
import shutil

import httpx
from fastapi import APIRouter
from api.models import HealthResponse

router = APIRouter()

TOOLS_DIR = os.environ.get("INSTRUMATE_TOOLS_DIR", "./tools")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check system health: Java, tools, Python, available analyzers/makers."""
    java_available = shutil.which("java") is not None
    jdk8_path = os.environ.get("JDK8_HOME", "")
    jdk8_available = os.path.isdir(jdk8_path) if jdk8_path else False

    misc_dir = os.path.join(TOOLS_DIR, "misc")
    tools_check = {
        "apktool": os.path.isfile(os.path.join(misc_dir, "apktool.jar")),
        "apkeditor": os.path.isfile(os.path.join(misc_dir, "APKEditor.jar")),
        "apksigner": os.path.isfile(os.path.join(misc_dir, "apksigner.jar")),
        "zipalign": shutil.which("zipalign") is not None,
        "dex2jar": os.path.isdir(os.path.join(misc_dir, "dex-tools")),
    }

    analyzers = [
        "basic", "callgraph", "andex",
        "content", "content+", "content++",
        "possible_modifications",
    ]
    makers = [
        "zip", "apkeditor", "apktool", "acvtool",
        "androlog", "aspectj", "fridagadget", "imcoverage",
    ]

    # Ollama connectivity check
    ollama_url = os.environ.get("OLLAMA_URL", "http://ollama:11434")
    ollama_available = False
    try:
        resp = httpx.get(f"{ollama_url}/api/tags", timeout=5.0)
        ollama_available = resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException, Exception):
        pass

    return HealthResponse(
        status="ok",
        java_available=java_available,
        jdk8_available=jdk8_available,
        tools_available=tools_check,
        python_version=sys.version,
        analyzers_available=analyzers,
        variant_makers_available=makers,
        ollama_available=ollama_available,
        virustotal_configured=bool(os.environ.get("VT_API_KEY", "")),
        auth_enabled=bool(os.environ.get("INSTRUMATE_API_KEY", "")),
    )
