"""Content type analysis for APK file composition assessment.

Analyzes file type distribution from TikaMimeTypeAnalyzer output,
detects automation scripts, crypto materials, and hidden executables.
"""

import csv
import os
from typing import Dict, List, Any
from pymate.classification.models import ContentMetrics

# Column names from TikaMimeTypeAnalyzer's content_type_analysis.csv.
# These are boolean flag columns indicating file category membership.
CONTENT_CATEGORIES = [
    "is_dex",
    "is_xml",
    "is_image",
    "is_audio",
    "is_video",
    "is_font",
    "is_text",
    "is_binary",
    "is_archive",
    "is_certificate",
    "is_native_lib",
    "is_html",
    "is_json",
    "is_protobuf",
]

# File types that are unusual in normal Android apps
UNUSUAL_INDICATORS = {
    "automation_scripts": [
        "application/x-sh",
        "application/x-shellscript",
        "text/x-python",
        "text/x-perl",
        "application/x-bat",
        "application/javascript",
    ],
    "crypto_materials": [
        "application/x-x509-ca-cert",
        "application/x-pem-file",
        "application/pkcs8",
        "application/pkcs12",
        "application/x-pkcs12",
        "application/pgp-keys",
    ],
    "hidden_executables": [
        "application/x-executable",
        "application/x-elf",
        "application/x-dosexec",
        "application/x-mach-binary",
        "application/x-pie-executable",
    ],
}


def _parse_bool(value: str) -> bool:
    """Parse boolean string from CSV."""
    return str(value).strip().lower() in ("true", "1", "yes")


def analyze_content_from_csv(csv_path: str) -> ContentMetrics:
    """Analyze content type distribution from content_type_analysis.csv.

    Args:
        csv_path: Path to content_type_analysis.csv file.

    Returns:
        ContentMetrics with file distribution and anomaly flags.
    """
    if not os.path.isfile(csv_path):
        return ContentMetrics()

    rows: List[Dict[str, str]] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        return ContentMetrics()

    total_files = len(rows)

    # Count files per category
    distribution: Dict[str, int] = {}
    for category in CONTENT_CATEGORIES:
        count = sum(1 for row in rows if _parse_bool(row.get(category, "")))
        if count > 0:
            distribution[category] = count

    # Compute code-to-resource ratio
    code_count = distribution.get("is_dex", 0) + distribution.get("is_native_lib", 0)
    resource_count = (
        distribution.get("is_image", 0)
        + distribution.get("is_xml", 0)
        + distribution.get("is_font", 0)
        + distribution.get("is_audio", 0)
        + distribution.get("is_video", 0)
    )
    code_to_resource = (
        code_count / resource_count if resource_count > 0 else float(code_count)
    )

    # Check for unusual file types via mime_type column
    has_automation = False
    has_crypto = False
    has_hidden_exec = False
    unusual_types: List[str] = []

    for row in rows:
        mime = row.get("mime_type", "").strip().lower()
        if not mime:
            continue

        if mime in UNUSUAL_INDICATORS["automation_scripts"]:
            has_automation = True
            unusual_types.append(f"automation: {mime}")
        if mime in UNUSUAL_INDICATORS["crypto_materials"]:
            has_crypto = True
            unusual_types.append(f"crypto: {mime}")
        if mime in UNUSUAL_INDICATORS["hidden_executables"]:
            has_hidden_exec = True
            unusual_types.append(f"executable: {mime}")

    return ContentMetrics(
        total_files=total_files,
        file_type_distribution=distribution,
        code_to_resource_ratio=round(code_to_resource, 3),
        has_automation_scripts=has_automation,
        has_crypto_materials=has_crypto,
        has_hidden_executables=has_hidden_exec,
        unusual_file_types=sorted(set(unusual_types)),
    )
