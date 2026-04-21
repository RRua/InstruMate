"""Permission analysis for Android APK security assessment.

Categorizes permissions into risk groups, flags dangerous permissions,
and detects suspicious permission combinations.
"""

from typing import List, Dict
from pymate.classification.models import PermissionMetrics

# Dangerous Android permissions that require runtime approval or grant
# elevated access to user data / device capabilities.
DANGEROUS_PERMISSIONS = {
    "android.permission.READ_SMS",
    "android.permission.SEND_SMS",
    "android.permission.RECEIVE_SMS",
    "android.permission.READ_CONTACTS",
    "android.permission.WRITE_CONTACTS",
    "android.permission.READ_CALL_LOG",
    "android.permission.WRITE_CALL_LOG",
    "android.permission.CAMERA",
    "android.permission.RECORD_AUDIO",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.ACCESS_BACKGROUND_LOCATION",
    "android.permission.READ_PHONE_STATE",
    "android.permission.CALL_PHONE",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.MANAGE_EXTERNAL_STORAGE",
    "android.permission.INTERNET",
    "android.permission.ACCESS_NETWORK_STATE",
    "android.permission.RECEIVE_BOOT_COMPLETED",
    "android.permission.SYSTEM_ALERT_WINDOW",
    "android.permission.INSTALL_PACKAGES",
    "android.permission.REQUEST_INSTALL_PACKAGES",
    "android.permission.BIND_ACCESSIBILITY_SERVICE",
    "android.permission.BIND_DEVICE_ADMIN",
    "android.permission.READ_PHONE_NUMBERS",
    "android.permission.PROCESS_OUTGOING_CALLS",
}

# Permission categories mapping
PERMISSION_CATEGORIES: Dict[str, List[str]] = {
    "privacy": [
        "android.permission.READ_SMS",
        "android.permission.RECEIVE_SMS",
        "android.permission.READ_CONTACTS",
        "android.permission.WRITE_CONTACTS",
        "android.permission.READ_CALL_LOG",
        "android.permission.WRITE_CALL_LOG",
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.ACCESS_COARSE_LOCATION",
        "android.permission.ACCESS_BACKGROUND_LOCATION",
        "android.permission.READ_PHONE_STATE",
        "android.permission.READ_PHONE_NUMBERS",
        "android.permission.READ_EXTERNAL_STORAGE",
        "android.permission.MANAGE_EXTERNAL_STORAGE",
    ],
    "network": [
        "android.permission.INTERNET",
        "android.permission.ACCESS_NETWORK_STATE",
        "android.permission.ACCESS_WIFI_STATE",
        "android.permission.CHANGE_NETWORK_STATE",
        "android.permission.CHANGE_WIFI_STATE",
    ],
    "system": [
        "android.permission.RECEIVE_BOOT_COMPLETED",
        "android.permission.SYSTEM_ALERT_WINDOW",
        "android.permission.INSTALL_PACKAGES",
        "android.permission.REQUEST_INSTALL_PACKAGES",
        "android.permission.BIND_DEVICE_ADMIN",
        "android.permission.WRITE_SETTINGS",
        "android.permission.WRITE_SECURE_SETTINGS",
        "android.permission.PROCESS_OUTGOING_CALLS",
    ],
    "hardware": [
        "android.permission.CAMERA",
        "android.permission.RECORD_AUDIO",
        "android.permission.VIBRATE",
        "android.permission.FLASHLIGHT",
        "android.permission.BLUETOOTH",
        "android.permission.BLUETOOTH_ADMIN",
        "android.permission.NFC",
    ],
    "financial": [
        "android.permission.SEND_SMS",
        "android.permission.CALL_PHONE",
        "android.permission.BIND_ACCESSIBILITY_SERVICE",
    ],
}

