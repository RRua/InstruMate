"""Tests for /api/apps endpoints."""

import json
import os


def test_list_apps_paginated(test_client):
    resp = test_client.get("/api/apps")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "pages" in data
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


def test_list_apps_search(test_client):
    resp = test_client.get("/api/apps?q=com.example")
    data = resp.json()
    assert data["total"] >= 1
    assert all("com.example" in item["package_name"] for item in data["items"])


def test_list_apps_search_no_results(test_client):
    resp = test_client.get("/api/apps?q=nonexistent_package_xyz")
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_apps_filter_variant(test_client):
    resp = test_client.get("/api/apps?is_variant=false")
    data = resp.json()
    for item in data["items"]:
        assert item["is_variant"] is False


def test_list_apps_pagination(test_client):
    resp = test_client.get("/api/apps?page=1&per_page=1")
    data = resp.json()
    assert data["per_page"] == 1
    assert len(data["items"]) <= 1


def test_list_apps_summary_flags(test_client):
    """Verify summary includes analysis flag fields (N+1 fix)."""
    resp = test_client.get("/api/apps")
    data = resp.json()
    item = data["items"][0]
    assert "has_classification" in item
    assert "has_virustotal_report" in item
    assert "has_security_metrics" in item


def test_get_app_detail(test_client):
    resp = test_client.get("/api/apps/abc123")
    assert resp.status_code == 200
    data = resp.json()
    assert data["app_id"] == "abc123"
    assert data["package_name"] == "com.example.test"
    assert "has_call_graph" in data
    assert data["has_call_graph"] is True


def test_get_app_detail_404(test_client):
    resp = test_client.get("/api/apps/nonexistent")
    assert resp.status_code == 404


