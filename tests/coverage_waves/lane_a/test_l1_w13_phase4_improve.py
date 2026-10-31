"""Wave 13 lane A behaviour tests for DMAIC_V3/phases/phase4_improve.py."""

import ast
import importlib
import json
import sys
from types import SimpleNamespace

import pytest


def _import_restoring_sys_path():
    saved = list(sys.path)
    try:
        return importlib.import_module("DMAIC_V3.phases.phase4_improve")
    finally:
        sys.path[:] = saved


p4 = _import_restoring_sys_path()

UNDOC = "class K:\n    def m(self):\n        return 1\n\n\ndef top(a):\n    return a\n"
LONG_CALL = "result = call(" + ", ".join(f"argument_{i}" for i in range(12)) + ")\n"


def _src(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def _read(path):
    return path.read_text(encoding="utf-8")


def _phase(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir(exist_ok=True)
    cfg = SimpleNamespace(
        paths=SimpleNamespace(workspace_root=str(ws), output_root=tmp_path / "out")
    )
    return p4.Phase4Improve(cfg, None)


# --- CodeImprover -----------------------------------------------------------


def test_add_missing_docstrings_inserts_and_parses(tmp_path):
    ci = p4.CodeImprover(tmp_path)
    f = _src(tmp_path / "a.py", UNDOC)
    res = ci.add_missing_docstrings(f)
    assert res["success"] is True
    assert res["modifications"] == 3
    assert {d["name"] for d in res["details"]} == {"K", "m", "top"}
    text = _read(f)
    ast.parse(text)
    assert '"""TODO: Add class description"""' in text
    assert text.count('"""TODO: Add function description"""') == 2
    assert ci.improvements_made == [res]


def test_add_missing_docstrings_noop_and_error(tmp_path):
    ci = p4.CodeImprover(tmp_path)
    f = _src(tmp_path / "d.py", 'def f():\n    """Doc."""\n    return 1\n')
    assert ci.add_missing_docstrings(f) == {
        "success": False,
        "reason": "No missing docstrings",
    }
    bad = _src(tmp_path / "bad.py", "def (:\n")
    assert "error" in ci.add_missing_docstrings(bad)
    assert ci.improvements_made == []


def test_fix_long_lines(tmp_path):
    ci = p4.CodeImprover(tmp_path)
    comment = "# " + "c" * 120 + "\n"
    no_comma = "x = " + "1" * 120 + "\n"
    doc = '"""' + "a, " * 50 + '"""\n'
    f = _src(tmp_path / "l.py", comment + no_comma + doc + LONG_CALL + "y = 1\n")
    res = ci.fix_long_lines(f)
    assert res == {"success": True, "file": str(f), "modifications": 1}
    lines = _read(f).splitlines()
    assert lines[0] == comment.rstrip("\n")
    assert lines[1] == no_comma.rstrip("\n")
    assert lines[3] == "result = call(argument_0,"
    assert lines[4] == "    argument_1,"
    assert lines[-2] == "    argument_11)"
    assert lines[-1] == "y = 1"


def test_fix_long_lines_noop_and_error(tmp_path):
    ci = p4.CodeImprover(tmp_path)
    f = _src(tmp_path / "s.py", "x = 1\n")
    assert ci.fix_long_lines(f)["reason"] == "No long lines found"
    assert "error" in ci.fix_long_lines(tmp_path / "missing.py")
    f2 = _src(tmp_path / "s2.py", "a = (1, 2, 3)\n")
    assert ci.fix_long_lines(f2, max_length=5)["modifications"] == 1


def test_add_type_hints_adds_import_and_skips(tmp_path):
    ci = p4.CodeImprover(tmp_path)
    text = (
        "class C:\n"
        "    def __init__(self):\n"
        "        pass\n"
        "    def typed(self) -> int:\n"
        "        return 1\n"
        "    def plain(self):\n"
        "        return 2\n"
    )
    f = _src(tmp_path / "t.py", text)
    res = ci.add_type_hints(f)
    assert res["success"] is True
    assert res["details"] == [
        {"line": 6, "function": "plain", "change": "added return type hint"}
    ]
    out = _read(f)
    assert out.startswith("from typing import Any\n")
    assert "def plain(self) -> Any:" in out
    assert "def __init__(self):" in out
    ast.parse(out)


def test_add_type_hints_keeps_existing_typing_import(tmp_path):
    ci = p4.CodeImprover(tmp_path)
    f = _src(tmp_path / "t.py", "from typing import Any\n\ndef f():\n    return 1\n")
    assert ci.add_type_hints(f)["modifications"] == 1
    assert _read(f).count("from typing import") == 1


def test_add_type_hints_noop_and_error(tmp_path):
    ci = p4.CodeImprover(tmp_path)
    f = _src(tmp_path / "t.py", "def f() -> int:\n    return 1\n")
    assert ci.add_type_hints(f)["reason"] == "No missing type hints"
    bad = _src(tmp_path / "bad.py", "def (:\n")
    assert "error" in ci.add_type_hints(bad)


def test_remove_unused_imports_conservative(tmp_path):
    ci = p4.CodeImprover(tmp_path)
    text = (
        "from __future__ import annotations\n"
        "import os\n"
        "import os.path as osp\n"
        "import sys, json\n"
        "import re  # keep comment\n"
        "import abc; import io\n"
        "from typing import (\n"
        "    List,\n"
        ")\n"
        "from glob import *\n"
        "from pathlib import Path\n"
        "import collections.abc\n"
        "print(sys.argv)\n"
    )
    f = _src(tmp_path / "u.py", text)
    res = ci.remove_unused_imports(f)
    assert res["success"] is True
    assert res["modifications"] == 4
    out = _read(f)
    for gone in ("import os\n", "osp", "from pathlib", "collections.abc"):
        assert gone not in out
    for kept in ("__future__", "import sys, json", "import re", "import abc;", "List"):
        assert kept in out
    assert "from glob import *" in out


@pytest.mark.parametrize(
    "text",
    [
        "import os\n__all__ = ['x']\n",
        "import os\nexec('pass')\n",
        "import os\nprint(os.sep)\n",
    ],
)
def test_remove_unused_imports_noop(tmp_path, text):
    f = _src(tmp_path / "n.py", text)
    assert p4.CodeImprover(tmp_path).remove_unused_imports(f) == {
        "success": False,
        "reason": "No unused imports",
    }
    assert _read(f) == text


def test_remove_unused_imports_error(tmp_path):
    bad = _src(tmp_path / "bad.py", "def (:\n")
    assert "error" in p4.CodeImprover(tmp_path).remove_unused_imports(bad)


# --- Phase4Improve planning -------------------------------------------------


def test_generate_refactoring_plan(tmp_path):
    tasks = _phase(tmp_path).generate_refactoring_plan(
        [
            {"category": "High Complexity", "severity": "high", "count": 4},
            {"category": "God Classes", "severity": "critical", "count": 1},
            {"category": "Low Documentation", "severity": "low", "count": 9},
            {"category": "Other"},
        ]
    )
    assert [t["category"] for t in tasks] == [
        "Complexity Reduction",
        "Class Decomposition",
        "Documentation",
    ]
    assert [t["task_id"] for t in tasks] == ["REFACTOR-1", "REFACTOR-2", "REFACTOR-3"]
    assert tasks[2]["estimated_effort"] == "Medium"
    assert tasks[0]["affected_files"] == 4


def test_prioritize_improvements(tmp_path):
    tasks = [
        {"priority": "low", "estimated_effort": "Low"},
        {"priority": "critical", "estimated_effort": "High"},
        {"priority": "weird"},
    ]
    out = _phase(tmp_path).prioritize_improvements(tasks)
    assert [t["roi_score"] for t in out] == [pytest.approx(40 / 3), 10.0, 5.0]
    assert out[0]["impact_score"] == 40


def test_roadmap_and_metrics(tmp_path):
    ph = _phase(tmp_path)
    tasks = [{"priority": "low", "estimated_effort": "Low"} for _ in range(12)]
    tasks[11] = {"priority": "critical", "estimated_effort": "High"}
    tasks[10] = {"priority": "high", "estimated_effort": "Medium"}
    roadmap = ph.generate_implementation_roadmap(tasks)
    assert len(roadmap["phase_1_immediate"]) == 4
    assert len(roadmap["phase_2_short_term"]) == 8
    assert roadmap["phase_3_long_term"] == []
    tasks.append({"priority": "low"})
    roadmap = ph.generate_implementation_roadmap(tasks)
    assert len(roadmap["phase_3_long_term"]) == 1
    metrics = ph.generate_improvement_metrics(roadmap)
    assert metrics["total_improvements"] == 13
    assert metrics["immediate_actions"] == 4
    assert metrics["long_term_actions"] == 1
    assert metrics["estimated_total_effort"] == 10 * 1 + 3 + 2 + 1


# --- Phase4Improve implementation ------------------------------------------


def test_implement_improvements(tmp_path):
    ph = _phase(tmp_path)
    ws = ph.workspace_root
    _src(ws / "doc.py", UNDOC)
    _src(ws / "cx.py", "import os\n" + LONG_CALL + "def g():\n    return result\n")
    _src(ws / "clean.py", 'def h() -> int:\n    """Doc."""\n    return 1\n')
    _src(ws / "notes.txt", "x")
    res = ph.implement_improvements(
        high_complexity_files=[{"file": "cx.py"}, {"file": "clean.py"}, {}],
        low_doc_files=[{"file": "doc.py"}, {"file": "notes.txt"}, {"file": "nope.py"}],
        max_files=10,
    )
    assert res["total_files_improved"] == 3
    assert len(res["docstrings_added"]) == 1
    assert len(res["long_lines_fixed"]) == 1
    assert len(res["unused_imports_removed"]) == 1
    assert len(res["type_hints_added"]) == 2
    assert res["total_modifications"] == 3 + 2 + 1 + 1 + 1
    assert [e["type"] for e in ph.improvements_log] == [
        "docstring",
        "complexity",
        "complexity",
    ]


def test_apply_improvements_by_category(tmp_path):
    ph = _phase(tmp_path)
    ws = ph.workspace_root
    _src(ws / "a.py", "import os\n" + LONG_CALL + UNDOC)
    out = ph.apply_improvements(
        [
            {"task_id": "T1", "category": "Complexity Reduction"},
            {"task_id": "T2", "category": "Documentation"},
            {"task_id": "T3", "category": "Misc"},
        ]
    )
    assert [r["task_id"] for r in out] == ["T1", "T2", "T3"]
    assert len(out[0]["details"]) == 2
    assert len(out[1]["details"]) == 2
    assert out[1]["applied_to_files"] == [str(ws / "a.py")] * 2
    assert out[2]["details"] == []


def test_apply_improvements_generic_category_modifies(tmp_path):
    ph = _phase(tmp_path)
    _src(ph.workspace_root / "b.py", "import os\n" + UNDOC)
    out = ph.apply_improvements([{"task_id": "G", "category": "Other"}])
    assert len(out[0]["details"]) == 2


def test_apply_improvements_missing_workspace(tmp_path):
    ph = _phase(tmp_path)
    ph.workspace_root = tmp_path / "gone"
    out = ph.apply_improvements([{"task_id": "T", "category": "Documentation"}])
    assert out == [
        {
            "task_id": "T",
            "category": "Documentation",
            "applied_to_files": [],
            "details": [],
        }
    ]


# --- run / execute ------------------------------------------------------------


def test_run_without_phase3_writes_minimal_result(tmp_path):
    ok, res = _phase(tmp_path).run(1)
    assert ok is False
    assert "Phase 3 output not found" in res["error"]
    it = tmp_path / "out" / "iteration_1"
    assert (it / "phase4_improvements.json").exists()
    saved = json.loads(
        (it / "phase4_improve" / "phase4_improve.json").read_text("utf-8")
    )
    assert saved["version"] == p4.__version__


def test_run_with_phase3(tmp_path):
    ph = _phase(tmp_path)
    _src(ph.workspace_root / "doc.py", UNDOC)
    it = tmp_path / "out" / "iteration_2"
    it.mkdir(parents=True)
    phase3 = {
        "root_causes": [
            {"category": "High Complexity", "severity": "high", "count": 1},
            {"category": "Low Documentation", "severity": "medium", "count": 1},
        ],
        "high_complexity_files": [{"file": "doc.py"}],
    }
    (it / "phase3_analysis.json").write_text(json.dumps(phase3), encoding="utf-8")
    ok, res = ph.execute(2)
    assert ok is True
    assert res["summary"]["total_improvements"] == 2
    assert res["summary"]["files_actually_improved"] == 2
    assert res["summary"]["total_modifications_made"] > 0
    assert res["improvements"] is res["refactoring_tasks"]
    saved = json.loads(
        (it / "phase4_improve" / "phase4_improve.json").read_text("utf-8")
    )
    assert saved["metrics"]["total_improvements"] == 2


def test_run_with_phase3_without_low_doc(tmp_path):
    ph = _phase(tmp_path)
    it = tmp_path / "out" / "iteration_1"
    it.mkdir(parents=True)
    (it / "phase3_analysis.json").write_text(
        json.dumps({"root_causes": [{"category": "God Classes"}]}), encoding="utf-8"
    )
    ok, res = ph.run(1)
    assert ok is True
    assert res["summary"]["files_actually_improved"] == 0


@pytest.mark.parametrize(
    "returned, expected_ok, key",
    [
        ((True, (True, {"k": 1})), True, "k"),
        ((True, (False, {"k": 1})), False, "k"),
        ("garbage", False, "error"),
        ((True, ["x"]), False, "error"),
    ],
)
def test_execute_normalisation(tmp_path, monkeypatch, returned, expected_ok, key):
    ph = _phase(tmp_path)
    monkeypatch.setattr(ph, "run", lambda iteration: returned)
    ok, payload = ph.execute(1)
    assert ok is expected_ok
    assert key in payload


def check_production_defect_type_hint_replaces_first_colon(tmp_path):
    # Pins a production_defect: add_type_hints replaces the FIRST ':' on the def
    # line, so an annotated parameter yields 'def f(x -> Any: int):' and the file
    # no longer parses. This check will fail once the insertion point is fixed.
    f = _src(tmp_path / "t.py", "def f(x: int):\n    return x\n")
    res = p4.CodeImprover(tmp_path).add_type_hints(f)
    assert res["success"] is True
    text = _read(f)
    assert "def f(x -> Any: int):" in text
    with pytest.raises(SyntaxError):
        ast.parse(text)


def check_production_defect_docstring_multiline_signature(tmp_path):
    # Pins a production_defect: add_missing_docstrings inserts the docstring right
    # after the 'def' line, which for a multi-line signature lands inside the
    # parameter list and breaks the file. This check will fail once fixed.
    f = _src(tmp_path / "m.py", "def f(\n    a,\n):\n    return a\n")
    res = p4.CodeImprover(tmp_path).add_missing_docstrings(f)
    assert res["success"] is True
    with pytest.raises(SyntaxError):
        ast.parse(_read(f))
