"""Pydantic models for APK security metrics and classification results."""

from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class SecurityRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MalwareLikelihood(str, Enum):
    BENIGN = "benign"
    SUSPICIOUS = "suspicious"
    LIKELY_MALICIOUS = "likely_malicious"


class PermissionCategory(str, Enum):
    PRIVACY = "privacy"
    NETWORK = "network"
    SYSTEM = "system"
    HARDWARE = "hardware"
    FINANCIAL = "financial"


class SuspiciousAPICategory(str, Enum):
    REFLECTION = "reflection"
    DYNAMIC_LOADING = "dynamic_loading"
    NATIVE_CALLS = "native_calls"
    CRYPTO = "crypto"
    RUNTIME_EXEC = "runtime_exec"
    NETWORK = "network"
    SMS_TELEPHONY = "sms_telephony"
    ACCESSIBILITY = "accessibility"


# --- Sub-metric models ---


class PermissionMetrics(BaseModel):
    total_permissions: int = 0
    dangerous_permissions: List[str] = Field(default_factory=list)
    dangerous_count: int = 0
    categories: Dict[str, List[str]] = Field(default_factory=dict)
    suspicious_combinations: List[Dict[str, str]] = Field(default_factory=list)
    permission_risk_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Normalized permission risk score (0-1)",
    )


class CodeMetrics(BaseModel):
    total_classes: int = 0
    total_methods: int = 0
    total_fields: int = 0
    total_strings: int = 0
    suspicious_api_calls: Dict[str, List[str]] = Field(default_factory=dict)
    suspicious_api_count: int = 0
    obfuscation_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Obfuscation likelihood score (0-1)",
    )
    obfuscation_indicators: List[str] = Field(default_factory=list)
    embedded_urls: List[str] = Field(default_factory=list)
    embedded_ips: List[str] = Field(default_factory=list)
    base64_strings_count: int = 0


class CallGraphMetrics(BaseModel):
    total_nodes: int = 0
    total_edges: int = 0
    density: float = 0.0
    avg_in_degree: float = 0.0
    avg_out_degree: float = 0.0
    max_in_degree: int = 0
    max_out_degree: int = 0
    sensitive_api_reachability: Dict[str, List[str]] = Field(default_factory=dict)
    sensitive_api_count: int = 0
    entry_points: List[str] = Field(default_factory=list)


class ContentMetrics(BaseModel):
    total_files: int = 0
    file_type_distribution: Dict[str, int] = Field(default_factory=dict)
    code_to_resource_ratio: float = 0.0
    has_automation_scripts: bool = False
    has_crypto_materials: bool = False
    has_hidden_executables: bool = False
    unusual_file_types: List[str] = Field(default_factory=list)


# --- Top-level metrics ---


class APKSecurityMetrics(BaseModel):
    package_name: str = ""
    app_name: Optional[str] = None
    version_name: Optional[str] = None
    version_code: Optional[str] = None
    min_sdk_version: Optional[str] = None
    target_sdk_version: Optional[str] = None
    is_variant: bool = False
    permissions: PermissionMetrics = Field(default_factory=PermissionMetrics)
    code: CodeMetrics = Field(default_factory=CodeMetrics)
    call_graph: CallGraphMetrics = Field(default_factory=CallGraphMetrics)
    content: ContentMetrics = Field(default_factory=ContentMetrics)


# --- Classification result ---


class RiskFactor(BaseModel):
    category: str
    description: str
    severity: SecurityRiskLevel


class ClassificationResult(BaseModel):
    security_risk_level: SecurityRiskLevel = SecurityRiskLevel.LOW
    malware_likelihood: MalwareLikelihood = MalwareLikelihood.BENIGN
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Model confidence in the classification (0-1)",
    )
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    reasoning: str = ""
    model_used: str = ""
    metrics_summary: Optional[Dict] = None
