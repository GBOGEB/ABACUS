"""Behaviour tests for abacus_v21_smoke_tests.py (gap lines and branches)."""

import json
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("abacus_v21_smoke_tests.py", name="abn_w6_abacus_v21_smoke_tests")

DMAIC_TESTS = [
    "test_phase1_define.py",
    "test_phase2_measure.py",
    "test_phase3_analyze.py",
    "test_phase4_improve.py",
    "test_phase5_control.py",
]


def _tracker(root, data):
    (root / "DOW_IMPLEMENTATION_TRACKER.json").write_text(
        json.dumps(data), encoding="utf-8"
    )


def _full_tree(root):
    for name in (
        "DMAIC_V3",
        "ABACUS_V21_MIGRATION_OUTPUT",
        "ABACUS_V21_DEPLOYMENT_OUTPUT",
        "ABACUS_SESSION_ANALYSIS",
    ):
        (root / name).mkdir(exist_ok=True)
    (root / "ABACUS_V21_PROGRESS_TRACKER.yaml").write_text("x: 1\n", encoding="utf-8")
    _tracker(root, {"meta": {}, "stages": {"a": 1, "b": 2}})
    tests_dir = root / "DMAIC_V3" / "tests"
    tests_dir.mkdir()
    for name in DMAIC_TESTS:
        (tests_dir / name).write_text("", encoding="utf-8")
    (root / "DMAIC_V3_IMPLEMENTATION_STATUS.md").write_text("ok", encoding="utf-8")
    (root / "ABACUS_V21_MIGRATION_OUTPUT" / "notes.md").write_text(
        "m", encoding="utf-8"
    )
    (root / "ABACUS_SESSION_ANALYSIS" / "notes.md").write_text("s", encoding="utf-8")


@pytest.fixture
def suite(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return mod.ABACUSv21SmokeTests()


def test_init_creates_output_dir_and_log_format(suite, tmp_path, capsys):
    assert (tmp_path / "ABACUS_V21_SMOKE_TEST_OUTPUT").is_dir()
    assert suite.passed == 0 and suite.failed == 0 and suite.results == []
    suite.log("hello", "WARN")
    out = capsys.readouterr().out
    assert "[WARN] hello" in out


def test_basic_import_fails_when_dirs_missing(suite):
    assert suite.test_smoke_basic_import() is False
    rec = suite.results[-1]
    assert rec["status"] == "FAIL"
    assert "Missing critical directories" in rec["message"]
    assert "DMAIC_V3" in rec["message"]
    assert suite.failed == 1


def test_basic_import_passes_when_dirs_present(suite, tmp_path):
    _full_tree(tmp_path)
    assert suite.test_smoke_basic_import() is True
    assert suite.results[-1]["test_id"] == "1.3.1"
    assert suite.results[-1]["status"] == "PASS"
    assert suite.passed == 1


def test_config_load_missing_yaml(suite):
    assert suite.test_smoke_config_load() is False
    assert "Progress tracker not found" in suite.results[-1]["message"]


def test_config_load_missing_json(suite, tmp_path):
    (tmp_path / "ABACUS_V21_PROGRESS_TRACKER.yaml").write_text("", encoding="utf-8")
    assert suite.test_smoke_config_load() is False
    assert "DOW tracker not found" in suite.results[-1]["message"]


def test_config_load_missing_keys(suite, tmp_path):
    (tmp_path / "ABACUS_V21_PROGRESS_TRACKER.yaml").write_text("", encoding="utf-8")
    _tracker(tmp_path, {"meta": {}})
    assert suite.test_smoke_config_load() is False
    assert "['stages']" in suite.results[-1]["message"]


def test_config_load_passes(suite, tmp_path):
    _full_tree(tmp_path)
    assert suite.test_smoke_config_load() is True
    rec = suite.results[-1]
    assert rec["status"] == "PASS"
    assert "DOW_IMPLEMENTATION_TRACKER.json" in rec["files_validated"]


def test_dow_integration_missing_tracker(suite):
    assert suite.test_smoke_dow_integration() is False
    assert suite.results[-1]["message"] == "DOW tracker not found"


def test_dow_integration_missing_stages(suite, tmp_path):
    _tracker(tmp_path, {"meta": {}})
    assert suite.test_smoke_dow_integration() is False
    assert "Missing 'stages'" in suite.results[-1]["message"]


def test_dow_integration_passes_and_counts_stages(suite, tmp_path):
    _tracker(tmp_path, {"stages": [1, 2, 3]})
    assert suite.test_smoke_dow_integration() is True
    rec = suite.results[-1]
    assert rec["stages_found"] == 3
    assert rec["dow_components"]["workflows"] == 8


def test_dmaic_engine_missing_dir(suite):
    assert suite.test_smoke_dmaic_engine() is False
    assert suite.results[-1]["message"] == "DMAIC_V3 directory not found"


def test_dmaic_engine_warns_then_fails_without_status(suite, tmp_path, capsys):
    (tmp_path / "DMAIC_V3").mkdir()
    assert suite.test_smoke_dmaic_engine() is False
    out = capsys.readouterr().out
    assert "Missing DMAIC test files" in out
    assert "status not found" in suite.results[-1]["message"]


def test_dmaic_engine_passes_with_all_files(suite, tmp_path, capsys):
    _full_tree(tmp_path)
    assert suite.test_smoke_dmaic_engine() is True
    rec = suite.results[-1]
    assert rec["test_files_found"] == 5
    assert rec["test_files_expected"] == 5
    assert "Missing DMAIC test files" not in capsys.readouterr().out


def test_recursive_engine_creates_dir_and_fails_without_artifacts(suite, tmp_path):
    assert suite.test_smoke_recursive_engine() is False
    assert (tmp_path / "ABACUS_V21_MIGRATION_OUTPUT").is_dir()
    assert suite.results[-1]["message"] == "No migration artifacts found"


def test_recursive_engine_structure_pass(suite, tmp_path):
    out_dir = tmp_path / "ABACUS_V21_MIGRATION_OUTPUT"
    out_dir.mkdir()
    (out_dir / "a.md").write_text("a", encoding="utf-8")
    (out_dir / "b.md").write_text("b", encoding="utf-8")
    assert suite.test_smoke_recursive_engine() is True
    rec = suite.results[-1]
    assert rec["migration_artifacts"] == 2
    assert "report pending" in rec["message"]


def _migration_report(root, data):
    out_dir = root / "ABACUS_V21_MIGRATION_OUTPUT"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "abacus_v21_migration_test_report.json").write_text(
        json.dumps(data), encoding="utf-8"
    )


