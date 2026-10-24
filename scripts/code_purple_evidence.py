"""CODE PURPLE evidence contracts: admission, root credit and notification.

Read-only. Never merges, approves, waives or edits GitHub rules.

Four independent KPIs, none of which establishes another: coverage growth, root
reduction, runner activity and merge admission. Unknown stays ``None``; it is
never coerced to ``0`` or ``False``-as-evidence.

Owners (this module imports them, never copies them):
  - MACH ladder decisions: scripts/code_purple_mach_admission.py
  - policy: config/governance/code_purple_mach_policy.json
"""

import hashlib
import importlib.util
import json
from pathlib import Path

GO = "GO_CANDIDATE_RECHECK_HEAD"

ISSUE_STATES = ("open", "closed")
ROOT_STATES = (
    "unknown",
    "open",
    "suspected",
    "fix_proposed",
    "displaced",
    "accepted_closure",
)
# Review authors that can never supply independent approval.
AUTOMATED_USER_TYPES = {"Bot", "Organization"}


def _mach():
    path = Path(__file__).with_name("code_purple_mach_admission.py")
    spec = importlib.util.spec_from_file_location("code_purple_mach_admission", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# 1. Admission: one fail-closed verdict
# --------------------------------------------------------------------------- #

def classify_reviews(reviews, head_sha, author):
    """Return the strongest review identity present at ``head_sha``.

    ``human_approval`` needs an APPROVED review by a non-bot user other than the
    PR author, made on the exact head. ``automated_comment_only`` covers every
    other review at the head (bots, COMMENTED, self-approval). Unknown input is
    ``unknown``.
    """
    if reviews is None or head_sha is None:
        return "unknown"
    at_head = [r for r in reviews if r.get("commit_id") == head_sha]
    for review in at_head:
        if (
            review.get("state") == "APPROVED"
            and review.get("user_type") not in AUTOMATED_USER_TYPES
            and review.get("login") not in (None, author)
        ):
            return "human_approval"
    return "automated_comment_only" if at_head else "none"


def _unknown_fields(evidence, fields):
    return [name for name in fields if evidence.get(name) is None]


def admission_verdict(level, evidence, policy):
    """Single admission answer: ``GO_*`` only if every gate is affirmatively met.

    Pre-gates apply at every level and run before the MACH ladder:
      * protection must be *effective* (enforced checks, rejected RED canary);
      * the evidence head must equal the PR head observed now;
      * a missing field is ``HOLD_UNKNOWN_<FIELD>``, never assumed.
    MACH-I (no recorded waiver) additionally needs independent human approval.
    Any exception while evaluating is ``HOLD_EVIDENCE_ERROR``.
    """
    try:
        unknown = _unknown_fields(
            evidence,
            ("head_sha", "observed_head_sha", "required_checks_enforced",
             "canary_rejected"),
        )
        if unknown:
            return "HOLD_UNKNOWN_" + unknown[0].upper()
        if evidence["head_sha"] != evidence["observed_head_sha"]:
            return "HOLD_EXACT_HEAD"
        if evidence["required_checks_enforced"] is not True:
            return "HOLD_CHECKS_NOT_ENFORCED"
        if evidence["canary_rejected"] is not True:
            return "HOLD_NO_REJECTED_CANARY"

        identity = classify_reviews(
            evidence.get("reviews"), evidence["head_sha"], evidence.get("author")
        )
        if level == "I":
            return GO if identity == "human_approval" else "HOLD_INDEPENDENT_REVIEW"
        if identity == "unknown":
            return "HOLD_UNKNOWN_REVIEWS"

        # The ladder reads ``automated_review_at_head``; derive it from reviews
        # rather than trusting a caller-supplied flag.
        derived = dict(
            evidence, automated_review_at_head=identity != "none", exact_head=True
        )
        return _mach().decide(level, derived, policy)
    except Exception:  # fail closed
        return "HOLD_EVIDENCE_ERROR"


def merge_verified(record):
    """True only for a governed merge proven by readback of the merged SHA.

    Needs an admission verdict recorded for the same head that was merged, and
    the merge SHA read back from main to equal the SHA the API reported.
    """
    needed = ("verdict", "admitted_head", "merged_head", "merge_sha",
              "merge_sha_readback")
    if any(record.get(name) is None for name in needed):
        return False
    return (
        str(record["verdict"]).startswith("GO_")
        and record["admitted_head"] == record["merged_head"]
        and record["merge_sha"] == record["merge_sha_readback"]
    )


# --------------------------------------------------------------------------- #
# 2. Issue state, root state and engineering credit are separate axes
# --------------------------------------------------------------------------- #

def engineering_credit(issue_state, root_state, closure_merge=None):
    """Credit for one root. GitHub issue closure alone never earns any.

    ``accepted_closure`` is the only root state that can earn credit, and only
    with a verified governed merge (``merge_verified``). Returns one of
    ``CREDITED``, ``HOUSEKEEPING_ONLY``, ``NONE`` or ``UNKNOWN``.
    """
    if issue_state not in ISSUE_STATES or root_state not in ROOT_STATES:
        return "UNKNOWN"
    if root_state == "unknown":
        return "UNKNOWN"
    if root_state == "accepted_closure":
        return "CREDITED" if closure_merge and merge_verified(closure_merge) else "NONE"
    return "HOUSEKEEPING_ONLY" if issue_state == "closed" else "NONE"


# --------------------------------------------------------------------------- #
# 3. Notification: material transitions only, deduplicated by event identity
# --------------------------------------------------------------------------- #

def _event_id(kind, current, discriminator):
    raw = json.dumps(
        [kind, current.get("source_sha"), current.get("baseline_id"), discriminator],
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _alert(kind, current, discriminator, **extra):
    return dict(
        {
            "event_id": _event_id(kind, current, discriminator),
            "kind": kind,
            "source_sha": current.get("source_sha"),
            "baseline_id": current.get("baseline_id"),
            "urls": current.get("urls"),
            "numerator": current.get("numerator"),
            "denominator": current.get("denominator"),
            "root_id": current.get("root_id"),
            "next_action": current.get("next_action"),
        },
        **extra,
    )


def notifications(previous, current, seen=frozenset()):
    """Alerts for state transitions not already notified.

    ``previous`` and ``current`` are observation dicts. ``seen`` holds
    ``event_id`` values already sent; the caller persists them. An alert needs a
    ``source_sha``: an observation without one is not evidence.
    """
    if not current.get("source_sha"):
        return []
    out = []

    if (
        current.get("governed_main_merge_verified") is True
        and previous.get("governed_main_merge_verified") is not True
        and current.get("merge_sha")
    ):
        out.append(_alert("governed_main_merge", current, current["merge_sha"]))

    delta = current.get("matched_coverage_delta")
    if (
        current.get("matched_coverage_delta_verified") is True
        and current.get("baseline_id")
        and delta is not None
        and delta > 0
    ):
        out.append(_alert("matched_coverage_gain", current, delta, delta=delta))

    if current.get("material_todo_milestone_newly_completed") is True:
        out.append(_alert("todo_milestone", current, current.get("todo_completed")))

    if (
        current.get("blocking_first_red_changed") is True
        and current.get("first_red_id")
        and current.get("first_red_id") != previous.get("first_red_id")
    ):
        out.append(_alert("blocking_first_red", current, current["first_red_id"]))

    return [alert for alert in out if alert["event_id"] not in seen]


def should_notify(previous, current, seen=frozenset()):
    return bool(notifications(previous, current, seen))
