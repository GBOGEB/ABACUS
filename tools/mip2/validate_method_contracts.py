#!/usr/bin/env python3
"""MIP2 canonical registry/corpus structural preflight; never attest scanner effectiveness."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
LEVELS = tuple(f"M{i}" for i in range(7))
REPOS = ("GBOGEB/ABACUS", "GBOGEB/CODEX", "GBOGEB/cryoplant-project")


def require(condition, reason: str) -> None:
    # Never use assert for a security/evidence check: python -O disables it.
    if not condition:
        raise ValueError(reason)


def load(name: str) -> dict:
    with (ROOT / name).open(encoding="utf-8") as handle:
        data = json.load(handle)
    require(isinstance(data, dict), name + ":INVALID_TOP_LEVEL")
    return data


def validate() -> dict:
    reg = load("method_qualification_registry.json")
    corpus = load("method_regression_corpus.json")
    require(reg.get("schema") == "mip2.method-qualification.v1", "REGISTRY_SCHEMA_MISMATCH")
    require(corpus.get("schema") == "mip2.method-regression-corpus.v1", "CORPUS_SCHEMA_MISMATCH")
    require(isinstance(reg.get("levels"), dict) and set(reg["levels"]) == set(LEVELS),
            "REGISTRY_MATURITY_LEVELS_INVALID")
    methods = reg.get("methods")
    require(isinstance(methods, list) and len(methods) >= 11, "REGISTRY_METHOD_COUNT_INVALID")
    ids = []
    for index, method in enumerate(methods):
        require(isinstance(method, dict), f"METHOD_{index}_NOT_OBJECT")
        method_id = method.get("method_id")
        require(isinstance(method_id, str) and bool(method_id), f"METHOD_{index}_ID_INVALID")
        ids.append(method_id)
        require(method.get("maturity") == "M0_UNVERIFIED", f"METHOD_{method_id}_SELF_ATTESTED")
        require(isinstance(method.get("tools"), list) and bool(method["tools"]) and
                isinstance(method.get("metrics"), str) and bool(method["metrics"]) and
                isinstance(method.get("acceptance"), str) and bool(method["acceptance"]),
                f"METHOD_{method_id}_CONTRACT_INCOMPLETE")
        propagation = method.get("propagation")
        require(isinstance(propagation, dict) and set(propagation) == set(REPOS),
                f"METHOD_{method_id}_FEDERATION_SCOPE_INVALID")
        require(all(value == "NOT_QUALIFIED" for value in propagation.values()),
                f"METHOD_{method_id}_FEDERATION_FALSE_GREEN")
    require(len(ids) == len(set(ids)), "REGISTRY_DUPLICATE_METHOD_ID")
    cases = corpus.get("cases")
    require(isinstance(cases, list) and bool(cases), "CORPUS_EMPTY_OR_INVALID")
    case_ids = []
    kinds = set()
    for index, case in enumerate(cases):
        require(isinstance(case, dict), f"CASE_{index}_NOT_OBJECT")
        case_id = case.get("id")
        require(isinstance(case_id, str) and bool(case_id), f"CASE_{index}_ID_INVALID")
        case_ids.append(case_id)
        kinds.add(case.get("kind"))
        require(case.get("family") in ids, f"CASE_{case_id}_UNKNOWN_FAMILY")
        require(isinstance(case.get("expected"), str) and bool(case["expected"]) and
                isinstance(case.get("input_class"), str) and bool(case["input_class"]),
                f"CASE_{case_id}_CONTRACT_INCOMPLETE")
    require(len(case_ids) == len(set(case_ids)), "CORPUS_DUPLICATE_CASE_ID")
    require(kinds == {"positive", "negative"}, "CORPUS_CONTROLS_INCOMPLETE")
    return {"status": "STRUCTURAL_PASS", "methods": len(methods), "cases": len(cases),
            "qualified_methods": 0, "executed_seeded_tests": 0}


if __name__ == "__main__":
    try:
        print(json.dumps(validate(), sort_keys=True))
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"status": "STRUCTURAL_FAIL", "error": str(exc)}))
        sys.exit(1)
