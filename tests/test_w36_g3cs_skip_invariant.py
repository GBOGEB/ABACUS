"""W36 strict one-item-marker skip contract: no removal or policy weakening."""
import ast
import importlib.util
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]/"MIP/G3CS_CONVERGENCE_V2/observatory/w10/test_w10_spine.py"


def _state():
    tree=ast.parse(SOURCE.read_text(encoding="utf-8"))
    klass=next(x for x in tree.body if isinstance(x,ast.ClassDef)
               and x.name=="GlobalSpineW10Tests")
    fun=next(x for x in klass.body if isinstance(x,ast.FunctionDef)
             and x.name=="test_native_zip_success_and_sha_guard")
    return tree,fun


def test_one_source_mark_not_two_decorators():
    _,fun=_state()
    marks=[d.id for d in fun.decorator_list if isinstance(d,ast.Name)]
    assert marks==["_govern_source_missing"],marks
    source=SOURCE.read_text(encoding="utf-8")
    assert "@pytest.mark.TEST_BLOCKED_SOURCE_MISSING" not in source


def test_skip_reason_exactly_matches_governed_classification():
    _,fun=_state()
    skips=[x for x in ast.walk(fun) if isinstance(x,ast.Call)
           and isinstance(x.func,ast.Attribute) and x.func.attr=="skipTest"]
    assert len(skips)==1
    text=skips[0].args[0].value
    assert text.startswith("TEST_BLOCKED_SOURCE_MISSING:")
    assert text.count("TEST_BLOCKED_SOURCE_MISSING")==1
    assert "TEST_BLOCKED_DEPENDENCY" not in text


def test_native_marker_method_has_one_marker_and_optional_unittest_fallback():
    spec=importlib.util.spec_from_file_location("g3cs_w36",SOURCE)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    marked=module.GlobalSpineW10Tests.test_native_zip_success_and_sha_guard
    states=[m.name for m in getattr(marked,"pytestmark",[])]
    assert states==["TEST_BLOCKED_SOURCE_MISSING"]
    source=SOURCE.read_text(encoding="utf-8")
    assert "except ImportError:" in source
    assert "def test_positive_native_zip_from_synthetic_receipt(" in source
    assert "with self.assertRaisesRegex(refresh.EvidenceError" in source
