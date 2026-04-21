from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class VariantCreateRequest(BaseModel):
    variant_makers: List[str] = ["zip", "apkeditor", "apktool"]
    variant_specs: List[str] = ["signature"]


class AppSummary(BaseModel):
    app_id: str
    package_name: str
    version_name: Optional[str] = None
    version_code: Optional[str] = None
    is_variant: bool = False
    output_dir: str
    has_classification: bool = False
    has_virustotal_report: bool = False
    has_security_metrics: bool = False


class PaginatedApps(BaseModel):
    items: List["AppSummary"]
    total: int
    page: int
    per_page: int
    pages: int


class AppDetail(BaseModel):
    app_id: str
    package_name: Optional[str] = None
    app_name: Optional[str] = None
    version_name: Optional[str] = None
    version_code: Optional[str] = None
    min_sdk_version: Optional[str] = None
    max_sdk_version: Optional[str] = None
    target_sdk_version: Optional[str] = None
    main_activity: Optional[str] = None
    permissions: Optional[List[str]] = None
    activities: Optional[List[str]] = None
    services: Optional[List[str]] = None
    features: Optional[List[str]] = None
    is_variant: bool = False
    variant_info: Optional[Dict[str, Any]] = None
    has_content_type_analysis: bool = False
    has_dex_analysis: bool = False
    has_call_graph: bool = False
    has_classification: bool = False
    has_security_metrics: bool = False
    has_virustotal_report: bool = False


class AnalysisResult(BaseModel):
    content_type_analysis: Optional[List[Dict[str, Any]]] = None
    dex_static_analysis: Optional[List[Dict[str, Any]]] = None
    native_static_analysis: Optional[List[Dict[str, Any]]] = None
    possible_modifications: Optional[Dict[str, Any]] = None


class JobStatus(BaseModel):
    job_id: str
    status: AnalysisStatus
    message: Optional[str] = None
    app_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    java_available: bool
    jdk8_available: bool
    tools_available: Dict[str, bool]
    python_version: str
    analyzers_available: List[str]
    variant_makers_available: List[str]
    ollama_available: bool = False
    virustotal_configured: bool = False
    auth_enabled: bool = False
