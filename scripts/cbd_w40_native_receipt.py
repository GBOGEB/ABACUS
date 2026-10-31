#!/usr/bin/env python3
"""Validate and emit exact-head W40 binary-parser native coverage receipts.

This is moved verbatim in contract from the inline workflow implementation.
An assertion failure must keep the calling GitHub Actions step red.
"""

import hashlib
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

SOURCE_SUFFIX = "tools/qps_binary_bridge.py"


def source_summary(report_path):
    report = json.loads(report_path.read_text())
    keys = [
        key for key in report["files"] if key.replace("\\", "/").endswith(SOURCE_SUFFIX)
    ]
    assert len(keys) == 1, "missing/ambiguous source-bound measured module"
    return keys[0], report["files"][keys[0]]["summary"]


def clean_cases(junit_path):
    tests = list(ET.parse(junit_path).iter("testcase"))
    assert all(
        not list(test.iter("failure"))
        and not list(test.iter("error"))
        and not list(test.iter("skipped"))
        for test in tests
    ), "native test failure or skip"
    return tests


def main():
    out = Path("artifacts/w40")
    source_key, after = source_summary(out / "coverage.json")
    _, before = source_summary(out / "baseline-coverage.json")
    assert (
        after["num_statements"],
        after["num_branches"],
    ) == (
        before["num_statements"],
        before["num_branches"],
    ), "changed eligible module denominator"
    assert (
        after["covered_lines"] >= before["covered_lines"]
        and after["covered_branches"] >= before["covered_branches"]
    ), "coverage regression on same source/config"

    baseline_tests = clean_cases(out / "baseline-junit.xml")
    assert baseline_tests, "baseline suite must be green"
    tests = clean_cases(out / "junit.xml")
    w40 = [
        test
        for test in tests
        if "test_qps_binary_bridge_w40_penetration"
        in (test.attrib.get("classname", "") + test.attrib.get("name", ""))
    ]
    w41 = [
        test
        for test in tests
        if "test_qps_binary_bridge_w41_frontier"
        in (test.attrib.get("classname", "") + test.attrib.get("name", ""))
    ]
    assert len(w40) == 42, ("W40 denominator mismatch", len(w40))
    assert len(w41) == 12, ("W41 denominator mismatch", len(w41))
    assert (
        len(tests) == len(baseline_tests) + 54
    ), "unmatched test populations or culled tests"

    source_sha = os.environ["EXACT_HEAD"]
    assert len(source_sha) == 40 and all(
        char in "0123456789abcdef" for char in source_sha
    )
    receipt = {
        "schema": "codepurple.w40.native-case-coverage/1.0",
        "source_sha": source_sha,
        "run_id": int(os.environ["RUN_ID"]),
        "attempt": int(os.environ["RUN_ATTEMPT"]),
        "cell": os.environ["GITHUB_JOB_NAME"],
        "job_id": None,
        "total_junit_cases": len(tests),
        "new_w40_cases": len(w40),
        "new_w41_cases": len(w41),
        "new_case_total": len(w40) + len(w41),
        "new_w40_failed": 0,
        "new_w40_skipped": 0,
        "statement_covered": after["covered_lines"],
        "statement_eligible": after["num_statements"],
        "branch_covered": after["covered_branches"],
        "branch_eligible": after["num_branches"],
        "baseline_junit_cases": len(baseline_tests),
        "baseline_statement_covered": before["covered_lines"],
        "baseline_branch_covered": before["covered_branches"],
        "delta_statement_covered": (after["covered_lines"] - before["covered_lines"]),
        "delta_branch_covered": (
            after["covered_branches"] - before["covered_branches"]
        ),
        "matched_eligible_opportunities": (
            after["num_statements"] + after["num_branches"]
        ),
        "matched_before_covered": (
            before["covered_lines"] + before["covered_branches"]
        ),
        "matched_after_covered": (after["covered_lines"] + after["covered_branches"]),
        "coverage_scope": "tools/qps_binary_bridge.py only",
        "source_file_key": source_key,
        "formal_main_uplift": None,
        "pr_diff_coverage": None,
        "admission": "HOLD",
        "authenticated_crew": None,
        "accepted_rex": None,
        "authority_transfer": False,
        "security_waiver": False,
    }
    (out / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    (out / "SHA256.json").write_text(
        json.dumps(
            {
                file.name: hashlib.sha256(file.read_bytes()).hexdigest()
                for file in sorted(out.iterdir())
                if file.name != "SHA256.json"
            },
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
