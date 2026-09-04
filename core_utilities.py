"""Core utility helpers used by the ABACUS parent test suite."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class TemporalContext:
    """Execution time context."""

    session_id: str
    timestamp: datetime
    dow: str
    week_number: int
    year: int


class WorkspaceUtilities:
    """Workspace file and serialization utilities."""

    @staticmethod
    def load_config(path: Path | str) -> dict[str, Any]:
        config_path = Path(path)
        if not config_path.exists():
            return {}
        if config_path.suffix.lower() == ".json":
            return json.loads(config_path.read_text(encoding="utf-8"))
        if config_path.suffix.lower() in {".yaml", ".yml"}:
            return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        return {}

    @staticmethod
    def save_json(data: Any, path: Path | str) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    @staticmethod
    def save_yaml(data: Any, path: Path | str) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(yaml.safe_dump(data, sort_keys=True), encoding="utf-8")

    @staticmethod
    def save_text(content: str, path: Path | str) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

    @staticmethod
    def to_json(data: Any) -> str:
        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def get_temporal_context() -> TemporalContext:
        now = datetime.now()
        return TemporalContext(
            session_id=f"session-{now.strftime('%Y%m%d%H%M%S')}",
            timestamp=now,
            dow=now.strftime("%A"),
            week_number=int(now.strftime("%V")),
            year=now.year,
        )


class PathUtilities:
    """Path scanning helpers."""

    @staticmethod
    def scan_files(
        root: Path | str,
        patterns: list[str],
        recursive: bool = True,
        exclude_dirs: list[str] | None = None,
    ) -> list[Path]:
        root_path = Path(root)
        excluded = set(exclude_dirs or [])
        files: list[Path] = []
        for pattern in patterns:
            candidates = root_path.rglob(pattern) if recursive else root_path.glob(pattern)
            for candidate in candidates:
                if not candidate.is_file():
                    continue
                if any(part in excluded for part in candidate.parts):
                    continue
                files.append(candidate)
        return sorted(set(files))

    @staticmethod
    def ensure_dir(path: Path | str) -> Path:
        directory = Path(path)
        directory.mkdir(parents=True, exist_ok=True)
        return directory


class LoggingUtilities:
    """Logging helpers."""

    @staticmethod
    def setup_logger(name: str, session_id: str | None = None) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            suffix = f" [{session_id}]" if session_id else ""
            handler.setFormatter(logging.Formatter(f"%(levelname)s:%(name)s{suffix}: %(message)s"))
            logger.addHandler(handler)
        return logger


def get_logger(name: str, session_id: str | None = None) -> logging.Logger:
    return LoggingUtilities.setup_logger(name, session_id=session_id)


class MetricsUtilities:
    """Metric payload helpers."""

    @staticmethod
    def create_metrics_dict(
        component_name: str,
        session_id: str,
        version: str = "0.1.0",
    ) -> dict[str, Any]:
        return {
            "component": component_name,
            "session_id": session_id,
            "version": version,
            "timestamp": datetime.now().isoformat(),
            "operations": [],
            "errors": [],
        }

    @staticmethod
    def finalize_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
        finalized = dict(metrics)
        finalized["end_timestamp"] = datetime.now().isoformat()
        finalized["total_operations"] = len(finalized.get("operations", []))
        finalized["total_errors"] = len(finalized.get("errors", []))
        return finalized
