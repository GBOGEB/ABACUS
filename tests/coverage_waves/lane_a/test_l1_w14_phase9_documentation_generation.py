"""Lane A wave 14: DMAIC_V3.phases.phase9_documentation_generation gates and books."""

import json
import sys

import pytest

from DMAIC_V3.phases import phase9_documentation_generation as p9


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _phase(root, it, name, data, fname=None):
    d = root / "DMAIC_V3_OUTPUT" / f"iteration_{it}" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / (fname or f"{name}.json")).write_text(json.dumps(data), encoding="utf-8")


def _minimum(root, it, total_files=10, python_files=("a.py",)):
    _phase(
        root,
        it,
        "phase1_define",
        {
            "total_files": total_files,
            "python_files": list(python_files),
            "markdown_files": ["r.md"],
        },
    )
    _phase(root, it, "phase2_measure", {"python_files_analyzed": 3})


def _saved(root, it):
    path = (
        root
        / "DMAIC_V3_OUTPUT"
        / f"iteration_{it}"
        / "phase9_documentation_generation"
        / "phase9_documentation_generation.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def test_skip_when_iteration_missing(cwd):
    ok, res = p9.Phase9_DocumentationGeneration().execute(1)
    assert ok is False
    assert res["reason"] == "execution_not_successful"
    assert _saved(cwd, 1)["status"] == "skipped"


def test_skip_when_phase2_missing(cwd):
    _phase(cwd, 2, "phase1_define", {})
    (cwd / "DMAIC_V3_OUTPUT" / "iteration_2" / "phase2_measure").mkdir()
    ok, res = p9.Phase9_DocumentationGeneration().execute(2)
    assert ok is False
    assert res["reason"] == "execution_not_successful"


def test_skip_on_open_bugs(cwd):
    _minimum(cwd, 3)
    bugs = [{"id": 1, "status": "open"}, {"id": 2, "status": "closed"}]
    _phase(cwd, 3, "phase5_control", {"bugs": bugs})
    ok, res = p9.Phase9_DocumentationGeneration().execute(3)
    assert ok is False
    assert res["reason"] == "bugs_detected"
    assert res["details"] == [{"id": 1, "status": "open"}]


def test_skip_on_failed_gate(cwd):
    _minimum(cwd, 4)
    gates = {"g1": dict(passed=True), "g2": {}}
    _phase(cwd, 4, "phase5_control", {"bugs": [], "quality_gates": gates})
    ok, res = p9.Phase9_DocumentationGeneration().execute(4)
    assert ok is False
    assert res["reason"] == "quality_gates_failed"


def test_full_success_with_discrepancies(cwd):
    it = 5
    _phase(cwd, it, "phase0_initialization", {"x": 1})
    _minimum(cwd, it)
    _phase(
        cwd,
        it,
        "phase2_measure",
        {
            "python_files_analyzed": 4,
            "analysis_success_rate": 0.5,
            "average_complexity": 2.0,
            "documentation_coverage": 0.25,
        },
    )
    mods = [
        {"file": "a.py", "type": "doc"},
        {"file": "a.py", "type": "doc"},
        {"file": "b.py"},
    ]
    _phase(cwd, it, "phase4_improve", {"modifications": mods})
    gates = {"g1": dict(passed=True)}
    _phase(cwd, it, "phase5_control", {"bugs": [], "quality_gates": gates})
    _phase(cwd, it, "phase6_knowledge", {"books_loaded": 7, "maturity_score": 80})
    actions = [{"status": "done"}, {"status": "done"}, {}]
    _phase(cwd, it, "phase7_action_tracking", {"local_actions": actions})
    _phase(
        cwd,
        it,
        "phase7_action_tracking",
        {"pending_actions": [1], "recommendations": [1, 2]},
        fname="feedback_for_next_iteration.json",
    )
    gen = p9.Phase9_DocumentationGeneration()
    ok, res = gen.execute(it)
    assert ok is True
    assert res["status"] == "success"
    assert res["books_generated"] == 4
    assert {d["field"] for d in res["discrepancies"]} == {"total_files", "python_files"}
    assert res["adjustments_made"] == 2
    adj = (
        cwd
        / "DMAIC_V3_OUTPUT"
        / f"iteration_{it}"
        / "phase9_documentation_generation"
        / "canonical_adjustments.json"
    )
    assert len(json.loads(adj.read_text(encoding="utf-8"))["adjustments"]) == 2
    books = {p.split("CANONICAL_KNOWLEDGE")[1][1:]: p for p in res["book_paths"]}
    dmaic = next(v for k, v in books.items() if k.startswith("DMAIC"))
    text = (cwd / dmaic).read_text(encoding="utf-8")
    assert "Quality Gates: 1/1 passed" in text
    assert "Books Loaded: 7" in text
    assert "Modifications Made: 3" in text
    assert "### Phase 0: Phase0 Initialization" in text
    metrics = next(v for k, v in books.items() if k.startswith("Execution"))
    mtext = (cwd / metrics).read_text(encoding="utf-8")
    assert "Files Modified:** 2" in mtext
    assert "  - doc: 2\n" in mtext and "  - unknown: 1\n" in mtext
    actions_book = next(v for k, v in books.items() if k.startswith("Planning"))
    atext = (cwd / actions_book).read_text(encoding="utf-8")
    assert "  - done: 2\n" in atext
    assert "**Recommendations:** 2" in atext


def test_success_without_phase5_or_discrepancies(cwd):
    _minimum(cwd, 6, total_files=130000, python_files=["f"] * 12000)
    gen = p9.Phase9_DocumentationGeneration()
    ok, res = gen.execute(6)
    assert ok is True
    assert res["discrepancies_found"] == 0
    assert res["adjustments"] == []
    assert gen.books_generated and len(gen.books_generated) == 4


def test_exception_returns_error(cwd, monkeypatch):
    gen = p9.Phase9_DocumentationGeneration()

    def boom(iteration):
        raise RuntimeError("disk gone")

    monkeypatch.setattr(gen, "_verify_execution_success", boom)
    assert gen.execute(1) == (False, {"error": "disk gone"})


def test_helpers():
    gen = p9.Phase9_DocumentationGeneration()
    assert gen._get_phase_name(9) == "phase9"
    assert gen._format_phase_summary(3, {}) == "**Status:** ✅ SUCCESS\n\n"
    assert gen._detect_discrepancies(99) == []


@pytest.mark.parametrize("prepare,code", [(True, 0), (False, 1)])
def test_main(cwd, monkeypatch, prepare, code):
    if prepare:
        _minimum(cwd, 7, total_files=130000, python_files=["f"] * 12000)
    monkeypatch.setattr(sys, "argv", ["phase9.py", "7"])
    with pytest.raises(SystemExit) as exc:
        p9.main()
    assert exc.value.code == code


def test_main_usage(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["phase9.py"])
    with pytest.raises(SystemExit) as exc:
        p9.main()
    assert exc.value.code == 1
    assert "Usage" in capsys.readouterr().out
