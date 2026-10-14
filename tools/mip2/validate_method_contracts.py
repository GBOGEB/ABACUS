#!/usr/bin/env python3
"""MIP2 method qualification schema and corpus structural preflight (stdlib only)."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
LEVELS = tuple(f"M{i}" for i in range(7))
REPOS = ("GBOGEB/ABACUS", "GBOGEB/CODEX", "GBOGEB/cryoplant-project")


def load(name: str) -> dict:
    with (ROOT / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def validate() -> dict:
    reg = load("method_qualification_registry.json")
    corpus = load("method_regression_corpus.json")
    assert reg["schema"] == "mip2.method-qualification.v1"
    assert corpus["schema"] == "mip2.method-regression-corpus.v1"
    assert set(reg["levels"]) == set(LEVELS)
    methods = reg["methods"]
    assert len(methods) >= 11
    ids = [m["method_id"] for m in methods]
    assert len(ids) == len(set(ids))
    for method in methods:
        assert method["maturity"] == "M0_UNVERIFIED"
        assert method["tools"] and method["metrics"] and method["acceptance"]
        assert set(method["propagation"]) == set(REPOS)
        assert all(value == "NOT_QUALIFIED" for value in method["propagation"].values())
    cases = corpus["cases"]
    case_ids = [case["id"] for case in cases]
    assert len(case_ids) == len(set(case_ids))
    assert {case["kind"] for case in cases} == {"positive", "negative"}
    assert {case["family"] for case in cases} <= set(ids)
    assert all(case["expected"] and case["input_class"] for case in cases)
    return {"status": "STRUCTURAL_PASS", "methods": len(methods), "cases": len(cases),
            "qualified_methods": 0, "executed_seeded_tests": 0}


if __name__ == "__main__":
    try:
        print(json.dumps(validate(), sort_keys=True))
    except (AssertionError, OSError, KeyError, ValueError) as exc:
        print(json.dumps({"status": "STRUCTURAL_FAIL", "error": str(exc)}))
        sys.exit(1)
