"""LLM-based APK classifier using Ollama.

Builds a structured prompt from APKSecurityMetrics, sends it to a local
Ollama instance, and parses the JSON response into a ClassificationResult.
Handles Ollama unavailability gracefully with safe defaults.
"""

import json
import logging
import os
from typing import Optional

import httpx

from pymate.classification.models import (
    APKSecurityMetrics,
    ClassificationResult,
    RiskFactor,
    SecurityRiskLevel,
    MalwareLikelihood,
)

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "REMOVED_SECRET_URL"
DEFAULT_MODEL = "mistral"
GENERATION_TIMEOUT = 120.0  # seconds


def _build_prompt(metrics: APKSecurityMetrics) -> str:
    """Build a structured classification prompt from security metrics."""
    sections = []

    sections.append(
        "You are a mobile security analyst. Analyze the following Android APK "
        "security metrics and provide a JSON classification.\n"
    )

    # App info
    sections.append(f"## App Information")
    sections.append(f"- Package: {metrics.package_name}")
    if metrics.app_name:
        sections.append(f"- App Name: {metrics.app_name}")
    if metrics.version_name:
        sections.append(f"- Version: {metrics.version_name} ({metrics.version_code})")
    if metrics.target_sdk_version:
        sections.append(f"- Target SDK: {metrics.target_sdk_version}")
    sections.append(f"- Is repackaged variant: {metrics.is_variant}")
    sections.append("")

    # Permissions
    p = metrics.permissions
    sections.append(f"## Permissions ({p.total_permissions} total)")
    sections.append(f"- Dangerous permissions ({p.dangerous_count}): "
                    f"{', '.join(p.dangerous_permissions) if p.dangerous_permissions else 'none'}")
    if p.categories:
        sections.append(f"- Categories present: {', '.join(p.categories.keys())}")
    if p.suspicious_combinations:
        sections.append("- Suspicious combinations detected:")
        for combo in p.suspicious_combinations:
            sections.append(f"  - {combo['name']}: {combo['description']}")
    sections.append(f"- Permission risk score: {p.permission_risk_score}")
    sections.append("")

    # Code analysis
    c = metrics.code
    sections.append(f"## Code Analysis")
    sections.append(
        f"- Classes: {c.total_classes}, Methods: {c.total_methods}, "
        f"Strings: {c.total_strings}"
    )
    if c.suspicious_api_calls:
        sections.append(
            f"- Suspicious API calls ({c.suspicious_api_count} total):"
        )
        for cat, calls in c.suspicious_api_calls.items():
            sections.append(f"  - {cat}: {len(calls)} calls")
    sections.append(f"- Obfuscation score: {c.obfuscation_score}")
    if c.obfuscation_indicators:
        for ind in c.obfuscation_indicators:
            sections.append(f"  - {ind}")
    if c.embedded_urls:
        sections.append(f"- Embedded URLs: {len(c.embedded_urls)}")
    if c.embedded_ips:
        sections.append(f"- Embedded IPs: {len(c.embedded_ips)}")
    if c.base64_strings_count > 0:
        sections.append(f"- Base64-encoded strings: {c.base64_strings_count}")
    sections.append("")

    # Call graph
    cg = metrics.call_graph
    if cg.total_nodes > 0:
        sections.append(f"## Call Graph")
        sections.append(
            f"- Nodes: {cg.total_nodes}, Edges: {cg.total_edges}, "
            f"Density: {cg.density}"
        )
        sections.append(
            f"- Max in-degree: {cg.max_in_degree}, "
            f"Max out-degree: {cg.max_out_degree}"
        )
        if cg.sensitive_api_reachability:
            sections.append(
                f"- Sensitive API families reachable ({cg.sensitive_api_count} nodes):"
            )
            for family, nodes in cg.sensitive_api_reachability.items():
                sections.append(f"  - {family}: {len(nodes)} nodes")
        sections.append(f"- Entry points found: {len(cg.entry_points)}")
        sections.append("")

    # Content
    ct = metrics.content
    if ct.total_files > 0:
        sections.append(f"## Content Analysis ({ct.total_files} files)")
        sections.append(
            f"- Code-to-resource ratio: {ct.code_to_resource_ratio}"
        )
        if ct.file_type_distribution:
            dist_str = ", ".join(
                f"{k}: {v}" for k, v in ct.file_type_distribution.items()
            )
            sections.append(f"- Distribution: {dist_str}")
        flags = []
        if ct.has_automation_scripts:
            flags.append("automation scripts")
        if ct.has_crypto_materials:
            flags.append("crypto materials")
        if ct.has_hidden_executables:
            flags.append("hidden executables")
        if flags:
            sections.append(f"- Anomalies: {', '.join(flags)}")
        if ct.unusual_file_types:
            sections.append(
                f"- Unusual types: {', '.join(ct.unusual_file_types)}"
            )
        sections.append("")

    # Classification request
    sections.append("## Task")
    sections.append(
        "Based on the above metrics, provide a security assessment as a JSON "
        "object with exactly these fields:\n"
        '- "security_risk_level": one of "low", "medium", "high", "critical"\n'
        '- "malware_likelihood": one of "benign", "suspicious", "likely_malicious"\n'
        '- "confidence": float 0.0-1.0\n'
        '- "risk_factors": list of objects with "category", "description", '
        '"severity" (low/medium/high/critical)\n'
        '- "recommendations": list of actionable recommendation strings\n'
        '- "reasoning": brief explanation of the assessment\n\n'
        "Respond ONLY with the JSON object, no markdown or extra text."
    )

    return "\n".join(sections)


