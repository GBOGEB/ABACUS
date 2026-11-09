"""Behaviour tests for ABACUS-v031/run_direct_improvements.py.

The module imports a ``dow_engine`` package (``DOWEngine`` and
``dow_engine.core.dmaic.DMAICEngine``) that is not present in the repository,
so the engine is replaced by in-memory stubs. The stubs are only visible in
``sys.modules`` while the module is being loaded.
"""

import json
import sys
import types
from pathlib import Path

import pytest

from tests.coverage_waves.lane_a._load import load

REL = "ABACUS-v031/run_direct_improvements.py"
STUB_NAMES = ("dow_engine", "dow_engine.core", "dow_engine.core.dmaic")


class StubDMAIC:
    def __init__(self, name):
        self.name = name
        self.phases = []

    def _record(self, phase, kwargs):
        self.phases.append((phase, kwargs))

    def define(self, **kw):
        self._record("define", kw)

    def measure(self, **kw):
        self._record("measure", kw)

    def analyze(self, **kw):
        self._record("analyze", kw)

    def improve(self, **kw):
        self._record("improve", kw)

    def control(self, **kw):
        self._record("control", kw)


class StubEngine:
    pass


def _load_with_stubs():
    saved = {name: sys.modules.get(name) for name in STUB_NAMES}
    pkg = types.ModuleType("dow_engine")
    pkg.DOWEngine = StubEngine
    core = types.ModuleType("dow_engine.core")
    dmaic = types.ModuleType("dow_engine.core.dmaic")
    dmaic.DMAICEngine = StubDMAIC
    sys.modules.update(
        {"dow_engine": pkg, "dow_engine.core": core, "dow_engine.core.dmaic": dmaic}
    )
    try:
        return load(REL)
    finally:
        for name, value in saved.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


rdi = _load_with_stubs()


# --- improve_markdown_quality -------------------------------------------------


def test_markdown_splits_long_sentences(tmp_path):
    p = tmp_path / "doc.md"
    words = "".join(["word "] * 25)
    long_line = "".join(["First sentence is here. ", words, "end. Last part"])
    assert len(long_line) > 100
    p.write_text("# Title\n- item\n" + long_line + "\nshort line", encoding="utf-8")
    assert rdi.improve_markdown_quality(p) is True
    lines = p.read_text(encoding="utf-8").split("\n")
    assert lines[:3] == ["# Title", "- item", "First sentence is here."]
    assert lines[-2] == "Last part."
    assert lines[-1] == "short line"


