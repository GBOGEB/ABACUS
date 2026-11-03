"""Wave 12 lane A behaviour tests for DMAIC_V3/phases/phase6_knowledge.py."""

import json
from types import SimpleNamespace

import pytest

from DMAIC_V3.phases import phase6_knowledge as p6


class GoodTracker:
    def __init__(self):
        self.hooks = []

    def register_recursive_hook(self, **kwargs):
        self.hooks.append(kwargs)


class BadHookTracker:
    def register_recursive_hook(self, **kwargs):
        raise RuntimeError("hook store offline")


class BrokenInitTracker:
    def __init__(self):
        raise RuntimeError("no db")


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _phase(tmp_path):
    cfg = SimpleNamespace(paths=SimpleNamespace(output_root=tmp_path / "out"))
    return p6.Phase6Knowledge(config=cfg, state=object())


def _books(root, spec):
    for category, name, body in spec:
        d = root / "CANONICAL_KNOWLEDGE" / category
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{category}_BOOK_{name}.md").write_bytes(body.encode("utf-8"))


PHASE4 = {
    "implementation_results": {
        "docstrings_added": [
            {"file": "a.py", "modifications": 3},
            {"modifications": 2},
            "loose",
        ],
        "long_lines_fixed": [],
        "type_hints_added": [{"file": "b.py"}],
        "extra_notes": "not a list",
    }
}


def _phase4(tmp_path, data, iteration=1):
    d = tmp_path / "out" / f"iteration_{iteration}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "phase4_improvements.json").write_text(json.dumps(data), encoding="utf-8")


def test_init_creates_output_and_temporal_disabled(cwd):
    ph = _phase(cwd)
    assert (cwd / "out").is_dir()
    assert ph.temporal_tracker is None


def test_init_with_temporal_tracker_ok_and_failing(cwd, monkeypatch, capsys):
    monkeypatch.setattr(p6, "TEMPORAL_AVAILABLE", True)
    monkeypatch.setattr(p6, "TemporalTracker", GoodTracker, raising=False)
    assert isinstance(_phase(cwd).temporal_tracker, GoodTracker)
    monkeypatch.setattr(p6, "TemporalTracker", BrokenInitTracker, raising=False)
    assert _phase(cwd).temporal_tracker is None
    assert "Could not initialize temporal tracker" in capsys.readouterr().out


def test_load_canonical_books(cwd, capsys):
    ph = _phase(cwd)
    assert ph._load_canonical_books() == []
    assert "Canonical directory not found" in capsys.readouterr().out
    _books(cwd, [("DMAIC", "one", "x"), ("Planning", "two", "yy")])
    (cwd / "CANONICAL_KNOWLEDGE" / "DMAIC" / "other.md").write_text("z")
    refs = ph._load_canonical_books()
    assert sorted((r.category, r.book_name, r.size_bytes) for r in refs) == [
        ("DMAIC", "DMAIC_BOOK_one", 1),
        ("Planning", "Planning_BOOK_two", 2),
    ]


def test_extract_improvement_knowledge(cwd, capsys):
    ph = _phase(cwd)
    assert ph._extract_improvement_knowledge(1) == []
    assert "Phase 4 output not found" in capsys.readouterr().out
    _phase4(cwd, PHASE4)
    know = ph._extract_improvement_knowledge(1)
    assert [k["pattern"] for k in know] == ["docstrings_added", "type_hints_added"]
    assert know[0]["count"] == 3
    assert know[0]["files_affected"] == ["a.py", "unknown"]
    assert know[0]["total_modifications"] == 5
    assert know[1]["total_modifications"] == 0


def test_extract_improvement_knowledge_bad_json(cwd, capsys):
    ph = _phase(cwd)
    _phase4(cwd, ["not", "a", "dict"])
    assert ph._extract_improvement_knowledge(1) == []
    assert "Could not extract improvement knowledge" in capsys.readouterr().out


def test_generate_knowledge_report_contents(cwd):
    ph = _phase(cwd)
    refs = [p6.KnowledgeReference("B1", "DMAIC", 0, 2 * 1024 * 1024, "p")]
    pats = [
        {
            "pattern": "docstrings_added",
            "count": 2,
            "total_modifications": 4,
            "files_affected": ["a", "b"],
        }
    ]
    ph._generate_knowledge_report(3, refs, 65, pats)
    report = cwd / "out" / "phase6_knowledge" / "KNOWLEDGE_REPORT_iter3.md"
    text = report.read_text(encoding="utf-8")
    assert "**Maturity Score:** 65/100" in text
    assert "| DMAIC | B1 | 2.00 MB |" in text
    assert "### Docstrings Added" in text
    assert "**Canonical Books:** [OK] Loaded" in text
    assert "**Improvement Patterns:** [OK] Extracted" in text
    assert "**Recursive Hooks:** [FAIL] Disabled" in text


def test_generate_knowledge_report_empty(cwd):
    ph = _phase(cwd)
    ph.temporal_tracker = GoodTracker()
    ph._generate_knowledge_report(1, [], 50)
    text = (cwd / "out" / "phase6_knowledge" / "KNOWLEDGE_REPORT_iter1.md").read_text(
        encoding="utf-8"
    )
    assert "| Category |" not in text
    assert "Improvement Knowledge Patterns" not in text
    assert "**Canonical Books:** [FAIL] Not Found" in text
    assert "**Recursive Hooks:** [OK] Registered" in text


