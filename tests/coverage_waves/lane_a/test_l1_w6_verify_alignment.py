"""Behaviour tests for ABACUS-v032/verify_alignment.py."""

import json

from tests.coverage_waves.lane_a._load import load

va = load("ABACUS-v032/verify_alignment.py")

V033_NAME = "execute_full_dmaic_phases_0_to_9_v033.py"
FULL_MARKERS = "\n".join(
    [
        "SPRINT TESTED | DOW TESTED | CANONICAL ALIGNED",
        "Version History:",
        "    sprint_tested: bool = False",
        "    dow_tested: bool = False",
    ]
)
GOOD_CONFIG = {
    "version": "v033",
    "phases": ["Phase 8", "Phase 9"],
    "sprint_tested": True,
    "dow_tested": True,
    "canonical_aligned": True,
    "abacus_engines": {"v033": "engine.py"},
}
PLAIN_FILES = [
    "test_sprint_readiness.py",
    "test_dow_phases.py",
    "dow_integration_module.py",
    "CANONICAL_ALIGNMENT_v032_v033.md",
    "ALIGNMENT_SUMMARY.md",
    "SPRINT_READINESS_REPORT_20251117.json",
    "DOW_PHASE_TEST_REPORT_20251117.json",
    "deploy.py",
    "docker-compose.yml",
    "Dockerfile",
    "requirements.txt",
]
DIRS = ["STATS", "logs", "output", "pipeline_output"]


def _point_at(monkeypatch, ws):
    monkeypatch.setattr(va, "__file__", str(ws / "verify_alignment.py"))


def _populate(ws, markers=FULL_MARKERS, config=None):
    (ws / V033_NAME).write_bytes(markers.encode("utf-8"))
    cfg = GOOD_CONFIG if config is None else config
    (ws / "sprint_config.json").write_bytes(json.dumps(cfg).encode("utf-8"))
    for name in PLAIN_FILES:
        (ws / name).write_bytes(b"x")
    for name in DIRS:
        (ws / name).mkdir()


def test_all_checks_pass_returns_zero(monkeypatch, tmp_path, capsys):
    _populate(tmp_path)
    _point_at(monkeypatch, tmp_path)
    assert va.verify_alignment() == 0
    out = capsys.readouterr().out
    assert "Total Checks: 29" in out
    assert "Passed: 29" in out
    assert "Failed: 0" in out
    assert "Success Rate: 100.0%" in out
    assert "ALIGNMENT VERIFIED" in out
    assert "PRODUCTION READY" in out
    assert "Sprint test report (1 found)" in out


def test_empty_workspace_reports_every_failure(monkeypatch, tmp_path, capsys):
    _point_at(monkeypatch, tmp_path)
    assert va.verify_alignment() == 1
    out = capsys.readouterr().out
    # 1 + 1 + 2 + 1 + 1 + 1 + 1 + 1 + 4 + 4 checks, none passing
    assert "Total Checks: 17" in out
    assert "Passed: 0" in out
    assert "Success Rate: 0.0%" in out
    assert "ALIGNMENT INCOMPLETE - 17 check(s) failed" in out
    assert "File not found" in out
    assert "v033 file exists" in out
    assert "sprint_config.json exists" in out
    assert "pipeline_output/ exists" in out
    assert "(0 found)" in out


def test_markers_and_config_flags_missing(monkeypatch, tmp_path, capsys):
    bad_config = {
        "version": "v032",
        "phases": ["Phase 1"],
        "sprint_tested": False,
        "abacus_engines": {"v032": "old.py"},
    }
    _populate(tmp_path, markers="nothing relevant here", config=bad_config)
    _point_at(monkeypatch, tmp_path)
    assert va.verify_alignment() == 1
    out = capsys.readouterr().out
    assert "Total Checks: 29" in out
    # 6 marker checks + 6 config checks fail
    assert "Failed: 12" in out
    assert "Passed: 17" in out
    assert "Success Rate: 58.6%" in out
    for name in [
        "SPRINT TESTED marker",
        "DOW TESTED marker",
        "CANONICAL ALIGNED marker",
        "Version history",
        "sprint_tested field",
        "dow_tested field",
        "Version is v033",
        "Phase 9 included",
        "sprint_tested flag",
        "dow_tested flag",
        "canonical_aligned flag",
        "v033 engine reference",
    ]:
        assert name in out


def test_partial_deploy_files_counted(monkeypatch, tmp_path, capsys):
    _populate(tmp_path)
    (tmp_path / "Dockerfile").unlink()
    (tmp_path / "STATS").rmdir()
    _point_at(monkeypatch, tmp_path)
    assert va.verify_alignment() == 1
    out = capsys.readouterr().out
    assert "Failed: 2" in out
    assert "Dockerfile exists" in out
    assert "STATS/ exists" in out
