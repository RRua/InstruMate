import csv
import io
import json
import os
import zipfile
from math import ceil
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from api.models import AppSummary, AppDetail, AnalysisResult, PaginatedApps
from api.app_registry import registry

router = APIRouter()

OUTPUT_DIR = os.environ.get("INSTRUMATE_OUTPUT_DIR", "./output")


def _find_apk_file(output_dir: str) -> Optional[str]:
    """Locate the APK file for an app.

    Strategy:
    1. Check app.json for an explicit apk_path field
    2. Scan installers/ subdirectory for .apk files
    3. Scan the output directory itself for .apk files
    """
    app_json_path = os.path.join(output_dir, "app.json")
    if os.path.isfile(app_json_path):
        with open(app_json_path, "r", encoding="utf-8") as f:
            app_data = json.load(f)
        apk_path = app_data.get("apk_path")
        if apk_path and os.path.isfile(apk_path):
            return apk_path

    installers_dir = os.path.join(output_dir, "installers")
    if os.path.isdir(installers_dir):
        for fname in os.listdir(installers_dir):
            if fname.lower().endswith(".apk"):
                return os.path.join(installers_dir, fname)

    for fname in os.listdir(output_dir):
        if fname.lower().endswith(".apk"):
            return os.path.join(output_dir, fname)

    return None


def _build_summary(entry: dict) -> AppSummary:
    """Build an AppSummary from a registry entry, including analysis flags."""
    data = entry["app_data"]
    output_dir = entry["output_dir"]
    return AppSummary(
        app_id=data.get("app_id", "unknown"),
        package_name=data.get("package_name", "unknown"),
        version_name=data.get("app_version_name"),
        version_code=data.get("app_version_code"),
        is_variant=data.get("variant_info") is not None,
        output_dir=output_dir,
        has_classification=os.path.isfile(
            os.path.join(output_dir, "classification.json")
        ),
        has_virustotal_report=os.path.isfile(
            os.path.join(output_dir, "virustotal_report.json")
        ),
        has_security_metrics=os.path.isfile(
            os.path.join(output_dir, "security_metrics.json")
        ),
    )