def test_markdown_unchanged_and_empty(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("# T\n* x\n\nplain", encoding="utf-8")
    assert rdi.improve_markdown_quality(p) is False
    e = tmp_path / "e.md"
    e.write_text("  \n", encoding="utf-8")
    assert rdi.improve_markdown_quality(e) is False


def test_markdown_long_line_without_period_untouched(tmp_path):
    p = tmp_path / "b.md"
    p.write_text("x" * 150, encoding="utf-8")
    assert rdi.improve_markdown_quality(p) is False


def test_markdown_error_is_reported(tmp_path, capsys):
    assert rdi.improve_markdown_quality(tmp_path / "missing.md") is False
    assert "Error improving" in capsys.readouterr().out


# --- add_documentation_header ---------------------------------------------------


@pytest.mark.parametrize("start", ["# h\n", '"""doc"""\n', "<!-- c -->\n"])
def test_header_skipped_when_present(tmp_path, start):
    p = tmp_path / "f.md"
    p.write_text(start, encoding="utf-8")
    assert rdi.add_documentation_header(p, "markdown") is False


def test_header_markdown(tmp_path):
    p = tmp_path / "my_doc.md"
    p.write_text("body", encoding="utf-8")
    assert rdi.add_documentation_header(p, "markdown") is True
    text = p.read_text(encoding="utf-8")
    assert text.startswith("# My Doc\n\n**File:** `my_doc.md`")
    assert "**Type:** Documentation" in text
    assert text.endswith("---\n\nbody")


def test_header_code(tmp_path):
    p = tmp_path / "some_mod.py"
    p.write_text("x = 1\n", encoding="utf-8")
    assert rdi.add_documentation_header(p, "code") is True
    text = p.read_text(encoding="utf-8")
    assert text.startswith('"""\nSome Mod\n\nModule: some_mod.py\n')
    assert text.endswith('"""\n\nx = 1\n')


@pytest.mark.parametrize("kind", ["yaml", "text"])
def test_header_yaml_text(tmp_path, kind):
    p = tmp_path / "conf.yaml"
    p.write_text("a: 1\n", encoding="utf-8")
    assert rdi.add_documentation_header(p, kind) is True
    text = p.read_text(encoding="utf-8")
    assert text.startswith("# File: conf.yaml\n# Purpose: Configuration file\n\n")
    assert text.endswith("a: 1\n")


def test_header_unknown_type_noop(tmp_path):
    p = tmp_path / "x.bin"
    p.write_text("data", encoding="utf-8")
    assert rdi.add_documentation_header(p, "binary") is False
    assert p.read_text(encoding="utf-8") == "data"


def test_header_error_is_reported(tmp_path, capsys):
    assert rdi.add_documentation_header(tmp_path / "nope.md", "markdown") is False
    assert "Error adding header" in capsys.readouterr().out


# --- improve_code_quality -------------------------------------------------------


def test_code_quality_never_rewrites(tmp_path):
    p = tmp_path / "c.py"
    long_value = "".join(["z"] * 130)
    body = "".join(["print('x')\nprint('TODO')\ny = '", long_value, "'\n# c\n"])
    p.write_text(body, encoding="utf-8")
    assert rdi.improve_code_quality(p) is False
    assert p.read_text(encoding="utf-8") == body


def test_code_quality_error_is_reported(tmp_path, capsys):
    assert rdi.improve_code_quality(tmp_path / "missing.py") is False
    assert "Error improving code" in capsys.readouterr().out


# --- main ---------------------------------------------------------------------


class Metrics:
    def __init__(self, score):
        self.score = score

    def overall_score(self):
        return self.score


class Ranking:
    def __init__(self, path, kind, score):
        self.artifact_path = path
        self.artifact_type = kind
        self.metrics = Metrics(score)


def make_engine_cls(first, second, created):
    class FakeEngine:
        def __init__(self, config_path, repo_path):
            assert config_path == Path("dow_engine_config.yaml")
            assert repo_path == Path(".")
            rows = first if not created else second
            created.append(self)
            self.ranking = types.SimpleNamespace(
                rankings=rows, generate_improvement_report=lambda: "PLAN\n"
            )
            self.indexed = False

        def ingest_directory(self, path):
            assert path == Path(".")
            return len(self.ranking.rankings)

        def run_dmaic_cycle(self):
            return None

        def generate_canonical_index(self):
            self.indexed = True

    return FakeEngine


@pytest.fixture
def dmaic_log(monkeypatch):
    log = []

    class Recorder(StubDMAIC):
        def __init__(self, name):
            super().__init__(name)
            log.append(self)

    monkeypatch.setattr(rdi, "DMAICEngine", Recorder)
    return log


def test_main_applies_improvements(tmp_path, monkeypatch, capsys, dmaic_log):
    monkeypatch.chdir(tmp_path)
    long_line = "Alpha beta gamma. " * 8
    Path("notes.md").write_text(long_line, encoding="utf-8")
    Path("tool.py").write_text("x = 1\n", encoding="utf-8")
    Path("cfg.yaml").write_text("a: 1\n", encoding="utf-8")
    Path("titled.md").write_text("# Done\n", encoding="utf-8")
    Path("blob.bin").write_text("b", encoding="utf-8")
    first = [
        Ranking("notes.md", "markdown", 0.1),
        Ranking("tool.py", "code", 0.1),
        Ranking("cfg.yaml", "yaml", 0.2),
        Ranking("gone.md", "markdown", 0.1),
        Ranking("titled.md", "markdown", 0.2),
        Ranking("blob.bin", "binary", 0.2),
        Ranking("good.md", "markdown", 0.9),
    ]
    second = [Ranking("notes.md", "markdown", 0.8)]
    created = []
    monkeypatch.setattr(rdi, "DOWEngine", make_engine_cls(first, second, created))
    with pytest.raises(SystemExit) as exc:
        rdi.main()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "Found 6 artifacts with score < 0.3" in out
    assert "Skipped: gone.md (not found)" in out
    assert "Improvements Applied:   3" in out
    assert "Success Rate:           50.0%" in out
    assert Path("improvement_plan.txt").read_text(encoding="utf-8") == "PLAN\n"
    assert Path("tool.py").read_text(encoding="utf-8").startswith('"""')
    assert Path("cfg.yaml").read_text(encoding="utf-8").startswith("# File:")
    assert Path("titled.md").read_text(encoding="utf-8") == "# Done\n"
    assert created[1].indexed is True
    phases = dict(dmaic_log[0].phases)
    assert dmaic_log[0].name == "direct_improvements"
    assert phases["measure"] == {"total_artifacts": 7, "ranked_artifacts": 7}
    assert phases["analyze"] == {"low_score_count": 6, "improvement_target": 6}
    assert phases["improve"]["improvements_applied"] == 3
    assert phases["control"]["improvements_made"] == 3
    assert phases["control"]["score_improvement"] == pytest.approx(0.8 - 1.8 / 7)


def test_main_without_changes_exits_1(tmp_path, monkeypatch, capsys, dmaic_log):
    monkeypatch.chdir(tmp_path)
    Path("ok.md").write_text("# Fine\n", encoding="utf-8")
    first = [Ranking("ok.md", "markdown", 0.1), Ranking("j.json", "json", 0.1)]
    created = []
    monkeypatch.setattr(rdi, "DOWEngine", make_engine_cls(first, first, created))
    with pytest.raises(SystemExit) as exc:
        rdi.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "No improvements were applied" in out
    assert "Success Rate:           0.0%" in out


def test_main_caps_targets_at_twenty(tmp_path, monkeypatch, capsys, dmaic_log):
    monkeypatch.chdir(tmp_path)
    first = [Ranking("m" + str(i) + ".md", "markdown", 0.0) for i in range(25)]
    monkeypatch.setattr(rdi, "DOWEngine", make_engine_cls(first, first, []))
    with pytest.raises(SystemExit):
        rdi.main()
    out = capsys.readouterr().out
    assert "[20/20]" in out
    assert "[21/" not in out
    assert dict(dmaic_log[0].phases)["analyze"]["improvement_target"] == 20


# Reproduction of a production_defect (see WAVE_LEDGER.jsonl). Named check_*
# so the governed suite does not collect it: a pinned defect must never block the fix.
# Run on demand: pytest -o python_functions=check_* <this file>
def check_production_defect_main_zero_low_score_division(tmp_path, monkeypatch):
    # Pins: main() divides by target_count in the summary; when no artifact
    # scores < 0.3 it crashes with ZeroDivisionError instead of exiting 1.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(rdi, "DMAICEngine", StubDMAIC)
    rows = [Ranking("a.md", "markdown", 0.9)]
    monkeypatch.setattr(rdi, "DOWEngine", make_engine_cls(rows, rows, []))
    with pytest.raises(ZeroDivisionError):
        rdi.main()


# Reproduction of a production_defect (see WAVE_LEDGER.jsonl). Named check_*
# so the governed suite does not collect it: a pinned defect must never block the fix.
# Run on demand: pytest -o python_functions=check_* <this file>
def check_production_defect_text_header_title_overwritten(tmp_path):
    # Pins: the yaml/text branch assigns the title line, then overwrites it with
    # "header = ..." instead of "+=", so the title never reaches the file.
    p = tmp_path / "my_conf.yaml"
    p.write_text("a: 1\n", encoding="utf-8")
    rdi.add_documentation_header(p, "yaml")
    assert "# My Conf" not in p.read_text(encoding="utf-8")


# Reproduction of a production_defect (see WAVE_LEDGER.jsonl). Named check_*
# so the governed suite does not collect it: a pinned defect must never block the fix.
# Run on demand: pytest -o python_functions=check_* <this file>
def check_production_defect_json_artifact_gets_comment_header(
    tmp_path, monkeypatch, dmaic_log
):
    # Pins: main() routes 'json' artifacts to the '#'-comment text header,
    # which turns a valid JSON file into invalid JSON.
    monkeypatch.chdir(tmp_path)
    Path("data.json").write_text('{"a": 1}', encoding="utf-8")
    rows = [Ranking("data.json", "json", 0.1)]
    monkeypatch.setattr(rdi, "DOWEngine", make_engine_cls(rows, rows, []))
    with pytest.raises(SystemExit):
        rdi.main()
    with pytest.raises(json.JSONDecodeError):
        json.loads(Path("data.json").read_text(encoding="utf-8"))


# Reproduction of a production_defect (see WAVE_LEDGER.jsonl). Named check_*
# so the governed suite does not collect it: a pinned defect must never block the fix.
# Run on demand: pytest -o python_functions=check_* <this file>
def check_production_defect_dow_engine_package_missing():
    # Pins: the module imports the dow_engine package (with core.dmaic), which
    # does not exist anywhere in the repository, so the script cannot start.
    saved = {name: sys.modules.pop(name, None) for name in STUB_NAMES}
    try:
        with pytest.raises(ModuleNotFoundError):
            load(REL, name="l1_w10_rdi_unstubbed")
    finally:
        sys.modules.pop("l1_w10_rdi_unstubbed", None)
        for name, value in saved.items():
            if value is not None:
                sys.modules[name] = value