def _parse_llm_response(raw: str, model: str) -> ClassificationResult:
    """Extract and parse JSON from LLM response text."""
    # Find JSON between first { and last }
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        logger.warning("No JSON object found in LLM response")
        return ClassificationResult(
            reasoning="Failed to parse LLM response",
            model_used=model,
        )

    json_str = raw[start:end + 1]
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse LLM JSON: %s", e)
        return ClassificationResult(
            reasoning=f"JSON parse error: {e}",
            model_used=model,
        )

    # Map risk factors
    risk_factors = []
    for rf in data.get("risk_factors", []):
        if isinstance(rf, dict):
            severity_str = rf.get("severity", "low").lower()
            try:
                severity = SecurityRiskLevel(severity_str)
            except ValueError:
                severity = SecurityRiskLevel.LOW
            risk_factors.append(RiskFactor(
                category=rf.get("category", "unknown"),
                description=rf.get("description", ""),
                severity=severity,
            ))

    # Parse top-level fields with safe defaults
    try:
        risk_level = SecurityRiskLevel(
            data.get("security_risk_level", "low").lower()
        )
    except ValueError:
        risk_level = SecurityRiskLevel.LOW

    try:
        malware = MalwareLikelihood(
            data.get("malware_likelihood", "benign").lower()
        )
    except ValueError:
        malware = MalwareLikelihood.BENIGN

    confidence = float(data.get("confidence", 0.0))
    confidence = max(0.0, min(1.0, confidence))

    return ClassificationResult(
        security_risk_level=risk_level,
        malware_likelihood=malware,
        confidence=round(confidence, 3),
        risk_factors=risk_factors,
        recommendations=data.get("recommendations", []),
        reasoning=data.get("reasoning", ""),
        model_used=model,
    )


class LLMClassifier:
    """Classifies APK security metrics using a local Ollama LLM."""

    def __init__(
        self,
        ollama_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.ollama_url = (
            ollama_url
            or os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)
        )
        self.model = (
            model
            or os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)
        )

    def is_available(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            resp = httpx.get(f"{self.ollama_url}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException, Exception):
            return False

    def classify(
        self,
        metrics: APKSecurityMetrics,
    ) -> ClassificationResult:
        """Send metrics to Ollama and return classification.

        If Ollama is unreachable, returns a safe default result with
        confidence=0.0.
        """
        prompt = _build_prompt(metrics)

        try:
            resp = httpx.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                    },
                },
                timeout=GENERATION_TIMEOUT,
            )
            resp.raise_for_status()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning("Ollama unreachable: %s", e)
            return ClassificationResult(
                reasoning="Ollama service unavailable — using safe defaults",
                model_used=self.model,
            )
        except httpx.HTTPStatusError as e:
            logger.warning("Ollama HTTP error: %s", e)
            return ClassificationResult(
                reasoning=f"Ollama HTTP error: {e.response.status_code}",
                model_used=self.model,
            )

        raw_response = resp.json().get("response", "")
        logger.debug("Raw LLM response: %s", raw_response[:500])

        result = _parse_llm_response(raw_response, self.model)

        # Attach a summary of the input metrics
        result.metrics_summary = {
            "package_name": metrics.package_name,
            "permission_risk_score": metrics.permissions.permission_risk_score,
            "dangerous_permissions_count": metrics.permissions.dangerous_count,
            "suspicious_api_count": metrics.code.suspicious_api_count,
            "obfuscation_score": metrics.code.obfuscation_score,
            "callgraph_sensitive_apis": metrics.call_graph.sensitive_api_count,
            "content_anomalies": (
                metrics.content.has_automation_scripts
                or metrics.content.has_crypto_materials
                or metrics.content.has_hidden_executables
            ),
        }

        return result

    def classify_and_save(
        self,
        metrics: APKSecurityMetrics,
        output_dir: str,
    ) -> ClassificationResult:
        """Classify metrics and save result to classification.json.

        Args:
            metrics: The extracted security metrics.
            output_dir: App output directory to save classification.json into.

        Returns:
            The ClassificationResult.
        """
        result = self.classify(metrics)
        output_path = os.path.join(output_dir, "classification.json")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))
        logger.info("Classification saved to %s", output_path)
        return result
