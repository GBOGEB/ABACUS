"""Fail-closed source-bound root-overlap telemetry without admission authority.

A common workflow/job label is not evidence of a common causal root.
Only explicit source-bound owner dispositions qualify a root hypothesis.
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


SHA40 = re.compile(r"[0-9a-f]{40}\Z")
ROOT_ID = re.compile(r"[A-Z][A-Z0-9_-]{2,79}\Z")
GITHUB_EVIDENCE = re.compile(
    r"https://github\.com/GBOGEB/[A-Za-z0-9_.-]+/(?:issues|pull|actions/runs)/[0-9]+(?:#.*)?\Z"
)


def _positive(value):
    return type(value) is int and value > 0


def analyze(observations):
    """Produce bounded observational, never self-authorizing, root candidates."""
    if not isinstance(observations, list) or len(observations) > 512:
        raise ValueError("bounded observations list required")
    seen = {}
    categories = defaultdict(set)
    roots = defaultdict(set)
    root_owner = {}
    unknown = set()
    failed_prs = set()
    for item in observations:
        if not isinstance(item, dict):
            raise ValueError("observation must be object")
        pr = item.get("pr")
        if not _positive(pr) or not isinstance(item.get("head_sha"), str):
            raise ValueError("invalid PR/source identity")
        if SHA40.fullmatch(item["head_sha"]) is None:
            raise ValueError("invalid PR/head SHA")
        if not all(
            _positive(item.get(key))
            for key in ("run_id", "run_attempt", "job_id")
        ):
            raise ValueError("missing native run/job/attempt identity")
        if item.get("status") not in ("failure", "success", "skipped"):
            raise ValueError("unsupported native terminal status")
        key = (
            pr,
            item["head_sha"],
            item["run_id"],
            item["run_attempt"],
            item["job_id"],
        )
        signature = (
            item.get("job"),
            item.get("status"),
            item.get("first_red_signature"),
            item.get("root_id"),
            item.get("root_owner"),
            item.get("root_evidence"),
            item.get("owner_disposition"),
        )
        if key in seen:
            if seen[key] != signature:
                raise ValueError("conflicting duplicate native identity")
            continue
        seen[key] = signature
        if item["status"] != "failure":
            if any(
                item.get(field) is not None
                for field in ("root_id", "root_owner", "owner_disposition")
            ):
                raise ValueError("nonfailure cannot assert a root")
            continue
        failed_prs.add(pr)
        categories[item.get("job") or "UNKNOWN"].add(pr)
        root = item.get("root_id")
        if root is None:
            if any(
                item.get(field) is not None
                for field in ("root_owner", "root_evidence", "owner_disposition")
            ):
                raise ValueError("unowned root evidence cannot be promoted")
            unknown.add(pr)
            continue
        if not isinstance(root, str) or ROOT_ID.fullmatch(root) is None:
            raise ValueError("invalid root ID")
        owner = item.get("root_owner")
        evidence = item.get("root_evidence")
        if (
            item.get("owner_disposition") != "ACCEPTED"
            or not isinstance(owner, str)
            or not owner.strip()
            or not isinstance(evidence, str)
            or GITHUB_EVIDENCE.fullmatch(evidence) is None
            or not isinstance(item.get("first_red_signature"), str)
            or not item["first_red_signature"].strip()
        ):
            raise ValueError("root lacks qualified owner/evidence/signature")
        binding = (owner, evidence)
        if root in root_owner and root_owner[root] != binding:
            raise ValueError("conflicting root owner or evidence")
        root_owner[root] = binding
        roots[root].add(pr)

    ranking = sorted(
        (
            {
                "root_id": root,
                "blocked_prs": len(prs),
                "prs": sorted(prs),
                "root_owner": root_owner[root][0],
                "root_evidence": root_owner[root][1],
            }
            for root, prs in roots.items()
        ),
        key=lambda record: (-record["blocked_prs"], record["root_id"]),
    )
    qualified_prs = set().union(*(set(x["prs"]) for x in ranking)) if ranking else set()
    # Owner-supplied URL and disposition are not authenticated by this reader.
    # Classify only claims; a downstream verified REX join owns promotion.
    owner_claim_complete = failed_prs - unknown
    return {
        "schema_version": 2,
        "observation_count_deduplicated": len(seen),
        "observed_pr_denominator": len({x["pr"] for x in observations}),
        "failed_pr_denominator": len(failed_prs),
        "failed_category_overlap": [
            {"job": name, "prs": sorted(prs), "count": len(prs)}
            for name, prs in sorted(categories.items())
        ],
        "proven_root_leverage": [],
        "owner_claimed_root_leverage": ranking,
        "root_claims_authenticated": False,
        "unknown_root_prs": sorted(unknown),
        "fully_owner_claimed_failed_prs": sorted(owner_claim_complete),
        "root_attribution_pr_fraction": None,
        "owner_claim_attribution_fraction": (
            round(len(owner_claim_complete) / len(failed_prs), 6)
            if failed_prs
            else None
        ),
        "potential_unique_prs_released": None,
        "candidate_pr_impact_upper_bound": len(qualified_prs),
        "global_open_pr_denominator": None,
        "actually_unblocked_prs": None,
        "accepted_root_closures": None,
        "merge_authorized": False,
        "security_waiver": False,
        "caveat": (
            "Submitted owner claims are not authenticated by this reader. "
            "Do not count roots, release, closure or merge credit."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = analyze(payload["observations"])
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
