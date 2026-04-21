"""InstruMate APK Security Classification Module.

Two-stage classification pipeline:
  Stage 1 — Metrics Extractor: Reads analysis output files and computes
            structured security-relevant metrics.
  Stage 2 — LLM Classifier: Sends structured metrics to Ollama for
            security risk assessment and malware likelihood classification.
"""

from pymate.classification.models import (
    APKSecurityMetrics,
    ClassificationResult,
    SecurityRiskLevel,
    MalwareLikelihood,
)
from pymate.classification.metrics_extractor import MetricsExtractor
from pymate.classification.llm_classifier import LLMClassifier

__all__ = [
    "APKSecurityMetrics",
    "ClassificationResult",
    "SecurityRiskLevel",
    "MalwareLikelihood",
    "MetricsExtractor",
    "LLMClassifier",
]
