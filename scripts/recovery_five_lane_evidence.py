"""Fail-closed reconciliation of externally authenticated recovery receipts.

Never promotes a source declaration, proposal, skipped job or comment to proof.
Upstream producers must bind received inputs to GitHub job/artifact identity.
"""

from __future__ import annotations

import json
import re

SHA = re.compile(r"^[0-9a-f]{40}$")
HASH = re.compile(r"^[0-9a-f]{64}$")
KNOWN = {
    "success": "PASS",
    "failure": "FAIL",
    "skipped": "SKIPPED",
    "cancelled": "CANCELLED",
    "timed_out": "FAIL",
}


def require_sha(value):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError("exact 40-character SHA required")
    return value


def native(row, sha):
    """Require a terminal GitHub-native job; absent is UNKNOWN."""
    if row is None:
        return {"status": "UNKNOWN", "job_id": None}
    if row.get("sha") != sha:
        raise ValueError("native job head mismatch")
    if row.get("status") != "completed":
        return {"status": "NONTERMINAL", "job_id": row.get("job_id")}
    if type(row.get("run_id")) is not int or type(row.get("job_id")) is not int:
        raise ValueError("native run/job IDs required")
    if not str(row.get("url", "")).startswith("https://github.com/"):
        raise ValueError("native evidence URL required")
    return {
        "status": KNOWN.get(row.get("conclusion"), "UNKNOWN"),
        "run_id": row["run_id"],
        "job_id": row["job_id"],
        "url": row["url"],
    }


def coverage(row, sha, base=None):
    if row is None:
        return {"status": "UNKNOWN", "covered": None, "eligible": None}
    if row.get("sha") != sha or (base is not None and row.get("base_sha") != base):
        raise ValueError("coverage head/base mismatch")
    covered, eligible = row.get("covered"), row.get("eligible")
    if (
        type(covered) is not int
        or type(eligible) is not int
        or eligible <= 0
        or not 0 <= covered <= eligible
    ):
        raise ValueError("coverage numerator/denominator invalid")
    if not (
        isinstance(row.get("config_sha256"), str)
        and HASH.fullmatch(row["config_sha256"])
        and row.get("scope_id")
        and type(row.get("run_id")) is int
        and type(row.get("artifact_id")) is int
    ):
        raise ValueError("coverage provenance incomplete")
    return {
        "status": "MEASURED",
        "covered": covered,
        "eligible": eligible,
        "percent": round(100 * covered / eligible, 6),
        "scope_id": row["scope_id"],
        "config_sha256": row["config_sha256"],
        "run_id": row["run_id"],
        "artifact_id": row["artifact_id"],
    }


def bd_roots(row, sha):
    """Counts root IDs, not scanner findings. Explicit native closed receipts."""
    if row is None:
        return {"status": "UNKNOWN", "opened": None, "closed": None, "reopened": None}
    if row.get("sha") != sha:
        raise ValueError("BD head mismatch")
    if row.get("complete") is not True or not row.get("scanner_config_sha256"):
        return {"status": "UNKNOWN", "opened": None, "closed": None, "reopened": None}
    if not HASH.fullmatch(str(row["scanner_config_sha256"])):
        raise ValueError("BD config fingerprint invalid")
    groups = {}
    for category in ("opened", "closed", "reopened"):
        vals = row.get(category)
        if not isinstance(vals, list) or len(set(vals)) != len(vals):
            raise ValueError("BD root IDs not independently reconciled")
        for value in vals:
            if not isinstance(value, str) or not value.startswith("BD-"):
                raise ValueError("BD root identifier invalid")
        groups[category] = set(vals)
    if any(
        groups[a] & groups[b]
        for a, b in (
            ("opened", "closed"),
            ("opened", "reopened"),
            ("closed", "reopened"),
        )
    ):
        raise ValueError("BD root transitions overlap")
    if not all(row.get(k) for k in ("run_id", "job_id", "evidence_url")):
        raise ValueError("BD native provenance missing")
    return {
        "status": "RECONCILED",
        **{k: len(v) for k, v in groups.items()},
        "scan_scope": row["scanner_config_sha256"],
        "run_id": row["run_id"],
        "job_id": row["job_id"],
    }


