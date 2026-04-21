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
