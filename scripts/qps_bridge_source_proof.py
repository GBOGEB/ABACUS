#!/usr/bin/env python3
"""Verify a versioned, source-bound successor to the historical W42 experiment.

The contract is reviewed source, never generated or repinned by this consumer.
Coverage opportunities and JUnit identities are verified as sets, not merely
counts. This module grants scoped test evidence only, never merge admission.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
from pathlib import Path

from defusedxml import ElementTree as ET


class ProofError(ValueError):
    """An input does not satisfy the frozen experiment contract."""


def require(condition: bool, message: str) -> None:
    """Retain the validation predicate when Python runs with optimization."""
    if not condition:
        raise ProofError(message)


def digest(data: bytes) -> str:
    """Return a byte digest without interpreting the source."""
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value: object) -> str:
    """Hash a platform-independent representation of a set or contract."""
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def source_bindings(root: Path, contract: dict) -> dict:
    """Check every declared source/config/test file before accepting reports."""
    require(contract.get("schema") == "qps.bridge.source-contract/2", "contract schema")
    bindings = contract.get("source_files")
    require(isinstance(bindings, dict) and bool(bindings), "empty source binding")
    observed = {}
    for name, expected in bindings.items():
        path = Path(name)
        require(not path.is_absolute() and ".." not in path.parts, "unsafe source path")
        raw = (root / path).read_bytes()
        actual = digest(raw)
        require(actual == expected, f"source pin mismatch: {name}")
        observed[name] = actual
    require(contract.get("target") in observed, "target is not source-bound")
    return observed


def _identities(raw: bytes) -> list[list[str]]:
    """Reject failures, skips, duplicates and empty test populations."""
    tree = ET.fromstring(raw)
    require(tree.tag in {"testsuites", "testsuite"}, "invalid JUnit root")
    suites = list(tree.iter("testsuite"))
    require(bool(suites), "JUnit has no testsuite")
    require(
        tree.tag != "testsuites" or not tree.findall("./testcase"),
        "JUnit case outside suite",
    )
    suite_cases = {id(case) for suite in suites for case in suite.iter("testcase")}
    require(
        len(suite_cases) == len(list(tree.iter("testcase"))), "JUnit case outside suite"
    )
    for tag in ("failure", "error", "skipped"):
        require(tree.find(f".//{tag}") is None, f"JUnit contains {tag}")
    if tree.tag == "testsuites":
        expected = {"tests": str(len(list(tree.iter("testcase"))))}
        expected.update(
            {key: "0" for key in ("failures", "errors", "skipped", "disabled")}
        )
        for key, value in expected.items():
            if key in tree.attrib:
                require(tree.get(key) == value, f"JUnit root counter: {key}")
    for suite in suites:
        for key in ("failures", "errors", "skipped", "disabled"):
            require(suite.get(key, "0") == "0", f"JUnit counter: {key}")
        require(
            suite.get("tests") == str(len(list(suite.iter("testcase")))),
            "JUnit count contradicts cases",
        )
    cases = [[t.get("classname", ""), t.get("name", "")] for t in tree.iter("testcase")]
    require(bool(cases) and all(all(item) for item in cases), "empty test identity")
    require(
        len(cases) == len({tuple(item) for item in cases}), "duplicate test identity"
    )
    return sorted(cases)


def _values(values: object, *, pairs: bool = False) -> set:
    """Validate coverage identities without silently deduplicating input."""
    require(isinstance(values, list), "coverage identities must be lists")
    if pairs:
        require(
            all(
                isinstance(v, list) and len(v) == 2 and all(type(x) is int for x in v)
                for v in values
            ),
            "invalid branch identity",
        )
        result = {tuple(v) for v in values}
    else:
        require(all(type(v) is int and v > 0 for v in values), "invalid line identity")
        result = set(values)
    require(len(result) == len(values), "duplicate coverage identity")
    return result


def _coverage(raw: bytes, contract: dict, epoch: dict) -> tuple[dict, set, set]:
    """Check measured target sets and their summary against the reviewed contract."""
    report = json.loads(raw)
    meta = report.get("meta", {})
    require(
        meta.get("version") == contract["coverage_version"], "coverage version mismatch"
    )
    require(meta.get("branch_coverage") is True, "branch instrumentation absent")
    target = contract["target"]
    matches = [v for k, v in report["files"].items() if k.replace("\\", "/") == target]
    aliases = [
        k for k in report["files"] if k.replace("\\", "/").endswith("/" + target)
    ]
    require(
        len(matches) == 1 and not aliases, "module coverage ambiguous or not relative"
    )
    module = matches[0]
    lines = _values(module["executed_lines"])
    missing = _values(module["missing_lines"])
    branches = _values(module["executed_branches"], pairs=True)
    missing_branches = _values(module["missing_branches"], pairs=True)
    require(
        not lines & missing and not branches & missing_branches,
        "overlapping coverage states",
    )
    population = contract["population"]
    require(
        lines | missing == _values(population["lines"]), "statement population changed"
    )
    require(
        branches | missing_branches == _values(population["branches"], pairs=True),
        "branch population changed",
    )
    require(module["excluded_lines"] == population["excluded_lines"], "exclusion drift")
    require(sorted(lines) == epoch["executed_lines"], "covered statement set changed")
    require(
        sorted([list(v) for v in branches]) == epoch["executed_branches"],
        "covered branch set changed",
    )
    expected_summary = {
        "covered_lines": len(lines),
        "num_statements": len(lines | missing),
        "missing_lines": len(missing),
        "covered_branches": len(branches),
        "num_branches": len(branches | missing_branches),
        "missing_branches": len(missing_branches),
        "excluded_lines": len(module["excluded_lines"]),
    }
    require(
        all(
            type(module["summary"].get(k)) is int and module["summary"][k] == v
            for k, v in expected_summary.items()
        ),
        "coverage summary contradicts identities",
    )
    return expected_summary, lines, branches


def qualify(root: Path, artifacts: Path, contract: dict) -> dict:
    """Accept all epochs or fail; never rewrite the experiment contract."""
    bindings = source_bindings(root, contract)
    previous_cases, previous_lines, previous_branches = set(), set(), set()
    states, receipts = [], {}
    epochs = contract.get("epochs", [])
    require(len(epochs) >= 2, "matched experiment needs multiple epochs")
    require(len({e["name"] for e in epochs}) == len(epochs), "duplicate epoch")
    for epoch in epochs:
        name = epoch["name"]
        require(
            all(path in bindings for path in epoch["test_files"]), "unbound test input"
        )
        require(bool(re.fullmatch(r"[a-z][a-z0-9]*", name)), "unsafe epoch name")
        junit = artifacts / f"{name}-junit.xml"
        coverage = artifacts / f"{name}-coverage.json"
        # Bind parsing and receipt hashing to the same captured report bytes.
        # Reopening paths after parsing permits a replace-and-restore race.
        junit_raw, coverage_raw = junit.read_bytes(), coverage.read_bytes()
        identities = _identities(junit_raw)
        require(identities == epoch["test_cases"], f"test population changed: {name}")
        cases = {tuple(v) for v in identities}
        require(
            previous_cases < cases, "test epochs are not strict cumulative supersets"
        )
        summary, lines, branches = _coverage(coverage_raw, contract, epoch)
        require(
            previous_lines <= lines and previous_branches <= branches,
            "coverage regressed across epochs",
        )
        receipts[junit.name] = digest(junit_raw)
        receipts[coverage.name] = digest(coverage_raw)
        states.append(
            {
                "name": name,
                "cases": len(cases),
                **summary,
                "combined_covered": len(lines) + len(branches),
                "combined_eligible": summary["num_statements"]
                + summary["num_branches"],
                "test_identity_sha256": canonical_digest(identities),
            }
        )
        previous_cases, previous_lines, previous_branches = cases, lines, branches
    require(
        states[-1]["missing_lines"] == 0 and states[-1]["missing_branches"] == 0,
        "final frontier remains open",
    )
    return {
        "schema": "qps.bridge.source-proof/2",
        "experiment_id": contract["experiment_id"],
        "contract_sha256": canonical_digest(contract),
        "source_files": bindings,
        "historical_baseline": contract["historical_baseline"],
        "epochs": states,
        "artifact_sha256": receipts,
        "module_coverage_accepted": True,
        "global_main_coverage": None,
        "pr_changed_line_coverage": None,
        "governed_merge_admission": None,
        "security_waiver": False,
        "authority_transfer": False,
        "merge_admission": "HOLD",
    }


def execution_context(root: Path, native: bool) -> dict:
    """Distinguish a local experiment from actual GitHub exact-head execution."""
    runtime = {"python": platform.python_version(), "platform": platform.platform()}
    if not native:
        return {
            "evidence_kind": "LOCAL_SOURCE_SNAPSHOT",
            "runtime": runtime,
            "head_sha": None,
            "run_id": None,
            "attempt": None,
            "job_id": None,
        }
    require(
        os.environ.get("GITHUB_ACTIONS") == "true",
        "native execution environment missing",
    )
    require(
        os.environ.get("GITHUB_REPOSITORY") == "GBOGEB/ABACUS",
        "wrong native repository",
    )
    head = os.environ.get("EXACT_HEAD", "")
    require(bool(re.fullmatch(r"[0-9a-f]{40}", head)), "invalid native head")
    # The immutable workflow obtains this value with git rev-parse immediately
    # before invoking us; provider readback still has to bind the run and job.
    actual = os.environ.get("CHECKED_OUT_HEAD", "")
    require(actual == head, "native checkout differs from exact head")
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    require(
        bool(event_path) and Path(event_path).is_file(), "native event source missing"
    )
    try:
        event = json.loads(Path(event_path).read_bytes())
    except (ValueError, OSError) as exc:
        raise ProofError("native event cannot be read") from exc
    require(isinstance(event, dict), "native event schema invalid")
    event_pr = event.get("pull_request", {})
    require(isinstance(event_pr, dict), "native event PR schema invalid")
    event_branch = event_pr.get("head", {})
    require(isinstance(event_branch, dict), "native event head schema invalid")
    event_head = event_branch.get("sha")
    event_head = event_head or os.environ.get("GITHUB_SHA")
    require(event_head == head, "native trigger differs from exact head")
    run, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get(
        "GITHUB_RUN_ATTEMPT", ""
    )
    require(
        run.isdigit() and attempt.isdigit() and int(run) > 0 and int(attempt) > 0,
        "native run identity missing",
    )
    return {
        "evidence_kind": "GITHUB_ACTIONS_REPORTED_HEAD",
        "native_execution_accepted": None,
        "provider_verification": "PENDING_EXTERNAL_READBACK",
        "runtime": runtime,
        "head_sha": head,
        "run_id": int(run),
        "attempt": int(attempt),
        "job_id": None,
        "cell": os.environ.get("CELL"),
        "job_id_binding": "PROVIDER_READBACK_REQUIRED",
    }


def main() -> None:
    """Validate bound inputs and optionally write a final receipt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--native", action="store_true")
    args = parser.parse_args()
    contract = json.loads(args.contract.read_bytes())
    source_bindings(args.root, contract)
    context = execution_context(args.root, args.native)
    if args.artifacts is None:
        print("SOURCE_BOUND_PREFLIGHT_PASS")
        return
    receipt = {**qualify(args.root, args.artifacts, contract), **context}
    (args.artifacts / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
