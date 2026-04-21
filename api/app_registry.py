"""Centralized app registry — singleton index of all analyzed apps.

Replaces the duplicated _find_app_output_dir / _scan_output_directory pattern
that was copy-pasted across four routers.
"""

import json
import logging
import os
import threading

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.environ.get("INSTRUMATE_OUTPUT_DIR", "./output")


class AppRegistry:
    """Thread-safe in-memory index of analyzed apps (app_id -> entry)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._index: dict[str, dict] = {}  # app_id -> {app_data, output_dir}
        self._loaded = False

    def _ensure_loaded(self):
        if not self._loaded:
            self.refresh()

    def refresh(self):
        """Re-scan the output directory and rebuild the index."""
        new_index: dict[str, dict] = {}
        if os.path.isdir(OUTPUT_DIR):
            for pkg_name in os.listdir(OUTPUT_DIR):
                pkg_dir = os.path.join(OUTPUT_DIR, pkg_name)
                if not os.path.isdir(pkg_dir):
                    continue
                for variant_dir_name in os.listdir(pkg_dir):
                    variant_dir = os.path.join(pkg_dir, variant_dir_name)
                    app_json_path = os.path.join(variant_dir, "app.json")
                    if os.path.isfile(app_json_path):
                        try:
                            with open(app_json_path, "r", encoding="utf-8") as f:
                                app_data = json.load(f)
                            app_id = app_data.get("app_id")
                            if app_id:
                                new_index[app_id] = {
                                    "app_data": app_data,
                                    "output_dir": variant_dir,
                                }
                        except (json.JSONDecodeError, OSError) as e:
                            logger.warning("Skipping %s: %s", app_json_path, e)
        with self._lock:
            self._index = new_index
            self._loaded = True
        logger.info("AppRegistry refreshed: %d apps indexed", len(new_index))

    def list_all(self) -> list[dict]:
        """Return all app entries as a list of {app_data, output_dir}."""
        self._ensure_loaded()
        with self._lock:
            return list(self._index.values())

    def get(self, app_id: str) -> dict | None:
        """Get a single app entry by app_id. Auto-refreshes on cache miss."""
        self._ensure_loaded()
        with self._lock:
            entry = self._index.get(app_id)
        if entry is not None:
            return entry
        # Cache miss — maybe the app was just analyzed
        self.refresh()
        with self._lock:
            return self._index.get(app_id)

    def get_output_dir(self, app_id: str) -> str | None:
        """Get the output directory path for an app_id."""
        entry = self.get(app_id)
        return entry["output_dir"] if entry else None


# Module-level singleton
registry = AppRegistry()
