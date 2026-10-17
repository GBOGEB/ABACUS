"""Independent admission *eligibility* evaluator, never a merge executor.
No data-file assertion can confer security/governance authority by itself.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib

from everred import InvalidEvidence, valid_sha
from native_ingest import GH_RE, GitHubReadOnly

GATES = (
    "exact_head_ci",
    "security",
    "coverage",
    "workflow_governance",
    "branch_protection",
    "independent_review",
    "review_conversations",
)


def utc(t):
    try:
        x = dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
        if x.utcoffset() is None:
            raise ValueError("naive")
        return x
    except (ValueError, AttributeError, TypeError) as e:
        raise InvalidEvidence("invalid UTC timestamp") from e


def evaluate(x, *, authenticated=False, now=None):
    if (
        not isinstance(x, dict)
        or x.get("schema") != "abacus.everred.admission.inputs.v1"
    ):
        raise InvalidEvidence("bad admission input schema")
    repo = x.get("repository")
    sha = x.get("candidate_sha")
    base = x.get("main_sha")
    if (
        not isinstance(repo, str)
        or not GH_RE.fullmatch(repo)
        or not valid_sha(sha)
        or not valid_sha(base)
    ):
        raise InvalidEvidence("repository/exact SHA binding required")
    if x.get("target_branch") != "main":
        raise InvalidEvidence("only main admission supported")
    gates = {k: "UNKNOWN" for k in GATES}
    why = {}
    checks = x.get("checks")
    needed = x.get("required_checks")
    if (
        isinstance(checks, list)
        and isinstance(needed, list)
        and needed
        and len(set(needed)) == len(needed)
    ):
        current = [j for j in checks if isinstance(j, dict) and j.get("sha") == sha]
        by_name = {n: [j for j in current if j.get("name") == n] for n in needed}
        if all(len(v) == 1 for v in by_name.values()):
            gates["exact_head_ci"] = (
                "PASS"
                if all(
                    v[0].get("conclusion") == "success"
                    and v[0].get("status") == "completed"
                    for v in by_name.values()
                )
                else "RED"
            )
        else:
            why["exact_head_ci"] = "missing, ambiguous or mismatched-SHA native checks"
    else:
        why["exact_head_ci"] = "missing complete required-check set"
    for field, gate in [
        ("security", "security"),
        ("coverage", "coverage"),
        ("workflow_governance", "workflow_governance"),
    ]:
        item = x.get(field)
        if (
            isinstance(item, dict)
            and item.get("sha") == sha
            and item.get("decision") in ("PASS", "RED")
        ):
            gates[gate] = item["decision"]
        else:
            why[gate] = "missing signed-off exact-SHA independent receipt"
    policy = x.get("policy")
    if (
        isinstance(policy, dict)
        and policy.get("source") == "effective_branch_rules"
        and policy.get("repository") == repo
        and policy.get("branch") == "main"
        and policy.get("main_sha") == base
    ):
        t = now or dt.datetime.now(dt.timezone.utc)
        fresh = abs((t - utc(policy.get("fetched_at"))).total_seconds()) <= 900
        props = (
            "protected",
            "required_pr",
            "strict_checks",
            "block_force_push",
            "block_deletion",
            "require_resolved_conversations",
            "require_last_push_approval",
            "dismiss_stale_reviews_on_push",
            "main_hard_gate_active",
            "main_hard_gate_no_bypass",
        )
        if (
            fresh
            and all(policy.get(k) is True for k in props)
            and type(policy.get("min_approvals")) is int
            and policy["min_approvals"] >= 1
            and isinstance(policy.get("status_contexts"), list)
            and len(policy["status_contexts"]) > 0
            and len(policy["status_contexts"]) == len(set(policy["status_contexts"]))
            and all(
                isinstance(name, str) and name for name in policy["status_contexts"]
            )
            and "PR Feedback Gate" in policy["status_contexts"]
            and isinstance(needed, list)
            and all(
                isinstance(name, str) and name in policy["status_contexts"]
                for name in needed
            )
        ):
            gates["branch_protection"] = "PASS"
        elif not fresh:
            why["branch_protection"] = (
                "server-side effective-rules snapshot older than 15 minutes"
            )
        else:
            gates["branch_protection"] = "RED"
            why["branch_protection"] = "one or more mandatory effective rules missing"
    else:
        why["branch_protection"] = "no bound effective-server-rules receipt"
    reviews = x.get("reviews")
    author = x.get("pr_author")
    if isinstance(reviews, list) and isinstance(author, str) and author:
        approved = [
            r
            for r in reviews
            if isinstance(r, dict)
            and r.get("state") == "APPROVED"
            and r.get("login") != author
            and r.get("commit_id") == sha
            and r.get("eligible") is True
        ]
        if approved and not any(
            isinstance(r, dict) and r.get("state") == "CHANGES_REQUESTED"
            for r in reviews
        ):
            gates["independent_review"] = "PASS"
        else:
            gates["independent_review"] = "RED"
            why["independent_review"] = "no eligible independent exact-head approval"
    else:
        why["independent_review"] = "review roster unavailable"
    conv = x.get("unresolved_review_conversations")
    if type(conv) is int and conv >= 0:
        gates["review_conversations"] = "PASS" if conv == 0 else "RED"
    else:
        why["review_conversations"] = "unresolved thread census unavailable"
    eligible = all(z == "PASS" for z in gates.values()) and authenticated
    return {
        "schema": "abacus.everred.admission.evaluation.v1",
        "repository": repo,
        "candidate_sha": sha,
        "main_sha": base,
        "gates": gates,
        "uncertainty": why,
        "decision": "ELIGIBLE_PENDING_AUTHORIZED_MERGE" if eligible else "HOLD",
        "evidence_authentication": (
            "AUTHENTICATED_COLLECTOR" if authenticated else "UNVERIFIED_IMPORT"
        ),
        "merge_authorized": False,
        "security_waiver": False,
        "authority_transfer": False,
    }


def effective_policy_from_rules(
    repo, main_sha, rules, branch, fetched_at, *, main_hard_gate=None
):
    """Fail closed on unbound controls. A protected branch alone is not admission."""
    if not isinstance(rules, list) or not isinstance(branch, dict):
        raise InvalidEvidence("invalid GitHub effective policy")
    by_type = {
        r.get("type"): r.get("parameters") or {} for r in rules if isinstance(r, dict)
    }
    reviews = by_type.get("pull_request", {})
    checks = by_type.get("required_status_checks", {})
    contexts = checks.get("required_status_checks")
    status_contexts = (
        [item.get("context") for item in contexts]
        if isinstance(contexts, list)
        and all(isinstance(item, dict) for item in contexts)
        else None
    )
    hard_gate_valid = (
        isinstance(main_hard_gate, dict)
        and main_hard_gate.get("id") == 24494381
        and main_hard_gate.get("source") == repo
        and main_hard_gate.get("target") == "branch"
        and main_hard_gate.get("enforcement") == "active"
    )
    return {
        "source": "effective_branch_rules",
        "repository": repo,
        "branch": "main",
        "main_sha": main_sha,
        "fetched_at": fetched_at,
        "protected": branch.get("protected") is True,
        "required_pr": "pull_request" in by_type,
        "min_approvals": reviews.get("required_approving_review_count"),
        "strict_checks": checks.get("strict_required_status_checks_policy") is True,
        "status_contexts": status_contexts,
        "require_last_push_approval": reviews.get("require_last_push_approval") is True,
        "dismiss_stale_reviews_on_push": reviews.get("dismiss_stale_reviews_on_push")
        is True,
        "main_hard_gate_active": hard_gate_valid,
        "main_hard_gate_no_bypass": (
            hard_gate_valid and main_hard_gate.get("bypass_actors") == []
        ),
        "block_force_push": "non_fast_forward" in by_type,
        "block_deletion": "deletion" in by_type,
        "require_resolved_conversations": reviews.get(
            "required_review_thread_resolution"
        )
        is True,
        "effective_rules_count": len(rules),
    }


def collect_readonly_policy(reader: GitHubReadOnly, repo, branch_sha):
    if not valid_sha(branch_sha):
        raise InvalidEvidence("invalid branch SHA")
    branch = reader.get(f"/repos/{repo}/branches/main")
    if branch.get("commit", {}).get("sha") != branch_sha:
        raise InvalidEvidence("main advanced; policy snapshot stale")
    rules = reader.get(f"/repos/{repo}/rules/branches/main")
    hard_gate = reader.get(f"/repos/{repo}/rulesets/24494381")
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    return effective_policy_from_rules(
        repo, branch_sha, rules, branch, now, main_hard_gate=hard_gate
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output")
    a = p.parse_args()
    x = json.loads(pathlib.Path(a.input).read_text())
    result = evaluate(x, authenticated=False)
    txt = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if a.output:
        pathlib.Path(a.output).write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
