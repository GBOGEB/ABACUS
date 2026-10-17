"""Read-only N to N+3 evidence rollup for the existing #1929 BD join.

Consumes already-qualified bd.ldab.joined.census.v1 reports; it is not a
second root authority and never implies closure, dispatch, or admission.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{40}\Z")
SCHEMA = "abacus.bd.three-pulse.v1"


def _count(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _ratio(n, d):
    return n / d if n is not None and d is not None and d > 0 else None


def _coverage(data):
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("coverage must be an object or null")
    result = {}
    for scope in ("main_statement", "main_branch", "diff_statement", "diff_branch"):
        row = data.get(scope)
        if row is None:
            result[scope] = None
            continue
        if not isinstance(row, dict) or set(row) != {"covered", "eligible", "config"}:
            raise ValueError("coverage requires covered, eligible and config")
        k = _count(row["covered"], "covered")
        d = _count(row["eligible"], "eligible")
        if k > d or d == 0 or not isinstance(row["config"], str) or not row["config"]:
            raise ValueError("invalid coverage denominator or config")
        result[scope] = dict(covered=k, eligible=d, config=row["config"], ratio=_ratio(k, d))
    return result


def rollup(pulses):
    if not isinstance(pulses, list) or len(pulses) != 3:
        raise ValueError("exactly three ordered pulses required")
    seen, out = set(), []
    for index, pulse in enumerate(pulses):
        if not isinstance(pulse, dict) or pulse.get("schema") != "bd.ldab.joined.census.v1":
            raise ValueError("canonical join output required")
        scope = pulse.get("scope")
        if not isinstance(scope, dict) or scope.get("repository") != "GBOGEB/ABACUS":
            raise ValueError("unexpected repository")
        sha = scope.get("head_sha")
        if not isinstance(sha, str) or not SHA.fullmatch(sha) or sha in seen:
            raise ValueError("unbound or duplicated exact source SHA")
        seen.add(sha)
        metrics = pulse.get("metrics")
        if not isinstance(metrics, dict):
            raise ValueError("missing canonical metrics")
        bandit = _count(metrics.get("full_bandit_unique"), "full_bandit_unique")
        roots = pulse.get("roots")
        if not isinstance(roots, list):
            raise ValueError("missing canonical roots")
        if pulse.get("merge_admission") != "HOLD" or pulse.get("authority_transfer") is not False or pulse.get("security_waiver") is not False:
            raise ValueError("authority/admission contract must remain HOLD")
        rootids = [r.get("root_id") for r in roots if isinstance(r, dict)]
        if len(rootids) != len(roots) or len(set(rootids)) != len(rootids) or any(not isinstance(r, str) or not r for r in rootids):
            raise ValueError("duplicate or invalid root IDs")
        out.append({
            "n": index + 1, "source_sha": sha,
            "bandit_observations": bandit, "candidate_root_count": len(roots),
            "canonical_comparable_delta": metrics.get("comparable_delta"),
            "authenticated_worker_launches": None,
            "accepted_engineering_root_closures": None,
            "root_open": None, "root_closed": None,
            "main_merge": None,
            "coverage": _coverage(pulse.get("coverage")),
        })
    movements = []
    for before, after in zip(out, out[1:]):
        measured = {}
        for name in ("main_statement", "main_branch", "diff_statement", "diff_branch"):
            left = before["coverage"].get(name) if before["coverage"] else None
            right = after["coverage"].get(name) if after["coverage"] else None
            comparable = left is not None and right is not None and left["config"] == right["config"] and left["eligible"] == right["eligible"]
            measured[name] = {
                "comparable": comparable,
                "delta_covered": right["covered"] - left["covered"] if comparable else None,
                "before": [left["covered"], left["eligible"]] if comparable else None,
                "after": [right["covered"], right["eligible"]] if comparable else None,
            }
        movements.append({"from_sha": before["source_sha"], "to_sha": after["source_sha"], "coverage": measured})
    return {"schema": SCHEMA, "pulses": out, "movements": movements,
            "canonical_root_census_owner": "GBOGEB/ABACUS#1929",
            "merge_admission": "HOLD", "authority_transfer": False,
            "security_waiver": False, "formal_credit_delta": 0,
            "engineering_credit_delta": 0,
            "interpretation": "Three observations are not three authenticated workers or admitted source repairs."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs=3, type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in args.inputs]
    result = rollup(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
