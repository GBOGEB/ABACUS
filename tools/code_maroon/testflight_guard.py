"""Fail-closed CODE_MAROON preflight and source-bound JUnit testflight."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COHORTS = (
    "test_code_maroon_reconcile",
    "test_code_maroon_ooxml",
    "test_code_maroon_testflight",
)


def preflight(root: Path = ROOT) -> dict:
    workflow = (root / ".github/workflows/code-maroon.yml").read_text(encoding="utf-8")
    if "python -m pytest" not in workflow or "--junitxml" not in workflow:
        raise ValueError("missing pytest runner or JUnit evidence")
    if "--noconftest" not in workflow:
        raise ValueError("missing bounded pytest conftest isolation")
    if "testflight_guard.py verify" not in workflow:
        raise ValueError("missing independent post-test verification")
    if re.search(r"python\s+-m\s+unittest\s+tests/test_code_maroon", workflow):
        raise ValueError("pytest functions must not be executed with unittest")
    counts = {}
    for name in COHORTS:
        path = root / "tests" / (name + ".py")
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        count = sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in tree.body
        )
        if count < 1:
            raise ValueError("no pytest tests declared: " + name)
        counts[name] = count
    return {
        "schema": "code-maroon.preflight.v1",
        "declared_test_functions": counts,
        "collection_proved": False,
        "merge_authorized": False,
    }


def verify_junit(path: Path, source_sha: str) -> dict:
    if re.fullmatch(r"[0-9a-f]{40}", source_sha) is None:
        raise ValueError("source SHA must be 40 lowercase hex digits")
    raw = path.read_bytes()
    if (
        not raw
        or len(raw) > 5_000_000
        or b"<!DOCTYPE" in raw.upper()
        or b"<!ENTITY" in raw.upper()
    ):
        raise ValueError("missing, oversized or unsafe JUnit XML")
    root = ET.fromstring(raw)
    if root.tag not in {"testsuites", "testsuite"}:
        raise ValueError("unsupported JUnit root")
    suites = list(root.iter("testsuite"))
    if not suites:
        raise ValueError("missing JUnit suite")
    cases = []
    for suite in suites:
        current = list(suite.findall("testcase"))
        if int(suite.get("tests", "-1")) != len(current) or not current:
            raise ValueError("reported denominator mismatch or zero tests")
        if any(
            int(suite.get(key, "-1")) != 0 for key in ("errors", "failures", "skipped")
        ):
            raise ValueError("failed, skipped or incomplete suite")
        cases.extend(current)
    identifiers = [(case.get("classname", ""), case.get("name", "")) for case in cases]
    if any(not all(ident) for ident in identifiers) or len(set(identifiers)) != len(
        identifiers
    ):
        raise ValueError("duplicate or empty test identity")
    if any(
        case.find(key) is not None
        for case in cases
        for key in ("failure", "error", "skipped")
    ):
        raise ValueError("unreported failure, error or skip")
    counts = {
        name: sum(
            name in (case.get("classname", "") + " " + case.get("file", ""))
            for case in cases
        )
        for name in COHORTS
    }
    if min(counts.values()) < 1:
        raise ValueError("required test cohort absent")
    return {
        "schema": "code-maroon.testflight.v1",
        "source_sha": source_sha,
        "junit_sha256": hashlib.sha256(raw).hexdigest(),
        "tests_executed": len(cases),
        "cohorts": counts,
        "failed": 0,
        "errored": 0,
        "skipped": 0,
        "native_github_identity_verified": False,
        "authority_transfer": False,
        "merge_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("preflight")
    p = sub.add_parser("verify")
    p.add_argument("--junit", type=Path, required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.mode == "preflight":
            receipt = preflight()
        else:
            receipt = verify_junit(args.junit, args.source_sha)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            raw = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("utf-8")
            args.out.write_bytes(raw)
            args.out.with_suffix(".sha256").write_text(
                hashlib.sha256(raw).hexdigest() + "\n", encoding="ascii"
            )
        print(json.dumps(receipt, sort_keys=True))
    except (OSError, ValueError, SyntaxError, ET.ParseError) as exc:
        parser.exit(2, "TESTFLIGHT HOLD: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
