"""Deterministic matched-workflow wave metrics, not merge/root authority."""

from __future__ import annotations

import hashlib
import json


def _validate(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError("nonempty workflow rows required")
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid row")
        name, outcome = row.get("name"), row.get("conclusion")
        if not isinstance(name, str) or not name.strip() or name in result:
            raise ValueError("duplicate or invalid workflow name")
        if outcome not in ("success", "failure", "cancelled", "skipped", None):
            raise ValueError("invalid workflow conclusion")
        result[name] = outcome
    return result


def compare(previous, current, *, previous_sha, current_sha):
    """Compare named workflow cohorts; never infer unique BD root closures."""
    for sha in (previous_sha, current_sha):
        if (
            not isinstance(sha, str)
            or len(sha) != 40
            or any(c not in "0123456789abcdef" for c in sha)
        ):
            raise ValueError("invalid exact source sha")
    a, b = _validate(previous), _validate(current)
    same = set(a) == set(b)
    matched = sorted(set(a) & set(b))
    moved = [
        {"workflow": n, "before": a[n], "after": b[n]} for n in matched if a[n] != b[n]
    ]
    output = {
        "schema": "abacus.mip.workflow-wave-transition/v1",
        "previous_sha": previous_sha,
        "current_sha": current_sha,
        "previous_count": len(a),
        "current_count": len(b),
        "matched_count": len(matched),
        "same_workflow_cohort": same,
        "added_workflows": sorted(set(b) - set(a)),
        "removed_workflows": sorted(set(a) - set(b)),
        "transitions": moved,
        "previous_successes": sum(v == "success" for v in a.values()),
        "current_successes": sum(v == "success" for v in b.values()),
        "success_rate_delta_pp": None,
        "improved_fail_to_pass": [
            n for n in matched if a[n] == "failure" and b[n] == "success"
        ],
        "regressed_pass_to_fail": [
            n for n in matched if a[n] == "success" and b[n] == "failure"
        ],
        "unique_bd_roots_closed": None,
        "coverage_gain_pp": None,
        "governance_admission": "HOLD",
    }
    if same and all(v is not None for v in list(a.values()) + list(b.values())):
        output["success_rate_delta_pp"] = round(
            100
            * (
                output["current_successes"] / len(b)
                - output["previous_successes"] / len(a)
            ),
            2,
        )
    payload = json.dumps(
        output, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    output["receipt_sha256"] = hashlib.sha256(payload).hexdigest()
    return output
