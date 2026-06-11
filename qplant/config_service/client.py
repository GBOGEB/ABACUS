"""QPLANT Config Service — Client SDK.

Provides a simple Python client for accessing the config service
from any component (Python engine, monitoring, API layer).

Usage:
    from config_service.client import ConfigClient

    client = ConfigClient()  # Defaults to http://localhost:8200
    config = client.get_all()
    value = client.get_value("compressor_specifications.hp_compressors.count")

For non-API access (direct file access):
    from config_service.client import DirectConfigClient

    client = DirectConfigClient("/path/to/config.yaml")
    config = client.get_all()
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class ConfigClient:
    """HTTP client for the config service API."""

    def __init__(self, base_url: str = "http://localhost:8200"):
        self.base_url = base_url.rstrip("/")
        try:
            import requests
            self._requests = requests
        except ImportError:
            self._requests = None
            logger.warning("requests library not available; install with: pip install requests")

    def _get(self, path: str) -> Any:
        if not self._requests:
            raise RuntimeError("requests library required for HTTP client")
        resp = self._requests.get(f"{self.base_url}{path}", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict) -> Any:
        if not self._requests:
            raise RuntimeError("requests library required for HTTP client")
        resp = self._requests.post(f"{self.base_url}{path}", json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def health(self) -> Dict[str, Any]:
        return self._get("/api/v1/health")

    def get_all(self) -> Dict[str, Any]:
        return self._get("/api/v1/config")

    def get_section(self, section: str) -> Any:
        return self._get(f"/api/v1/config/section/{section}")

    def get_value(self, path: str) -> Any:
        result = self._get(f"/api/v1/config/value?path={path}")
        return result.get("value")

    def set_value(self, path: str, value: Any, user: str = "sdk", reason: str = "") -> Dict:
        return self._post("/api/v1/config/set", {
            "path": path, "value": value, "user": user, "reason": reason
        })

    def validate(self) -> Dict[str, Any]:
        return self._get("/api/v1/config/validate")

    def get_schema(self) -> Dict[str, Any]:
        return self._get("/api/v1/config/schema")

    def get_history(self) -> list:
        return self._get("/api/v1/config/history")

    def reload(self) -> Dict[str, Any]:
        return self._post("/api/v1/config/reload", {})

    def get_hash(self) -> str:
        result = self._get("/api/v1/config/hash")
        return result.get("hash", "")


class DirectConfigClient:
    """Direct file-based config client (no HTTP server needed).

    Use this when the config service API is not running (e.g., in build scripts).
    """

    def __init__(self, config_path: str = "data/config.yaml"):
        self._path = Path(config_path).resolve()
        self._config: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            raise FileNotFoundError(f"Config not found: {self._path}")
        with open(self._path) as f:
            self._config = yaml.safe_load(f) or {}

    def get_all(self) -> Dict[str, Any]:
        return dict(self._config)

    def get_section(self, section: str) -> Any:
        if section not in self._config:
            raise KeyError(f"Section not found: {section}")
        return self._config[section]

    def get_value(self, path: str) -> Any:
        parts = path.split(".")
        current = self._config
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise KeyError(f"Path not found: {path}")
        return current

    def reload(self) -> None:
        self._load()
