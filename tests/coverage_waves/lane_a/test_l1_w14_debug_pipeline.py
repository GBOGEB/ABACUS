"""Lane A wave 14: DMAIC_V3.debug_pipeline diagnostics on synthetic workspaces."""

import importlib
import json
import sys

import pytest


def _import_restoring_sys_path():
    saved = list(sys.path)
    try:
        return importlib.import_module("DMAIC_V3.debug_pipeline")
    finally:
        sys.path[:] = saved


dp = _import_restoring_sys_path()

PHASES = [
    "phase0_init.py",
    "phase1_define.py",
    "phase2_measure.py",
    "phase3_analyze.py",
    "phase4_improve.py",
    "phase5_control.py",
    "phase6_knowledge.py",
    "phase7_action_tracking.py",
    "phase8_todo_management.py",
]


def _healthy_ws(root):
    for sub in ("DMAIC_V3/phases", "DMAIC_V3/core", "DMAIC_V3/convergence"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    for name in PHASES:
        (root / "DMAIC_V3" / "phases" / name).write_text(
            "def execute(self):\n    return 1\n", encoding="utf-8"
        )
    for name in ("index.json", "ranking.json", "ranking.yaml", "manifest.json"):
        (root / name).write_text("{}", encoding="utf-8")
    it = root / "DMAIC_V3_OUTPUT" / "iteration_1"
    for n in range(9):
        d = it / f"phase{n}_x"
        d.mkdir(parents=True)
        (d / "out.json").write_text(json.dumps({"ok": 1}), encoding="utf-8")
    return root


def test_healthy_workspace(tmp_path, capsys):
    dbg = dp.PipelineDebugger(_healthy_ws(tmp_path))
    res = dbg.run_full_diagnostic()
    assert res["status"] == "healthy"
    assert res["issues"] == []
    assert res["checks"]["outputs"]["iterations"][0]["number"] == 1
    assert all(
        v["exists"]
        for v in res["checks"]["outputs"]["iterations"][0]["phases"].values()
    )
    assert res["checks"]["phases"]["phases"]["phase0_init.py"]["has_execute"] is True
    assert "SYSTEM HEALTHY" in capsys.readouterr().out


def test_empty_workspace_is_critical(tmp_path, capsys):
    dbg = dp.PipelineDebugger(tmp_path)
    res = dbg.run_full_diagnostic()
    assert res["status"] == "critical"
    assert "Created DMAIC_V3_OUTPUT directory" in res["fixes"]
    assert (tmp_path / "DMAIC_V3_OUTPUT").is_dir()
    assert res["checks"]["structure"]["status"] == "error"
    out = capsys.readouterr().out
    assert "CRITICAL ISSUES DETECTED" in out
    assert "FIXES APPLIED" in out


def test_warning_status_when_only_canonical_missing(tmp_path, capsys):
    ws = _healthy_ws(tmp_path)
    (ws / "manifest.json").unlink()
    res = dp.PipelineDebugger(ws).run_full_diagnostic()
    assert res["status"] == "warning"
    assert res["checks"]["canonical"]["files"]["manifest.json"]["exists"] is False
    assert "WARNINGS DETECTED" in capsys.readouterr().out


def test_check_imports_syntax_and_decode_errors(tmp_path):
    ws = _healthy_ws(tmp_path)
    phases = ws / "DMAIC_V3" / "phases"
    (phases / "phase_bad.py").write_text("def x(:\n", encoding="utf-8")
    (phases / "phase_bin.py").write_bytes(b"\xff\xfe\x00bad")
    dbg = dp.PipelineDebugger(ws)
    res = dbg._check_imports()
    assert res["status"] == "error"
    assert any("Syntax error at line 1" in e for e in res["errors"])
    assert any(e.startswith("phase_bin.py:") for e in res["errors"])
    assert [i["category"] for i in dbg.issues] == ["imports"]


def test_check_phase_files_missing_execute_and_unreadable(tmp_path):
    ws = _healthy_ws(tmp_path)
    phases = ws / "DMAIC_V3" / "phases"
    (phases / "phase1_define.py").write_text("x = 1\n", encoding="utf-8")
    (phases / "phase2_measure.py").write_bytes(b"\xff\xfe\x00bad")
    (phases / "phase3_analyze.py").unlink()
    dbg = dp.PipelineDebugger(ws)
    res = dbg._check_phase_files()["phases"]
    assert res["phase1_define.py"]["has_execute"] is False
    assert "error" in res["phase2_measure.py"]
    assert res["phase3_analyze.py"] == {
        "exists": False,
        "size": 0,
        "has_execute": False,
    }
    sev = sorted(i["severity"] for i in dbg.issues)
    assert sev == ["critical", "warning", "warning"]


def test_output_structure_skips_invalid_names(tmp_path, capsys):
    out = tmp_path / "DMAIC_V3_OUTPUT"
    (out / "iteration_x").mkdir(parents=True)
    dbg = dp.PipelineDebugger(tmp_path)
    res = dbg._check_output_structure()
    assert res["iterations"] == []
    text = capsys.readouterr().out
    assert "Skipping invalid directory: iteration_x" in text
    assert "No valid iterations found" in text
    (out / "iteration_2" / "phase3_a").mkdir(parents=True)
    res = dbg._check_output_structure()
    phases = res["iterations"][0]["phases"]
    assert phases["phase3"]["files"] == 0
    assert phases["phase0"] == {"exists": False}


def test_empty_phase_detection_reasons(tmp_path):
    out = tmp_path / "DMAIC_V3_OUTPUT"
    (out / "iteration_bad").mkdir(parents=True)
    it = out / "iteration_3"
    (it / "phase0_empty").mkdir(parents=True)
    p1 = it / "phase1_files"
    p1.mkdir()
    (p1 / "empty.json").write_text("{}", encoding="utf-8")
    (p1 / "broken.json").write_text("{not json", encoding="utf-8")
    (p1 / "dir.json").mkdir()
    (p1 / "good.json").write_text('{"a": 1}', encoding="utf-8")
    dbg = dp.PipelineDebugger(tmp_path)
    res = dbg._check_empty_phases()
    assert res["status"] == "warning"
    reasons = {e.get("file", e["phase"]): e["reason"] for e in res["empty_phases"]}
    assert reasons["phase0_empty"] == "no_json_files"
    assert reasons["empty.json"] == "empty_json"
    assert reasons["broken.json"] == "invalid_json"
    assert reasons["dir.json"] not in ("empty_json", "invalid_json")
    assert "good.json" not in reasons
    msgs = [i["message"] for i in dbg.issues]
    assert any("iteration_bad" in m for m in msgs)


def test_empty_phases_all_valid(tmp_path, capsys):
    dbg = dp.PipelineDebugger(_healthy_ws(tmp_path))
    assert dbg._check_empty_phases()["status"] == "ok"
    assert "All phase outputs valid" in capsys.readouterr().out


def test_failed_iterations(tmp_path):
    out = tmp_path / "DMAIC_V3_OUTPUT"
    (out / "iteration_zz").mkdir(parents=True)
    (out / "iteration_4" / "phase0_a").mkdir(parents=True)
    dbg = dp.PipelineDebugger(tmp_path)
    res = dbg._check_failed_iterations()
    assert res["status"] == "warning"
    assert res["failures"] == [
        {
            "iteration": 4,
            "completed_phases": 1,
            "expected_phases": 9,
            "status": "incomplete",
        }
    ]


def test_common_errors_detects_missing_import(tmp_path):
    ws = _healthy_ws(tmp_path)
    (ws / "DMAIC_V3" / "phases" / "phase1_define.py").write_text(
        "def execute():\n    ensure_directory('x')\n", encoding="utf-8"
    )
    dbg = dp.PipelineDebugger(ws)
    res = dbg._check_common_errors()
    assert res["status"] == "error"
    assert res["errors"][0]["file"] == "phase1_define.py"
    assert dbg.issues[0]["severity"] == "critical"


def test_analyze_logs_collects_errors(tmp_path):
    it = tmp_path / "DMAIC_V3_OUTPUT" / "iteration_1" / "phase0_a"
    it.mkdir(parents=True)
    (it / "a.json").write_text('{"error": "boom"}', encoding="utf-8")
    (it / "b.json").write_text('{"success": false, "message": "bad"}', encoding="utf-8")
    (it / "c.json").write_text('{"success": false}', encoding="utf-8")
    (it / "d.json").write_text("[1, 2]", encoding="utf-8")
    (it / "e.json").write_text("{oops", encoding="utf-8")
    (it / "f.json").write_text('{"success": true}', encoding="utf-8")
    res = dp.PipelineDebugger(tmp_path)._analyze_logs()
    assert res["status"] == "warning"
    errs = sorted(e["error"] for e in res["recent_errors"])
    assert errs == ["Unknown failure", "bad", "boom"]


def test_summary_unknown_status_and_many_issues(capsys):
    dbg = dp.PipelineDebugger.__new__(dp.PipelineDebugger)
    issues = [{"severity": "critical", "message": f"c{i}"} for i in range(12)]
    issues += [{"severity": "warning", "message": f"w{i}"} for i in range(12)]
    dbg._print_diagnostic_summary({"status": "odd", "issues": issues, "fixes": []})
    out = capsys.readouterr().out
    assert "Overall Status: ? ODD" in out
    assert "c9" in out and "c10" not in out
    assert "SYSTEM HEALTHY" in out


def test_auto_fix_adds_import_and_creates_files(tmp_path, capsys):
    ws = tmp_path
    phases = ws / "DMAIC_V3" / "phases"
    phases.mkdir(parents=True)
    p1 = phases / "phase1_define.py"
    p1.write_text(
        "from ..core.state import StateManager\nensure_directory('x')\n",
        encoding="utf-8",
    )
    dbg = dp.PipelineDebugger(ws)
    fixes = dbg.auto_fix()
    assert fixes[0] == "Added ensure_directory import to phase1_define.py"
    assert "Created index.json" in fixes
    assert "Created DMAIC_V3_OUTPUT directory" in fixes
    lines = p1.read_text(encoding="utf-8").split("\n")
    assert lines[1] == "from ..core.utils import ensure_directory, safe_write_json"
    data = json.loads((ws / "ranking.json").read_text(encoding="utf-8"))
    assert data == {"ranking_version": "3.3", "total_artifacts": 0}
    assert dbg.auto_fix() == []
    assert "Applied 0 fixes" in capsys.readouterr().out


@pytest.mark.parametrize(
    "setup,argv,code",
    [
        ("healthy", ["--json"], 0),
        ("warning", [], 1),
        ("empty", ["--fix"], 2),
    ],
)
def test_main_exit_codes(tmp_path, monkeypatch, capsys, setup, argv, code):
    ws = tmp_path / "ws"
    ws.mkdir()
    if setup != "empty":
        _healthy_ws(ws)
    if setup == "warning":
        (ws / "ranking.yaml").unlink()
    run_dir = ws / "run"
    run_dir.mkdir()
    monkeypatch.chdir(run_dir)
    monkeypatch.setattr(sys, "argv", ["debug_pipeline.py", *argv])
    with pytest.raises(SystemExit) as exc:
        dp.main()
    assert exc.value.code == code
    out = capsys.readouterr().out
    if "--json" in argv:
        assert '"status": "healthy"' in out
    if "--fix" in argv:
        assert "Re-running diagnostic" in out