def test_recursive_engine_report_without_knowledge(suite, tmp_path):
    _migration_report(tmp_path, {})
    assert suite.test_smoke_recursive_engine() is False
    assert "knowledge_preservation" in suite.results[-1]["message"]


def test_recursive_engine_report_with_loss(suite, tmp_path):
    _migration_report(tmp_path, {"knowledge_preservation": {"artifacts_lost": 2}})
    assert suite.test_smoke_recursive_engine() is False
    assert "2 artifacts lost" in suite.results[-1]["message"]


def test_recursive_engine_report_missing_lost_defaults_to_loss(suite, tmp_path):
    _migration_report(tmp_path, {"knowledge_preservation": {}})
    assert suite.test_smoke_recursive_engine() is False
    assert suite.results[-1]["status"] == "FAIL"


def test_recursive_engine_report_preserved(suite, tmp_path):
    _migration_report(
        tmp_path,
        {"knowledge_preservation": {"artifacts_lost": 0, "artifacts_preserved": 7}},
    )
    assert suite.test_smoke_recursive_engine() is True
    rec = suite.results[-1]
    assert rec["artifacts_preserved"] == 7
    assert rec["artifacts_lost"] == 0


def _analysis_report(root, data):
    out_dir = root / "ABACUS_SESSION_ANALYSIS"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "session_analysis_report.json").write_text(
        json.dumps(data), encoding="utf-8"
    )


def test_temporal_engine_creates_dir_and_fails_without_artifacts(suite, tmp_path):
    assert suite.test_smoke_temporal_engine() is False
    assert (tmp_path / "ABACUS_SESSION_ANALYSIS").is_dir()
    assert suite.results[-1]["message"] == "No session analysis artifacts found"


def test_temporal_engine_structure_pass(suite, tmp_path):
    out_dir = tmp_path / "ABACUS_SESSION_ANALYSIS"
    out_dir.mkdir()
    (out_dir / "a.md").write_text("a", encoding="utf-8")
    assert suite.test_smoke_temporal_engine() is True
    assert suite.results[-1]["analysis_artifacts"] == 1


def test_temporal_engine_report_without_tuples(suite, tmp_path):
    _analysis_report(tmp_path, {})
    assert suite.test_smoke_temporal_engine() is False
    assert "conversation_tuples" in suite.results[-1]["message"]


def test_temporal_engine_report_with_empty_tuples(suite, tmp_path):
    _analysis_report(tmp_path, {"conversation_tuples": []})
    assert suite.test_smoke_temporal_engine() is False
    assert suite.results[-1]["message"] == "No conversation tuples found"


def test_temporal_engine_report_valid(suite, tmp_path):
    _analysis_report(
        tmp_path,
        {"conversation_tuples": [1, 2], "recursive_knowledge": ["k"]},
    )
    assert suite.test_smoke_temporal_engine() is True
    rec = suite.results[-1]
    assert rec["conversation_tuples"] == 2
    assert rec["recursive_knowledge_items"] == 1


def test_run_all_tests_all_pass_writes_reports(suite, tmp_path, capsys):
    _full_tree(tmp_path)
    assert suite.run_all_tests() is True
    out_dir = tmp_path / "ABACUS_V21_SMOKE_TEST_OUTPUT"
    data = json.loads(
        (out_dir / "abacus_v21_smoke_test_report.json").read_text(encoding="utf-8")
    )
    assert data["summary"]["total_tests"] == 6
    assert data["summary"]["pass_rate"] == 100
    assert data["summary"]["status"] == "PASS"
    md = (out_dir / "abacus_v21_smoke_test_report.md").read_text(encoding="utf-8")
    assert "**Status:** PASS" in md
    assert "test_smoke_temporal_engine" in md
    assert "ALL TESTS PASSED" in capsys.readouterr().out


def test_run_all_tests_failures_reported(suite, tmp_path, capsys):
    assert suite.run_all_tests() is False
    out_dir = tmp_path / "ABACUS_V21_SMOKE_TEST_OUTPUT"
    data = json.loads(
        (out_dir / "abacus_v21_smoke_test_report.json").read_text(encoding="utf-8")
    )
    assert data["summary"]["status"] == "FAIL"
    assert data["summary"]["failed"] == 6
    md = (out_dir / "abacus_v21_smoke_test_report.md").read_text(encoding="utf-8")
    assert "**Status:** FAIL" in md
    assert "SOME TESTS FAILED" in capsys.readouterr().out


def test_main_block_exits_nonzero_on_empty_tree(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(mod.__file__, run_name="__main__")
    assert exc.value.code == 1
    assert "SMOKE TEST SUMMARY" in capsys.readouterr().out


def test_main_block_exits_zero_on_full_tree(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _full_tree(tmp_path)
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(mod.__file__, run_name="__main__")
    assert exc.value.code == 0