def test_get_app_analysis(test_client):
    resp = test_client.get("/api/apps/abc123/analysis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["content_type_analysis"] is not None
    assert data["dex_static_analysis"] is not None


def test_download_apk(test_client):
    resp = test_client.get("/api/apps/abc123/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/vnd.android.package-archive"
    assert b"PK" in resp.content


def test_download_apk_404(test_client):
    resp = test_client.get("/api/apps/nonexistent/download")
    assert resp.status_code == 404


def test_export_results(test_client):
    resp = test_client.get("/api/apps/abc123/export")
    assert resp.status_code == 200
    assert "application/zip" in resp.headers["content-type"]
    assert b"PK" in resp.content[:4]  # ZIP magic number


def test_export_results_404(test_client):
    resp = test_client.get("/api/apps/nonexistent/export")
    assert resp.status_code == 404


def test_callgraph(test_client):
    resp = test_client.get("/api/apps/abc123/callgraph")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert "total_nodes" in data
    assert data["total_nodes"] == 3


def test_callgraph_with_filter(test_client):
    resp = test_client.get("/api/apps/abc123/callgraph?filter=methodA")
    data = resp.json()
    assert len(data["nodes"]) == 1
    assert data["nodes"][0]["label"] == "methodA"


def test_callgraph_with_limit(test_client):
    resp = test_client.get("/api/apps/abc123/callgraph?limit=2")
    data = resp.json()
    assert len(data["nodes"]) <= 2


def test_callgraph_404(test_client):
    resp = test_client.get("/api/apps/nonexistent/callgraph")
    assert resp.status_code == 404


# --- Additional /api/apps coverage ---


def test_list_apps_per_page_max_enforced(test_client):
    """per_page > 200 must fail validation."""
    resp = test_client.get("/api/apps?per_page=500")
    assert resp.status_code == 422


def test_list_apps_filter_has_classification(test_client, tmp_output_dir):
    out_dir = tmp_output_dir / "com.example.test" / "com.example.test-1.0_original"
    (out_dir / "classification.json").write_text("{}")

    from api.app_registry import registry
    registry.refresh()

    with_clf = test_client.get("/api/apps?has_classification=true").json()
    without_clf = test_client.get("/api/apps?has_classification=false").json()
    assert with_clf["total"] == 1
    assert without_clf["total"] == 0


def test_list_apps_pagination_overflow_returns_empty(test_client):
    """Asking for a page past the end yields an empty items list."""
    body = test_client.get("/api/apps?page=99&per_page=10").json()
    assert body["items"] == []
    assert body["page"] == 99


def test_get_app_detail_flags_off_when_files_absent(test_client):
    """Without analysis side files, has_* flags should be False."""
    body = test_client.get("/api/apps/abc123").json()
    assert body["has_classification"] is False
    assert body["has_security_metrics"] is False
    assert body["has_virustotal_report"] is False


def test_get_app_detail_marks_variant(test_client, tmp_output_dir):
    """An app.json with variant_info present produces is_variant=True."""
    import json
    pkg_dir = tmp_output_dir / "com.example.test" / "com.example.test-1.0_zip"
    pkg_dir.mkdir(parents=True)
    with open(pkg_dir / "app.json", "w") as f:
        json.dump(
            {
                "app_id": "v-2",
                "package_name": "com.example.test",
                "variant_info": {"maker": "zip"},
            },
            f,
        )

    from api.app_registry import registry
    registry.refresh()

    body = test_client.get("/api/apps/v-2").json()
    assert body["is_variant"] is True
    assert body["variant_info"] == {"maker": "zip"}


def test_get_app_analysis_includes_native_and_modifications(
    test_client, tmp_output_dir
):
    import json
    out_dir = tmp_output_dir / "com.example.test" / "com.example.test-1.0_original"
    with open(out_dir / "native_static_analysis.json", "w") as f:
        json.dump([{"lib": "libfoo.so"}], f)
    with open(out_dir / "possible_modifications_analysis.json", "w") as f:
        json.dump({"layout_changes": []}, f)

    body = test_client.get("/api/apps/abc123/analysis").json()
    assert body["native_static_analysis"] == [{"lib": "libfoo.so"}]
    assert body["possible_modifications"] == {"layout_changes": []}


def test_get_app_analysis_404_unknown_app(test_client):
    resp = test_client.get("/api/apps/no-such/analysis")
    assert resp.status_code == 404


def test_callgraph_filter_returns_no_matches(test_client):
    """Filter that matches nothing yields empty nodes/edges with totals preserved."""
    body = test_client.get("/api/apps/abc123/callgraph?filter=zzz").json()
    assert body["nodes"] == []
    assert body["edges"] == []
    assert body["total_nodes"] == 3


def test_callgraph_handles_dict_nodes(test_client, tmp_output_dir):
    """Dict-form nodes/edges (vis.js source/target) are supported."""
    import json
    cg_path = tmp_output_dir / "com.example.test" / "com.example.test-1.0_original" / "call_graph.json"
    with open(cg_path, "w") as f:
        json.dump(
            {
                "nodes": [
                    {"id": 10, "label": "alpha"},
                    {"id": 20, "label": "beta"},
                ],
                "edges": [{"source": 10, "target": 20}],
            },
            f,
        )

    body = test_client.get("/api/apps/abc123/callgraph").json()
    labels = sorted(n["label"] for n in body["nodes"])
    assert labels == ["alpha", "beta"]
    assert body["edges"] == [{"from": 10, "to": 20}]


def test_download_apk_filename_in_disposition(test_client):
    resp = test_client.get("/api/apps/abc123/download")
    assert resp.status_code == 200
    # FileResponse sets Content-Disposition with the basename
    assert "test.apk" in resp.headers.get("content-disposition", "")


def test_download_no_apk_returns_404(test_client, tmp_output_dir):
    """Removing all APKs from the app dir surfaces a 404."""
    apk = tmp_output_dir / "com.example.test" / "com.example.test-1.0_original" / "installers" / "test.apk"
    apk.unlink()
    resp = test_client.get("/api/apps/abc123/download")
    assert resp.status_code == 404


def test_export_zip_contains_app_json(test_client):
    import io
    import zipfile
    resp = test_client.get("/api/apps/abc123/export")
    assert resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        names = zf.namelist()
    assert "app.json" in names


def test_export_zip_omits_missing_files(test_client):
    """Files that don't exist on disk are not in the archive."""
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(test_client.get("/api/apps/abc123/export").content)) as zf:
        names = zf.namelist()
    assert "classification.json" not in names
    assert "virustotal_report.json" not in names
