"""Strict source-bound E0-E3 pulse telemetry contract."""
from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA = "code-purple.bd-pulse.v1"
MODES = {"E0", "E1", "E2", "E3"}
RESULTS = {"PASS", "FAIL", "HOLD", "UNKNOWN"}


def validate(record: dict[str, Any]) -> dict[str, Any]:
    required = (
        "schema", "mode", "source_sha", "base_sha", "root_id", "attempt",
        "artifact_digest", "line_covered", "line_total", "branch_covered",
        "branch_total", "queue_seconds", "result",
    )
    if not isinstance(record, dict):
        raise ValueError("telemetry must be an object")
    missing = [field for field in required if field not in record]
    if missing:
        raise ValueError("missing telemetry fields: " + ", ".join(missing))
    if record["schema"] != SCHEMA or record["mode"] not in MODES:
        raise ValueError("unsupported schema or emulation mode")
    if record["result"] not in RESULTS:
        raise ValueError("unsupported result")
    for key in ("source_sha", "base_sha"):
        val = record[key]
        if not isinstance(val, str) or len(val) != 40:
            raise ValueError(f"{key} must be a full commit SHA")
        try:
            int(val, 16)
        except ValueError as exc:
            raise ValueError(f"{key} must be hex") from exc
    digest = record["artifact_digest"]
    if digest is not None:
        if not isinstance(digest, str) or not digest.startswith("sha256:"):
            raise ValueError("invalid artifact digest")
        hexpart = digest[7:]
        if len(hexpart) != 64:
            raise ValueError("invalid artifact digest length")
        try:
            int(hexpart, 16)
        except ValueError as exc:
            raise ValueError("invalid artifact digest hex") from exc
    if not isinstance(record["root_id"], str) or not record["root_id"]:
        raise ValueError("missing root ID")
    if type(record["attempt"]) is not int or record["attempt"] < 1:
        raise ValueError("attempt must be a positive integer")
    for covered, total in (
        ("line_covered", "line_total"), ("branch_covered", "branch_total")
    ):
        numerator, denominator = record[covered], record[total]
        if numerator is None or denominator is None:
            if numerator is not None or denominator is not None:
                raise ValueError("partial coverage ratio")
        elif (type(numerator) is not int or type(denominator) is not int
              or denominator <= 0 or not 0 <= numerator <= denominator):
            raise ValueError("invalid coverage numerator/denominator")
    q = record["queue_seconds"]
    if q is not None and (type(q) not in (int, float) or q < 0):
        raise ValueError("invalid queue seconds")
    if record["mode"] == "E3" and record["result"] == "PASS":
        if (record["artifact_digest"] is None or record["line_total"] is None
                or record["branch_total"] is None or q is None):
            raise ValueError("native PASS needs complete evidence")
    return record


def canonical_json(record: dict[str, Any]) -> str:
    validate(record)
    return json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)


def evidence_digest(record: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(record).encode("utf-8")).hexdigest()
