"""Compare coverage only where canonical module and denominator identities match."""

import argparse
import json
from pathlib import Path


def compare(base: dict, head: dict) -> dict:
    if not isinstance(base, dict) or not isinstance(head, dict):
        raise ValueError("coverage receipts must be objects")
    if not all(isinstance(x.get("modules"), dict) for x in (base, head)):
        raise ValueError("module-scoped evidence required")
    cohort = sorted(set(base["modules"]) & set(head["modules"]))
    required = (
        "covered_lines",
        "eligible_lines",
        "covered_branches",
        "eligible_branches",
    )
    valid = [
        k
        for k in cohort
        if all(
            isinstance(r["modules"][k].get(f), int) and r["modules"][k][f] >= 0
            for r in (base, head)
            for f in required
        )
        and all(
            base["modules"][k][f] == head["modules"][k][f]
            for f in ("eligible_lines", "eligible_branches")
        )
    ]

    def totals(receipt):
        return {f: sum(receipt["modules"][k][f] for k in valid) for f in required}

    a, b = totals(base), totals(head)
    return {
        "schema": "coverage.comparable.v1",
        "cohort": valid,
        "excluded": sorted(set(cohort) - set(valid)),
        "base": a,
        "head": b,
        "line_covered_delta": b["covered_lines"] - a["covered_lines"],
        "branch_covered_delta": b["covered_branches"] - a["covered_branches"],
        "admission": "HOLD",
        "closure_credit": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("base", type=Path)
    p.add_argument("head", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.out.write_text(
        json.dumps(
            compare(json.loads(a.base.read_text()), json.loads(a.head.read_text())),
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
