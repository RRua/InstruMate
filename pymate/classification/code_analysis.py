"""DEX bytecode analysis for suspicious API detection and obfuscation scoring.

Scans DEX method signatures against known suspicious API patterns,
detects obfuscation indicators, and extracts embedded URLs/IPs/base64.
"""

import re
from typing import Dict, List, Any
from pymate.classification.models import CodeMetrics

# Suspicious API patterns grouped by category.
# Each pattern is a regex matched against fully-qualified method/class names.
SUSPICIOUS_API_PATTERNS: Dict[str, List[str]] = {
    "reflection": [
        r"java/lang/reflect/",
        r"java/lang/Class;->forName",
        r"java/lang/Class;->getMethod",
        r"java/lang/Class;->getDeclaredMethod",
        r"java/lang/reflect/Method;->invoke",
        r"java/lang/ClassLoader;->loadClass",
    ],
    "dynamic_loading": [
        r"dalvik/system/DexClassLoader",
        r"dalvik/system/PathClassLoader",
        r"dalvik/system/InMemoryDexClassLoader",
        r"dalvik/system/DexFile;->loadDex",
        r"android/app/DexLoadingHelper",
    ],
    "native_calls": [
        r"java/lang/System;->loadLibrary",
        r"java/lang/System;->load\(",
        r"java/lang/Runtime;->loadLibrary",
    ],
    "crypto": [
        r"javax/crypto/Cipher",
        r"javax/crypto/spec/SecretKeySpec",
        r"javax/crypto/spec/IvParameterSpec",
        r"java/security/MessageDigest",
        r"javax/crypto/Mac",
    ],
    "runtime_exec": [
        r"java/lang/Runtime;->exec",
        r"java/lang/ProcessBuilder;->start",
        r"java/lang/ProcessBuilder;-><init>",
    ],
    "network": [
        r"java/net/URL;->openConnection",
        r"java/net/HttpURLConnection",
        r"org/apache/http/",
        r"okhttp3/",
    ],
    "sms_telephony": [
        r"android/telephony/SmsManager;->send",
        r"android/telephony/TelephonyManager;->getDeviceId",
        r"android/telephony/TelephonyManager;->getSubscriberId",
        r"android/telephony/TelephonyManager;->getLine1Number",
        r"android/telephony/TelephonyManager;->getSimSerialNumber",
    ],
    "accessibility": [
        r"android/accessibilityservice/AccessibilityService",
        r"android/view/accessibility/AccessibilityNodeInfo;->performAction",
    ],
}

# Pre-compile patterns for performance
_COMPILED_PATTERNS: Dict[str, List[re.Pattern]] = {
    cat: [re.compile(p) for p in patterns]
    for cat, patterns in SUSPICIOUS_API_PATTERNS.items()
}

# Regex patterns for extracting embedded data from string constants
_URL_PATTERN = re.compile(r'https?://[^\s"\'<>]+')
_IP_PATTERN = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
_BASE64_PATTERN = re.compile(r'^[A-Za-z0-9+/]{20,}={0,2}$')

# ProGuard / R8 obfuscation indicators
_PROGUARD_CLASS_PATTERN = re.compile(r'^[a-z]{1,2}(\.[a-z]{1,2})*\.[a-z]{1,2}$')


def _scan_methods_for_suspicious_apis(
    methods: List[str],
) -> Dict[str, List[str]]:
    """Match method signatures against suspicious API patterns.

    Returns dict mapping category -> list of matched method signatures.
    """
    hits: Dict[str, List[str]] = {}
    for method in methods:
        for category, patterns in _COMPILED_PATTERNS.items():
            for pat in patterns:
                if pat.search(method):
                    hits.setdefault(category, []).append(method)
                    break  # one match per category per method is enough
    return hits


