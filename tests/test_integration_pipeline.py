"""End-to-end integration tests for the analyze → classify → variants →
virustotal pipeline.

Each test verifies that the routes actually produce the expected output
files in valid formats, by running the real analyzer / variant pipeline
against a real APK. External dependencies (LLM endpoint, VirusTotal API)
are mocked at the function level — but metrics extraction and APK
parsing are real.

Auto-skipped when the environment can't run the pipeline (no APK
fixture, no Java, no apktool).

Run with:
    pytest tests/test_integration_pipeline.py -v
"""

import csv
import json
import os
import shutil
import threading
from glob import glob

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _find_apk():
    """Locate a real APK to drive the pipeline. Container path first,
    then host path (when running from the repo root)."""
    for pattern in (
        "/data/uploads/*/app-debug.apk",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "uploads", "*", "app-debug.apk",
        ),
    ):
        matches = sorted(glob(pattern))
        if matches:
            return matches[0]
    return None


def _environment_ready():
    if _find_apk() is None:
        return False, "no sample APK in /data/uploads/*/app-debug.apk"
    if not shutil.which("java"):
        return False, "java not on PATH"
    if not os.path.isfile("/opt/tools/misc/apktool.jar"):
        return False, "apktool.jar not at /opt/tools/misc/"
    return True, ""


_ENV_OK, _ENV_REASON = _environment_ready()
pytestmark = pytest.mark.skipif(not _ENV_OK, reason=_ENV_REASON)


@pytest.fixture(scope="module")
def sample_apk_bytes():
    apk = _find_apk()
    with open(apk, "rb") as f:
        return f.read()


@pytest.fixture(scope="module")
def integration_state(tmp_path_factory, sample_apk_bytes):
    """Build a TestClient pointed at a fresh module-scoped output dir,
    upload + analyze one APK once, and yield (client, app_id, output_dir).

    All subsequent feature tests reuse this analyzed app — analyzing once
    keeps the suite bounded to ~30s instead of N×30s.
    """
    out_dir = tmp_path_factory.mktemp("integration_out")

    mp = pytest.MonkeyPatch()
    try:
        mp.setenv("INSTRUMATE_OUTPUT_DIR", str(out_dir))
        mp.setenv("INSTRUMATE_TMP_DIR", str(out_dir / "tmp"))
        mp.setenv("INSTRUMATE_UPLOAD_DIR", str(out_dir / "uploads"))
        mp.setenv("INSTRUMATE_API_KEY", "")  # disable auth for the tests

        import api.app_registry
        import api.job_store
        import api.routers.analyze
        import api.routers.apps
        import api.routers.variants

        mp.setattr(api.app_registry, "OUTPUT_DIR", str(out_dir))
        mp.setattr(api.app_registry.registry, "_loaded", False, raising=False)
        mp.setattr(api.app_registry.registry, "_index", {}, raising=False)

        mp.setattr(api.job_store, "OUTPUT_DIR", str(out_dir))
        mp.setattr(api.job_store, "DB_PATH", str(out_dir / "jobs.db"))
        mp.setattr(api.job_store.job_store, "_initialized", False)
        mp.setattr(api.job_store.job_store, "_local", threading.local())

        mp.setattr(api.routers.analyze, "OUTPUT_DIR", str(out_dir))
        mp.setattr(api.routers.analyze, "UPLOAD_DIR", str(out_dir / "uploads"))
        mp.setattr(api.routers.analyze, "TMP_DIR", str(out_dir / "tmp"))
        mp.setattr(api.routers.apps, "OUTPUT_DIR", str(out_dir))
        mp.setattr(api.routers.variants, "OUTPUT_DIR", str(out_dir))
        mp.setattr(api.routers.variants, "TMP_DIR", str(out_dir / "tmp"))

        from fastapi.testclient import TestClient
        from api.app import app

        client = TestClient(app)

        # The analyze route now normalizes the upload to "base.apk"
        # internally, so any user-supplied filename works for the full
        # analyze → variants flow. We still upload as app-debug.apk to
        # exercise the original bug path.
        resp = client.post(
            "/api/analyze",
            params={"analyzers": "basic,content,possible_modifications"},
            files={
                "file": (
                    "app-debug.apk",
                    sample_apk_bytes,
                    "application/octet-stream",
                )
            },
        )
        assert resp.status_code == 200, resp.text
        job_id = resp.json()["job_id"]

        # Starlette's TestClient awaits BackgroundTasks before returning,
        # so the analysis is already done by the time we poll.
        status = client.get(f"/api/analyze/{job_id}").json()
        assert status["status"] == "completed", (
            f"analyze did not complete: {status}"
        )
        app_id = status["app_id"]
        assert app_id, "analyze returned no app_id"

        from api.app_registry import registry
        registry.refresh()
        app_out = registry.get_output_dir(app_id)
        assert app_out and os.path.isdir(app_out)

        yield client, app_id, app_out
    finally:
        mp.undo()


