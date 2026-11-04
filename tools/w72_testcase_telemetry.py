"""Defensive JUnit case census and comparable repeat-testing plan for W72.

Actual JUnit output is the evidence; GitHub Actions success alone does not
establish collection size or native testcase duration. No statistical trial
independence is asserted from a job matrix on one source revision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

SCHEMA = "abacus.w72.junit-case-history.v1"
MAX_JUNIT_BYTES = 32_000_000
MAX_CASES = 100_000
MAX_NAME = 800
STATUS = ("passed", "skipped", "failed", "error")


def _time(element):
    raw = element.attrib.get("time")
    if raw is None:
        return None
    try:
        seconds = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("bad testcase duration") from exc
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError("nonfinite or negative testcase duration")
    return round(seconds, 6)


def parse_junit(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_JUNIT_BYTES:
        raise ValueError("missing or oversized JUnit XML")
    # ElementTree does not resolve external entities by default; refuse DTD
    # and processing instructions to keep the provenance parser simple.
    if re.search(rb"<!\s*(?:DOCTYPE|ENTITY)|<\?(?!xml\s)[^?]*\?>", raw, re.I):
        raise ValueError("JUnit DTD, entity or processing instruction forbidden")
    try:
        tree = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("malformed JUnit XML") from exc
    if tree.tag not in ("testsuite", "testsuites"):
        raise ValueError("unexpected JUnit top-level element")
    suites = [tree] if tree.tag == "testsuite" else list(tree)
    if not suites or any(s.tag != "testsuite" for s in suites):
        raise ValueError("invalid JUnit testsuite set")
    cases = []
    reported_subtests_without_case_nodes = 0
    seen = set()
    counts = Counter({status: 0 for status in STATUS})
    for suite in suites:
        for element in suite.iter("testcase"):
            classname = element.attrib.get("classname", "")
            name = element.attrib.get("name", "")
            if (
                not isinstance(classname, str)
                or not name
                or len(classname) + len(name) > MAX_NAME
            ):
                raise ValueError("invalid testcase identity")
            case_id = classname + "::" + name
            if case_id in seen:
                raise ValueError("duplicate testcase identity without parameterization")
            seen.add(case_id)
            terminal = [
                node.tag
                for node in element
                if node.tag in ("failure", "error", "skipped")
            ]
            if len(terminal) > 1:
                raise ValueError("conflicting testcase conclusions")
            status = (
                {"failure": "failed", "error": "error", "skipped": "skipped"}.get(
                    terminal[0], "passed"
                )
                if terminal
                else "passed"
            )
            counts[status] += 1
            item = {"case_id": case_id, "status": status, "duration_s": _time(element)}
            if status == "skipped":
                skip = next(c for c in element if c.tag == "skipped")
                item["skip_reason_present"] = bool(
                    (skip.attrib.get("message") or skip.text or "").strip()
                )
                # Do not copy environment/private skip text into release receipts.
                item["skip_class"] = "UNCLASSIFIED_REQUIRES_OWNER"
            cases.append(item)
            if len(cases) > MAX_CASES:
                raise ValueError("excessive testcase count")
    if not cases:
        raise ValueError("JUnit collected zero tests")
    # Each suite is bounded by its declared total only if reported; pytest
    # sometimes emits collection counts without a suite nested in testsuites.
    for suite in suites:
        attr = suite.attrib.get("tests")
        if attr is not None:
            try:
                declared = int(attr)
            except ValueError as exc:
                raise ValueError("nonnumeric declared suite count") from exc
            observed = len(list(suite.iter("testcase")))
            if declared != observed:
                # pytest + unittest subTest may count subtest iterations in
                # suite.tests without emitting a separate testcase XML node.
                # Preserve this gap explicitly, never manufacture testcase IDs.
                pytest_subtests = (
                    tree.tag == "testsuites"
                    and tree.attrib.get("name") == "pytest tests"
                    and suite.attrib.get("name") == "pytest"
                    and declared > observed
                    and declared <= MAX_CASES
                )
                if not pytest_subtests:
                    raise ValueError("declared suite test count mismatch")
                reported_subtests_without_case_nodes += declared - observed
    cases.sort(key=lambda c: c["case_id"])
    durations = sorted(c["duration_s"] for c in cases if c["duration_s"] is not None)
    p95 = (
        durations[min(len(durations) - 1, math.ceil(0.95 * len(durations)) - 1)]
        if durations
        else None
    )
    return {
        "schema": SCHEMA,
        "counts": {
            "collected": len(cases),
            "passed": counts["passed"],
            "failed": counts["failed"],
            "errors": counts["error"],
            "skipped": counts["skipped"],
        },
        "duration_observations": len(durations),
        "unmaterialized_pytest_unittest_subtests": reported_subtests_without_case_nodes,
        "reported_total_test_iterations": len(cases)
        + reported_subtests_without_case_nodes,
        "case_identity_census_complete": reported_subtests_without_case_nodes == 0,
        "duration_p50_s": statistics.median(durations) if durations else None,
        "duration_p95_s": p95,
        "case_identity_fingerprint": hashlib.sha256(
            ("\n".join(c["case_id"] for c in cases) + "\n").encode()
        ).hexdigest(),
        "skip_owner_classified": False if counts["skipped"] else None,
        "cases": cases,
        "source_class": "JUNIT_BY_PRODUCER_NOT_AUTHENTICATED_BY_PARSER",
        "root_closure_count": None,
    }


def compare(before: dict, after: dict) -> dict:
    if before.get("schema") != SCHEMA or after.get("schema") != SCHEMA:
        raise ValueError("unknown JUnit schema")

    def keyed(src):
        rows = src.get("cases")
        if not isinstance(rows, list) or len(rows) != src.get("counts", {}).get(
            "collected"
        ):
            raise ValueError("invalid testcase denominator")
        result = {c["case_id"]: c["status"] for c in rows}
        if len(result) != len(rows) or any(v not in STATUS for v in result.values()):
            raise ValueError("duplicate/unknown test identity or status")
        return result

    b, a = keyed(before), keyed(after)
    common = set(a) & set(b)
    recovered = sorted(
        x for x in common if b[x] in ("failed", "error") and a[x] == "passed"
    )
    regressed = sorted(
        x for x in common if b[x] == "passed" and a[x] in ("failed", "error")
    )
    missing = sorted(set(b) - set(a))
    added = sorted(set(a) - set(b))
    return {
        "schema": "abacus.w72.junit-comparison.v1",
        "before_cases": len(b),
        "after_cases": len(a),
        "common_cases": len(common),
        "added_cases": len(added),
        "missing_cases": len(missing),
        "recovered_cases": len(recovered),
        "regressed_cases": len(regressed),
        "recovered_case_ids": recovered,
        "regressed_case_ids": regressed,
        "missing_case_ids": missing,
        "new_case_ids": added,
        "population_scope_matched": not (added or missing),
        "root_closures": None,
        "independent_trials": None,
        "merge_authorized": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--junit", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    o = p.parse_args()
    payload = parse_junit(o.junit.read_bytes())
    o.out.parent.mkdir(parents=True, exist_ok=True)
    o.out.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "collected": payload["counts"]["collected"],
                "skipped": payload["counts"]["skipped"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
