"""Lane-B wave 11: script generators (global index, iteration report, md index)."""

import json
import sys
import types

import pytest

from ._l2_loader import load

gi = load("scripts/generate_global_index.py")
mdi = load("scripts/generate_md_index.py")

SAVED_REPORTS = []


class _Level:
    def __init__(self, level, name, completion, status, conv):
        self.level = level
        self.name = name
        self.completion_percentage = completion
        self.status = status
        self.convergence_achieved = conv


class FakeMaturityTracker:
    def __init__(self, workspace):
        self.workspace = workspace

    def generate_report(self):
        return types.SimpleNamespace(
            current_level=1,
            convergence_score=72.25,
            overall_completion=55.5,
            levels=[
                _Level(0, "Planning", 100.0, "COMPLETED", True),
                _Level(1, "Foundation", 60.0, "IN_PROGRESS", False),
                _Level(2, "Development", 10.0, "ACTIVE", False),
                _Level(3, "Production", 0.0, "PENDING", False),
            ],
            recommendations=["Add tests", "Stabilise phases"],
            next_milestone="Level 2",
        )

    def save_report(self):
        path = self.workspace / "maturity_report_x.json"
        path.write_text("{}", encoding="utf-8")
        SAVED_REPORTS.append(path)
        return path


class FakeStabilityMonitor:
    def __init__(self, workspace):
        self.workspace = workspace
        self.scanned = False

    def scan_workspace(self):
        self.scanned = True

    def generate_report(self):
        return types.SimpleNamespace(
            overall_stability=88.0,
            file_stability=90.0,
            test_stability=80.0,
            metric_stability=70.0,
            changes_detected=3,
            alerts=["a", "b"],
        )

    def save_report(self):
        path = self.workspace / "stability_report_x.json"
        path.write_text("{}", encoding="utf-8")
        return path


class FakeVersionManager:
    def __init__(self, workspace):
        self.workspace = workspace

    def get_current_version(self):
        return "3.2.1"


class FakeGitManager:
    clean = True

    def __init__(self, workspace):
        self.workspace = workspace

    def get_status(self):
        return types.SimpleNamespace(
            branch="main",
            is_clean=self.clean,
            modified_files=["a.py"],
            untracked_files=["b.py", "c.py"],
        )


_saved_path = list(sys.path)
ir = load(
    "scripts/generate_iteration_report.py",
    deps={
        "DMAIC_V3.convergence.maturity_tracker": types.SimpleNamespace(
            MaturityTracker=FakeMaturityTracker
        ),
        "DMAIC_V3.convergence.stability_monitor": types.SimpleNamespace(
            StabilityMonitor=FakeStabilityMonitor
        ),
        "DMAIC_V3.integrations.version_manager": types.SimpleNamespace(
            VersionManager=FakeVersionManager
        ),
        "DMAIC_V3.integrations.git_manager": types.SimpleNamespace(
            GitManager=FakeGitManager
        ),
    },
)
sys.path[:] = _saved_path


# --------------------------------------------------------------------------
# generate_global_index
# --------------------------------------------------------------------------


