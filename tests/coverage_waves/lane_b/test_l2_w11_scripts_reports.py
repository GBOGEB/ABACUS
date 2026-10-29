"""Lane-B wave 11: markdown exec runner, repo relevance report, metrics charts."""

import functools
import json
import sys
from datetime import datetime as real_datetime

import matplotlib
import pytest

from ._l2_loader import load

mx = load("scripts/markdown_exec_runner.py")
rr = load("scripts/report_repo_relevance.py")

with matplotlib.rc_context():
    mc = load("scripts/generate_metrics_charts.py")

FIXED = real_datetime(2026, 1, 2, 3, 4, 5)


class _FrozenDatetime(real_datetime):
    @classmethod
    def utcnow(cls):
        return FIXED


# --------------------------------------------------------------------------
# markdown_exec_runner
# --------------------------------------------------------------------------


class _Runner:
    """Records subprocess.run calls and returns scripted results."""

    def __init__(self, mod, results=None):
        self.mod = mod
        self.calls = []
        self.results = list(results or [])

    def __call__(self, args, capture_output, text):
        assert capture_output is True and text is True
        self.calls.append(list(args))
        code, out, err = self.results.pop(0) if self.results else (0, "ok", "")
        return self.mod.subprocess.CompletedProcess(
            args=args, returncode=code, stdout=out, stderr=err
        )


@pytest.fixture
def md_env(tmp_path, monkeypatch):
    out_root = tmp_path / "out"
    monkeypatch.setattr(mx, "OUT_ROOT", out_root)
    monkeypatch.setattr(mx, "datetime", _FrozenDatetime)
    tmpdir = tmp_path / "tmpfiles"
    tmpdir.mkdir()
    monkeypatch.setattr(
        mx.tempfile,
        "NamedTemporaryFile",
        functools.partial(mx.tempfile.NamedTemporaryFile, dir=str(tmpdir)),
    )
    return out_root, tmpdir


def _doc(tmp_path, body):
    p = tmp_path / "doc.md"
    p.write_text(body, encoding="utf-8")
    return p


def test_run_block_bash(monkeypatch):
    runner = _Runner(mx, [(3, "o", "e")])
    monkeypatch.setattr(mx.subprocess, "run", runner)
    res = mx.run_block("sh", "echo hi")
    assert runner.calls == [["bash", "-lc", "echo hi"]]
    assert (res.returncode, res.stdout, res.stderr) == (3, "o", "e")


def test_run_block_python_writes_temp_script(md_env, monkeypatch):
    _, tmpdir = md_env
    runner = _Runner(mx)
    monkeypatch.setattr(mx.subprocess, "run", runner)
    mx.run_block("python", "print(1)\n")
    (call,) = runner.calls
    assert call[0] == mx.sys.executable
    script = tmpdir / call[1].replace("\\", "/").rsplit("/", 1)[-1]
    assert script.read_text(encoding="utf-8") == "print(1)\n"


def test_run_block_unsupported_language(monkeypatch):
    monkeypatch.setattr(mx.subprocess, "run", _Runner(mx, []))
    res = mx.run_block("ruby", "puts 1")
    assert res.returncode == 0
    assert res.stderr == "Unsupported lang: ruby"


def test_main_usage(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog"])
    assert mx.main() == 2
    assert "Usage" in capsys.readouterr().out


def test_main_missing_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path / "nope.md")])
    assert mx.main() == 2
    assert "Not found" in capsys.readouterr().out


def test_main_runs_exec_blocks_and_records_summary(
    tmp_path, md_env, monkeypatch, capsys
):
    out_root, _ = md_env
    body = (
        "intro\n"
        "```python\nprint('not executed')\n```\n"
        "```bash exec\nfalse\n```\n"
        "```python exec:assert\nprint(2)\n```\n"
        "```ruby exec\nputs 1\n```\n"
    )
    doc = _doc(tmp_path, body)
    runner = _Runner(mx, [(1, "", "boom"), (0, "2\n", "")])
    monkeypatch.setattr(mx.subprocess, "run", runner)
    monkeypatch.setattr(sys, "argv", ["prog", str(doc)])

    assert mx.main() == 0
    assert "Executed 3 exec blocks; passed=True" in capsys.readouterr().out
    assert len(runner.calls) == 2
    run_dir = out_root / "doc" / "20260102_030405"
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["timestamp"] == FIXED.isoformat() + "Z"
    assert summary["passed"] is True
    assert [(b["lang"], b["assert"], b["returncode"]) for b in summary["blocks"]] == [
        ("bash", False, 1),
        ("python", True, 0),
        ("ruby", False, 0),
    ]
    assert (run_dir / "block_001.bash.err").read_text(encoding="utf-8") == "boom"
    assert (run_dir / "block_002.python.out").read_text(encoding="utf-8") == "2\n"
    assert (run_dir / "block_003.ruby.err").read_text(encoding="utf-8") == (
        "Unsupported lang: ruby"
    )


def test_main_assert_failure_stops(tmp_path, md_env, monkeypatch, capsys):
    out_root, _ = md_env
    body = "```bash exec assert\nexit 4\n```\n" "```bash exec\necho later\n```\n"
    doc = _doc(tmp_path, body)
    runner = _Runner(mx, [(4, None, None)])
    monkeypatch.setattr(mx.subprocess, "run", runner)
    monkeypatch.setattr(sys, "argv", ["prog", str(doc)])

    assert mx.main() == 1
    assert "passed=False" in capsys.readouterr().out
    assert len(runner.calls) == 1
    run_dir = out_root / "doc" / "20260102_030405"
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["passed"] is False
    assert len(summary["blocks"]) == 1
    assert (run_dir / "block_001.bash.out").read_text(encoding="utf-8") == ""


