"""Fail closed on stale or unbound native test/coverage evidence.

An engineering measurement receipt, never a merge or security gate.
Coverage must have been generated after the referenced JUnit suite completed.
"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree

SCHEMA = "cbd.coverage-temporal-receipt.v1"
TARGETS = (
    "DMAIC_V3/quick_error_fix.py",
    "DMAIC_V3/quick_error_lister.py",
)


def _timestamp(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    # GitHub coverage.py emits a naive UTC timestamp. Scope this assumption
    # explicitly to this native runner contract, not local time elsewhere.
    return (
        parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    ).astimezone(timezone.utc)


def _suite_end(junit_xml):
    root = ElementTree.fromstring(junit_xml)
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    if not suites:
        raise ValueError("JUnit testsuite missing")
    ends = []
    for suite in suites:
        start = _timestamp(suite.get("timestamp"))
        try:
            elapsed = float(suite.get("time", "nan"))
        except ValueError as exc:
            raise ValueError("invalid suite duration") from exc
        if not (0 <= elapsed < 86400):
            raise ValueError("invalid suite duration")
        ends.append(start + timedelta(seconds=elapsed))
    return max(ends)


def measure(coverage, junit_xml, coverage_binding, test_binding, *, expected_sha):
    """Return a non-authoritative receipt; invalid evidence is never green."""
    if not isinstance(expected_sha, str) or len(expected_sha) != 40 or any(
        c not in "0123456789abcdef" for c in expected_sha
    ):
        raise ValueError("invalid exact source head")
    if not all(
        isinstance(v, dict) for v in (coverage, coverage_binding, test_binding)
    ):
        raise ValueError("invalid evidence payload")
    if (
        coverage_binding.get("exact_sha") != expected_sha
        or test_binding.get("exact_sha") != expected_sha
    ):
        raise ValueError("coverage/test evidence is not bound to exact head")
    if coverage.get("meta", {}).get("branch_coverage") is not True:
        raise ValueError("branch coverage instrumentation missing")
    collected_at = _timestamp(coverage.get("meta", {}).get("timestamp"))
    suite_end = _suite_end(junit_xml)
    files = coverage.get("files")
    if not isinstance(files, dict):
        raise ValueError("coverage file inventory unavailable")
    rows = []
    for path in TARGETS:
        file_data = files.get(path)
        if not isinstance(file_data, dict):
            raise ValueError("target coverage file missing: " + path)
        s = file_data.get("summary")
        if not isinstance(s, dict):
            raise ValueError("target coverage summary missing: " + path)
        fields = (
            "covered_lines",
            "num_statements",
            "covered_branches",
            "num_branches",
        )
        if not all(type(s.get(k)) is int for k in fields):
            raise ValueError("non-integer coverage denominator")
        lines, line_total = s["covered_lines"], s["num_statements"]
        branches, branch_total = s["covered_branches"], s["num_branches"]
        if not (
            0 <= lines <= line_total
            and 0 <= branches <= branch_total
            and line_total > 0
            and branch_total > 0
        ):
            raise ValueError("invalid coverage numerator/denominator")
        rows.append(
            {
                "path": path,
                "statements": line_total,
                "covered_statements": lines,
                "branches": branch_total,
                "covered_branches": branches,
            }
        )
    stale = collected_at < suite_end
    return {
        "schema": SCHEMA,
        "exact_sha": expected_sha,
        "coverage_generated_at": collected_at.isoformat(),
        "junit_suite_completed_at": suite_end.isoformat(),
        "time_gap_seconds": round((collected_at - suite_end).total_seconds(), 3),
        "targets": rows,
        "covered_target_statements": sum(x["covered_statements"] for x in rows),
        "eligible_target_statements": sum(x["statements"] for x in rows),
        "covered_target_branches": sum(x["covered_branches"] for x in rows),
        "eligible_target_branches": sum(x["branches"] for x in rows),
        "coverage_provenance": (
            "STALE_BEFORE_TEST_COMPLETION" if stale else "TEMPORALLY_VALID"
        ),
        "accepted_coverage_uplift": None,
        "root_closure_credit": None,
        "merge_admission": "HOLD",
        "status": "HOLD" if stale else "ELIGIBLE_FOR_MATCHED_COVERAGE_REVIEW",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--coverage-binding", type=Path, required=True)
    parser.add_argument("--test-binding", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = measure(
        json.loads(args.coverage.read_text(encoding="utf-8")),
        args.junit.read_text(encoding="utf-8"),
        json.loads(args.coverage_binding.read_text(encoding="utf-8")),
        json.loads(args.test_binding.read_text(encoding="utf-8")),
        expected_sha=args.head,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(
        {"status": receipt["status"], "time_gap_seconds": receipt["time_gap_seconds"]}
    ))
    return 0 if receipt["status"] != "HOLD" else 2


if __name__ == "__main__":
    raise SystemExit(main())
