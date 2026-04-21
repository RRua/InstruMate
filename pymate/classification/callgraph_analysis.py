"""Call graph analysis for security-relevant metrics.

Computes graph structural metrics (density, degree distribution) and
checks method nodes for reachability to sensitive Android API families.
"""

import re
from typing import Dict, List, Any
from pymate.classification.models import CallGraphMetrics

# Sensitive API families — regex patterns matched against call graph node names.
SENSITIVE_API_FAMILIES: Dict[str, List[str]] = {
    "sms": [
        r"android/telephony/SmsManager",
        r"android/telephony/gsm/SmsManager",
    ],
    "telephony": [
        r"android/telephony/TelephonyManager",
        r"android/telecom/TelecomManager",
    ],
    "camera": [
        r"android/hardware/camera2/",
        r"android/hardware/Camera",
        r"android/media/MediaRecorder",
    ],
    "location": [
        r"android/location/LocationManager",
        r"com/google/android/gms/location/",
    ],
    "crypto": [
        r"javax/crypto/",
        r"java/security/",
    ],
    "exec": [
        r"java/lang/Runtime;->exec",
        r"java/lang/ProcessBuilder",
    ],
    "reflection": [
        r"java/lang/reflect/",
        r"java/lang/Class;->forName",
    ],
    "file_io": [
        r"java/io/File;->",
        r"java/io/FileOutputStream",
        r"java/io/FileInputStream",
    ],
    "network": [
        r"java/net/URL",
        r"java/net/HttpURLConnection",
        r"okhttp3/",
    ],
    "content_provider": [
        r"android/content/ContentResolver",
    ],
    "package_manager": [
        r"android/content/pm/PackageManager",
        r"android/app/admin/DevicePolicyManager",
    ],
    "dynamic_loading": [
        r"dalvik/system/DexClassLoader",
        r"dalvik/system/PathClassLoader",
    ],
    "accessibility": [
        r"android/accessibilityservice/",
    ],
    "contacts": [
        r"android/provider/ContactsContract",
    ],
}

# Pre-compile all patterns
_COMPILED_FAMILIES: Dict[str, List[re.Pattern]] = {
    family: [re.compile(p) for p in patterns]
    for family, patterns in SENSITIVE_API_FAMILIES.items()
}

# Common Android entry point patterns
_ENTRY_POINT_PATTERNS = [
    re.compile(r"onCreate\("),
    re.compile(r"onReceive\("),
    re.compile(r"onStartCommand\("),
    re.compile(r"onBind\("),
    re.compile(r"onHandleIntent\("),
    re.compile(r"main\(\[Ljava/lang/String;\)"),
    re.compile(r"attachBaseContext\("),
]


def _match_sensitive_family(node_name: str) -> List[str]:
    """Return list of sensitive API families a node matches."""
    matched = []
    for family, patterns in _COMPILED_FAMILIES.items():
        for pat in patterns:
            if pat.search(node_name):
                matched.append(family)
                break
    return matched


def analyze_call_graph(cg_data: Dict[str, Any]) -> CallGraphMetrics:
    """Analyze call graph structure and sensitive API reachability.

    Args:
        cg_data: Dict with "nodes" (list of str) and
                 "edges" (list of {"from": str, "to": str}).

    Returns:
        CallGraphMetrics with graph structural metrics and API reachability.
    """
    if not cg_data:
        return CallGraphMetrics()

    nodes = cg_data.get("nodes", [])
    edges = cg_data.get("edges", [])

    if not nodes:
        return CallGraphMetrics()

    total_nodes = len(nodes)
    total_edges = len(edges)

    # Compute degree distributions
    in_degree: Dict[str, int] = {}
    out_degree: Dict[str, int] = {}

    for edge in edges:
        src = edge.get("from", "")
        dst = edge.get("to", "")
        out_degree[src] = out_degree.get(src, 0) + 1
        in_degree[dst] = in_degree.get(dst, 0) + 1

    max_possible_edges = total_nodes * (total_nodes - 1) if total_nodes > 1 else 1
    density = total_edges / max_possible_edges if max_possible_edges > 0 else 0.0

    avg_in = sum(in_degree.values()) / total_nodes if total_nodes > 0 else 0.0
    avg_out = sum(out_degree.values()) / total_nodes if total_nodes > 0 else 0.0
    max_in = max(in_degree.values()) if in_degree else 0
    max_out = max(out_degree.values()) if out_degree else 0

    # Check nodes against sensitive API families
    sensitive_reachability: Dict[str, List[str]] = {}
    for node in nodes:
        families = _match_sensitive_family(node)
        for family in families:
            sensitive_reachability.setdefault(family, []).append(node)

    sensitive_count = sum(len(v) for v in sensitive_reachability.values())

    # Identify entry points
    entry_points = []
    for node in nodes:
        for pat in _ENTRY_POINT_PATTERNS:
            if pat.search(node):
                entry_points.append(node)
                break

    return CallGraphMetrics(
        total_nodes=total_nodes,
        total_edges=total_edges,
        density=round(density, 6),
        avg_in_degree=round(avg_in, 3),
        avg_out_degree=round(avg_out, 3),
        max_in_degree=max_in,
        max_out_degree=max_out,
        sensitive_api_reachability=sensitive_reachability,
        sensitive_api_count=sensitive_count,
        entry_points=entry_points[:50],  # cap to avoid huge payloads
    )