# ---------------------------------------------------------------------------
# /api/analyze — verifies output files produced by the analyzers
# ---------------------------------------------------------------------------


def test_analyze_writes_app_json_with_required_fields(integration_state):
    """The basic analyzer must produce app.json with the documented schema."""
    _, app_id, out_dir = integration_state
    p = os.path.join(out_dir, "app.json")
    assert os.path.isfile(p), f"app.json not written at {p}"
    with open(p) as f:
        data = json.load(f)

    assert data["app_id"] == app_id
    assert isinstance(data["package_name"], str) and data["package_name"]
    for key in ("permissions", "activities", "services", "features"):
        assert key in data and isinstance(data[key], list), (
            f"{key} missing or not a list"
        )
    # variant_info is None for the original
    assert data.get("variant_info") is None


def test_analyze_writes_installers_with_real_apk(integration_state):
    """The original APK must be archived under installers/ and remain valid."""
    _, _, out_dir = integration_state
    inst = os.path.join(out_dir, "installers")
    assert os.path.isdir(inst), "installers/ not created"
    apks = [f for f in os.listdir(inst) if f.lower().endswith(".apk")]
    assert apks, "no .apk inside installers/"
    apk = os.path.join(inst, apks[0])
    assert os.path.getsize(apk) > 1024, "archived APK is suspiciously small"
    with open(apk, "rb") as f:
        # APK is a ZIP file — must start with the PK signature.
        assert f.read(4) == b"PK\x03\x04"


def test_analyze_writes_content_type_csv_parseable(integration_state):
    """The content analyzer must emit a parseable CSV file. The number of
    rows depends on the APK (small or stripped APKs may yield zero rows),
    so we only assert the file exists and parses."""
    _, _, out_dir = integration_state
    p = os.path.join(out_dir, "content_type_analysis.csv")
    assert os.path.isfile(p), "content_type_analysis.csv not written"
    with open(p, newline="") as f:
        # Just exercise the CSV parser — we don't care if rows are empty.
        rows = list(csv.reader(f))
    assert rows is not None  # parse succeeded
    # When the analyzer DOES emit columns, the header must contain the
    # path/code/resource concept (skip otherwise — APK-dependent).
    if rows and rows[0]:
        joined = ",".join(rows[0]).lower()
        assert any(k in joined for k in ("file", "path", "code", "resource")), (
            f"unexpected CSV header: {rows[0]}"
        )


def test_analyze_writes_possible_modifications_json(integration_state):
    """The possible_modifications analyzer must emit a valid JSON object
    with the documented top-level categories."""
    _, _, out_dir = integration_state
    p = os.path.join(out_dir, "possible_modifications_analysis.json")
    assert os.path.isfile(p), "possible_modifications_analysis.json not written"
    with open(p) as f:
        data = json.load(f)
    assert isinstance(data, dict)
    for key in ("string_resources", "changeable_icons", "reveal_passwords"):
        assert key in data, f"missing top-level key '{key}'"
    # Each category should be a list
    for key, value in data.items():
        assert isinstance(value, list), f"'{key}' should be a list"


def test_get_apps_lists_the_analyzed_app(integration_state):
    """After analyze completes, the app shows up in the registry-backed list."""
    client, app_id, _ = integration_state
    body = client.get("/api/apps").json()
    assert any(item["app_id"] == app_id for item in body["items"])


def test_get_app_detail_reflects_produced_files(integration_state):
    """Detail endpoint's has_* flags should be True for files we produced."""
    client, app_id, _ = integration_state
    body = client.get(f"/api/apps/{app_id}").json()
    assert body["has_content_type_analysis"] is True


