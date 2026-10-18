"""Fail-closed W26 TestPilot same-SHA baseline vs expanded native coverage.

Not repository-wide, not merge authority. JUnit/JSON inputs must be native job
artifacts from one source SHA and coverage configuration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from defusedxml import ElementTree

SHA = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_FILE = "scripts/testpilot_preflight.py"


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(detail)


def load_coverage(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    require(0 < len(raw) < 2_000_000, "missing or oversized coverage input")
    doc = json.loads(raw)
    require(isinstance(doc, dict), "invalid coverage document")
    meta, files, totals = doc.get("meta", {}), doc.get("files", {}), doc.get("totals", {})
    require(isinstance(meta, dict) and meta.get("branch_coverage") is True,
            "branch instrumentation required")
    require(isinstance(files, dict) and set(files) == {EXPECTED_FILE},
            "only exact TestPilot source coverage allowed")
    keys = ("num_statements", "covered_lines", "num_branches", "covered_branches")
    for field in keys:
        require(type(totals.get(field)) is int and totals[field] >= 0,
                "missing nonnegative coverage integer: " + field)
    require(totals["num_statements"] > 0 and totals["num_branches"] > 0,
            "empty statement/branch denominator")
    require(totals["covered_lines"] <= totals["num_statements"]
            and totals["covered_branches"] <= totals["num_branches"],
            "invalid covered population")
    source = files[EXPECTED_FILE]
    summary = source.get("summary") if isinstance(source, dict) else None
    require(isinstance(summary, dict), "source coverage summary missing")
    require(all(type(summary.get(k)) is int and summary[k] == totals[k]
                for k in keys), "coverage source/global totals mismatch")
    return {k: totals[k] for k in keys}, hashlib.sha256(raw).hexdigest()


def load_junit(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    require(0 < len(raw) < 2_000_000, "missing or oversized JUnit input")
    root = ElementTree.fromstring(raw)
    suites = [root] if root.tag == "testsuite" else list(root) if root.tag == "testsuites" else []
    require(bool(suites) and all(s.tag == "testsuite" for s in suites), "JUnit root invalid")
    count = {key: 0 for key in ("tests", "failures", "errors", "skipped")}
    seen = set()
    for suite in suites:
        declared = {}
        for key in count:
            v = suite.get(key)
            require(isinstance(v, str) and v.isdecimal(), "invalid JUnit " + key)
            declared[key] = int(v)
        cases = suite.findall("testcase")
        require(declared["tests"] == len(cases),
                "JUnit declared tests differ from testcase count")
        observed = {key: 0 for key in ("failures", "errors", "skipped")}
        for case in cases:
            name, classname = case.get("name"), case.get("classname")
            require(bool(name and name.strip() and classname and classname.strip()),
                    "JUnit testcase identity missing")
            identity = (classname, name)
            require(identity not in seen, "duplicate JUnit testcase identity")
            seen.add(identity)
            outcome_count = 0
            for key, tag in (("failures", "failure"), ("errors", "error"),
                             ("skipped", "skipped")):
                if case.find(tag) is not None:
                    observed[key] += 1
                    outcome_count += 1
            require(outcome_count <= 1, "conflicting JUnit testcase outcomes")
        for key in observed:
            require(observed[key] == declared[key],
                    "JUnit declared " + key + " differs from testcase outcomes")
        for key in count:
            count[key] += declared[key]
    require(count["tests"] > 0, "zero tests may not pass")
    require(count["failures"] == count["errors"] == 0,
            "failing JUnit may not provide coverage uplift credit")
    return count, hashlib.sha256(raw).hexdigest()


def compare(base_cov: dict, expanded_cov: dict, base_junit: dict,
            expanded_junit: dict, source_sha: str) -> dict:
    require(isinstance(source_sha, str) and bool(SHA.fullmatch(source_sha)),
            "unverified exact-source SHA")
    require(base_cov["num_statements"] == expanded_cov["num_statements"]
            and base_cov["num_branches"] == expanded_cov["num_branches"],
            "mismatched coverage denominators")
    require(expanded_cov["covered_lines"] >= base_cov["covered_lines"]
            and expanded_cov["covered_branches"] >= base_cov["covered_branches"],
            "coverage regression under same-head test expansion")
    old_executed = base_junit["tests"] - base_junit["skipped"]
    new_executed = expanded_junit["tests"] - expanded_junit["skipped"]
    require(new_executed > old_executed,
            "no independently executed new test cases")
    statements = expanded_cov["covered_lines"] - base_cov["covered_lines"]
    branches = expanded_cov["covered_branches"] - base_cov["covered_branches"]
    require(statements > 0 and branches > 0, "no verified statement and branch uplift")
    denominator = expanded_cov["num_statements"] + expanded_cov["num_branches"]
    old = base_cov["covered_lines"] + base_cov["covered_branches"]
    new = expanded_cov["covered_lines"] + expanded_cov["covered_branches"]
    return {
        "schema": "abacus.w26.testpilot.matched-native-coverage.v1",
        "source_sha": source_sha,
        "scope": EXPECTED_FILE,
        "configuration": "coverage.py --branch --source=scripts.testpilot_preflight",
        "baseline": {"coverage": base_cov, "junit": base_junit},
        "expanded": {"coverage": expanded_cov, "junit": expanded_junit},
        "uplift": {"covered_statements": statements, "covered_branches": branches,
                   "additional_executed_tests": new_executed - old_executed,
                   "combined_covered_before": old, "combined_covered_after": new,
                   "combined_denominator": denominator,
                   "combined_pp": round(100 * (new - old) / denominator, 6)},
        "global_main_coverage_uplift": None,
        "matched_diff_coverage_uplift": None,
        "verified_engineering_root_closure": None,
        "governed_merge_admission": "HOLD",
        "mutation_worker_launch": None,
        "security_waiver": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-cov", type=Path, required=True)
    ap.add_argument("--expanded-cov", type=Path, required=True)
    ap.add_argument("--base-junit", type=Path, required=True)
    ap.add_argument("--expanded-junit", type=Path, required=True)
    ap.add_argument("--exact-head", required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    old_c, old_hash = load_coverage(a.base_cov)
    new_c, new_hash = load_coverage(a.expanded_cov)
    old_t, old_t_hash = load_junit(a.base_junit)
    new_t, new_t_hash = load_junit(a.expanded_junit)
    report = compare(old_c, new_c, old_t, new_t, a.exact_head)
    report["input_sha256"] = {"baseline_coverage": old_hash, "expanded_coverage": new_hash,
                              "baseline_junit": old_t_hash, "expanded_junit": new_t_hash}
    a.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"source_sha": a.exact_head, "uplift": report["uplift"],
                      "admission": "HOLD"}, sort_keys=True))


if __name__ == "__main__":
    main()