@pytest.mark.parametrize("count,expected", [(0, 50), (3, 65), (20, 100)])
def test_calculate_maturity_score(cwd, count, expected):
    refs = [p6.KnowledgeReference("b", "c", 0, 0, "p")] * count
    assert _phase(cwd)._calculate_maturity_score(refs) == expected


def test_generate_human_report_full_and_minimal(cwd):
    ph = _phase(cwd)
    full = cwd / "full.md"
    ph._generate_human_report(
        {
            "iteration": 2,
            "duration_seconds": 1.5,
            "canonical_books_count": 4,
            "recursive_hooks_registered": 1,
            "maturity_score": 70,
        },
        full,
    )
    text = full.read_text(encoding="utf-8")
    assert "**Duration:** 1.50s" in text
    assert "**Books Referenced:** 4" in text
    assert "**Hooks Registered:** 1" in text
    assert "**Current Maturity Score:** 70/100" in text
    minimal = cwd / "min.md"
    ph._generate_human_report({}, minimal)
    mtext = minimal.read_text(encoding="utf-8")
    assert "**Iteration:** N/A" in mtext
    assert "Maturity Assessment" not in mtext


def test_knowledge_hunger_with_phase4(cwd):
    ph = _phase(cwd)
    _phase4(cwd, PHASE4)
    refs = [
        p6.KnowledgeReference("a", "DMAIC", 0, 120 * 1024 * 1024, "x"),
        p6.KnowledgeReference("b", "Planning", 0, 0, "y"),
    ]
    m = ph._activate_knowledge_hunger(1, refs)
    assert m["depth_level"] == 4  # 2 books + 120 MB // 50
    assert m["gaps_count"] == 2
    assert m["insights_count"] == 4  # list lengths 3 + 0 + 1


def test_knowledge_hunger_bad_phase4(cwd, capsys):
    ph = _phase(cwd)
    _phase4(cwd, [1, 2])
    m = ph._activate_knowledge_hunger(1, [])
    assert m == {"depth_level": 0, "insights_count": 0, "gaps_count": 4}
    assert "Could not analyze Phase 4" in capsys.readouterr().out


def test_knowledge_hunger_scans_books(cwd):
    ph = _phase(cwd)
    good = cwd / "g.md"
    good.write_text("Improve this. REFACTOR that. improve again.", encoding="utf-8")
    other = cwd / "g.pdf"
    other.write_text("improve", encoding="utf-8")
    bad = cwd / "bad.txt"
    bad.write_bytes(b"\xff\xfe\xfa improve")
    refs = [
        p6.KnowledgeReference("g", "DMAIC", 0, 1, str(good)),
        p6.KnowledgeReference("o", "Reference", 0, 1, str(other)),
        p6.KnowledgeReference("m", "Planning", 0, 1, str(cwd / "missing.md")),
        p6.KnowledgeReference("b", "Architecture", 0, 1, str(bad)),
    ]
    m = ph._activate_knowledge_hunger(9, refs)
    assert m["insights_count"] == 3
    assert m["gaps_count"] == 0
    assert m["depth_level"] == 4


def test_execute_happy_path_with_hooks(cwd, monkeypatch):
    monkeypatch.setattr(p6, "TEMPORAL_AVAILABLE", True)
    monkeypatch.setattr(p6, "TemporalTracker", GoodTracker, raising=False)
    _books(cwd, [("DMAIC", "one", "improve")])
    _phase4(cwd, PHASE4, iteration=2)
    ph = _phase(cwd)
    ok, res = ph.execute(2)
    assert ok is True
    assert res["canonical_books_count"] == 1
    assert res["recursive_hooks_registered"] == 1
    assert res["maturity_score"] == 55
    assert res["improvement_patterns_extracted"] == 2
    assert res["temporal_integration"] is True
    assert ph.temporal_tracker.hooks[0]["target_version"] == "v2"
    assert (cwd / "out" / "phase6_knowledge" / "KNOWLEDGE_REPORT_iter2.md").exists()


def test_execute_hook_failure_is_tolerated(cwd, monkeypatch, capsys):
    ph = _phase(cwd)
    ph.temporal_tracker = BadHookTracker()
    ok, res = ph.execute(1)
    assert ok is True
    assert res["recursive_hooks_registered"] == 0
    assert "Could not register hooks" in capsys.readouterr().out


def test_execute_failure_returns_error(cwd, monkeypatch):
    ph = _phase(cwd)

    def boom():
        raise RuntimeError("disk gone")

    monkeypatch.setattr(ph, "_load_canonical_books", boom)
    ok, res = ph.execute(4)
    assert ok is False
    assert res["error"] == "disk gone"
    assert res["iteration"] == 4


def check_production_defect_knowledge_report_returns_none(cwd):
    # Pins a production_defect (phase6_knowledge.py:248): the "return report_path"
    # sits inside a dead nested duplicate def, so _generate_knowledge_report returns
    # None and execute() reports report_path "None". Fails once fixed.
    ph = _phase(cwd)
    assert ph._generate_knowledge_report(1, [], 50) is None
    ok, res = ph.execute(1)
    assert ok is True
    assert res["report_path"] == "None"
