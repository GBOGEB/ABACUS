"""Read-only CODE PURPLE exact-head recovery triage.

This is a diagnostic planner, not a GitHub dispatch or admission authority.
Only authenticated native GitHub receipts can satisfy external security DoV.
"""

from __future__ import annotations

import re
from collections import Counter

SCHEMA = "code-purple.recovery-triage.v1"
SHA = re.compile(r"[0-9a-f]{40}\Z")

# Match an independent first-red message, never a downstream summary alone.
SIGNATURES = (
    ("API_QUOTA", "api rate limit exceeded for installation"),
    ("DEPENDENCY_GRAPH_DISABLED", "dependency review is not supported"),
    ("A10_REVIEW", "tender guard"),
    ("SAFETY", "safety is red"),
    ("BANDIT", "bandit ratchet"),
    ("FORMAT", "per-tool black new-debt ratchet failed"),
)
ACTIONS = {
    "API_QUOTA": "BACKOFF_ONE_CANARY_AFTER_TRUSTED_QUOTA_PROOF",
    "DEPENDENCY_GRAPH_DISABLED": "REPOSITORY_ADMIN_ENABLE_GRAPH",
    "A10_REVIEW": "INDEPENDENT_CONFIDENTIALITY_REVIEW",
    "SAFETY": "SECURITY_OWNER_REPAIR",
    "BANDIT": "SECURITY_OWNER_REPAIR",
    "FORMAT": "DISJOINT_FORMAT_OWNER_REPAIR",
    "UNCLASSIFIED": "INSPECT_FIRST_RED_EVIDENCE",
}
CANARY_STATUSES = {"NOT_RUN", "QUEUED", "IN_PROGRESS", "FAILURE", "SUCCESS"}


def _sha(value, field):
    if not isinstance(value, str) or SHA.fullmatch(value) is None:
        raise ValueError(f"invalid canonical {field}")
    return value


def _id(value, field):
    if type(value) is not int or value <= 0:
        raise ValueError(f"invalid {field}")
    return value


def fingerprint(message):
    """Normalize only explicit first-red signatures; unknowns stay unknown."""
    if not isinstance(message, str) or not message.strip():
        raise ValueError("first-red text is required")
    normalized = message.casefold()
    matches = [root for root, needle in SIGNATURES if needle in normalized]
    if len(matches) > 1:
        return "UNCLASSIFIED"
    return matches[0] if matches else "UNCLASSIFIED"


def reconcile(observations, canary=None):
    """Summarize independently sourced failures; never execute a retry.

    Observations are untrusted declarations until the caller validates native
    run/job/attempt and actual log bytes against the external GitHub source.
    """
    if not isinstance(observations, list):
        raise ValueError("observations must be a list")
    seen = set()
    roots = Counter()
    grouped = {}
    exact_heads = set()
    for item in observations:
        if not isinstance(item, dict):
            raise ValueError("observation must be a record")
        repository = item.get("repository")
        if repository != "GBOGEB/ABACUS":
            raise ValueError("out-of-scope repository")
        head = _sha(item.get("head_sha"), "source head")
        run_id = _id(item.get("run_id"), "run ID")
        job_id = _id(item.get("job_id"), "job ID")
        attempt = _id(item.get("attempt"), "run attempt")
        if item.get("status") != "completed" or item.get("conclusion") != "failure":
            raise ValueError("first-red requires terminal failing native job")
        identity = (repository, head, run_id, job_id, attempt)
        if identity in seen:
            raise ValueError("duplicate exact-head run/job/attempt")
        seen.add(identity)
        root = fingerprint(item.get("first_red"))
        roots[root] += 1
        exact_heads.add(head)
        grouped.setdefault(root, []).append(
            {"head_sha": head, "run_id": run_id,
             "job_id": job_id, "attempt": attempt}
        )

    if canary is None:
        canary_status = "NOT_RUN"
        canary_native_terminal = False
    else:
        if not isinstance(canary, dict):
            raise ValueError("invalid canary receipt")
        canary_status = canary.get("status")
        if canary_status not in CANARY_STATUSES:
            raise ValueError("invalid canary status")
        _sha(canary.get("head_sha"), "canary head")
        _id(canary.get("run_id"), "canary run ID")
        _id(canary.get("attempt"), "canary attempt")
        canary_native_terminal = canary_status in ("SUCCESS", "FAILURE")
        if canary_status == "SUCCESS" and not canary.get("receipt_ref"):
            raise ValueError("successful canary needs native evidence reference")
    ordered_roots = []
    for root in sorted(roots, key=lambda x: (-roots[x], x)):
        ordered_roots.append({
            "root_id": root,
            "manifestations": roots[root],
            "action": ACTIONS[root],
            "members": sorted(
                grouped[root],
                key=lambda x: (x["head_sha"], x["run_id"],
                               x["job_id"], x["attempt"]),
            ),
        })
    quota_manifestations = roots["API_QUOTA"]
    return {
        "schema": SCHEMA,
        "observations": len(observations),
        "distinct_causal_candidates": len(roots),
        "exact_heads": sorted(exact_heads),
        "roots": ordered_roots,
        "quota_failure_manifestations": quota_manifestations,
        "canary_status": canary_status,
        "canary_native_terminal": canary_native_terminal,
        "quota_recovery_independently_verified": False,
        "automatic_retry_authorized": False,
        "automatic_fanout_authorized": False,
        "security_gates_waived": 0,
        "merge_admission": "HOLD",
        "note": (
            "An accepted rerun or reported PASS is not externally trusted proof. "
            "A separate owner must authenticate native receipts and capacity."
        ),
    }