@router.get("/apps", response_model=PaginatedApps)
async def list_apps(
    q: Optional[str] = Query(default=None, description="Search by package name or app ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=50, ge=1, le=200, description="Items per page"),
    has_classification: Optional[bool] = Query(default=None),
    has_virustotal_report: Optional[bool] = Query(default=None),
    is_variant: Optional[bool] = Query(default=None),
):
    """List all analyzed apps with search, filter, and pagination."""
    entries = registry.list_all()
    summaries = [_build_summary(e) for e in entries]

    # Filters
    if q:
        q_lower = q.lower()
        summaries = [
            s for s in summaries
            if q_lower in s.package_name.lower() or q_lower in s.app_id.lower()
        ]
    if has_classification is not None:
        summaries = [s for s in summaries if s.has_classification == has_classification]
    if has_virustotal_report is not None:
        summaries = [s for s in summaries if s.has_virustotal_report == has_virustotal_report]
    if is_variant is not None:
        summaries = [s for s in summaries if s.is_variant == is_variant]

    total = len(summaries)
    pages = ceil(total / per_page) if total > 0 else 1
    start = (page - 1) * per_page
    items = summaries[start : start + per_page]

    return PaginatedApps(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/apps/{app_id}", response_model=AppDetail)
async def get_app_detail(app_id: str):
    """Get detailed metadata for a specific app."""
    entry = registry.get(app_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")

    data = entry["app_data"]
    output_dir = entry["output_dir"]

    return AppDetail(
        app_id=data.get("app_id"),
        package_name=data.get("package_name"),
        app_name=data.get("app_name"),
        version_name=data.get("app_version_name"),
        version_code=data.get("app_version_code"),
        min_sdk_version=data.get("min_sdk_version"),
        max_sdk_version=data.get("max_sdk_version"),
        target_sdk_version=data.get("target_sdk_version"),
        main_activity=data.get("main_activity"),
        permissions=data.get("permissions"),
        activities=data.get("activities"),
        services=data.get("services"),
        features=data.get("features"),
        is_variant=data.get("variant_info") is not None,
        variant_info=data.get("variant_info"),
        has_content_type_analysis=os.path.isfile(
            os.path.join(output_dir, "content_type_analysis.csv")
        ),
        has_dex_analysis=os.path.isfile(
            os.path.join(output_dir, "dex_static_analysis.json")
        ),
        has_call_graph=os.path.isfile(
            os.path.join(output_dir, "call_graph.json")
        ),
        has_classification=os.path.isfile(
            os.path.join(output_dir, "classification.json")
        ),
        has_security_metrics=os.path.isfile(
            os.path.join(output_dir, "security_metrics.json")
        ),
        has_virustotal_report=os.path.isfile(
            os.path.join(output_dir, "virustotal_report.json")
        ),
    )


@router.get("/apps/{app_id}/analysis", response_model=AnalysisResult)
async def get_app_analysis(app_id: str):
    """Get analysis results (content types, DEX, native, modifications)."""
    entry = registry.get(app_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")

    output_dir = entry["output_dir"]
    result = AnalysisResult()

    ct_path = os.path.join(output_dir, "content_type_analysis.csv")
    if os.path.isfile(ct_path):
        with open(ct_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            result.content_type_analysis = list(reader)

    dex_path = os.path.join(output_dir, "dex_static_analysis.json")
    if os.path.isfile(dex_path):
        with open(dex_path, "r", encoding="utf-8") as f:
            result.dex_static_analysis = json.load(f)

    native_path = os.path.join(output_dir, "native_static_analysis.json")
    if os.path.isfile(native_path):
        with open(native_path, "r", encoding="utf-8") as f:
            result.native_static_analysis = json.load(f)

    pm_path = os.path.join(output_dir, "possible_modifications_analysis.json")
    if os.path.isfile(pm_path):
        with open(pm_path, "r", encoding="utf-8") as f:
            result.possible_modifications = json.load(f)

    return result


@router.get("/apps/{app_id}/callgraph")
async def get_call_graph(
    app_id: str,
    limit: int = Query(default=500, ge=1, le=50000, description="Max nodes to return"),
    filter: Optional[str] = Query(default=None, description="Substring filter on node names"),
):
    """Get call graph data in vis.js format."""
    entry = registry.get(app_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")

    output_dir = entry["output_dir"]
    cg_path = os.path.join(output_dir, "call_graph.json")
    if not os.path.isfile(cg_path):
        raise HTTPException(status_code=404, detail="Call graph not available")

    with open(cg_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    raw_nodes = raw.get("nodes", [])
    raw_edges = raw.get("edges", [])

    # Build vis.js formatted nodes
    nodes = []
    for i, node in enumerate(raw_nodes):
        if isinstance(node, str):
            label = node
            node_id = i
        elif isinstance(node, dict):
            label = node.get("label", node.get("id", str(i)))
            node_id = node.get("id", i)
        else:
            label = str(node)
            node_id = i

        if filter and filter.lower() not in label.lower():
            continue
        nodes.append({"id": node_id, "label": label})
        if len(nodes) >= limit:
            break

    # Build node ID set for filtering edges
    node_ids = {n["id"] for n in nodes}

    # Build vis.js formatted edges
    edges = []
    for edge in raw_edges:
        if isinstance(edge, dict):
            from_id = edge.get("from", edge.get("source"))
            to_id = edge.get("to", edge.get("target"))
        elif isinstance(edge, (list, tuple)) and len(edge) >= 2:
            from_id, to_id = edge[0], edge[1]
        else:
            continue
        if from_id in node_ids and to_id in node_ids:
            edges.append({"from": from_id, "to": to_id})

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(raw_nodes),
        "total_edges": len(raw_edges),
    }


@router.get("/apps/{app_id}/download")
async def download_apk(app_id: str):
    """Download the APK file for an app."""
    entry = registry.get(app_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")

    apk_path = _find_apk_file(entry["output_dir"])
    if apk_path is None:
        raise HTTPException(status_code=404, detail="No APK file found for this app")

    return FileResponse(
        apk_path,
        media_type="application/vnd.android.package-archive",
        filename=os.path.basename(apk_path),
    )


@router.get("/apps/{app_id}/export")
async def export_results(app_id: str):
    """Export all analysis results as a ZIP archive."""
    entry = registry.get(app_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")

    output_dir = entry["output_dir"]
    package_name = entry["app_data"].get("package_name", app_id)

    export_files = [
        "app.json",
        "security_metrics.json",
        "classification.json",
        "virustotal_report.json",
        "content_type_analysis.csv",
        "dex_static_analysis.json",
        "native_static_analysis.json",
        "possible_modifications_analysis.json",
    ]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in export_files:
            fpath = os.path.join(output_dir, fname)
            if os.path.isfile(fpath):
                zf.write(fpath, fname)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{package_name}_export.zip"'
        },
    )