@pytest.fixture
def gen(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return gi.GlobalIndexGenerator()


def _write_history(gen, history):
    (gen.output_dir / ".file_hashes.json").write_text(
        json.dumps(history), encoding="utf-8"
    )


def test_init_creates_output_dir_and_mapping(gen, tmp_path):
    assert (tmp_path / "DMAIC_V3_OUTPUT").is_dir()
    assert gen.maturity_mapping["DMAIC_V3/convergence/"] == 3
    assert ".git" in gen.exclude_patterns


@pytest.mark.parametrize(
    "path, level",
    [
        ("DMAIC_V3/core/x.py", 1),
        ("DMAIC_V3/phases/phase3_x.py", 2),
        ("DMAIC_V3/convergence/y.py", 3),
        ("misc/other.py", 0),
    ],
)
def test_determine_maturity_level(gen, path, level):
    assert gen.determine_maturity_level(path) == level


def test_calculate_file_hash_ok_and_error(gen, tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"abc")
    assert gen.calculate_file_hash(f) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    assert gen.calculate_file_hash(tmp_path / "missing.bin") == "ERROR"


def test_stable_iterations_no_file(gen):
    assert gen.get_stable_iterations("a.py") == 0


def test_stable_iterations_short_history(gen):
    _write_history(gen, [{"hashes": {"a.py": "h1"}}])
    assert gen.get_stable_iterations("a.py") == 0


def test_stable_iterations_counts_until_change(gen):
    _write_history(
        gen,
        [
            {"hashes": {"a.py": "h0"}},
            {"hashes": {"a.py": "h1"}},
            {"hashes": {"a.py": "h1"}},
            {"hashes": {"a.py": "h1"}},
        ],
    )
    assert gen.get_stable_iterations("a.py") == 3


def test_stable_iterations_whole_history_stable(gen):
    _write_history(gen, [{"hashes": {"a.py": "h1"}}, {"hashes": {"a.py": "h1"}}])
    assert gen.get_stable_iterations("a.py") == 2


def test_stable_iterations_stops_at_missing_entry(gen):
    _write_history(gen, [{"hashes": {"a.py": "h1"}}, {"hashes": {}}])
    assert gen.get_stable_iterations("a.py") == 0
    _write_history(gen, [{"hashes": {}}, {"hashes": {"a.py": "h1"}}])
    assert gen.get_stable_iterations("a.py") == 1


def test_stable_iterations_corrupt_json(gen):
    (gen.output_dir / ".file_hashes.json").write_text("{bad", encoding="utf-8")
    assert gen.get_stable_iterations("a.py") == 0


def test_extract_code_elements(gen, tmp_path):
    src = tmp_path / "m.py"
    src.write_text(
        "import os, sys\n"
        "from DMAIC_V3.core import x\n"
        "from . import y\n"
        "class K:\n"
        "    def meth(self):\n"
        "        pass\n"
        "def top():\n"
        "    pass\n",
        encoding="utf-8",
    )
    res = gen.extract_code_elements(src)
    assert res["classes"] == ["K"]
    assert sorted(res["functions"]) == ["meth", "top"]
    assert res["imports"] == ["os", "sys", "DMAIC_V3.core"]


def test_extract_code_elements_syntax_error(gen, tmp_path):
    src = tmp_path / "bad.py"
    src.write_text("def (:\n", encoding="utf-8")
    assert gen.extract_code_elements(src) == {
        "functions": [],
        "classes": [],
        "imports": [],
    }


def test_find_test_files(gen, tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_foo.py").write_text("", encoding="utf-8")
    (tmp_path / "foo_test.py").write_text("", encoding="utf-8")
    found = gen.find_test_files("pkg/foo.py")
    assert len(found) == 2
    assert any(p.endswith("test_foo.py") for p in found)
    assert "foo_test.py" in found
    assert gen.find_test_files("pkg/none.py") == []


def test_analyze_dependencies(gen):
    assert gen.analyze_dependencies(["os", "DMAIC_V3.core", "DMAIC_V3"]) == [
        "DMAIC_V3.core",
        "DMAIC_V3",
    ]


def _make_tree(tmp_path):
    core = tmp_path / "DMAIC_V3" / "core"
    core.mkdir(parents=True)
    (core / "engine.py").write_text(
        "from DMAIC_V3.config import C\nclass Engine:\n    pass\n", encoding="utf-8"
    )
    conv = tmp_path / "DMAIC_V3" / "convergence"
    conv.mkdir(parents=True)
    (conv / "conv.py").write_text("def f():\n    pass\n", encoding="utf-8")
    (tmp_path / "loose.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "skip.py").write_text("", encoding="utf-8")
    (tmp_path / "dir.py").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_engine.py").write_text("", encoding="utf-8")


def test_scan_artifacts_statuses(gen, tmp_path, monkeypatch):
    _make_tree(tmp_path)
    stab = {"engine.py": 5, "conv.py": 1}

    def fake_stable(path):
        for name, value in stab.items():
            if path.endswith(name):
                return value
        return 0

    monkeypatch.setattr(gen, "get_stable_iterations", fake_stable)
    arts = {a.path.replace("\\", "/"): a for a in gen.scan_artifacts()}
    assert set(arts) == {
        "DMAIC_V3/core/engine.py",
        "DMAIC_V3/convergence/conv.py",
        "loose.py",
        "tests/test_engine.py",
    }
    eng = arts["DMAIC_V3/core/engine.py"]
    assert eng.status == "STABLE"
    assert eng.classes == ["Engine"]
    assert eng.dependencies == ["DMAIC_V3.config"]
    assert eng.tests == [str(gi.Path("tests/test_engine.py"))]
    assert eng.id.startswith("ARTF_")
    assert len(eng.hash_sha256) == 64
    assert arts["DMAIC_V3/convergence/conv.py"].status == "ACTIVE"
    assert arts["loose.py"].status == "NEW"
    assert eng.to_dict()["path"] == eng.path


def test_convergence_metrics_variants(gen):
    assert gen.get_convergence_metrics() is None
    mf = gen.output_dir / ".convergence_history.json"
    mf.write_text("[]", encoding="utf-8")
    assert gen.get_convergence_metrics() is None
    mf.write_text("{bad", encoding="utf-8")
    assert gen.get_convergence_metrics() is None
    mf.write_text(json.dumps([{"a": 1}, {"a": 2}]), encoding="utf-8")
    assert gen.get_convergence_metrics() == {"a": 2}


def test_knowledge_summary(gen):
    assert gen.get_knowledge_summary() == {"total_packs": 0, "total_iterations": 0}
    kd = gen.output_dir / "knowledge"
    (kd / "ITERATION_7").mkdir(parents=True)
    (kd / "ITERATION_7" / "p.json").write_text("{}", encoding="utf-8")
    (kd / "other.json").write_text("{}", encoding="utf-8")
    assert gen.get_knowledge_summary() == {"total_packs": 2, "total_iterations": 1}


def test_generate_index_with_convergence(gen, tmp_path, capsys):
    """Maturity patterns use "/" so they only match where os.sep is "/"."""
    _make_tree(tmp_path)
    posix = gi.os.sep == "/"
    (gen.output_dir / ".convergence_history.json").write_text(
        json.dumps([{"iteration": 4, "convergence_score": 81.25, "maturity_level": 2}]),
        encoding="utf-8",
    )
    path = gen.generate_index()
    data = json.loads((tmp_path / "GLOBAL_index.json").read_text(encoding="utf-8"))
    assert path.name == "GLOBAL_index.json"
    assert data["metadata"]["iteration"] == 4
    assert data["metadata"]["convergence_score"] == 81.25
    assert data["metadata"]["maturity_level"] == 2
    assert data["metadata"]["total_artifacts"] == 4
    assert data["statistics"]["by_maturity"]["level_1_foundation"] == int(posix)
    assert data["statistics"]["by_maturity"]["level_3_production"] == int(posix)
    assert data["statistics"]["by_status"]["NEW"] == 4
    assert data["statistics"]["total_classes"] == 1
    assert data["statistics"]["total_tests"] == 1
    assert len(data["maturity_levels"]["0"]) == (2 if posix else 4)
    out = capsys.readouterr().out
    assert "Convergence score: 81.2%" in out
    assert "GLOBAL INDEX GENERATED" in out


def test_main_without_convergence(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert gi.main() == 0
    data = json.loads((tmp_path / "GLOBAL_index.json").read_text(encoding="utf-8"))
    assert data["metadata"]["iteration"] == 1
    assert data["metadata"]["convergence_score"] == 0.0
    assert data["convergence"] is None
    out = capsys.readouterr().out
    assert "No convergence data available" in out
    assert "GLOBAL index saved to" in out


# --------------------------------------------------------------------------
# generate_md_index
# --------------------------------------------------------------------------


def test_md_index_generate_and_save(tmp_path):
    for name in ("b.md", "a.md", "c.txt"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    content = mdi.generate_markdown_index(str(tmp_path))
    lines = content.splitlines()
    assert lines[0] == "# Markdown Index"
    assert lines[2].startswith("- [a.md](")
    assert lines[3].startswith("- [b.md](")
    assert "c.txt" not in content
    mdi.save_index_file(str(tmp_path), content)
    assert (tmp_path / "INDEX.md").read_text() == content


def test_md_index_empty_dir(tmp_path):
    assert mdi.generate_markdown_index(str(tmp_path)) == "# Markdown Index\n\n"


# --------------------------------------------------------------------------
# generate_iteration_report
# --------------------------------------------------------------------------


def test_detect_iteration_default(tmp_path):
    g = ir.IterationReportGenerator(workspace_path=tmp_path)
    assert g.iteration == 6
    assert isinstance(g.maturity_tracker, FakeMaturityTracker)


def test_detect_iteration_from_yaml(tmp_path):
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "task_definitions.yaml").write_text(
        "metadata:\n  iteration: 9\n", encoding="utf-8"
    )
    assert ir.IterationReportGenerator(workspace_path=tmp_path).iteration == 10


def test_detect_iteration_bad_yaml_falls_back(tmp_path):
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "task_definitions.yaml").write_text("- a\n- b\n", encoding="utf-8")
    assert ir.IterationReportGenerator(workspace_path=tmp_path).iteration == 6


def test_default_workspace_is_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    g = ir.IterationReportGenerator(iteration=3)
    assert g.workspace_path == tmp_path
    assert g.iteration == 3


def test_collect_statistics(tmp_path):
    g = ir.IterationReportGenerator(workspace_path=tmp_path, iteration=2)
    stats = g.collect_statistics()
    assert g.stability_monitor.scanned is True
    assert stats["iteration"] == 2
    assert stats["version"] == "3.2.1"
    assert stats["maturity"]["levels"][1]["name"] == "Foundation"
    assert stats["stability"]["alerts_count"] == 2
    assert stats["git"] == {
        "branch": "main",
        "is_clean": True,
        "modified_files": 1,
        "untracked_files": 2,
    }


@pytest.mark.parametrize("clean, marker", [(True, "Yes"), (False, "No")])
def test_markdown_report(tmp_path, monkeypatch, clean, marker):
    monkeypatch.setattr(FakeGitManager, "clean", clean)
    g = ir.IterationReportGenerator(workspace_path=tmp_path, iteration=2)
    md = g.generate_markdown_report(g.collect_statistics())
    assert md.startswith("# DMAIC V3 - ITERATION REPORT")
    assert "**Current Maturity Level:** 1 - Foundation" in md
    assert "**Convergence Score:** 72.2/100" in md
    assert "| \u2705 0 | Planning | 100.0% | COMPLETED | \u2713 |" in md
    assert "| \U0001f504 1 | Foundation | 60.0% | IN_PROGRESS | \u2717 |" in md
    assert "| \U0001f504 2 | Development" in md
    assert "| \u23f3 3 | Production" in md
    assert "1. Add tests" in md
    assert "2. Stabilise phases" in md
    assert "- **Clean:** " + marker in md
    assert "iteration_2_report_" + ir.TIMESTAMP + ".md" in md


def test_generate_reports_writes_files(tmp_path, capsys):
    SAVED_REPORTS.clear()
    g = ir.IterationReportGenerator(workspace_path=tmp_path, iteration=4)
    paths = g.generate_reports()
    assert paths["json"].parent == tmp_path
    data = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert data["iteration"] == 4
    assert paths["markdown"].read_text(encoding="utf-8").startswith("# DMAIC V3")
    assert paths["maturity"] == SAVED_REPORTS[0]
    assert paths["stability"].name == "stability_report_x.json"
    out = capsys.readouterr().out
    assert "ITERATION 4 REPORT GENERATOR" in out
    assert "Next Milestone: Level 2" in out


def test_iteration_main(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["prog", "--iteration", "8", "--workspace", str(tmp_path)]
    )
    ir.main()
    assert len(list(tmp_path.glob("iteration_8_report_*.json"))) == 1
    assert len(list(tmp_path.glob("iteration_8_report_*.md"))) == 1
