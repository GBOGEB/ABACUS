"""W31 actual pytest test-state marker qualification, not textual skip-only."""
import ast
import importlib.util
from pathlib import Path
import pytest

SOURCE=Path(__file__).resolve().parents[1]/"MIP/G3CS_CONVERGENCE_V2/observatory/w10/test_w10_spine.py"


def test_actual_pytest_marker_attached_to_optional_native_zip():
    spec=importlib.util.spec_from_file_location("g3cs_w31_marker",SOURCE)
    assert spec and spec.loader
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    method=m.GlobalSpineW10Tests.test_native_zip_success_and_sha_guard
    marks=[mark.name for mark in getattr(method,"pytestmark",[])]
    assert marks.count("TEST_BLOCKED_SOURCE_MISSING")==1
    assert not any(x in marks for x in
                   ("TEST_BLOCKED_CONFIG","TEST_BLOCKED_DEPENDENCY","TEST_NOT_IMPLEMENTED"))


def test_standard_unittest_path_remains_optional_dependency():
    tree=ast.parse(SOURCE.read_text(encoding="utf-8"))
    helper=next(x for x in tree.body if isinstance(x,ast.FunctionDef)
                and x.name=="_govern_source_missing")
    assert any(isinstance(n,ast.ExceptHandler) and
               isinstance(n.type,ast.Name) and n.type.id=="ImportError"
               for n in ast.walk(helper))
    cases=[n for n in tree.body if isinstance(n,ast.ClassDef)
           and n.name=="GlobalSpineW10Tests"]
    func=next(x for x in cases[0].body if isinstance(x,ast.FunctionDef)
              and x.name=="test_native_zip_success_and_sha_guard")
    assert any(isinstance(d,ast.Name) and d.id=="_govern_source_missing"
               for d in func.decorator_list)
