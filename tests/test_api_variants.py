"""Tests for /api/apps/{app_id}/variants (POST + GET)."""

import json


def _stub_run(monkeypatch):
    import api.routers.variants

    captured = {}

    def fake_run(job_id, app_id, maker_keys, spec_levels):
        captured.update(
            job_id=job_id,
            app_id=app_id,
            makers=maker_keys,
            specs=spec_levels,
        )

    monkeypatch.setattr(api.routers.variants, "_run_variant_creation", fake_run)
    return captured


def test_post_variants_creates_job(test_client, monkeypatch):
    captured = _stub_run(monkeypatch)
    resp = test_client.post(
        "/api/apps/abc123/variants",
        json={"variant_makers": ["zip"], "variant_specs": ["signature"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    assert body["app_id"] == "abc123"
    assert body["job_id"]

    assert captured["app_id"] == "abc123"
    assert captured["makers"] == ["zip"]
    assert captured["specs"] == ["signature"]


def test_post_variants_uses_defaults(test_client, monkeypatch):
    """No body fields → uses VariantCreateRequest defaults."""
    captured = _stub_run(monkeypatch)
    resp = test_client.post("/api/apps/abc123/variants", json={})
    assert resp.status_code == 200
    assert captured["makers"] == ["zip", "apkeditor", "apktool"]
    assert captured["specs"] == ["signature"]


def test_post_variants_unknown_app_404(test_client, monkeypatch):
    _stub_run(monkeypatch)
    resp = test_client.post("/api/apps/no-such-app/variants", json={})
    assert resp.status_code == 404


def test_post_variants_invalid_body(test_client, monkeypatch):
    _stub_run(monkeypatch)
    # variant_makers must be a list
    resp = test_client.post(
        "/api/apps/abc123/variants",
        json={"variant_makers": "zip"},
    )
    assert resp.status_code == 422


def test_get_variants_empty_when_none_present(test_client):
    resp = test_client.get("/api/apps/abc123/variants")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_variants_returns_known_variant(test_client, tmp_output_dir):
    """A second app.json with variant_info set should appear in the list."""
    pkg_dir = tmp_output_dir / "com.example.test" / "com.example.test-1.0_zip_signature"
    pkg_dir.mkdir(parents=True)
    with open(pkg_dir / "app.json", "w") as f:
        json.dump(
            {
                "app_id": "variant-1",
                "package_name": "com.example.test",
                "app_version_name": "1.0",
                "app_version_code": "1",
                "variant_info": {"maker": "zip", "spec": "signature"},
            },
            f,
        )

    # Force registry to re-scan so it picks up the new variant.
    from api.app_registry import registry

    registry.refresh()

    resp = test_client.get("/api/apps/abc123/variants")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["app_id"] == "variant-1"
    assert items[0]["is_variant"] is True
    assert items[0]["package_name"] == "com.example.test"


def test_get_variants_unknown_app_404(test_client):
    resp = test_client.get("/api/apps/no-such-app/variants")
    assert resp.status_code == 404


# --- Additional coverage ---


def test_post_variants_persists_job(test_client, monkeypatch):
    """Returned job_id is visible in the job store (via classify endpoint)
    (variants share the same job_store, so a POST must create a record)."""
    from api.job_store import job_store

    _stub_run(monkeypatch)
    job_id = test_client.post(
        "/api/apps/abc123/variants", json={}
    ).json()["job_id"]

    stored = job_store.get(job_id)
    assert stored is not None
    assert stored.app_id == "abc123"
    assert stored.status.value == "pending"


def test_post_variants_passes_multiple_makers(test_client, monkeypatch):
    captured = _stub_run(monkeypatch)
    test_client.post(
        "/api/apps/abc123/variants",
        json={
            "variant_makers": ["zip", "apktool", "apkeditor"],
            "variant_specs": ["signature", "manifest"],
        },
    )
    assert captured["makers"] == ["zip", "apktool", "apkeditor"]
    assert captured["specs"] == ["signature", "manifest"]


def test_post_variants_accepts_empty_lists(test_client, monkeypatch):
    """Empty maker/spec lists are accepted — the route does not reject them."""
    captured = _stub_run(monkeypatch)
    resp = test_client.post(
        "/api/apps/abc123/variants",
        json={"variant_makers": [], "variant_specs": []},
    )
    assert resp.status_code == 200
    assert captured["makers"] == []
    assert captured["specs"] == []


def test_get_variants_returns_multiple(test_client, tmp_output_dir):
    """Two variant subdirectories should both appear in the listing."""
    import json
    base = tmp_output_dir / "com.example.test"
    for i, tag in enumerate(["zip_sig", "apktool_sig"], start=1):
        vdir = base / f"com.example.test-1.0_{tag}"
        vdir.mkdir(parents=True)
        with open(vdir / "app.json", "w") as f:
            json.dump(
                {
                    "app_id": f"v-{i}",
                    "package_name": "com.example.test",
                    "app_version_name": "1.0",
                    "variant_info": {"maker": tag.split("_")[0]},
                },
                f,
            )

    from api.app_registry import registry
    registry.refresh()

    items = test_client.get("/api/apps/abc123/variants").json()
    ids = sorted(it["app_id"] for it in items)
    assert ids == ["v-1", "v-2"]
    assert all(it["is_variant"] is True for it in items)


def test_get_variants_excludes_original(test_client, tmp_output_dir):
    """The original (no variant_info) must NOT be listed as a variant."""
    import json
    # sibling variant
    vdir = tmp_output_dir / "com.example.test" / "com.example.test-1.0_zip"
    vdir.mkdir(parents=True)
    with open(vdir / "app.json", "w") as f:
        json.dump(
            {
                "app_id": "vx",
                "package_name": "com.example.test",
                "variant_info": {"maker": "zip"},
            },
            f,
        )

    from api.app_registry import registry
    registry.refresh()

    items = test_client.get("/api/apps/abc123/variants").json()
    # abc123 (the original) has variant_info=None, so it must NOT appear
    assert all(it["app_id"] != "abc123" for it in items)
    assert any(it["app_id"] == "vx" for it in items)
