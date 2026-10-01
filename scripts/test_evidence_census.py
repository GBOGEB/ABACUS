#!/usr/bin/env python3
"""Build a governed test outcome/skip census from pytest JUnit XML."""

from __future__ import annotations

import argparse
import json
import os
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.pytest_test_state_plugin import BLOCKING_STATES, TEST_STATES


def _properties(case: ET.Element) -> dict[str, str]:
    props: dict[str, str] = {}
    parent = case.find("properties")
    if parent is None:
        return props
    for prop in parent.findall("property"):
        name = prop.attrib.get("name")
        if name:
            props[name] = prop.attrib.get("value", "")
    return props


def _skip_state(case: ET.Element) -> str | None:
    skipped = case.find("skipped")
    if skipped is None:
        return None
    text = " ".join(
        value
        for value in (
            skipped.attrib.get("message", ""),
            skipped.text or "",
        )
        if value
    )
    for state in BLOCKING_STATES:
        if state in text:
            return state
    return None


def _outcome(case: ET.Element) -> str:
    if case.find("error") is not None:
        return "error"
    if case.find("failure") is not None:
        return "fail"
    if case.find("skipped") is not None:
        return "skip"
    return "pass"


def build_census(junit_xml: Path) -> dict[str, Any]:
    root = ET.parse(junit_xml).getroot()
    rows: list[dict[str, Any]] = []
    outcomes: Counter[str] = Counter()
    states: Counter[str] = Counter()
    uncategorized_skips: list[str] = []
    xfail_count = 0

    for case in root.iter("testcase"):
        props = _properties(case)
        outcome = _outcome(case)
        node = "::".join(
            part
            for part in (
                case.attrib.get("classname", ""),
                case.attrib.get("name", ""),
            )
            if part
        )
        state = props.get("test_state")
        is_xfail = props.get("xfail") == "true"

        if is_xfail:
            xfail_count += 1
            state = "TEST_FAILING"
        elif outcome == "skip":
            state = state if state in BLOCKING_STATES else _skip_state(case)
            if state not in BLOCKING_STATES:
                uncategorized_skips.append(node)
                state = state or "UNCLASSIFIED_SKIP"
        elif outcome in {"fail", "error"}:
            state = "TEST_FAILING"
        elif outcome == "pass":
            state = "TEST_GREEN"

        outcomes[outcome] += 1
        states[state] += 1
        rows.append(
            {
                "test": node,
                "outcome": outcome,
                "test_state": state,
                "test_state_source": props.get("test_state_source", "derived"),
                "xfail": is_xfail,
            }
        )

    return {
        "schema": "abacus-test-evidence-census/1.0.0",
        "exact_sha": os.environ.get("GITHUB_SHA", "WITHHELD"),
        "outcomes": dict(sorted(outcomes.items())),
        "states": dict(sorted(states.items())),
        "skip_count": outcomes["skip"],
        "xfail_count": xfail_count,
        "uncategorized_skips": sorted(uncategorized_skips),
        "rows": rows,
        "state_vocabulary": list(TEST_STATES),
        "authority_transfer": False,
        "formal_credit_delta": 0,
        "engineering_credit_delta": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-skips", type=int, default=None)
    parser.add_argument("--max-xfails", type=int, default=None)
    args = parser.parse_args(argv)

    census = build_census(args.junit)
    errors: list[str] = []
    if census["uncategorized_skips"]:
        errors.append(
            f"uncategorized skips: {len(census['uncategorized_skips'])}"
        )
    if args.max_skips is not None and census["skip_count"] > args.max_skips:
        errors.append(
            f"skip ratchet exceeded: {census['skip_count']} > {args.max_skips}"
        )
    if args.max_xfails is not None and census["xfail_count"] > args.max_xfails:
        errors.append(
            f"xfail ratchet exceeded: {census['xfail_count']} > {args.max_xfails}"
        )

    census["ratchet_status"] = "PASS" if not errors else "FAIL"
    census["ratchet_errors"] = errors
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(census, indent=2, sort_keys=True) + "\n")
    print(json.dumps(census, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
