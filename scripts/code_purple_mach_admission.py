"""CODE PURPLE MACH II-IV admission evaluator: never edits GitHub rules or merges PRs.

MACH-II   solo-owner standing mode: approval count waived by recorded owner
          policy, compensated by enforced required checks, green required
          lanes at the exact head and automated review at that head.
MACH-III  owner single-PR exception (scripts/mach_iii_admission.py), with the
          MACH-II waiver standing in for the approval it would otherwise need.
MACH-IV   merge train: ordered MACH-II/III steps, each qualified on the main
          produced by the previous step, closed by a post-train main baseline.
"""

import importlib.util
import json
from pathlib import Path

NON_TERMINAL = {None, "queued", "in_progress", "pending", "action_required"}


def _mach_iii_decide():
    path = Path(__file__).with_name("mach_iii_admission.py")
    spec = importlib.util.spec_from_file_location("mach_iii_admission", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.decide


def _lanes(lanes, required):
    if not required:
        return "HOLD_NO_REQUIRED_LANES"
    if any(lanes.get(name) in NON_TERMINAL for name in required):
        return "HOLD_NONTERMINAL_LANE"
    if any(lanes.get(name) != "success" for name in required):
        return "HOLD_RED_LANE"
    return None


def _waiver_covers(evidence, policy):
    waiver = policy.get("solo_owner_waiver") or {}
    return waiver.get("active") is True and evidence.get("author") in waiver.get(
        "owners", []
    )


def decide_mach_ii(evidence, policy):
    if not _waiver_covers(evidence, policy):
        return "HOLD_WAIVER_NOT_APPLICABLE"
    if evidence.get("exact_head") is not True:
        return "HOLD_EXACT_HEAD"
    if evidence.get("required_checks_enforced") is not True:
        return "HOLD_CHECKS_NOT_ENFORCED"
    lane_hold = _lanes(evidence.get("lanes") or {}, policy.get("required_lanes", []))
    if lane_hold:
        return lane_hold
    if evidence.get("automated_review_at_head") is not True:
        return "HOLD_AUTOMATED_REVIEW"
    if evidence.get("mergeable") is not True:
        return "HOLD_MERGEABILITY"
    return "GO_CANDIDATE_RECHECK_HEAD"


def decide_mach_iii(evidence, policy):
    config = policy.get("mach_iii") or {}
    exception = evidence.get("exception") or {}
    if not all(
        exception.get(k) for k in ("reason", "authorized_actor", "expiry", "source_sha")
    ):
        return "HOLD_EXCEPTION_RECORD"
    if not 0 < exception.get("minutes", 0) <= config.get("max_duration_minutes", 60):
        return "HOLD_EXCEPTION_WINDOW"
    if exception["source_sha"] != evidence.get("head_sha"):
        return "HOLD_EXACT_HEAD"
    reviewed = dict(evidence)
    if _waiver_covers(evidence, policy):
        reviewed["required_reviews_satisfied"] = True
    return _mach_iii_decide()(reviewed, {"active": config.get("active", False)})


def decide_mach_iv(evidence, policy):
    config = policy.get("merge_train") or {}
    if not config.get("active", False):
        return "HOLD_POLICY_NOT_ACTIVE"
    steps = evidence.get("train") or []
    if not steps:
        return "HOLD_EMPTY_TRAIN"
    if len(steps) > config.get("max_steps", 0):
        return "HOLD_TRAIN_TOO_LONG"
    expected_base = evidence.get("main_before")
    for number, step in enumerate(steps, 1):
        if step.get("base_sha") != expected_base:
            return f"HOLD_STEP_{number}_STALE_BASE"
        verdict = decide(step.get("level"), step, policy)
        if not verdict.startswith("GO_"):
            return f"HOLD_STEP_{number}_{verdict}"
        expected_base = step.get("merge_sha")
        if expected_base is None:
            return (
                "GO_NEXT_STEP_CANDIDATE"
                if number == len(steps)
                else f"HOLD_STEP_{number}_NO_MERGE_SHA"
            )
    if evidence.get("main_after") != expected_base:
        return "HOLD_POST_TRAIN_MAIN_MISMATCH"
    lane_hold = _lanes(
        evidence.get("post_train_lanes") or {}, config.get("post_train_lanes", [])
    )
    if lane_hold:
        return f"HOLD_POST_TRAIN_{lane_hold[len('HOLD_'):]}"
    return "GO_TRAIN_VERIFIED"


LEVELS = {"II": decide_mach_ii, "III": decide_mach_iii, "IV": decide_mach_iv}


def decide(level, evidence, policy):
    if level not in LEVELS:
        return "HOLD_UNKNOWN_LEVEL"
    return LEVELS[level](evidence, policy)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("level", choices=sorted(LEVELS))
    parser.add_argument("evidence", type=Path)
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("config/governance/code_purple_mach_policy.json"),
    )
    args = parser.parse_args()
    print(
        decide(
            args.level,
            json.loads(args.evidence.read_text()),
            json.loads(args.policy.read_text()),
        )
    )


if __name__ == "__main__":
    main()