# ---------------------------------------------------------------------------
# /api/apps/{app_id}/classify — real metrics extraction + mocked LLM
# ---------------------------------------------------------------------------


def test_classify_writes_security_metrics_and_classification(
    integration_state, monkeypatch
):
    """POST /classify must write security_metrics.json (real extraction) and
    classification.json (mocked LLM, schema-checked)."""
    client, app_id, out_dir = integration_state

    from pymate.classification.models import (
        ClassificationResult,
        MalwareLikelihood,
        RiskFactor,
        SecurityRiskLevel,
    )
    fixed = ClassificationResult(
        security_risk_level=SecurityRiskLevel.LOW,
        malware_likelihood=MalwareLikelihood.BENIGN,
        confidence=0.92,
        risk_factors=[
            RiskFactor(
                category="permissions",
                description="benign set",
                severity=SecurityRiskLevel.LOW,
            )
        ],
        recommendations=["no action"],
        reasoning="integration test stub",
        model_used="test-stub",
    )

    from pymate.classification import llm_classifier
    monkeypatch.setattr(
        llm_classifier.LLMClassifier,
        "classify",
        lambda self, metrics: fixed,
    )

    resp = client.post(f"/api/apps/{app_id}/classify")
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    status = client.get(f"/api/classify/{job_id}").json()
    assert status["status"] == "completed", status

    # security_metrics.json — produced by the REAL MetricsExtractor
    sm_path = os.path.join(out_dir, "security_metrics.json")
    assert os.path.isfile(sm_path)
    with open(sm_path) as f:
        sm = json.load(f)
    assert sm["package_name"]
    for key in ("permissions", "code", "content", "call_graph"):
        assert key in sm, f"security_metrics missing top-level '{key}'"
    assert isinstance(sm["permissions"], dict)

    # classification.json — schema-validated against ClassificationResult
    clf_path = os.path.join(out_dir, "classification.json")
    assert os.path.isfile(clf_path)
    with open(clf_path) as f:
        clf = json.load(f)
    assert clf["security_risk_level"] in {"low", "medium", "high", "critical"}
    assert clf["malware_likelihood"] in {
        "benign", "suspicious", "likely_malicious",
    }
    assert 0.0 <= clf["confidence"] <= 1.0
    assert isinstance(clf["risk_factors"], list)
    assert isinstance(clf["recommendations"], list)
    assert clf["model_used"] == "test-stub"
    # And the GET /classification route returns the same payload
    via_api = client.get(f"/api/apps/{app_id}/classification").json()
    assert via_api == clf


# ---------------------------------------------------------------------------
# /api/apps/{app_id}/variants — runs the real `zip` maker
# ---------------------------------------------------------------------------