def crew(row, sha):
    """Authenticated returns require attested executor, matching job and REX."""
    if row is None:
        return {
            "status": "UNKNOWN",
            "verified_launches": None,
            "accepted_rex": None,
            "ldab_sessions": None,
        }
    if row.get("sha") != sha:
        raise ValueError("Crew source mismatch")
    if row.get("authority_verified") is not True:
        return crew(None, sha)
    receipts = row.get("receipts")
    if not isinstance(receipts, list):
        raise ValueError("Crew receipts missing")
    ids = set()
    counts = {"verified_launches": 0, "accepted_rex": 0, "ldab_sessions": 0}
    for receipt in receipts:
        rid = receipt.get("launch_id")
        if not rid or rid in ids:
            raise ValueError("Missing or duplicate authenticated launch ID")
        ids.add(rid)
        if not (
            receipt.get("executor_identity_verified") is True
            and receipt.get("run_sha") == sha
            and receipt.get("run_id")
            and receipt.get("job_id")
            and receipt.get("receipt_url")
        ):
            raise ValueError("Unauthenticated Crew receipt")
        counts["verified_launches"] += 1
        if receipt.get("rex_status") == "ACCEPTED":
            if not receipt.get("rex_url"):
                raise ValueError("REX acceptance receipt URL required")
            counts["accepted_rex"] += 1
        if receipt.get("ldab_session_id"):
            if not receipt.get("runner_id") or not receipt.get("debug_log_url"):
                raise ValueError("LDAB runner/debug session receipt required")
            counts["ldab_sessions"] += 1
    return {"status": "ATTESTED", **counts}


def review(row, sha):
    if row is None:
        return {"status": "UNKNOWN", "eligible_approval": None}
    if row.get("sha") != sha:
        raise ValueError("review head mismatch")
    if row.get("reviewer_eligibility_verified") is not True:
        return {"status": "HOLD", "eligible_approval": None}
    approvals = [
        r
        for r in row.get("reviews", [])
        if r.get("state") == "APPROVED"
        and r.get("commit_id") == sha
        and r.get("eligible") is True
        and r.get("author") != row.get("pr_author")
    ]
    return {
        "status": "APPROVAL_OBSERVED" if approvals else "HOLD",
        "eligible_approval": len(approvals) > 0,
        "approval_count": len(approvals),
        "merge_authorized": False,
    }


def reconcile(bundle):
    """Shape-validated producer boundary; never grants integration authority."""
    main = require_sha(bundle["main_sha"])
    head = require_sha(bundle["head_sha"])
    jobs = bundle.get("native_jobs", {})
    return {
        "schema": "abacus.recovery.five-lane.v1",
        "main_sha": main,
        "head_sha": head,
        "canonical_main_coverage": coverage(bundle.get("main_coverage"), main),
        "changed_line_coverage": coverage(bundle.get("diff_coverage"), head, main),
        "bd_distinct_roots": bd_roots(bundle.get("bd_receipt"), head),
        "crew_ldab_rex": crew(bundle.get("crew_attestations"), head),
        "governance_review": review(bundle.get("review_receipt"), head),
        "rhel8": native(jobs.get("rhel8"), head),
        "rhel9": native(jobs.get("rhel9"), head),
        "ubi9": native(jobs.get("ubi9"), head),
        "docs": native(jobs.get("docs"), head),
        "matrix": native(jobs.get("matrix"), head),
        "full_ci": native(jobs.get("full_ci"), head),
        "security": native(jobs.get("security"), head),
        "merge_authorized": False,
    }


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    report = reconcile(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
