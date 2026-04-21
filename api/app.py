import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.routers import health, analyze, apps, variants, classify, virustotal
from api.middleware import APIKeyMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

OUTPUT_DIR = os.environ.get("INSTRUMATE_OUTPUT_DIR", "./output")
TMP_DIR = os.environ.get("INSTRUMATE_TMP_DIR", "./tmp")
UPLOAD_DIR = os.environ.get("INSTRUMATE_UPLOAD_DIR", "./data/uploads")
WWWREPORT_DIR = os.environ.get("INSTRUMATE_WWWREPORT_DIR", "/opt/wwwreport-build")


@asynccontextmanager
async def lifespan(app: FastAPI):
    for d in [OUTPUT_DIR, TMP_DIR, UPLOAD_DIR]:
        os.makedirs(d, exist_ok=True)
    yield


app = FastAPI(
    title="InstruMate API",
    description=(
        "Android APK Static Analysis and Instrumentation Platform. "
        "Upload APKs, run static analysis, create instrumented variants, "
        "and browse results."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(APIKeyMiddleware)

# API routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(analyze.router, prefix="/api", tags=["Analysis"])
app.include_router(apps.router, prefix="/api", tags=["Apps"])
app.include_router(variants.router, prefix="/api", tags=["Variants"])
app.include_router(classify.router, prefix="/api", tags=["Classification"])
app.include_router(virustotal.router, prefix="/api", tags=["VirusTotal"])


# Serve React frontend if the build directory exists
if os.path.isdir(WWWREPORT_DIR):
    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(os.path.join(WWWREPORT_DIR, "index.html"))

    app.mount(
        "/",
        StaticFiles(directory=WWWREPORT_DIR, html=True),
        name="frontend",
    )
