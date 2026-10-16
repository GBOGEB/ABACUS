"""Conservative source-bound root-overlap telemetry; standard library only.

Input JSON: {"observations":[{"pr":2070,"head_sha":"...","run_id":123,
"job_id":456,"workflow":"...","job":"...","first_red_signature":"...",
"root_id":null,"root_evidence":null,"status":"failure"}]}
A shared job label is NOT a shared root. Missing evidence stays UNKNOWN.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path


def analyze(observations):
    seen = set()
    categories = defaultdict(set)
    roots = defaultdict(set)
    unknown = set()
    for item in observations:
        pr = item["pr"]
        key = (pr, item.get("head_sha"), item.get("run_id"), item.get("job_id"))
        if key in seen:
            continue
        seen.add(key)
        if item.get("status") != "failure":
            continue
        categories[item.get("job") or "UNKNOWN"].add(pr)
        root = item.get("root_id")
        if root and item.get("root_evidence") and item.get("first_red_signature"):
            roots[root].add(pr)
        else:
            unknown.add(pr)
    ranking = sorted(
        ({"root_id": root, "blocked_prs": len(prs), "prs": sorted(prs)}
         for root, prs in roots.items()),
        key=lambda r: (-r["blocked_prs"], r["root_id"]),
    )
    return {
        "schema_version": 1,
        "observation_count_deduplicated": len(seen),
        "observed_pr_denominator": len({x["pr"] for x in observations}),
        "failed_category_overlap": [
            {"job": name, "prs": sorted(prs), "count": len(prs)}
            for name, prs in sorted(categories.items())
        ],
        "proven_root_leverage": ranking,
        "unknown_root_prs": sorted(unknown),
        "potential_unique_prs_released": len(set().union(*(set(r["prs"]) for r in ranking)))
        if ranking else 0,
        "global_open_pr_denominator": None,
        "caveat": "Potential release is an upper bound, not merge eligibility; other blockers may remain.",
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
