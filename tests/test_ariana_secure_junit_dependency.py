"""Fail-closed install contract for source-owned Ariana/DOW secure JUnit parser.

Regression from exact-head native B0 #39056760386 and Python Matrix #39056760298,
where collection died with ModuleNotFoundError: defusedxml on all three lanes.
"""
from __future__ import annotations

from pathlib import Path

from defusedxml import ElementTree as SAFE_XML
from defusedxml.common import DefusedXmlException

ROOT = Path(__file__).resolve().parents[1]


def test_root_install_declares_secure_junit_parser() -> None:
    """The existing B0/CI install path uses requirements-dev -> root requirements."""
    root_lines = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    dev_lines = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8").splitlines()
    assert any(line.split("#", 1)[0].strip().startswith("defusedxml>=") for line in root_lines)
    assert "-r requirements.txt" in dev_lines
    assert "-r DMAIC_V3/requirements.txt" in root_lines


def test_junit_entity_expansion_is_rejected() -> None:
    """Native import must be present, and XML entity expansion must stay forbidden."""
    malicious = '<!DOCTYPE testsuite [<!ENTITY gotcha "forged-pass">]><testsuite><testcase name="&gotcha;"/></testsuite>'
    try:
        SAFE_XML.fromstring(
            malicious, forbid_dtd=True, forbid_entities=True, forbid_external=True
        )
    except DefusedXmlException:
        pass
    else:
        raise AssertionError("secure JUnit parser unexpectedly admitted an entity")
