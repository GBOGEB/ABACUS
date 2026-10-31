"""Exact-head, same-source W29 native temporal-coverage engineering receipt.

This is a measured testflight comparator, not GitHub authentication, merge
authority, security clearance, global-main coverage or changed-line coverage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from scripts import cbd_coverage_temporal_gate as temporal

SOURCE = "scripts/cbd_coverage_temporal_gate.py"
ALLOWED = {SOURCE, SOURCE.replace("/", "\\")}
SHA40 = re.compile(r"^[a-f0-9]{40}$")
METRICS = ("num_statements", "covered_lines", "num_branches", "covered_branches")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def coverage_from(path: Path):
    raw = path.read_bytes()
    require(0 < len(raw) < 2_000_000, "missing/oversized native coverage")
    doc = json.loads(raw)
    require(isinstance(doc, dict), "invalid native coverage document")
    meta, files, totals = doc.get("meta"), doc.get("files"), doc.get("totals")
    require(
        isinstance(meta, dict) and meta.get("branch_coverage") is True,
        "branch instrumentation required",
    )
    require(
        isinstance(files, dict) and len(files) == 1 and next(iter(files)) in ALLOWED,
        "unexpected source path/scope",
    )
    require(isinstance(totals, dict), "coverage totals unavailable")
    source = next(iter(files.values()))
    source_summary = source.get("summary") if isinstance(source, dict) else None
    require(isinstance(source_summary, dict), "source summary missing")
    for key in METRICS:
        require(
            type(totals.get(key)) is int and totals[key] >= 0,
            "invalid coverage counter: " + key,
        )
        require(
            type(source_summary.get(key)) is int and source_summary[key] == totals[key],
            "source/global counter mismatch: " + key,
        )
    require(
        totals["num_statements"] > 0 and totals["num_branches"] > 0,
        "empty coverage denominator",
    )
    require(
        totals["covered_lines"] <= totals["num_statements"]
        and totals["covered_branches"] <= totals["num_branches"],
        "coverage numerator exceeds denominator",
    )
    return (
        {key: totals[key] for key in METRICS},
        temporal._timestamp(meta.get("timestamp")),
        hashlib.sha256(raw).hexdigest(),
    )


def junit_from(path: Path):
    raw = path.read_bytes()
    require(0 < len(raw) < 2_000_000, "missing/oversized native JUnit")
    ended, integrity, counts = temporal._suite_end(raw)
    require(integrity, "JUnit identity/case counts inconsistent")
    require(counts["executed"] > 0, "zero executed JUnit cases")
    return counts, ended, hashlib.sha256(raw).hexdigest()


def compare(old_cov, new_cov, old_tests, new_tests, *, exact_head):
    require(
        isinstance(exact_head, str) and bool(SHA40.fullmatch(exact_head)),
        "invalid 40-character head",
    )
    old, old_generated, old_hash = old_cov
    new, new_generated, new_hash = new_cov
    old_cases, old_finished, old_junit_hash = old_tests
    new_cases, new_finished, new_junit_hash = new_tests
    require(
        old_generated >= old_finished and new_generated >= new_finished,
        "coverage evidence predates native JUnit completion",
    )
    require(
        old["num_statements"] == new["num_statements"]
        and old["num_branches"] == new["num_branches"],
        "unmatched statement/branch denominators",
    )
    ds = new["covered_lines"] - old["covered_lines"]
    db = new["covered_branches"] - old["covered_branches"]
    dt = new_cases["executed"] - old_cases["executed"]
    require(ds >= 0 and db >= 0, "behavioral coverage regression")
    require(db > 0, "no measured branch-coverage uplift")
    require(dt > 0, "no independently executed new test cases")
    covered_old = old["covered_lines"] + old["covered_branches"]
    covered_new = new["covered_lines"] + new["covered_branches"]
    eligible = new["num_statements"] + new["num_branches"]
    return {
        "schema": "abacus.w29.native-temporal-coverage.v1",
        "exact_head": exact_head,
        "scope": SOURCE,
        "configuration": "coverage.py --branch --source=scripts.cbd_coverage_temporal_gate",
        "before": {"coverage": old, "junit": old_cases},
        "after": {"coverage": new, "junit": new_cases},
        "delta": {
            "covered_statements": ds,
            "covered_branches": db,
            "new_executed_test_cases": dt,
            "combined_covered_before": covered_old,
            "combined_covered_after": covered_new,
            "combined_eligible": eligible,
            "combined_delta_pp": round(100 * (covered_new - covered_old) / eligible, 6),
        },
        "input_sha256": {
            "before_coverage": old_hash,
            "after_coverage": new_hash,
            "before_junit": old_junit_hash,
            "after_junit": new_junit_hash,
        },
        "global_main_coverage_delta": None,
        "pr_changed_line_coverage_delta": None,
        "formal_root_closed": None,
        "merge_admission": "HOLD",
        "security_waiver": False,
        "authority_transfer": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before-cov", type=Path, required=True)
    parser.add_argument("--after-cov", type=Path, required=True)
    parser.add_argument("--before-junit", type=Path, required=True)
    parser.add_argument("--after-junit", type=Path, required=True)
    parser.add_argument("--exact-head", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = compare(
        coverage_from(args.before_cov),
        coverage_from(args.after_cov),
        junit_from(args.before_junit),
        junit_from(args.after_junit),
        exact_head=args.exact_head,
    )
    source_bytes = Path(SOURCE).read_bytes()
    require(bool(source_bytes), "missing exact physical module")
    receipt["source_sha256"] = hashlib.sha256(source_bytes).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"head": args.exact_head, "delta": receipt["delta"], "admission": "HOLD"},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