def _compute_obfuscation_score(
    classes: List[str],
    methods: List[str],
    strings: List[str],
) -> tuple[float, List[str]]:
    """Estimate obfuscation likelihood from naming patterns and string density.

    Returns (score 0-1, list of indicator descriptions).
    """
    indicators = []
    scores = []

    # 1. Short class name ratio (single-letter or two-letter class names)
    if classes:
        short_classes = sum(
            1 for c in classes
            if len(c.split("/")[-1].rstrip(";")) <= 2
        )
        short_ratio = short_classes / len(classes)
        scores.append(short_ratio)
        if short_ratio > 0.3:
            indicators.append(
                f"High short class name ratio: {short_ratio:.1%} "
                f"({short_classes}/{len(classes)})"
            )

    # 2. ProGuard-style naming patterns
    if classes:
        proguard_matches = sum(
            1 for c in classes
            if _PROGUARD_CLASS_PATTERN.match(
                c.replace("/", ".").lstrip("L").rstrip(";")
            )
        )
        pg_ratio = proguard_matches / len(classes)
        scores.append(pg_ratio)
        if pg_ratio > 0.2:
            indicators.append(
                f"ProGuard naming patterns detected: {pg_ratio:.1%}"
            )

    # 3. Short method name ratio
    if methods:
        short_methods = sum(
            1 for m in methods
            if len(m.split("->")[-1].split("(")[0]) <= 2
        )
        sm_ratio = short_methods / len(methods)
        scores.append(sm_ratio)
        if sm_ratio > 0.3:
            indicators.append(
                f"High short method name ratio: {sm_ratio:.1%}"
            )

    # 4. Base64-encoded string density
    if strings:
        b64_count = sum(1 for s in strings if _BASE64_PATTERN.match(s))
        b64_ratio = b64_count / len(strings)
        scores.append(min(b64_ratio * 5, 1.0))  # amplify low ratios
        if b64_count > 10:
            indicators.append(
                f"Embedded base64 strings: {b64_count}"
            )

    if not scores:
        return 0.0, indicators

    return round(sum(scores) / len(scores), 3), indicators


def _extract_embedded_data(
    strings: List[str],
) -> tuple[List[str], List[str], int]:
    """Extract URLs, IPs, and count base64 strings from string constants.

    Returns (urls, ips, base64_count).
    """
    urls = set()
    ips = set()
    b64_count = 0

    for s in strings:
        for url in _URL_PATTERN.findall(s):
            urls.add(url)
        for ip in _IP_PATTERN.findall(s):
            # Filter common non-suspicious IPs
            if not ip.startswith(("0.", "127.", "255.")):
                ips.add(ip)
        if _BASE64_PATTERN.match(s):
            b64_count += 1

    return sorted(urls), sorted(ips), b64_count


def analyze_dex(dex_data: Dict[str, Any]) -> CodeMetrics:
    """Analyze DEX static analysis output for suspicious patterns.

    Args:
        dex_data: Dict keyed by dex file name (e.g. "dex_0"), each value
                  is a dict with keys: classes, methods, fields, strings.

    Returns:
        CodeMetrics with suspicious API findings and obfuscation score.
    """
    if not dex_data:
        return CodeMetrics()

    all_classes: List[str] = []
    all_methods: List[str] = []
    all_fields: List[str] = []
    all_strings: List[str] = []

    for dex_key, dex_content in dex_data.items():
        if not isinstance(dex_content, dict):
            continue
        all_classes.extend(dex_content.get("classes", []))
        all_methods.extend(dex_content.get("methods", []))
        all_fields.extend(dex_content.get("fields", []))
        all_strings.extend(dex_content.get("strings", []))

    # Scan for suspicious APIs
    suspicious = _scan_methods_for_suspicious_apis(all_methods)
    suspicious_count = sum(len(v) for v in suspicious.values())

    # Obfuscation analysis
    obf_score, obf_indicators = _compute_obfuscation_score(
        all_classes, all_methods, all_strings
    )

    # Embedded data extraction
    urls, ips, b64_count = _extract_embedded_data(all_strings)

    return CodeMetrics(
        total_classes=len(all_classes),
        total_methods=len(all_methods),
        total_fields=len(all_fields),
        total_strings=len(all_strings),
        suspicious_api_calls=suspicious,
        suspicious_api_count=suspicious_count,
        obfuscation_score=obf_score,
        obfuscation_indicators=obf_indicators,
        embedded_urls=urls[:100],  # cap at 100 to avoid huge payloads
        embedded_ips=ips[:50],
        base64_strings_count=b64_count,
    )
