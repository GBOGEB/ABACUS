"""QPLANT Centralised Configuration Service.

Provides version-controlled configuration access with audit trail,
validation, environment-specific overrides, and hot-reload capability.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .schemas import (
    ConfigChange,
    ConfigHistory,
    ConfigVersion,
    Environment,
    QplantConfig,
)

logger = logging.getLogger(__name__)


class ConfigService:
    """Centralised SSOT configuration service with versioning and audit.

    Features:
    - Load from YAML file (SSoT)
    - Environment-specific overrides (dev, staging, prod, dr)
    - Validation via Pydantic schemas
    - Version-controlled change history
    - Change audit trail
    - Hot-reload capability (file watcher)
    - Thread-safe access
    """

    def __init__(
        self,
        config_path: str = "data/config.yaml",
        env: Environment = Environment.DEV,
        history_path: Optional[str] = None,
        auto_reload: bool = False,
        reload_interval: int = 5,
    ):
        self._config_path = Path(config_path).resolve()
        self._env = env
        self._history_path = Path(history_path) if history_path else self._config_path.parent / "config_history.json"
        self._auto_reload = auto_reload
        self._reload_interval = reload_interval
        self._lock = threading.RLock()
        self._config: Dict[str, Any] = {}
        self._validated: Optional[QplantConfig] = None
        self._history = ConfigHistory()
        self._last_hash: str = ""
        self._last_modified: float = 0.0
        self._watcher_thread: Optional[threading.Thread] = None

        # Load initial config
        self._load_config()
        self._load_history()

        # Start file watcher if requested
        if auto_reload:
            self._start_watcher()

    # ── Public API ───────────────────────────────────────────────────────────

    def get_all(self) -> Dict[str, Any]:
        """Return the full configuration dict."""
        with self._lock:
            return copy.deepcopy(self._config)

    def get_section(self, section: str) -> Any:
        """Return a specific top-level section."""
        with self._lock:
            if section not in self._config:
                raise KeyError(f"Section not found: {section}")
            return copy.deepcopy(self._config[section])

    def get_value(self, path: str) -> Any:
        """Get a value by dot-notation path (e.g. 'compressor_specifications.hp_compressors.count')."""
        with self._lock:
            parts = path.split(".")
            current = self._config
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    raise KeyError(f"Path not found: {path}")
            return copy.deepcopy(current) if isinstance(current, (dict, list)) else current

    def set_value(self, path: str, value: Any, user: str = "system", reason: str = "") -> ConfigChange:
        """Set a configuration value with audit trail."""
        with self._lock:
            old_value = None
            try:
                old_value = self.get_value(path)
            except KeyError:
                pass

            # Apply change
            parts = path.split(".")
            current = self._config
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value

            # Validate
            self._validate()

            # Record change
            change = ConfigChange(
                timestamp=datetime.now(timezone.utc).isoformat(),
                user=user,
                path=path,
                old_value=old_value,
                new_value=value,
                reason=reason,
            )
            self._record_change(change)

            # Save to disk
            self._save_config()

            logger.info(f"Config updated: {path} = {value} (by {user})")
            return change

    def validate(self) -> Dict[str, Any]:
        """Validate current config against Pydantic schema."""
        with self._lock:
            try:
                self._validated = QplantConfig(**self._config)
                return {
                    "valid": True,
                    "version": self._validated.version,
                    "sections": list(self._config.keys()),
                    "errors": [],
                }
            except Exception as e:
                return {
                    "valid": False,
                    "errors": [str(e)],
                }

    def get_history(self) -> List[Dict[str, Any]]:
        """Return version history."""
        with self._lock:
            return [v.model_dump() for v in self._history.versions]

    def get_env(self) -> str:
        """Return current environment."""
        return self._env.value

    def get_hash(self) -> str:
        """Return current config hash."""
        with self._lock:
            return self._compute_hash()

    def get_diff(self, version1: str, version2: str) -> List[Dict[str, Any]]:
        """Get changes between two versions."""
        with self._lock:
            changes = []
            for v in self._history.versions:
                if v.version == version2:
                    changes.extend([c.model_dump() for c in v.changes])
            return changes

    def reload(self) -> bool:
        """Reload configuration from disk."""
        with self._lock:
            current_hash = self._compute_file_hash()
            if current_hash != self._last_hash:
                self._load_config()
                logger.info("Config reloaded from disk")
                return True
            return False

    def export_env_config(self, env: Environment) -> Dict[str, Any]:
        """Export config with environment-specific overrides."""
        with self._lock:
            config = copy.deepcopy(self._config)
            env_overrides = self._get_env_overrides(env)
            self._merge_dict(config, env_overrides)
            return config

    def get_metrics(self) -> Dict[str, Any]:
        """Return service metrics for monitoring."""
        with self._lock:
            return {
                "config_path": str(self._config_path),
                "environment": self._env.value,
                "config_hash": self._compute_hash(),
                "version": self._config.get("version", "unknown"),
                "sections": list(self._config.keys()),
                "section_count": len(self._config),
                "history_versions": len(self._history.versions),
                "auto_reload": self._auto_reload,
                "last_modified": self._last_modified,
            }

    # ── Private Methods ──────────────────────────────────────────────────────

    def _load_config(self) -> None:
        """Load YAML config from disk."""
        if not self._config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self._config_path}")

        with open(self._config_path, "r") as f:
            self._config = yaml.safe_load(f) or {}

        # Apply environment overrides
        env_overrides = self._get_env_overrides(self._env)
        self._merge_dict(self._config, env_overrides)

        self._last_hash = self._compute_file_hash()
        self._last_modified = self._config_path.stat().st_mtime

        # Validate
        self._validate()
        logger.info(f"Config loaded: v{self._config.get('version', '?')} ({self._env.value})")

    def _validate(self) -> None:
        """Validate config against Pydantic schema."""
        try:
            self._validated = QplantConfig(**self._config)
        except Exception as e:
            logger.warning(f"Config validation warning: {e}")

    def _save_config(self) -> None:
        """Save current config to YAML."""
        with open(self._config_path, "w") as f:
            yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
        self._last_hash = self._compute_file_hash()
        self._last_modified = time.time()

    def _compute_hash(self) -> str:
        """Compute hash of current in-memory config."""
        config_str = json.dumps(self._config, sort_keys=True, default=str)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]

    def _compute_file_hash(self) -> str:
        """Compute hash of config file on disk."""
        if self._config_path.exists():
            return hashlib.sha256(self._config_path.read_bytes()).hexdigest()[:16]
        return ""

    def _record_change(self, change: ConfigChange) -> None:
        """Record a change in history."""
        version = self._config.get("version", "unknown")
        current_version = None
        for v in self._history.versions:
            if v.version == version:
                current_version = v
                break

        if current_version is None:
            current_version = ConfigVersion(
                version=version,
                timestamp=change.timestamp,
                config_hash=self._compute_hash(),
            )
            self._history.versions.append(current_version)

        current_version.changes.append(change)
        current_version.config_hash = self._compute_hash()

        self._save_history()

    def _load_history(self) -> None:
        """Load change history from disk."""
        if self._history_path.exists():
            try:
                data = json.loads(self._history_path.read_text())
                self._history = ConfigHistory(**data)
            except Exception as e:
                logger.warning(f"Could not load history: {e}")
                self._history = ConfigHistory()

    def _save_history(self) -> None:
        """Save change history to disk."""
        self._history_path.write_text(
            json.dumps(self._history.model_dump(), indent=2, default=str)
        )

    def _get_env_overrides(self, env: Environment) -> Dict[str, Any]:
        """Get environment-specific overrides from overlay files."""
        overlay_path = self._config_path.parent / f"config.{env.value}.yaml"
        if overlay_path.exists():
            with open(overlay_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _merge_dict(self, base: dict, overlay: dict) -> None:
        """Deep-merge overlay into base dict."""
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_dict(base[key], value)
            else:
                base[key] = value

    def _start_watcher(self) -> None:
        """Start file watcher thread for hot-reload."""
        def watch():
            while self._auto_reload:
                try:
                    self.reload()
                except Exception as e:
                    logger.error(f"Reload error: {e}")
                time.sleep(self._reload_interval)

        self._watcher_thread = threading.Thread(target=watch, daemon=True, name="config-watcher")
        self._watcher_thread.start()
        logger.info(f"Config watcher started (interval={self._reload_interval}s)")

    def stop(self) -> None:
        """Stop the config service and file watcher."""
        self._auto_reload = False
        if self._watcher_thread:
            self._watcher_thread.join(timeout=10)
