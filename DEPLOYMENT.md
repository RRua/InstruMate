# InstruMate — Deployment & Usage Guide

InstruMate is an Android APK static-analysis and instrumentation platform. It runs as a single FastAPI service that also serves a React frontend. LLM-assisted classification is delegated to an **external** Ollama-compatible API (configured via `.env`), so no local model server is required.

---

## 1. Prerequisites

- Docker 24+ and Docker Compose v2
- ~5 GB free disk (Java 8 + 17, apktool, dex2jar, APKEditor)
- Port `8000` (API + UI) free
- An Ollama-compatible endpoint reachable from the container (only required if you want LLM classification)
- Optional: a VirusTotal API key (only required for VirusTotal submissions / lookups)

---

## 2. Quick start (Docker Compose)

```bash
git clone <this repo>
cd InstruMate

# Create your local config from the template and fill in secrets
cp .env.example .env
$EDITOR .env            # set OLLAMA_URL, OLLAMA_BEARER_TOKEN, VT_API_KEY, etc.

# Build images and start the stack in the background
docker compose up -d --build

# Tail logs while it warms up
docker compose logs -f instrumate
```

`.env` is git-ignored; `.env.example` is the committed template. Never put secrets in `docker-compose.yml` or anywhere else that gets committed.

First build takes several minutes (Maven build of the Java analyzer, npm install for the React frontend, Ubuntu base + JDK 8/17 + tool downloads).

When healthy:

- Web UI:     http://localhost:8000/
- API docs:   http://localhost:8000/docs
- Health:     http://localhost:8000/api/health

### LLM backend (external)

InstruMate calls an Ollama-compatible HTTP API for classification — it does **not** run a local model server. Relevant `.env` keys:

- `OLLAMA_URL` — endpoint URL (empty = classification disabled)
- `OLLAMA_MODEL` — model name to request (default `mistral`)
- `OLLAMA_BEARER_TOKEN` — sent as `Authorization: Bearer <token>` if set

If the endpoint is unreachable or unset, classification jobs return safe defaults with `confidence=0.0`; static analysis, variants, and VirusTotal continue to work.

### Stopping / resetting

```bash
docker compose down              # stop the container, keep data
docker compose down -v           # stop and wipe the instrumate-data volume
```

---

## 3. Configuration

Configuration comes from two places:

- **`.env`** (git-ignored) — secrets and environment-specific values. Start from `.env.example`.
- **`docker-compose.yml`** — non-secret operational defaults (paths, worker count, log level, upload size).

### Secrets (from `.env`)

| Variable | Purpose |
|---|---|
| `OLLAMA_URL` | External Ollama-compatible endpoint. Empty disables classification. |
| `OLLAMA_MODEL` | Model name to request from the endpoint. |
| `OLLAMA_BEARER_TOKEN` | Optional `Authorization: Bearer <token>`. Leave empty if the endpoint is open. |
| `VT_API_KEY` | VirusTotal API key. Empty disables VT. |
| `INSTRUMATE_API_KEY` | If set, all `/api/*` requests must send `X-API-Key: <value>`. |

### Operational defaults (in `docker-compose.yml`)

| Variable | Default | Purpose |
|---|---|---|
| `INSTRUMATE_OUTPUT_DIR` | `/data/output` | CSV/JSON analysis outputs |
| `INSTRUMATE_TMP_DIR` | `/data/tmp` | Scratch space for tools |
| `INSTRUMATE_UPLOAD_DIR` | `/data/uploads` | Uploaded APKs |
| `INSTRUMATE_TOOLS_DIR` | `/opt/tools` | apktool, APKEditor, dex2jar |
| `INSTRUMATE_INPUT_DIR` | `/app/input` | Read-only inputs (api-jar, etc.) |
| `JAVA_HOME` / `JDK8_HOME` | `/opt/java-17`, `/opt/java-8` | JDK selection |
| `WORKERS` | `2` | uvicorn worker count |
| `LOG_LEVEL` | `info` | uvicorn log level |
| `MAX_UPLOAD_SIZE` | `209715200` | Max APK upload size in bytes (default 200 MB) |

### Securing the API

Set `INSTRUMATE_API_KEY` in `.env` to a strong random string, restart, and pass `X-API-Key: <key>` on every API request.

---

## 4. Using the platform

### Via the web UI

