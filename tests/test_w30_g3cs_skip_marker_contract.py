"""Ensure missing optional archive is a typed BLOCKED_SOURCE_MISSING skip.

Never relax B0 skip policy or silently count an unavailable native ZIP as PASS.
The standalone synthetic positive/forged-archive tests remain fully collected.
"""
import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"MIP"/"G3CS_CONVERGENCE_V2"/"observatory"/"w10"/"test_w10_spine.py"


def test_optional_zip_skip_has_exact_governed_source_missing_marker():
    tree=ast.parse(SOURCE.read_text(encoding="utf-8"))
    bodies=[
        n for c in tree.body if isinstance(c,ast.ClassDef)
        for n in c.body if isinstance(n,ast.FunctionDef)
        and n.name=="test_native_zip_success_and_sha_guard"
    ]
    assert len(bodies)==1
    skips=[x for x in ast.walk(bodies[0]) if isinstance(x,ast.Call)
           and isinstance(x.func,ast.Attribute) and x.func.attr=="skipTest"]
    assert len(skips)==1
    assert isinstance(skips[0].args[0],ast.Constant)
    reason=skips[0].args[0].value
    assert reason.count("TEST_BLOCKED_SOURCE_MISSING")==1
    assert reason.startswith("TEST_BLOCKED_SOURCE_MISSING:")
    assert all(x not in reason for x in ("TEST_BLOCKED_CONFIG", "TEST_NOT_IMPLEMENTED"))


def test_synthetic_proof_and_forged_archive_negative_tests_preserved():
    source=SOURCE.read_text(encoding="utf-8")
    assert "def test_positive_native_zip_from_synthetic_receipt(" in source
    assert "with self.assertRaisesRegex(refresh.EvidenceError,'SHA256 differs')" in source
    assert "with self.assertRaisesRegex(refresh.EvidenceError,'another source')" in source
    assert "assert" in source


def test_skip_is_not_false_green_or_artifact_autogeneration():
    source=SOURCE.read_text(encoding="utf-8")
    assert "archive=ROOT/'b0-pr2239.zip'" in source
    assert "if not archive.exists():self.skipTest(" in source
    assert "TEST_BLOCKED_SOURCE_MISSING:" in source
    assert ".write_bytes(" not in source
