"""Append-only W43 federation session registry.

The registry is intentionally file-backed for the first implementation wave.
A later wave may replace storage without changing the record contract.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json

TERMINAL_RESULTS = {"ACCEPTED", "REJECTED", "DEFERRED", "FAILED"}


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    federation_id: str
    repo: str
    branch: str
    commit_sha: str
    wave: str
    pulse_id: str
    agent: str | None = None
    worker: str | None = None
    runtime: str | None = None
    target: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    result: str | None = None
    evidence_uri: str | None = None


def validate_session(record: SessionRecord) -> list[str]:
    errors: list[str] = []
    for field in ("session_id", "federation_id", "repo", "branch", "commit_sha", "wave", "pulse_id"):
        if not getattr(record, field):
            errors.append(f"{field} must be non-empty")
    if record.result and record.result not in TERMINAL_RESULTS and record.result != "RUNNING":
        errors.append(f"unsupported result: {record.result}")
    if record.result in TERMINAL_RESULTS and not record.finished_at:
        errors.append("finished_at required for terminal result")
    return errors


def append_session(path: str | Path, record: SessionRecord) -> None:
    errors = validate_session(record)
    if errors:
        raise ValueError("; ".join(errors))
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")


def read_sessions(path: str | Path) -> list[dict[str, Any]]:
    target = Path(path)
    if not target.exists():
        return []
    return [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
