"""Fail-closed, read-only G3C-S post-merge evidence comparison.

This is a SOURCE-REPORTED diagnostic, not GitHub authentication, independent
review, branch-policy enforcement, or permission to merge/dispatch.
No missing measurement is replaced with zero.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_SHA = re.compile(r"^[0-9a-f]{40}$")
_REQUIRED_HEAD = ("B0", "MATRIX", "A10", "SECURITY")
_REQUIRED_MAIN = ("B0", "MATRIX")
_TERMINAL = {
    "success",
    "failure",
    "cancelled",
    "timed_out",
    "action_required",
    "neutral",
    "skipped",
    "startup_failure",
}


def _sha(value, field):
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ValueError(field + " requires an exact lowercase 40-hex SHA")
    return value


def _object(value, field):
    if not isinstance(value, dict):
        raise ValueError(field + " must be an object")
    return value


def _run(value, source_sha, field):
    run = _object(value, field)
    identifier = run.get("id")
    attempt = run.get("attempt")
    if type(identifier) is not int or identifier < 1:
        raise ValueError(field + ".id requires a positive native run ID")
    if type(attempt) is not int or attempt < 1:
        raise ValueError(field + ".attempt requires a positive native attempt")
    if run.get("url") != (
        "https://github.com/GBOGEB/ABACUS/actions/runs/" + str(identifier)
    ):
        raise ValueError(field + " run URL does not match native run ID")
    if _sha(run.get("head_sha"), field + ".head_sha") != source_sha:
        raise ValueError(field + " is not bound to the selected source SHA")
    status = run.get("status")
    conclusion = run.get("conclusion")
    if status not in (
        "queued",
        "pending",
        "waiting",
        "requested",
        "in_progress",
        "completed",
    ):
        raise ValueError(field + " has an unknown workflow status")
    if status != "completed" and conclusion is not None:
        raise ValueError(field + " has a nonterminal conclusion")
    if status == "completed" and conclusion not in _TERMINAL:
        raise ValueError(field + " lacks a classified terminal conclusion")
    return status == "completed" and conclusion == "success"


def _ci_group(group, selected_sha, required, field):
    if group is None:
        return False, list(required)
    group = _object(group, field)
    missing = []
    ids = set()
    for name in required:
        item = group.get(name)
        if item is None:
            missing.append(name)
            continue
        if not _run(item, selected_sha, field + "." + name):
            missing.append(name)
        native = (item["id"], item["attempt"])
        if native in ids:
            raise ValueError(
                field + " reuses one workflow ID/attempt for different proof families"
            )
        ids.add(native)
    return not missing, missing


def _coverage_pair(pair, prev_sha, next_sha, field):
    if pair is None:
        return {"status": "UNKNOWN", "delta_pp": None}
    pair = _object(pair, field)
    before = pair.get("before")
    after = pair.get("after")
    if before is None or after is None:
        return {"status": "UNKNOWN", "delta_pp": None}
    before = _object(before, field + ".before")
    after = _object(after, field + ".after")
    if _sha(before.get("source_sha"), field + ".before.source_sha") != prev_sha:
        raise ValueError(field + " before source is not the pinned baseline")
    if _sha(after.get("source_sha"), field + ".after.source_sha") != next_sha:
        raise ValueError(field + " after source is not the pinned outcome")
    for side, measure in (("before", before), ("after", after)):
        for item in ("covered", "eligible"):
            val = measure.get(item)
            if type(val) is not int or val < 0:
                raise ValueError(
                    field + "." + side + "." + item + " requires an integer"
                )
        if not (0 < measure["eligible"] and measure["covered"] <= measure["eligible"]):
            raise ValueError(
                field + "." + side + " has an invalid coverage denominator"
            )
        for hash_field in ("selection_sha256", "tool_sha256", "scope_sha256"):
            digest = measure.get(hash_field)
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError(field + "." + side + " lacks " + hash_field)
    identity = ("selection_sha256", "tool_sha256", "scope_sha256", "eligible")
    if any(before[k] != after[k] for k in identity):
        return {"status": "NONCOMPARABLE", "delta_pp": None}
    delta = 100 * (after["covered"] - before["covered"]) / before["eligible"]
    return {
        "status": "PAIRED_SOURCE_REPORTED",
        "before": before["covered"],
        "after": after["covered"],
        "eligible": before["eligible"],
        "delta_covered": after["covered"] - before["covered"],
        "delta_pp": round(delta, 6),
    }


def evaluate(packet):
    packet = _object(packet, "packet")
    if packet.get("schema") != "codepurple.g3cs.postmerge-evidence.v1":
        raise ValueError("unknown postmerge receipt schema")
    if packet.get("repository") != "GBOGEB/ABACUS":
        raise ValueError("wrong source repository")
    pr = _object(packet.get("pr"), "pr")
    number = pr.get("number")
    if type(number) is not int or number < 1:
        raise ValueError("pr.number requires a positive integer")
    head = _sha(pr.get("head_sha"), "pr.head_sha")
    base = _sha(pr.get("parent_main_sha"), "pr.parent_main_sha")
    main = _sha(pr.get("main_sha"), "pr.main_sha")
    merge = _sha(pr.get("merge_commit_sha"), "pr.merge_commit_sha")
    if pr.get("merged") is not True or main != merge:
        raise ValueError("merge event and exact-main merge SHA do not reconcile")
    if head in (base, main) or main == base:
        raise ValueError("degenerate source/parent/merge lineage")
    if pr.get("url") != f"https://github.com/GBOGEB/ABACUS/pull/{number}":
        raise ValueError("PR URL and number disagree")
    # GitHub must independently validate merge parents/reviews/rules. Caller
    # assertions alone cannot confer approved admission.
    head_ok, head_missing = _ci_group(
        packet.get("head_ci"), head, _REQUIRED_HEAD, "head_ci"
    )
    main_ok, main_missing = _ci_group(
        packet.get("main_ci"), main, _REQUIRED_MAIN, "main_ci"
    )
    governance = _object(packet.get("governance"), "governance")
    checks = (
        "required_statuses_enforced",
        "last_push_approval_enforced",
        "thread_resolution_enforced",
        "red_canary_blocked",
        "independent_security_review_verified",
    )
    unproven = [key for key in checks if governance.get(key) is not True]
    minimum = governance.get("required_approvals")
    eligible = governance.get("eligible_approvals")
    if type(minimum) is not int or minimum < 1:
        unproven.append("required_approvals")
    if (
        type(eligible) is not int
        or eligible < 1
        or (type(minimum) is int and eligible < minimum)
    ):
        unproven.append("eligible_approvals")
    coverage = _object(packet.get("coverage"), "coverage")
    # A historical 36.85%/36.92%/51% figure is NOT an equivalent scope receipt.
    main_cov = _coverage_pair(coverage.get("main"), base, main, "coverage.main")
    pr_broad = _coverage_pair(coverage.get("pr_broad"), base, head, "coverage.pr_broad")
    pr_diff = _coverage_pair(coverage.get("pr_diff"), base, head, "coverage.pr_diff")
    first_red = _object(packet.get("first_red", {}), "first_red")
    before_red, after_red = first_red.get("before"), first_red.get("after")
    if before_red is not None and not isinstance(before_red, str):
        raise ValueError("first_red.before must be a string or null")
    if after_red is not None and not isinstance(after_red, str):
        raise ValueError("first_red.after must be a string or null")
    transition = "UNKNOWN"
    if before_red is not None and after_red is not None and head_ok:
        transition = (
            "SAME" if before_red == after_red else "CANDIDATE_DISPLACED_NOT_ROOT_CLOSED"
        )
    # Never promote source-reported claims into authoritative admission.
    reasons = ["independent server-side merge-admission attestation not present"]
    reasons += ["head_ci." + n for n in head_missing]
    reasons += ["main_ci." + n for n in main_missing]
    reasons += ["governance." + n for n in unproven]
    return {
        "schema": "codepurple.g3cs.postmerge-evaluation.v1",
        "repository": packet["repository"],
        "pr_number": number,
        "head_sha": head,
        "parent_main_sha": base,
        "merge_main_sha": main,
        "merge_event": "SOURCE_REPORTED_MERGED",
        "merge_admission": "HOLD",
        "governed_merge_credit": False,
        "source_reported_proofs_complete": head_ok and main_ok and not unproven,
        "unmet_or_unverified": reasons,
        "main_coverage": main_cov,
        "pr_broad_coverage": pr_broad,
        "pr_diff_coverage": pr_diff,
        "first_red_transition": transition,
        "accepted_causal_root_closures": None,
        "authenticated_crew_launch_ids": None,
        "accepted_rex_receipts": None,
        "authority_transfer": False,
        "security_waiver": False,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