# Suspicious permission combinations that may indicate malicious behavior
SUSPICIOUS_COMBINATIONS = [
    {
        "name": "SMS exfiltration",
        "required": ["android.permission.READ_SMS", "android.permission.INTERNET"],
        "description": "Can read SMS messages and send them over the network",
    },
    {
        "name": "SMS fraud",
        "required": ["android.permission.SEND_SMS", "android.permission.RECEIVE_SMS"],
        "description": "Can send and intercept SMS messages (premium SMS fraud)",
    },
    {
        "name": "Surveillance (audio/video)",
        "required": [
            "android.permission.CAMERA",
            "android.permission.RECORD_AUDIO",
            "android.permission.INTERNET",
        ],
        "description": "Can capture audio/video and transmit over network",
    },
    {
        "name": "Location tracking",
        "required": [
            "android.permission.ACCESS_FINE_LOCATION",
            "android.permission.INTERNET",
            "android.permission.ACCESS_BACKGROUND_LOCATION",
        ],
        "description": "Can track device location continuously in background",
    },
    {
        "name": "Contact exfiltration",
        "required": [
            "android.permission.READ_CONTACTS",
            "android.permission.INTERNET",
        ],
        "description": "Can read contacts and exfiltrate over the network",
    },
    {
        "name": "Call log exfiltration",
        "required": [
            "android.permission.READ_CALL_LOG",
            "android.permission.INTERNET",
        ],
        "description": "Can read call history and exfiltrate over the network",
    },
    {
        "name": "Persistence + overlay",
        "required": [
            "android.permission.RECEIVE_BOOT_COMPLETED",
            "android.permission.SYSTEM_ALERT_WINDOW",
        ],
        "description": "Can auto-start on boot and display overlay windows (phishing)",
    },
    {
        "name": "Silent app installation",
        "required": [
            "android.permission.REQUEST_INSTALL_PACKAGES",
            "android.permission.INTERNET",
        ],
        "description": "Can download and install additional packages silently",
    },
]


def _normalize_permission(perm: str) -> str:
    """Ensure permission has full android.permission. prefix."""
    if not perm.startswith("android.permission."):
        return f"android.permission.{perm}"
    return perm


def analyze_permissions(permissions: List[str]) -> PermissionMetrics:
    """Analyze a list of Android permissions for security risks.

    Args:
        permissions: List of permission strings from app.json.

    Returns:
        PermissionMetrics with categorization, risk flags, and score.
    """
    if not permissions:
        return PermissionMetrics()

    normalized = [_normalize_permission(p) for p in permissions]
    perm_set = set(normalized)

    # Find dangerous permissions
    dangerous = sorted(perm_set & DANGEROUS_PERMISSIONS)

    # Categorize permissions
    categories: Dict[str, List[str]] = {}
    for category, category_perms in PERMISSION_CATEGORIES.items():
        matched = sorted(perm_set & set(category_perms))
        if matched:
            categories[category] = matched

    # Detect suspicious combinations
    suspicious = []
    for combo in SUSPICIOUS_COMBINATIONS:
        if all(p in perm_set for p in combo["required"]):
            suspicious.append({
                "name": combo["name"],
                "description": combo["description"],
                "permissions": combo["required"],
            })

    # Compute risk score (0-1)
    # Factors: dangerous permission ratio, suspicious combos, category spread
    dangerous_ratio = len(dangerous) / max(len(DANGEROUS_PERMISSIONS), 1)
    combo_factor = min(len(suspicious) / 4.0, 1.0)  # cap at 4 combos
    category_factor = len(categories) / len(PERMISSION_CATEGORIES)

    risk_score = min(
        0.4 * dangerous_ratio + 0.4 * combo_factor + 0.2 * category_factor,
        1.0,
    )

    return PermissionMetrics(
        total_permissions=len(permissions),
        dangerous_permissions=dangerous,
        dangerous_count=len(dangerous),
        categories=categories,
        suspicious_combinations=suspicious,
        permission_risk_score=round(risk_score, 3),
    )
