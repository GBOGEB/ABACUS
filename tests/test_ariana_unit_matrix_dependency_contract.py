"""Exact-manifest regression for the 3x3 Ariana secure-JUnit test dependency."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MINIMAL = ROOT / "requirements-test.txt"
PRODUCT_SHIM = ROOT / "requirements.txt"
WORKFLOW = ROOT / ".github/workflows/ci-cd-tests.yml"


def _secure_constraint(text: str, expected: str = "defusedxml>=0.7.1,<0.8.0") -> str:
    declared = [
        line.split("#", 1)[0].strip()
        for line in text.splitlines()
        if line.split("#", 1)[0].strip().startswith("defusedxml")
    ]
    if len(declared) != 1:
        raise ValueError("exactly one secure JUnit parser constraint required")
    if declared[0] != expected:
        raise ValueError("unmatched secure JUnit parser constraint")
    return declared[0]


def _unit_matrix_workflow() -> str:
    source = WORKFLOW.read_text(encoding="utf-8")
    section = re.search(
        r"(?ms)^  unit-tests:\n(.*?)(?=^  [a-z][a-z0-9-]*:\n|\Z)",
        source,
    )
    if section is None:
        raise ValueError("missing canonical unit-tests workflow job")
    return section.group(1)


def test_nine_cell_ci_uses_shared_minimal_dependency_manifest() -> None:
    unit = _unit_matrix_workflow()
    assert "os: [ubuntu-latest, windows-latest, macos-latest]" in unit
    assert "python-version: ['3.10', '3.11', '3.12']" in unit
    assert "pip install -r requirements-test.txt" in unit
    assert "pip install -r requirements-dev.txt" not in unit


def test_minimal_and_root_secure_parser_constraints_are_consistent() -> None:
    minimal = MINIMAL.read_text(encoding="utf-8")
    root = PRODUCT_SHIM.read_text(encoding="utf-8")
    # Root production shim and isolated CI install share the secure floor;
    # deliberate upper bounds differ: <1.0 for root, <0.8.0 for test-only.
    isolated = _secure_constraint(minimal)
    runtime = _secure_constraint(root, expected="defusedxml>=0.7.1,<1.0")
    assert isolated == "defusedxml>=0.7.1,<0.8.0"
    assert runtime == "defusedxml>=0.7.1,<1.0"
    assert isolated.split(",", 1)[0] == runtime.split(",", 1)[0]
    assert "-r DMAIC_V3/requirements.txt" in root


def test_missing_or_downgraded_runtime_parser_fails_closed() -> None:
    source = PRODUCT_SHIM.read_text(encoding="utf-8")
    constraint = _secure_constraint(source, expected="defusedxml>=0.7.1,<1.0")
    for replacement in ("", "defusedxml>=0.6.0,<1.0", "defusedxml>=0.7.1,<2.0"):
        malformed = source.replace(constraint, replacement)
        try:
            _secure_constraint(malformed, expected="defusedxml>=0.7.1,<1.0")
        except ValueError:
            pass
        else:
            raise AssertionError("missing or drifted root secure parser accepted")


def test_missing_or_drifted_minimal_parser_fails_closed() -> None:
    source = MINIMAL.read_text(encoding="utf-8")
    constraint = _secure_constraint(source)
    for replacement in ("", "defusedxml>=0.6.0,<0.7.0"):
        malformed = source.replace(constraint, replacement)
        try:
            _secure_constraint(malformed)
        except ValueError:
            pass
        else:
            raise AssertionError("missing or downgraded parser was accepted")


def test_ariana_junit_reader_uses_secure_entity_policy() -> None:
    source = (ROOT / "scripts/ci/ariana_dow_evidence.py").read_text(
        encoding="utf-8"
    )
    assert "from defusedxml import ElementTree as ET" in source
    assert "forbid_dtd=True, forbid_entities=True, forbid_external=True" in source

def test_real_ariana_reader_preserves_failures_and_skips() -> None:
    from scripts.ci.ariana_dow_evidence import read_junit

    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "native.xml"
        path.write_text(
            "<testsuite><testcase name='pass'/>"
            "<testcase name='fail'><failure/></testcase>"
            "<testcase name='skip'><skipped/></testcase></testsuite>",
            encoding="utf-8",
        )
        result = read_junit(path)
        assert result is not None
        assert result["total"] == 3
        assert result["passed"] == 1
        assert result["failures"] == 1
        assert result["skipped"] == 1


def test_real_ariana_reader_rejects_external_xml_entity() -> None:
    from defusedxml.common import DefusedXmlException

    from scripts.ci.ariana_dow_evidence import read_junit

    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "hostile.xml"
        path.write_text(
            '<!DOCTYPE testsuite [<!ENTITY leak SYSTEM "file:///etc/passwd">]>'
            '<testsuite><testcase name="&leak;"/></testsuite>',
            encoding="utf-8",
        )
        try:
            read_junit(path)
        except DefusedXmlException:
            pass
        else:
            raise AssertionError("external JUnit entity was accepted")