# --------------------------------------------------------------------------
# report_repo_relevance
# --------------------------------------------------------------------------


def _workspace(tmp_path, rels):
    ws = tmp_path / "ws"
    ws.mkdir(exist_ok=True)
    for rel in rels:
        p = ws / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    return ws


ALL_FILES = list(rr.WORKFLOW_CHECKS.values()) + list(rr.UTILITY_CHECKS.values())


def test_detect_repository_precedence(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    assert rr.detect_repository("x/Y", tmp_path) == "x/Y"
    assert rr.detect_repository(None, tmp_path) == tmp_path.name
    monkeypatch.setenv("GITHUB_REPOSITORY", "env/R")
    assert rr.detect_repository(None, tmp_path) == "env/R"


def test_build_report_abacus_full(tmp_path):
    ws = _workspace(tmp_path, ALL_FILES)
    rep = rr.build_report("GBOGEB/abacus", ws)
    assert rep["role"] == "abacus-main"
    assert rep["workflows"] == rr.WORKFLOW_CHECKS
    assert rep["utilities"] == rr.UTILITY_CHECKS
    assert len(rep["similarities"]) == 3
    assert rep["similarities"][2].startswith("ABACUS keeps")


def test_build_report_codex_partial(tmp_path):
    ws = _workspace(
        tmp_path, [rr.WORKFLOW_CHECKS["codex"], "run_deployment_test_system.py"]
    )
    rep = rr.build_report("CODEX", ws)
    assert rep["role"] == "codex-main"
    assert rep["workflows"] == {"codex": rr.WORKFLOW_CHECKS["codex"]}
    assert rep["utilities"] == {"deployment_runner": "run_deployment_test_system.py"}
    assert len(rep["similarities"]) == 1
    assert rep["similarities"][0].startswith("CODEX can reuse")


def test_build_report_generic_bridge_only(tmp_path):
    ws = _workspace(tmp_path, [rr.WORKFLOW_CHECKS["bridge"]])
    rep = rr.build_report("other/thing", ws)
    assert rep["role"] == "generic"
    assert rep["stack"] == ["unknown"]
    assert rep["similarities"] == []
    assert rep["utilities"] == {}


def test_render_text_and_markdown(tmp_path):
    ws = _workspace(tmp_path, ALL_FILES)
    rep = rr.build_report("GBOGEB/ABACUS", ws)
    text = rr.render_text(rep)
    assert text.splitlines()[0] == "Repository: GBOGEB/ABACUS"
    assert "- ci: .github/workflows/ci.yml" in text
    assert "Improvement steps:" in text
    md = rr.render_markdown(rep)
    assert md.startswith("## Repo relevance summary")
    assert "- **Stack:** `DMAIC_V3`, `bridge-testing`, `docs-validation`" in md
    assert "- `repo_relevance` → `scripts/report_repo_relevance.py`" in md


@pytest.mark.parametrize(
    "fmt,marker",
    [
        (None, "Repository: GBOGEB/ABACUS"),
        ("text", "Role: abacus-main"),
        ("github-step-summary", "## Repo relevance summary"),
    ],
)
def test_main_rendered_formats(tmp_path, monkeypatch, capsys, fmt, marker):
    ws = _workspace(tmp_path, [])
    argv = ["prog", "--repo", "GBOGEB/ABACUS", "--workspace", str(ws)]
    if fmt:
        argv += ["--format", fmt]
    monkeypatch.setattr(sys, "argv", argv)
    assert rr.main() == 0
    assert marker in capsys.readouterr().out


def test_main_json(tmp_path, monkeypatch, capsys):
    ws = _workspace(tmp_path, [rr.UTILITY_CHECKS["docs_validator"]])
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setattr(
        sys, "argv", ["prog", "--workspace", str(ws), "--format", "json"]
    )
    assert rr.main() == 0
    data = json.loads(capsys.readouterr().out)
    assert data["repository"] == "ws"
    assert data["utilities"] == {"docs_validator": "scripts/validate_docs_links.py"}


def test_main_rejects_unknown_format(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--format", "xml"])
    with pytest.raises(SystemExit) as exc:
        rr.main()
    assert exc.value.code == 2


# --------------------------------------------------------------------------
# generate_metrics_charts
# --------------------------------------------------------------------------

CHARTS = [
    ("chart_test_growth", "test_growth"),
    ("chart_tests_per_phase", "tests_per_phase"),
    ("chart_module_breakdown", "module_breakdown"),
    ("chart_phase_loc", "phase_loc"),
    ("chart_version_lineage", "version_lineage"),
    ("chart_dmaic_radar", "dmaic_radar"),
]


def test_chart_module_uses_agg_and_accessible_palette():
    assert matplotlib.get_backend().lower() == "agg"
    assert set(mc.PALETTE) == {
        "define",
        "measure",
        "analyze",
        "improve",
        "control",
        "infra",
        "accent",
    }
    assert all(v.startswith("#") and len(v) == 7 for v in mc.PALETTE.values())


@pytest.mark.parametrize("func,name", CHARTS)
def test_chart_writes_svg(tmp_path, monkeypatch, capsys, func, name):
    monkeypatch.setattr(mc, "OUT_DIR", str(tmp_path))
    with matplotlib.rc_context():
        getattr(mc, func)()
    svg = tmp_path / (name + ".svg")
    content = svg.read_text(encoding="utf-8")
    assert "<svg" in content
    assert name + ".svg" in capsys.readouterr().out
    assert mc.plt.get_fignums() == []
