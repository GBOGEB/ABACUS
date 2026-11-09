"""Strict source-bound E0-E3 pulse telemetry contract."""

from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
from typing import Any

SCHEMA = "code-purple.bd-pulse.v1"
MODES = {"E0", "E1", "E2", "E3"}
RESULTS = {"PASS", "FAIL", "HOLD", "UNKNOWN"}
ROLLUP_SCHEMA = "code-purple.bd-pulse-series.v1"
SHA = re.compile(r"[0-9a-f]{40}")
ARTIFACT_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


def validate(record: dict[str, Any]) -> dict[str, Any]:
    required = (
        "schema",
        "mode",
        "source_sha",
        "base_sha",
        "root_id",
        "attempt",
        "artifact_digest",
        "line_covered",
        "line_total",
        "branch_covered",
        "branch_total",
        "queue_seconds",
        "result",
    )
    if not isinstance(record, dict):
        raise ValueError("telemetry must be an object")
    missing = [field for field in required if field not in record]
    if missing:
        raise ValueError("missing telemetry fields: " + ", ".join(missing))
    if (
        record["schema"] != SCHEMA
        or not isinstance(record["mode"], str)
        or record["mode"] not in MODES
    ):
        raise ValueError("unsupported schema or emulation mode")
    if not isinstance(record["result"], str) or record["result"] not in RESULTS:
        raise ValueError("unsupported result")
    for key in ("source_sha", "base_sha"):
        val = record[key]
        if not isinstance(val, str) or not SHA.fullmatch(val):
            raise ValueError(f"{key} must be a canonical full commit SHA")
    digest = record["artifact_digest"]
    if digest is not None and (
        not isinstance(digest, str) or not ARTIFACT_DIGEST.fullmatch(digest)
    ):
        raise ValueError("invalid canonical artifact digest")
    if not isinstance(record["root_id"], str) or not record["root_id"]:
        raise ValueError("missing root ID")
    if type(record["attempt"]) is not int or record["attempt"] < 1:
        raise ValueError("attempt must be a positive integer")
    for covered, total in (
        ("line_covered", "line_total"),
        ("branch_covered", "branch_total"),
    ):
        numerator, denominator = record[covered], record[total]
        if numerator is None or denominator is None:
            if numerator is not None or denominator is not None:
                raise ValueError("partial coverage ratio")
        elif (
            type(numerator) is not int
            or type(denominator) is not int
            or denominator <= 0
            or not 0 <= numerator <= denominator
        ):
            raise ValueError("invalid coverage numerator/denominator")
    q = record["queue_seconds"]
    if q is not None and (
        type(q) not in (int, float)
        or q < 0
        or (type(q) is float and not math.isfinite(q))
    ):
        raise ValueError("invalid queue seconds")
    if record["mode"] == "E3" and record["result"] == "PASS":
        if (
            record["artifact_digest"] is None
            or record["line_total"] is None
            or record["branch_total"] is None
            or q is None
        ):
            raise ValueError("native PASS needs complete evidence")
    return record


def canonical_json(record: dict[str, Any]) -> str:
    validate(record)
    return json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)


def evidence_digest(record: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(record).encode("utf-8")).hexdigest()


def summarize_series(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe source-bound E0-E3 observations; never certify external proof.

    Percentiles use the empirical nearest-rank estimator. Cross-head coverage
    deltas are intentionally withheld because denominators/config may differ.
    """
    if not isinstance(records, list):
        raise ValueError("pulse series must be a list")
    modes = {mode: {result: 0 for result in sorted(RESULTS)} for mode in sorted(MODES)}
    seen = set()
    queue_samples = []
    coverage_samples = []
    line_known = 0
    branch_known = 0
    heads = set()
    roots = set()
    for record in records:
        validate(record)
        key = (
            record["source_sha"],
            record["base_sha"],
            record["root_id"],
            record["mode"],
            record["attempt"],
        )
        if key in seen:
            raise ValueError("duplicate source-bound pulse observation")
        seen.add(key)
        modes[record["mode"]][record["result"]] += 1
        heads.add(record["source_sha"])
        roots.add(record["root_id"])
        if record["queue_seconds"] is not None:
            queue_samples.append(record["queue_seconds"])
        if record["mode"] == "E3":
            # Failed/held E3 observations may have independently missing line
            # or branch evidence. Preserve each dimension as UNKNOWN (None)
            # rather than raising an unrelated TypeError or inventing 0%.
            known_lines = record["line_total"] is not None
            known_branches = record["branch_total"] is not None
            line_known += int(known_lines)
            branch_known += int(known_branches)
            coverage_samples.append(
                {
                    "source_sha": record["source_sha"],
                    "root_id": record["root_id"],
                    "attempt": record["attempt"],
                    "result": record["result"],
                    "line_covered": record["line_covered"],
                    "line_total": record["line_total"],
                    "branch_covered": record["branch_covered"],
                    "branch_total": record["branch_total"],
                    "line_percent": (
                        round(100 * record["line_covered"] / record["line_total"], 4)
                        if known_lines
                        else None
                    ),
                    "branch_percent": (
                        round(
                            100 * record["branch_covered"] / record["branch_total"], 4
                        )
                        if known_branches
                        else None
                    ),
                }
            )
    queue_samples.sort()
    native = modes["E3"]
    native_total = sum(native.values())
    observed = len(queue_samples)
    coverage_samples.sort(
        key=lambda item: (item["source_sha"], item["root_id"], item["attempt"])
    )
    return {
        "schema": ROLLUP_SCHEMA,
        "observations": len(records),
        "source_heads": sorted(heads),
        "root_ids": sorted(roots),
        "mode_outcomes": modes,
        "e3_pass_claims": native["PASS"],
        "e3_observations": native_total,
        "e3_pass_claim_fraction": (
            native["PASS"] / native_total if native_total else None
        ),
        "queue_seconds": {
            "observations": observed,
            "missing": len(records) - observed,
            "median": statistics.median(queue_samples) if observed else None,
            "p95_nearest_rank": (
                queue_samples[math.ceil(0.95 * observed) - 1] if observed else None
            ),
            "p95_qualified": observed >= 20,
        },
        "declared_native_coverage": coverage_samples,
        "e3_line_coverage_known": line_known,
        "e3_branch_coverage_known": branch_known,
        "e3_line_coverage_unknown": native_total - line_known,
        "e3_branch_coverage_unknown": native_total - branch_known,
        "cross_head_coverage_delta_pp": None,
        "externally_verified_artifact_count": 0,
        "verified_root_closures": 0,
        "merge_admission": "HOLD",
        "note": (
            "Reported E3 passes and coverage are source declarations, not "
            "authenticated external byte evidence or merge admission."
        ),
    }
