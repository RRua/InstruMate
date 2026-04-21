"""Shared fixtures for InstruMate API tests."""

import json
import os
import tempfile

import pytest


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Create a temporary output directory with a sample app.json."""
    pkg_dir = tmp_path / "com.example.test" / "com.example.test-1.0_original"
    pkg_dir.mkdir(parents=True)

    app_data = {
        "app_id": "abc123",
        "package_name": "com.example.test",
        "app_name": "Test App",
        "app_version_name": "1.0",
        "app_version_code": "1",
        "min_sdk_version": "21",
        "max_sdk_version": None,
        "target_sdk_version": "33",
        "main_activity": "com.example.test.MainActivity",
        "permissions": ["android.permission.INTERNET"],
        "activities": ["com.example.test.MainActivity"],
        "services": [],
        "features": [],
        "variant_info": None,
    }

    with open(pkg_dir / "app.json", "w") as f:
        json.dump(app_data, f)

    # Create a dummy APK in installers/
    installers = pkg_dir / "installers"
    installers.mkdir()
    (installers / "test.apk").write_bytes(b"PK\x03\x04" + b"\x00" * 100)

    # Create sample analysis files
    with open(pkg_dir / "dex_static_analysis.json", "w") as f:
        json.dump([{"classes": ["Lcom/example/Test;"], "methods": [], "strings": []}], f)

    with open(pkg_dir / "content_type_analysis.csv", "w") as f:
        f.write("file_path,is_code,is_resource\n")
        f.write("classes.dex,True,False\n")

    # Create a sample call graph
    with open(pkg_dir / "call_graph.json", "w") as f:
        json.dump({
            "nodes": ["methodA", "methodB", "methodC"],
            "edges": [{"from": 0, "to": 1}, {"from": 1, "to": 2}],
        }, f)

    return tmp_path


@pytest.fixture
def test_client(tmp_output_dir, monkeypatch):
    """Create a FastAPI TestClient with mocked environment."""
    monkeypatch.setenv("INSTRUMATE_OUTPUT_DIR", str(tmp_output_dir))
    monkeypatch.setenv("INSTRUMATE_TMP_DIR", str(tmp_output_dir / "tmp"))
    monkeypatch.setenv("INSTRUMATE_UPLOAD_DIR", str(tmp_output_dir / "uploads"))

    # Reset singletons before importing
    # We need to reimport modules after setting env vars
    import importlib
    import api.app_registry
    import api.job_store

    # Update module-level OUTPUT_DIR in registry and job_store
    api.app_registry.OUTPUT_DIR = str(tmp_output_dir)
    api.app_registry.registry._loaded = False
    api.app_registry.registry._index = {}

    api.job_store.OUTPUT_DIR = str(tmp_output_dir)
    api.job_store.DB_PATH = os.path.join(str(tmp_output_dir), "jobs.db")
    api.job_store.job_store._initialized = False
    api.job_store.job_store._local = __import__("threading").local()

    # Also update OUTPUT_DIR in routers that read it at module level
    import api.routers.apps
    import api.routers.analyze
    import api.routers.variants
    api.routers.apps.OUTPUT_DIR = str(tmp_output_dir)
    api.routers.analyze.OUTPUT_DIR = str(tmp_output_dir)
    api.routers.analyze.UPLOAD_DIR = str(tmp_output_dir / "uploads")
    api.routers.analyze.TMP_DIR = str(tmp_output_dir / "tmp")
    api.routers.variants.OUTPUT_DIR = str(tmp_output_dir)

    from fastapi.testclient import TestClient
    from api.app import app
    return TestClient(app)
