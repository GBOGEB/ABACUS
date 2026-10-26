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
# Only a positively identified actor type counts. A review whose ``user_type``
# is missing or unrecognised is neither human nor automated: it counts for
# nothing, so incomplete identity can only ever hold.
AUTOMATED_USER_TYPES = {"Bot", "Organization"}
HUMAN_USER_TYPES = {"User"}


def _mach():
    path = Path(__file__).with_name("code_purple_mach_admission.py")
    spec = importlib.util.spec_from_file_location("code_purple_mach_admission", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _number(value):
    """``value`` if it is a real number, else ``None`` (bools and strings are not)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


# --------------------------------------------------------------------------- #
# 1. Admission: one fail-closed verdict
# --------------------------------------------------------------------------- #


def review_facts(reviews, head_sha, author):
    """Review facts at ``head_sha``: ``(known, human_approval, automated_review)``.

    ``human_approval``: an APPROVED review by a positively identified human
    (``user_type`` User, with a login) who is not the PR author, and only when
    the author is known. ``automated_review``: any review by a positively
    identified automated actor. Reviews on other heads and reviews with
    incomplete identity count for neither. Missing reviews or head: not known.
    """
    if reviews is None or head_sha is None:
        return (False, False, False)
    at_head = [r for r in reviews if r.get("commit_id") == head_sha]
    human = any(
        r.get("state") == "APPROVED"
        and r.get("user_type") in HUMAN_USER_TYPES
        and r.get("login")
        and author
        and r.get("login") != author
        for r in at_head
    )
    automated = any(r.get("user_type") in AUTOMATED_USER_TYPES for r in at_head)
    return (True, human, automated)


def classify_reviews(reviews, head_sha, author):
    """Strongest review identity present at ``head_sha``, for reporting.

    One of ``human_approval``, ``automated_review``, ``other_review`` (a review
    that is neither: human COMMENTED, self-review, incomplete identity),
    ``none`` or ``unknown``.
    """
    known, human, automated = review_facts(reviews, head_sha, author)
    if not known:
        return "unknown"
    if human:
        return "human_approval"
    if automated:
        return "automated_review"
    at_head = [r for r in reviews if r.get("commit_id") == head_sha]
    return "other_review" if at_head else "none"


def _pregate(evidence):
    """Gates common to every level; a ``HOLD_*`` string, or ``None`` if met."""
    for name in (
        "head_sha",
        "observed_head_sha",
        "required_checks_enforced",
        "canary_rejected",
    ):
        if evidence.get(name) is None:
            return "HOLD_UNKNOWN_" + name.upper()
    if evidence["head_sha"] != evidence["observed_head_sha"]:
        return "HOLD_EXACT_HEAD"
    if evidence["required_checks_enforced"] is not True:
        return "HOLD_CHECKS_NOT_ENFORCED"
    if evidence["canary_rejected"] is not True:
        return "HOLD_NO_REJECTED_CANARY"
    return None


def _derive(evidence):
    """Overwrite every review assertion the ladder reads with a derived one.

    Caller-supplied ``automated_review_at_head``, ``required_reviews_satisfied``
    and ``exact_head`` are never trusted; they come from the review list and
    the head comparison. Lane results and mergeability stay observations the
    caller supplies.
    """
    _, human, automated = review_facts(
        evidence.get("reviews"), evidence.get("head_sha"), evidence.get("author")
    )
    return dict(
        evidence,
        automated_review_at_head=automated,
        required_reviews_satisfied=human,
        exact_head=True,
    )


def _admit_mach_i(evidence, policy):
    """No recorded waiver: independent approval plus every other MACH-I control."""
    known, human, _ = review_facts(
        evidence.get("reviews"), evidence["head_sha"], evidence.get("author")
    )
    if not known:
        return "HOLD_UNKNOWN_REVIEWS"
    # An approval on the exact head is also the last-push approval.
    if not human:
        return "HOLD_INDEPENDENT_REVIEW"
    threads = _number(evidence.get("unresolved_threads"))
    if threads is None:
        return "HOLD_UNKNOWN_UNRESOLVED_THREADS"
    if threads > 0:
        return "HOLD_UNRESOLVED_THREADS"
    lane_hold = _mach()._lanes(
        evidence.get("lanes") or {}, policy.get("required_lanes", [])
    )
    if lane_hold:
        return lane_hold
    return GO if evidence.get("mergeable") is True else "HOLD_MERGEABILITY"


def admission_verdict(level, evidence, policy):
    """Single admission answer: ``GO_*`` only if every gate is affirmatively met.

    Pre-gates apply at every level and run before the MACH ladder:
      * protection must be *effective* (enforced checks, rejected RED canary);
      * the evidence head must equal the PR head observed now;
      * a missing field is ``HOLD_UNKNOWN_<FIELD>``, never assumed.
    MACH-I (no recorded waiver) additionally needs independent human approval
    on the exact head, no unresolved threads, green lanes and mergeability.
    Levels II to IV have their review assertions derived from review lists (for
    MACH-IV, per train step, each step also passing the pre-gates); an
    automated review must come from a positively identified automated actor.
    Any exception while evaluating is ``HOLD_EVIDENCE_ERROR``.
    """
    try:
        if level == "IV":
            derived = []
            for number, step in enumerate(evidence.get("train") or [], 1):
                hold = _pregate(step)
                if hold:
                    return f"HOLD_STEP_{number}_{hold}"
                derived.append(_derive(step))
            return _mach().decide(level, dict(evidence, train=derived), policy)
        hold = _pregate(evidence)
        if hold:
            return hold
        if level == "I":
            return _admit_mach_i(evidence, policy)
        known, _, _ = review_facts(
            evidence.get("reviews"), evidence["head_sha"], evidence.get("author")
        )
        if not known:
            return "HOLD_UNKNOWN_REVIEWS"
        return _mach().decide(level, _derive(evidence), policy)
    except Exception:  # noqa: BLE001  fail closed: any evaluation error is a HOLD
        return "HOLD_EVIDENCE_ERROR"


def merge_verified(record):
    """True only for a governed merge proven by readback of the merged SHA.

    Needs an admission verdict recorded for the same head that was merged, and
    the merge SHA read back from main to equal the SHA the API reported.
    """
    needed = (
        "verdict",
        "admitted_head",
        "merged_head",
        "merge_sha",
        "merge_sha_readback",
    )
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

    ``previous`` and ``current`` are observation dicts (``previous`` may be ``None``
    for a first observation). ``seen`` holds
    ``event_id`` values already sent; the caller persists them. An alert needs a
    ``source_sha``: an observation without one is not evidence.
    """
    previous = previous or {}
    if not current or not current.get("source_sha"):
        return []
    out = []

    # A new verified merge is a new merge SHA, not merely "still verified".
    if (
        current.get("governed_main_merge_verified") is True
        and current.get("merge_sha")
        and (
            previous.get("governed_main_merge_verified") is not True
            or previous.get("merge_sha") != current["merge_sha"]
        )
    ):
        out.append(_alert("governed_main_merge", current, current["merge_sha"]))

    delta = _number(current.get("matched_coverage_delta"))
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


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    """``admission LEVEL EVIDENCE`` prints a verdict; ``notify PREV CUR`` prints alerts.

    ``notify --seen FILE`` reads and then updates a JSON list of sent event ids,
    so re-running on the same observation prints nothing.
    """
    import argparse

    parser = argparse.ArgumentParser(description=main.__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    adm = sub.add_parser("admission")
    adm.add_argument("level", choices=("I", "II", "III", "IV"))
    adm.add_argument("evidence", type=Path)
    adm.add_argument(
        "--policy",
        type=Path,
        default=Path("config/governance/code_purple_mach_policy.json"),
    )
    note = sub.add_parser("notify")
    note.add_argument("previous", type=Path)
    note.add_argument("current", type=Path)
    note.add_argument("--seen", type=Path)
    args = parser.parse_args(argv)

    if args.command == "admission":
        print(admission_verdict(args.level, _load(args.evidence), _load(args.policy)))
        return 0

    seen = set(_load(args.seen)) if args.seen and args.seen.exists() else set()
    alerts = notifications(_load(args.previous), _load(args.current), seen)
    if args.seen and alerts:
        args.seen.write_text(
            json.dumps(sorted(seen | {a["event_id"] for a in alerts})) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps(alerts, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
