"""Read-only evidence classifier for completed feedback upstream events.

A negative linked-PR census is only a diagnostic no-op *candidate* for one
completed workflow_run, never permission to skip checks or merge a PR.
"""

from __future__ import annotations

import re

SHA = re.compile(r"^[0-9a-f]{40}$")
SCHEMA = "abacus.feedback.noop-linkage.v1"


def classify(event, main_sha, linked_prs):
    result = {
        "schema": SCHEMA,
        "classification": "UNKNOWN",
        "reason": "INCOMPLETE_OR_INCONSISTENT_EVIDENCE",
        "skip_authorized": False,
        "authority_transfer": False,
    }
    if not isinstance(main_sha, str) or not SHA.fullmatch(main_sha):
        return result
    if not isinstance(event, dict) or event.get("action") != "completed":
        return result
    run = event.get("workflow_run")
    if not isinstance(run, dict) or run.get("status") != "completed":
        return result
    if run.get("head_sha") != main_sha or run.get("head_branch") != "main":
        return {
            **result,
            "classification": "EVALUATE",
            "reason": "PR_OR_NON_CURRENT_MAIN_EVENT",
        }
    source_pulls = run.get("pull_requests")
    if not isinstance(source_pulls, list):
        return result
    if source_pulls:
        return {
            **result,
            "classification": "EVALUATE",
            "reason": "EVENT_DECLARED_PR_ASSOCIATION",
        }
    if not isinstance(linked_prs, list):
        return result
    numbers = set()
    for pr in linked_prs:
        if not isinstance(pr, dict):
            return result
        number, state = pr.get("number"), pr.get("state")
        if type(number) is not int or number <= 0 or number in numbers:
            return result
        numbers.add(number)
        if state not in ("open", "closed"):
            return result
        if state == "open":
            return {
                **result,
                "classification": "EVALUATE",
                "reason": "OPEN_COMMIT_LINKED_PR_PRESENT",
            }
    return {
        **result,
        "classification": "PROVEN_NO_OPEN_LINKED_PR",
        "reason": "EVENT_EMPTY_AND_COMMIT_LINKED_PRS_CLOSED",
        "main_sha": main_sha,
        "linked_pr_count": len(linked_prs),
        "read_only_candidate": True,
        "skip_authorized": False,
    }
