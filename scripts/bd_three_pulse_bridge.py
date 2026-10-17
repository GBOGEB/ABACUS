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
FP = re.compile(r"[0-9a-f]{64}\Z")
ROOT_ID = re.compile(r"(?:BD|CI)-[0-9a-f]{24}\Z")
LANES = ("B2-source", "B3-subprocess", "B4-files-secrets", "B5-tests")


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
        if (
            k > d
            or d == 0
            or not isinstance(row["config"], str)
            or not row["config"]
        ):
            raise ValueError("invalid coverage denominator or config")
        result[scope] = dict(
            covered=k, eligible=d, config=row["config"], ratio_unverified=_ratio(k, d)
        )
    return result


def _validate_root_census(roots, bandit_count, scope):
    """Require the canonical producer's one BANDIT root per unique finding."""
    if not isinstance(roots, list):
        raise ValueError("missing canonical roots")
    seen, fingerprints, bandit_roots = set(), set(), 0
    for root in roots:
        if not isinstance(root, dict):
            raise ValueError("root must be an object")
        root_id = root.get("root_id")
        if (
            not isinstance(root_id, str)
            or not ROOT_ID.fullmatch(root_id)
            or root_id in seen
        ):
            raise ValueError("duplicate or invalid root IDs")
        seen.add(root_id)
        category = root.get("category")
        if category == "CI":
            if not root_id.startswith("CI-") or root.get("fingerprint") is not None:
                raise ValueError("invalid CI root")
            continue
        if category != "BANDIT" or not root_id.startswith("BD-"):
            raise ValueError("invalid canonical root category")
        bandit_roots += 1
        fp = root.get("fingerprint")
        if (
            not isinstance(fp, str)
            or not FP.fullmatch(fp)
            or fp in fingerprints
        ):
            raise ValueError("invalid Bandit fingerprint")
        fingerprints.add(fp)
        if (
            root.get("owner_lane") not in LANES
            or type(root.get("line")) is not int
            or root["line"] <= 0
        ):
            raise ValueError("invalid Bandit lane or line")
        for field in ("source_path", "rule_or_error_code", "disposition"):
            value = root.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError("missing Bandit source metadata")
        rows = root.get("observations")
        if not isinstance(rows, list):
            raise ValueError("missing Bandit observations")
        native = [
            obs for obs in rows
            if isinstance(obs, dict) and obs.get("source") == "bandit_disjoint"
        ]
        if len(native) != 1:
            raise ValueError("Bandit root needs one source-bound observation")
        for field in (
            "repository", "source_sha", "run_id", "job_id",
            "evidence_url", "scan_configuration",
        ):
            expected = (
                scope.get("head_sha")
                if field == "source_sha"
                else scope.get(field)
            )
            if native[0].get(field) != expected:
                raise ValueError("Bandit source mismatch: " + field)
    if bandit_roots != bandit_count:
        raise ValueError("Bandit numerator does not reconcile with roots")


def rollup(pulses):
    if not isinstance(pulses, list) or len(pulses) != 3:
        raise ValueError("exactly three ordered pulses required")
    seen, out = set(), []
    for index, pulse in enumerate(pulses):
        if (
            not isinstance(pulse, dict)
            or pulse.get("schema") != "bd.ldab.joined.census.v1"
        ):
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
        if (
            pulse.get("merge_admission") != "HOLD"
            or pulse.get("authority_transfer") is not False
            or pulse.get("security_waiver") is not False
        ):
            raise ValueError("authority/admission contract must remain HOLD")
        _validate_root_census(roots, bandit, scope)
        out.append(
            {
                "n": index + 1,
                "source_sha": sha,
                "bandit_observations": bandit,
                "candidate_root_count": len(roots),
                "canonical_comparable_delta": metrics.get("comparable_delta"),
                "authenticated_worker_launches": None,
                "accepted_engineering_root_closures": None,
                "root_open": None,
                "root_closed": None,
                "main_merge": None,
                "coverage": None,
                "coverage_candidates_unverified": _coverage(pulse.get("coverage")),
                "coverage_proof_state": (
                    "UNVERIFIED" if pulse.get("coverage") is not None
                    else "NOT_SUPPLIED"
                ),
            }
        )
    movements = []
    for before, after in zip(out, out[1:]):
        # No independently verified native coverage is emitted by the v1 join.
        measured = {
            name: {
                "comparable": False,
                "delta_covered": None,
                "before": None,
                "after": None,
                "reason": "NATIVE_COVERAGE_PROOF_NOT_AVAILABLE",
            }
            for name in (
                "main_statement", "main_branch", "diff_statement", "diff_branch"
            )
        }
        movements.append(
            {
                "from_sha": before["source_sha"],
                "to_sha": after["source_sha"],
                "coverage": measured,
            }
        )
    return {
        "schema": SCHEMA,
        "pulses": out,
        "movements": movements,
        "canonical_root_census_owner": "GBOGEB/ABACUS#1929",
        "merge_admission": "HOLD",
        "authority_transfer": False,
        "security_waiver": False,
        "formal_credit_delta": 0,
        "engineering_credit_delta": 0,
        "interpretation": (
            "Three observations are not three authenticated workers, native-verified coverage artifacts, "
            "or admitted source repairs."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs=3, type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in args.inputs]
    result = rollup(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