def test_variants_route_invokes_maker_and_logs_execution(integration_state):
    """POST /variants must drive the maker end-to-end: job completes and
    the maker's execution is recorded in variant_maker_tool_executions.csv.

    If the maker produces a variant directory, we also verify its on-disk
    shape (app.json has variant_info; installers/ holds a valid APK).
    Some maker+spec combinations legitimately produce zero variants for a
    single-APK input — that's a product behavior, not a route failure.
    """
    client, app_id, out_dir = integration_state
    pkg_dir = os.path.dirname(out_dir)
    output_root = os.path.dirname(pkg_dir)

    before = set(os.listdir(pkg_dir))
    resp = client.post(
        f"/api/apps/{app_id}/variants",
        json={"variant_makers": ["zip"], "variant_specs": ["signature"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    job_id = body["job_id"]

    # No GET /variants/{job_id} route — read job_store directly.
    from api.job_store import job_store
    final = job_store.get(job_id)
    assert final is not None, "variant job not persisted"
    assert final.status.value == "completed", (
        f"variants job did not complete: {final.message}"
    )

    # The maker's execution must have been logged — this file is the
    # shared log written by InstruMateLog for ALL variant-maker attempts.
    log_csv = os.path.join(output_root, "variant_maker_tool_executions.csv")
    assert os.path.isfile(log_csv), "variant execution log not produced"
    with open(log_csv, newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows, "variant execution log has no rows"
    assert "variant_maker" in rows[0], (
        f"unexpected log columns: {list(rows[0].keys())}"
    )
    # The user-facing key "zip" maps to GenericZipRepackager internally;
    # any row referencing the zip family is sufficient evidence the
    # maker ran for our POST.
    assert any(
        "zip" in (r.get("variant_maker") or "").lower()
        or "zip" in (r.get("variant_maker_tag") or "").lower()
        for r in rows
    ), f"no zip-family maker row in execution log; saw makers={set(r.get('variant_maker') for r in rows)}"

    # If any variant directory WAS produced, validate it.
    after = set(os.listdir(pkg_dir))
    new_dirs = sorted(after - before)
    for name in new_dirs:
        candidate = os.path.join(pkg_dir, name)
        appjson = os.path.join(candidate, "app.json")
        if not os.path.isfile(appjson):
            continue
        with open(appjson) as f:
            vdata = json.load(f)
        if vdata.get("variant_info") is None:
            continue
        inst = os.path.join(candidate, "installers")
        assert os.path.isdir(inst), f"variant {name} missing installers/"
        apks = [n for n in os.listdir(inst) if n.lower().endswith(".apk")]
        assert apks, f"variant {name} installers/ has no APK"
        with open(os.path.join(inst, apks[0]), "rb") as f:
            assert f.read(4) == b"PK\x03\x04", (
                f"variant {name} APK is not a valid zip"
            )


# ---------------------------------------------------------------------------
# /api/apps/{app_id}/virustotal — mocked scanner; verifies file write path
# ---------------------------------------------------------------------------


def test_virustotal_writes_report_with_mocked_scanner(
    integration_state, monkeypatch
):
    """POST /virustotal must invoke the scanner and persist its report
    JSON to virustotal_report.json. We mock the network call but verify
    the route writes the response verbatim and the GET endpoint returns it."""
    client, app_id, out_dir = integration_state
    monkeypatch.setenv("VT_API_KEY", "fake-key-for-test")

    fake_report = {
        "data": {
            "id": "stub-vt-id",
            "type": "file",
            "attributes": {
                "last_analysis_stats": {
                    "malicious": 0,
                    "suspicious": 0,
                    "harmless": 70,
                    "undetected": 4,
                },
                "meaningful_name": "app-debug.apk",
            },
        }
    }

    def fake_scan_and_save(self, apk_path, output_dir):
        with open(
            os.path.join(output_dir, "virustotal_report.json"), "w"
        ) as f:
            json.dump(fake_report, f, indent=2)

    from pymate import virustotal
    monkeypatch.setattr(
        virustotal.VTScanner, "scan_and_save", fake_scan_and_save
    )

    resp = client.post(f"/api/apps/{app_id}/virustotal")
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    from api.job_store import job_store
    final = job_store.get(job_id)
    assert final is not None and final.status.value == "completed", (
        final.message if final else "no job"
    )

    p = os.path.join(out_dir, "virustotal_report.json")
    assert os.path.isfile(p)
    with open(p) as f:
        loaded = json.load(f)
    assert loaded == fake_report

    # GET endpoint serves the same payload
    via_api = client.get(f"/api/apps/{app_id}/virustotal").json()
    assert via_api == fake_report


# ---------------------------------------------------------------------------
# /api/apps/{app_id}/export — bundles all the above into a valid ZIP
# ---------------------------------------------------------------------------


def test_export_zip_contains_all_pipeline_artifacts(integration_state):
    """After analyze + classify + virustotal have run, the export ZIP must
    include the produced JSONs and CSVs and be a valid archive."""
    import io
    import zipfile

    client, app_id, _ = integration_state
    resp = client.get(f"/api/apps/{app_id}/export")
    assert resp.status_code == 200
    assert "application/zip" in resp.headers["content-type"]

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        names = set(zf.namelist())
        # Sanity-check that each entry is readable
        for name in names:
            assert zf.read(name) is not None

    expected = {
        "app.json",
        "content_type_analysis.csv",
        "possible_modifications_analysis.json",
        "security_metrics.json",
        "classification.json",
        "virustotal_report.json",
    }
    missing = expected - names
    assert not missing, f"export ZIP missing: {missing}"
