"""W31 read-only merge-admission readback; never writes GitHub settings.

A reported rule and a claimed human review are NOT effective enforcement proof.
Missing API access is UNKNOWN rather than zero; all outputs remain on HOLD.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
APPROVER_PERMISSIONS = frozenset({"write", "maintain", "admin"})


def require(ok, message):
    if not ok:
        raise ValueError(message)


def _status_rules(rules):
    statuses = []
    for rule in rules:
        if rule.get("type") != "required_status_checks":
            continue
        parameter = rule.get("parameters", {})
        checks = parameter.get("required_status_checks", [])
        require(isinstance(checks, list), "invalid status check population")
        for check in checks:
            name = check.get("context") if isinstance(check, dict) else None
            require(isinstance(name, str) and bool(name.strip()), "invalid required context")
            statuses.append(name)
    require(len(statuses) == len(set(statuses)), "duplicate required context")
    return statuses


def observe(payload):
    require(isinstance(payload, dict), "invalid admission readback")
    sha = payload.get("exact_head")
    require(isinstance(sha, str) and bool(SHA40.fullmatch(sha)), "invalid exact-head SHA")
    require(payload.get("default_branch") == "main", "default branch not re-resolved")
    author = payload.get("pr_author")
    require(isinstance(author, str) and bool(author), "missing PR author")
    ruleset = payload.get("ruleset")
    require(isinstance(ruleset, dict), "effective rules unavailable")
    rules = ruleset.get("rules")
    require(isinstance(rules, list), "missing raw rule population")
    pr_rules = [v.get("parameters", {}) for v in rules if v.get("type") == "pull_request"]
    require(len(pr_rules) <= 1, "conflicting PR review rule")
    pr = pr_rules[0] if pr_rules else {}
    configured = _status_rules(rules)
    desired = payload.get("expected_status_contexts", [])
    require(isinstance(desired, list) and all(isinstance(v, str) and v for v in desired),
            "invalid expected contexts")
    require(len(desired) == len(set(desired)), "duplicated expected contexts")
    checks = payload.get("check_runs")
    require(isinstance(checks, list), "check-run readback unavailable")
    names = set()
    statuses = {"success": 0, "failure": 0, "other_terminal": 0, "nonterminal": 0}
    for check in checks:
        require(isinstance(check, dict), "invalid check-run record")
        name = check.get("name")
        require(isinstance(name, str) and bool(name), "check name unavailable")
        require(check.get("head_sha") == sha, "foreign-head check-run")
        require(name not in names, "ambiguous duplicate check name")
        names.add(name)
        if check.get("status") != "completed":
            statuses["nonterminal"] += 1
        elif check.get("conclusion") == "success":
            statuses["success"] += 1
        elif check.get("conclusion") == "failure":
            statuses["failure"] += 1
        else:
            statuses["other_terminal"] += 1
    reviews = payload.get("reviews")
    require(isinstance(reviews, list), "review readback unavailable")
    candidates = 0
    for review in reviews:
        require(isinstance(review, dict), "invalid review metadata")
        if (review.get("state") == "APPROVED"
                and review.get("login") != author
                and review.get("account_type") == "User"
                and review.get("permission") in APPROVER_PERMISSIONS
                and review.get("head_sha") == sha):
            candidates += 1
    blockers = []
    if ruleset.get("enforcement") != "active":
        blockers.append("RULESET_NOT_ACTIVE")
    if not pr_rules or type(pr.get("required_approving_review_count")) is not int or pr["required_approving_review_count"] < 1:
        blockers.append("REVIEW_MINIMUM_NOT_CONFIGURED")
    if not pr.get("dismiss_stale_reviews_on_push"):
        blockers.append("STALE_REVIEW_PROTECTION_MISSING")
    if not pr.get("require_last_push_approval"):
        blockers.append("LAST_PUSH_APPROVAL_MISSING")
    if not pr.get("required_review_thread_resolution"):
        blockers.append("THREAD_RESOLUTION_NOT_REQUIRED")
    if not configured or any(name not in configured for name in desired):
        blockers.append("REQUIRED_CHECK_CONTEXTS_INCOMPLETE")
    bypass = [v for v in ruleset.get("bypass_actors", [])
              if isinstance(v, dict) and v.get("bypass_mode") == "always"]
    if bypass:
        blockers.append("ALWAYS_BYPASS_INTEGRATIONS")
    for name in configured:
        if name not in names:
            blockers.append("CHECK_RESULT_MISSING:" + name)
        else:
            matching = next(x for x in checks if x["name"] == name)
            if matching.get("status") != "completed" or matching.get("conclusion") != "success":
                blockers.append("CHECK_NOT_GREEN:" + name)
    if candidates == 0:
        blockers.append("INDEPENDENT_REVIEW_NOT_OBSERVED")
    if payload.get("branch_protection_readback") is None:
        blockers.append("EFFECTIVE_PROTECTION_UNKNOWN")
    if payload.get("rejected_red_canary") is not True:
        blockers.append("REJECTED_RED_CANARY_UNPROVEN")
    return {
        "schema": "abacus.cbd.w31.admission-readback.v1",
        "exact_head": sha,
        "default_branch": "main",
        "rule_enforcement": ruleset.get("enforcement"),
        "configured_required_status_contexts": configured,
        "expected_contexts": desired,
        "observed_check_runs": len(checks),
        "check_run_counts": statuses,
        "review_submissions": len(reviews),
        "eligible_review_metadata_candidates": candidates,
        "eligible_human_approval_independently_verified": None,
        "effective_branch_protection_verified": None,
        "rejected_red_canary_source_verified": None,
        "always_bypass_integrations": len(bypass),
        "blockers": sorted(set(blockers)),
        "formal_credit_delta": 0,
        "merge_admission": "HOLD",
        "security_waiver": False,
        "authority_transfer": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    result = observe(json.loads(a.evidence.read_text(encoding="utf-8")))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                     encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
