"""Fail-closed canonical method contract tests, including optimized execution."""

import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "mip2_contracts", ROOT / "validate_method_contracts.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def originals():
    reg = json.loads(
        (ROOT / "method_qualification_registry.json").read_text(encoding="utf-8")
    )
    corpus = json.loads(
        (ROOT / "method_regression_corpus.json").read_text(encoding="utf-8")
    )
    return reg, corpus


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("bad_schema", "REGISTRY_SCHEMA_MISMATCH"),
        ("duplicate_id", "REGISTRY_DUPLICATE_METHOD_ID"),
        ("false_maturity", "SELF_ATTESTED"),
        ("false_federation", "FEDERATION_FALSE_GREEN"),
        ("bad_level", "REGISTRY_MATURITY_LEVELS_INVALID"),
        ("bad_case", "UNKNOWN_FAMILY"),
        ("duplicate_case", "CORPUS_DUPLICATE_CASE_ID"),
        ("missing_negative", "CORPUS_CONTROLS_INCOMPLETE"),
    ],
)
def test_contract_mutation_rejected(monkeypatch, mutation, error):
    reg, corpus = originals()
    if mutation == "bad_schema":
        reg["schema"] = "forged"
    elif mutation == "duplicate_id":
        reg["methods"][1]["method_id"] = reg["methods"][0]["method_id"]
    elif mutation == "false_maturity":
        reg["methods"][0]["maturity"] = "M6"
    elif mutation == "false_federation":
        reg["methods"][0]["propagation"]["GBOGEB/CODEX"] = "QUALIFIED"
    elif mutation == "bad_level":
        reg["levels"].pop("M6")
    elif mutation == "bad_case":
        corpus["cases"][0]["family"] = "foreign"
    elif mutation == "duplicate_case":
        corpus["cases"][1]["id"] = corpus["cases"][0]["id"]
    elif mutation == "missing_negative":
        corpus["cases"] = [
            case for case in corpus["cases"] if case["kind"] == "positive"
        ]
    monkeypatch.setattr(
        mod,
        "load",
        lambda name: reg if name.startswith("method_qualification") else corpus,
    )
    with pytest.raises(ValueError, match=error):
        mod.validate()


def test_unoptimized_and_optimized_reject_invalid_contract():
    # subprocess isolation verifies that the explicit validation survives python -O.
    snippet = (
        "import sys;sys.path.insert(0, 'tools/mip2');"
        "from validate_method_contracts import require;"
        "require(False,'EXPECTED_REJECTION')"
    )
    for options in ([], ["-O"]):
        p = subprocess.run(
            [sys.executable, *options, "-c", snippet],
            cwd=ROOT.parents[1],
            capture_output=True,
            text=True,
        )
        assert p.returncode != 0
        assert "EXPECTED_REJECTION" in p.stderr


def test_structural_pass_does_not_claim_execution_or_admission():
    actual = mod.validate()
    assert actual["status"] == "STRUCTURAL_PASS"
    assert actual["qualified_methods"] == 0
    assert actual["executed_seeded_tests"] == 0
