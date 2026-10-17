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
FP = re.compile(r"[0-9a-f]{64}\Z")
SCHEMA = "abacus.bd.three-pulse.v1"


def _count(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _coverage(data):
    """No self-reported coverage: #1929 does not attest native artifacts yet."""
    if data is not None:
        raise ValueError(
            "unverified coverage enrichment: require independently validated "
            "native source/run/job/artifact proof before calculating movements"
        )
    return None


def _validate_roots(roots, bandit, scope):
    """Reconcile the canonical producer's disjoint Bandit root population."""
    if not isinstance(roots, list):
        raise ValueError("missing canonical roots")
    ids = set()
    bandit_roots = 0
    for root in roots:
        if not isinstance(root, dict):
            raise ValueError("invalid canonical root")
        rid = root.get("root_id")
        kind = root.get("category")
        if not isinstance(rid, str) or not rid or rid in ids:
            raise ValueError("duplicate or invalid root IDs")
        ids.add(rid)
        if kind not in ("BANDIT", "CI"):
            raise ValueError("invalid canonical root category")
        observations = root.get("observations")
        if (
            not isinstance(observations, list)
            or not observations
            or any(not isinstance(obs, dict) for obs in observations)
        ):
            raise ValueError("root requires canonical observations")
        if kind == "CI":
            if not rid.startswith("CI-") or root.get("fingerprint") is not None:
                raise ValueError("invalid CI root identity")
            continue
        bandit_roots += 1
        fp = root.get("fingerprint")
        if not rid.startswith("BD-") or not isinstance(fp, str) or not FP.fullmatch(fp):
            raise ValueError("invalid Bandit fingerprint or root identity")
        if not any(
            obs.get("source") == "bandit_disjoint"
            and obs.get("repository") == scope["repository"]
            and obs.get("source_sha") == scope["head_sha"]
            and obs.get("run_id") == scope["run_id"]
            and obs.get("job_id") == scope["job_id"]
            and obs.get("scan_configuration") == scope["scan_configuration"]
            for obs in observations
        ):
            raise ValueError("Bandit root lacks exact-source census observation")
    if bandit_roots != bandit:
        raise ValueError("full Bandit denominator does not reconcile with roots")


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
        for name in ("run_id", "job_id"):
            if type(scope.get(name)) is not int or scope[name] < 1:
                raise ValueError(f"scope.{name} requires positive integer")
        config = scope.get("scan_configuration")
        url = scope.get("evidence_url")
        if not isinstance(config, str) or not config.strip():
            raise ValueError("missing scanner configuration")
        if not isinstance(url, str) or not url.startswith("https://github.com/"):
            raise ValueError("missing GitHub evidence URL")
        metrics = pulse.get("metrics")
        if not isinstance(metrics, dict):
            raise ValueError("missing canonical metrics")
        bandit = _count(metrics.get("full_bandit_unique"), "full_bandit_unique")
        roots = pulse.get("roots")
        if (
            pulse.get("merge_admission") != "HOLD"
            or pulse.get("authority_transfer") is not False
            or pulse.get("security_waiver") is not False
        ):
            raise ValueError("authority/admission contract must remain HOLD")
        if pulse.get("security_disposition") not in (None, "INDEPENDENT_REVIEW_REQUIRED"):
            raise ValueError("security review disposition is not independently accepted")
        if pulse.get("formal_credit_delta", 0) != 0 or pulse.get("engineering_credit_delta", 0) != 0:
            raise ValueError("unadmitted source claims cannot earn engineering credit")
        _validate_roots(roots, bandit, scope)
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
                "coverage": _coverage(pulse.get("coverage")),
            }
        )
    movements = []
    for before, after in zip(out, out[1:]):
        measured = {}
        for name in ("main_statement", "main_branch", "diff_statement", "diff_branch"):
            left = before["coverage"].get(name) if before["coverage"] else None
            right = after["coverage"].get(name) if after["coverage"] else None
            comparable = (
                left is not None
                and right is not None
                and left["config"] == right["config"]
                and left["eligible"] == right["eligible"]
            )
            measured[name] = {
                "comparable": comparable,
                "delta_covered": right["covered"] - left["covered"]
                if comparable
                else None,
                "before": [left["covered"], left["eligible"]] if comparable else None,
                "after": [right["covered"], right["eligible"]] if comparable else None,
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
            "Three observations are not three authenticated workers "
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
