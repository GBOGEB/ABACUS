"""MACH-III proposal evaluator: never edits GitHub rules or merges PRs."""
import json
from pathlib import Path


def decide(evidence, policy):
    if not policy.get("active", False):
        return "HOLD_POLICY_NOT_ACTIVE"
    if not all(evidence.get(k) is True for k in (
        "exact_head", "core_functional_checks", "effective_ruleset_compliance",
        "source_bound_receipt")):
        return "HOLD_REQUIRED"
    if evidence.get("security_severities") is None:
        return "HOLD_UNKNOWN_SECURITY"
    severities = set(evidence["security_severities"])
    if severities.intersection({"P0", "P1", "UNKNOWN"}):
        return "HOLD_SECURITY"
    if severities.intersection({"P2", "P3"}) and not evidence.get("deferred_findings_complete"):
        return "HOLD_DEFERRAL_RECORD"
    if evidence.get("required_reviews_satisfied") is not True:
        return "HOLD_REVIEW"
    if evidence.get("mergeable") is not True:
        return "HOLD_MERGEABILITY"
    return "GO_CANDIDATE_RECHECK_HEAD"


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--policy", type=Path, default=Path("config/governance/mach_iii_proposal.json"))
    args = parser.parse_args()
    print(decide(json.loads(args.evidence.read_text()), json.loads(args.policy.read_text())))


if __name__ == "__main__":
    main()
