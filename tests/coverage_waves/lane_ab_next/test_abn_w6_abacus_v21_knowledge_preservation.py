"""Gap tests for abacus_v21_knowledge_preservation.py (failure paths, summary)."""

import json
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("abacus_v21_knowledge_preservation.py", name="abn_w6_knowledge_preservation")
MOD_PATH = mod.__file__

GENERATORS = [
    ("generate_knowledge_index", "1.6.1"),
    ("generate_changelog", "1.6.2"),
    ("generate_migration_guide", "1.6.3"),
    ("generate_system_documentation", "1.6.4"),
]


@pytest.fixture
def suite(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return mod.KnowledgePreservationSuite()


@pytest.mark.parametrize("method,test_id", GENERATORS)
def test_generator_success_records_pass(suite, method, test_id, capsys):
    assert getattr(suite, method)() is True
    entry = suite.results[-1]
    assert entry["test_id"] == test_id
    assert entry["status"] == "PASS"
    assert suite.passed == 1
    assert suite.failed == 0
    with open(entry["output_file"], encoding="utf-8") as fh:
        assert fh.read().strip()
    assert "[SUCCESS]" in capsys.readouterr().out


@pytest.mark.parametrize("method,test_id", GENERATORS)
def test_generator_failure_records_fail(suite, tmp_path, method, test_id, capsys):
    suite.output_dir = tmp_path / "missing" / "nested"
    assert getattr(suite, method)() is False
    entry = suite.results[-1]
    assert entry["test_id"] == test_id
    assert entry["status"] == "FAIL"
    assert entry["message"]
    assert suite.failed == 1
    assert suite.passed == 0
    assert "[ERROR]" in capsys.readouterr().out


def test_log_unknown_level_uses_default_colour(suite, capsys):
    suite.log("hello", "ODD")
    out = capsys.readouterr().out
    assert "[ODD]" in out
    assert "hello" in out


def test_run_all_tests_success_writes_report(suite, capsys):
    assert suite.run_all_tests() is True
    out = capsys.readouterr().out
    assert "ALL KNOWLEDGE PRESERVED" in out
    report_path = suite.output_dir / "abacus_v21_knowledge_preservation_report.json"
    with open(report_path, encoding="utf-8") as fh:
        report = json.load(fh)
    summary = report["summary"]
    assert summary["total_tasks"] == 4
    assert summary["completed"] == 4
    assert summary["success_rate"] == 100.0
    assert summary["status"] == "COMPLETE"
    assert len(report["artifacts"]) == 4


def test_run_all_tests_with_failure_reports_incomplete(suite, monkeypatch, capsys):
    def broken():
        suite.failed += 1
        return False

    monkeypatch.setattr(suite, "generate_changelog", broken)
    assert suite.run_all_tests() is False
    out = capsys.readouterr().out
    assert "SOME TASKS FAILED" in out
    assert "Failed: 1" in out
    report_path = suite.output_dir / "abacus_v21_knowledge_preservation_report.json"
    with open(report_path, encoding="utf-8") as fh:
        summary = json.load(fh)["summary"]
    assert summary["status"] == "INCOMPLETE"
    assert summary["success_rate"] == 75.0


def test_run_all_tests_with_no_tasks_has_zero_rate(suite, monkeypatch):
    for name, _ in GENERATORS:
        monkeypatch.setattr(suite, name, lambda: None)
    assert suite.run_all_tests() is True
    report_path = suite.output_dir / "abacus_v21_knowledge_preservation_report.json"
    with open(report_path, encoding="utf-8") as fh:
        summary = json.load(fh)["summary"]
    assert summary["total_tasks"] == 0
    assert summary["success_rate"] == 0


def test_main_entrypoint_exits_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(MOD_PATH, run_name="__main__")
    assert excinfo.value.code == 0
    assert "KNOWLEDGE PRESERVATION SUMMARY" in capsys.readouterr().out
