"""Gap tests for abacus_v21_session_tuple_analyzer.py (reports, metrics, main)."""

import json
import logging
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("abacus_v21_session_tuple_analyzer.py", name="abn_w6_session_tuple_analyzer")
MOD_PATH = mod.__file__

Intent = mod.ConversationIntent
Outcome = mod.ConversationOutcome


class _Result:
    def __init__(self, returncode):
        self.returncode = returncode


def _tuple(num, outcome, intent=None, updates=None):
    return mod.ConversationTuple(
        tuple_number=num,
        timestamp="2026-01-01T00:00:00",
        user_input="input %d" % num,
        user_input_length=7,
        intent=intent or Intent.TESTING,
        outcome=outcome,
        output_created=["out%d.txt" % num],
        next_steps=["step %d" % num],
        recursive_updates=list(updates or []),
    )


@pytest.fixture
def analyzer(tmp_path):
    return mod.SessionTupleAnalyzer(workspace_root=tmp_path)


@pytest.fixture
def pdf_calls(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _Result(1)

    monkeypatch.setattr("subprocess.run", fake_run)
    return calls


def test_track_recursive_updates_skips_unknown_tuples(analyzer, caplog):
    caplog.set_level(logging.INFO)
    analyzer._track_recursive_updates()
    assert len(analyzer.session_metadata.recursive_knowledge_items) == 5
    assert analyzer.conversation_tuples == []
    assert "Total knowledge items tracked: 5" in caplog.text


def test_track_recursive_updates_links_tuples(analyzer):
    analyzer._extract_conversation_tuples()
    analyzer._track_recursive_updates()
    first, second, third = analyzer.conversation_tuples
    assert first.recursive_updates == [
        "migration_test_suite",
        "migration_documentation",
    ]
    assert second.recursive_updates == [
        "deployment_execution",
        "migration_documentation",
        "deployment_reports",
    ]
    assert third.recursive_updates == ["session_analysis"]


def test_metrics_all_success_sets_success(analyzer):
    analyzer.conversation_tuples = [
        _tuple(1, Outcome.SUCCESS),
        _tuple(2, Outcome.SUCCESS),
    ]
    analyzer._calculate_session_metrics()
    assert analyzer.session_metadata.overall_outcome is Outcome.SUCCESS
    assert analyzer.session_metadata.end_time


def test_metrics_with_in_progress(analyzer):
    analyzer.conversation_tuples = [
        _tuple(1, Outcome.SUCCESS),
        _tuple(2, Outcome.IN_PROGRESS),
    ]
    analyzer._calculate_session_metrics()
    assert analyzer.session_metadata.overall_outcome is Outcome.IN_PROGRESS


def test_markdown_report_sections_and_counts(analyzer):
    analyzer.conversation_tuples = [
        _tuple(1, Outcome.SUCCESS, Intent.MIGRATION, updates=["kb_item"]),
        _tuple(2, Outcome.SUCCESS, Intent.MIGRATION),
        _tuple(3, Outcome.BLOCKED, Intent.TESTING),
    ]
    analyzer.recursive_knowledge_base = {
        "kb_item": dict(
            created_in_tuple=1,
            updated_in_tuples=[1, 3],
            current_status="completed",
            files=["f1.py", "f2.py"],
        )
    }
    analyzer.session_metadata.overall_outcome = Outcome.SUCCESS
    analyzer.session_metadata.primary_intent = Intent.MIGRATION
    analyzer.session_metadata.total_user_input_chars = 30
    analyzer.session_metadata.total_output_created = 3
    analyzer._generate_markdown_report()
    text = (analyzer.output_dir / "session_analysis_report.md").read_text(
        encoding="utf-8"
    )
    assert "COMPLETED" in text
    assert "**Primary Intent:** migration" in text
    assert "**Recursive Updates (1):**" in text
    assert text.count("**Recursive Updates") == 1
    assert "- **Updated in Tuples:** 1, 3" in text
    assert "  - `f2.py`" in text
    assert "- **migration**: 2 occurrences (66.7%)" in text
    assert "- **blocked**: 1 occurrences (33.3%)" in text
    assert "| Average User Input Length | 10 chars |" in text
    assert "| Average Files per Tuple | 1.0 |" in text


def test_markdown_report_empty_session(analyzer):
    analyzer._generate_markdown_report()
    text = (analyzer.output_dir / "session_analysis_report.md").read_text(
        encoding="utf-8"
    )
    assert "IN PROGRESS" in text
    assert "**Primary Intent:** N/A" in text
    assert "**Overall Outcome:** N/A" in text
    assert "| Average User Input Length | 0 chars |" in text
    assert "### Tuple" not in text


def test_pdf_report_failure_falls_back_to_markdown(analyzer, pdf_calls, caplog):
    caplog.set_level(logging.INFO)
    analyzer._generate_pdf_report()
    assert pdf_calls[0][0] == "pandoc"
    assert pdf_calls[0][-1] == "--pdf-engine=xelatex"
    assert "PDF generation requires pandoc" in caplog.text


def test_pdf_report_success_when_file_exists(analyzer, monkeypatch, caplog):
    def fake_run(cmd, **kwargs):
        (analyzer.output_dir / "session_analysis_report.pdf").write_bytes(b"%PDF")
        return _Result(0)

    monkeypatch.setattr("subprocess.run", fake_run)
    caplog.set_level(logging.INFO)
    analyzer._generate_pdf_report()
    assert "PDF report:" in caplog.text
    assert "requires pandoc" not in caplog.text


def test_pdf_report_returncode_zero_without_file(analyzer, monkeypatch, caplog):
    monkeypatch.setattr("subprocess.run", lambda cmd, **kw: _Result(0))
    caplog.set_level(logging.INFO)
    analyzer._generate_pdf_report()
    assert "PDF generation requires pandoc" in caplog.text


def test_pdf_report_exception_is_logged(analyzer, monkeypatch, caplog):
    def boom(cmd, **kwargs):
        raise FileNotFoundError("pandoc missing")

    monkeypatch.setattr("subprocess.run", boom)
    caplog.set_level(logging.INFO)
    analyzer._generate_pdf_report()
    assert "PDF generation skipped: pandoc missing" in caplog.text


def test_analyze_session_end_to_end(analyzer, pdf_calls):
    analyzer.analyze_session()
    meta = analyzer.session_metadata
    assert meta.total_tuples == 3
    assert meta.overall_outcome is Outcome.IN_PROGRESS
    assert meta.t0_original_input.startswith("continue with the migration test")
    with open(
        analyzer.output_dir / "session_analysis_report.json", encoding="utf-8"
    ) as fh:
        report = json.load(fh)
    assert report["summary"]["total_tuples"] == 3
    assert report["summary"]["total_files_created"] == 12
    assert report["summary"]["total_recursive_updates"] == 6
    assert (analyzer.output_dir / "session_analysis_report.md").is_file()
    assert len(pdf_calls) == 1


def test_main_uses_cwd(tmp_path, monkeypatch, pdf_calls):
    monkeypatch.chdir(tmp_path)
    assert mod.main() == 0
    assert (
        tmp_path / "ABACUS_SESSION_ANALYSIS" / "session_analysis_report.json"
    ).is_file()


def test_main_entrypoint_exits_zero(tmp_path, monkeypatch, pdf_calls):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(MOD_PATH, run_name="__main__")
    assert excinfo.value.code == 0
    assert (
        tmp_path / "ABACUS_SESSION_ANALYSIS" / "session_analysis_report.md"
    ).is_file()
