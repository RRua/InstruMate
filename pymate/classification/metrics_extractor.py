"""Metrics extractor — orchestrates the four sub-analyzers.

Reads app.json and all analysis output files from an app's output directory,
delegates to permission_analysis, code_analysis, callgraph_analysis, and
content_analysis, then returns a complete APKSecurityMetrics object.
"""

import json
import logging
import os

from pymate.classification.models import APKSecurityMetrics
from pymate.classification.permission_analysis import analyze_permissions
from pymate.classification.code_analysis import analyze_dex
from pymate.classification.callgraph_analysis import analyze_call_graph
from pymate.classification.content_analysis import analyze_content_from_csv

logger = logging.getLogger(__name__)


class MetricsExtractor:
    """Reads InstruMate analysis output and computes security metrics."""

    def __init__(self, output_dir: str):
        """
        Args:
            output_dir: Path to the app's output directory containing
                        app.json and analysis result files.
        """
        self.output_dir = output_dir

    def _read_json(self, filename: str) -> dict | list | None:
        """Read a JSON file from the output directory."""
        path = os.path.join(self.output_dir, filename)
        if not os.path.isfile(path):
            logger.debug("File not found: %s", path)
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read %s: %s", path, e)
            return None

    def extract(self) -> APKSecurityMetrics:
        """Run all sub-analyzers and return combined metrics.

        Returns:
            APKSecurityMetrics with all available analysis results.
        """
        # Load app metadata
        app_data = self._read_json("app.json")
        if app_data is None:
            logger.error("app.json not found in %s", self.output_dir)
            return APKSecurityMetrics()

        metrics = APKSecurityMetrics(
            package_name=app_data.get("package_name", ""),
            app_name=app_data.get("app_name"),
            version_name=app_data.get("app_version_name"),
            version_code=app_data.get("app_version_code"),
            min_sdk_version=app_data.get("min_sdk_version"),
            target_sdk_version=app_data.get("target_sdk_version"),
            is_variant=app_data.get("variant_info") is not None,
        )

        # Stage 1a: Permission analysis
        permissions = app_data.get("permissions", [])
        if permissions:
            logger.info("Analyzing %d permissions", len(permissions))
            metrics.permissions = analyze_permissions(permissions)

        # Stage 1b: DEX code analysis
        dex_data = self._read_json("dex_static_analysis.json")
        if dex_data and isinstance(dex_data, dict):
            logger.info("Analyzing DEX data (%d files)", len(dex_data))
            metrics.code = analyze_dex(dex_data)

        # Stage 1c: Call graph analysis
        cg_data = self._read_json("call_graph.json")
        if cg_data and isinstance(cg_data, dict):
            logger.info(
                "Analyzing call graph (%d nodes, %d edges)",
                len(cg_data.get("nodes", [])),
                len(cg_data.get("edges", [])),
            )
            metrics.call_graph = analyze_call_graph(cg_data)

        # Stage 1d: Content type analysis
        csv_path = os.path.join(self.output_dir, "content_type_analysis.csv")
        if os.path.isfile(csv_path):
            logger.info("Analyzing content types from CSV")
            metrics.content = analyze_content_from_csv(csv_path)

        return metrics

    def extract_and_save(self) -> APKSecurityMetrics:
        """Extract metrics and save to security_metrics.json.

        Returns:
            The extracted APKSecurityMetrics.
        """
        metrics = self.extract()
        output_path = os.path.join(self.output_dir, "security_metrics.json")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(metrics.model_dump_json(indent=2))
        logger.info("Security metrics saved to %s", output_path)
        return metrics