1. Open http://localhost:8000/.
2. Upload an APK on the upload page (or drop one into `./input/` before starting; it's mounted read-only at `/app/input`).
3. Wait for analysis to complete.
4. Browse results: app list → app detail → permissions, activities, services, call graph.
5. Optional: trigger LLM classification, generate instrumented variants, or submit to VirusTotal from the app detail view.

### Via the API

The API is documented at `/docs` (Swagger) and `/redoc`. Common endpoints:

```bash
# Health
curl http://localhost:8000/api/health

# Upload + analyze an APK (returns a job id)
curl -F "file=@app-debug.apk" http://localhost:8000/api/analyze

# Poll job status
curl http://localhost:8000/api/analyze/<job_id>

# List analyzed apps (paginated)
curl "http://localhost:8000/api/apps?page=1&page_size=20"

# Get full analysis for a single app
curl http://localhost:8000/api/apps/<app_id>/analysis

# Trigger classification (LLM)
curl -X POST http://localhost:8000/api/apps/<app_id>/classify

# Generate instrumented variants
curl -X POST http://localhost:8000/api/apps/<app_id>/variants

# Submit to VirusTotal
curl -X POST http://localhost:8000/api/apps/<app_id>/virustotal

# Download original APK / export results
curl -OJ http://localhost:8000/api/apps/<app_id>/download
curl -OJ http://localhost:8000/api/apps/<app_id>/export
```

If `INSTRUMATE_API_KEY` is set, add `-H "X-API-Key: <key>"` to every call.

---

## 5. Data persistence

One named volume holds all state:

- `instrumate-data` — uploaded APKs, analysis outputs, scratch, generated variants

Back up with:

```bash
docker run --rm -v instrumate_instrumate-data:/data -v "$PWD":/backup \
  alpine tar czf /backup/instrumate-data.tgz -C /data .
```

---

## 6. Production notes

- **Reverse proxy**: front the container with nginx/Caddy/Traefik for TLS, real client IPs, and rate limiting. The app listens on plain HTTP on `:8000`.
- **CORS**: `api/app.py` currently sets `allow_origins=["*"]`. Tighten this before exposing the API to the public internet.
- **API key**: always set `INSTRUMATE_API_KEY` in any deployment reachable beyond localhost.
- **Workers**: bump `WORKERS` for higher concurrency; analysis jobs are CPU- and I/O-heavy, so size by core count.
- **Resources**: APK analysis can spike memory (Java decompilers); give the container at least 4 GB.
- **Upload size**: raise `MAX_UPLOAD_SIZE` if you need to ingest APKs larger than 200 MB; also raise the matching limit in any reverse proxy.
- **Logs**: `docker compose logs -f instrumate` for the API; analysis tool output is captured per-job under `/data/output`.
- **Secret hygiene**: `.env` is git-ignored. If you ever commit a secret, rotate it immediately — history rewriting does not invalidate leaked keys.

---

## 7. Local development (no Docker)

The container is the supported path. For bare-metal dev, see the install notes in `README.md` (Python 3.10, JDK 8 + 17, apktool, dex2jar, APKEditor on `INSTRUMATE_TOOLS_DIR`), then export the same env vars from `.env` and:

```bash
python3.10 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
set -a && source .env && set +a        # load .env into the shell
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload

# Frontend (separate terminal)
cd wwwreport
npm install --legacy-peer-deps
npm start          # dev server on :3000, proxies API to :8000
```

---

## 8. Troubleshooting

| Symptom | Check |
|---|---|
| `/api/health` returns 401/403 | `INSTRUMATE_API_KEY` is set — pass `X-API-Key` header |
| Classification always returns defaults | `OLLAMA_URL` unset in `.env`, or `curl -H "Authorization: Bearer $OLLAMA_BEARER_TOKEN" $OLLAMA_URL/api/tags` from inside the container fails |
| Analysis job stuck in `pending` | `docker compose logs instrumate` for tool errors; check `/data/tmp` disk space |
| Build fails on `npm install` | Network/proxy; rerun `docker compose build --no-cache instrumate` |
| Build fails on Maven stage | Confirm `pom.xml` and `src/` are intact; rerun `--no-cache` |
| Port 8000 in use | Change the host-side port mapping in `docker-compose.yml` (e.g. `"18000:8000"`) |
| Frontend loads but API calls 404 | Confirm UI is on `:8000` (served by FastAPI), not the React dev server on `:3000` |
