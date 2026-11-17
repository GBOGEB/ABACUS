"""Wave 12 lane A behaviour tests for DMAIC_V3/generators/execution_tracker.py."""

import json
from types import SimpleNamespace

import pytest
import yaml

from DMAIC_V3.generators import execution_tracker as et


class FakeMetrics:
    def __init__(self):
        self.calls = []

    def record_counter(self, name, value):
        self.calls.append(("counter", name, value))

    def record_histogram(self, name, value, unit):
        self.calls.append(("histogram", name, unit))

    def record_gauge(self, name, value, unit):
        self.calls.append(("gauge", name, value))


def _fake_run(returncode=0, stdout="out", stderr=""):
    def run(cmd, **kwargs):
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)

    return run


@pytest.fixture
def tracker(tmp_path):
    return et.ExecutionTracker(output_dir=tmp_path / "out", timeout=5)


PY_SRC = (
    "import os\n"
    "import os\n"
    "from json import dumps\n"
    "from . import x\n"
    "# comment\n"
    "\n"
    "class A:\n"
    "    def f(self):\n"
    "        return 1\n"
    "def g():\n"
    "    pass\n"
)


def test_execution_result_to_dict_with_and_without_error():
    ok = et.ExecutionResult("a.py", "python", et.ExecutionStatus.SUCCESS, 0.1)
    d = ok.to_dict()
    assert d["status"] == "SUCCESS"
    assert d["error_type"] is None
    assert ok.timestamp
    bad = et.ExecutionResult(
        "a.py",
        "python",
        et.ExecutionStatus.FAILED,
        0.1,
        error_type=et.ErrorType.NAME_ERROR,
        timestamp="fixed",
    )
    d2 = bad.to_dict()
    assert d2["error_type"] == "NameError"
    assert d2["timestamp"] == "fixed"


def test_statistics_defaults_and_to_dict():
    s = et.ExecutionStatistics()
    assert s.error_breakdown == {}
    assert s.victory_conditions_met == {}
    s2 = et.ExecutionStatistics(error_breakdown={"X": 1}, victory_conditions_met={})
    assert s2.to_dict()["error_breakdown"] == {"X": 1}


def test_execute_python_success_counts_ast_and_metrics(tmp_path, monkeypatch):
    f = tmp_path / "mod.py"
    f.write_text(PY_SRC, encoding="utf-8")
    metrics = FakeMetrics()
    tr = et.ExecutionTracker(tmp_path / "o", metrics_tracker=metrics)
    monkeypatch.setattr(et.subprocess, "run", _fake_run(0, "hello", ""))
    r = tr.execute_python_file(f)
    assert r.status == et.ExecutionStatus.SUCCESS
    assert r.functions_count == 2
    assert r.classes_count == 1
    assert r.imports_count == 3  # os, json, '' (relative import)
    assert r.lines_of_code == 9
    assert r.stdout == "hello"
    assert r.exit_code == 0
    kinds = [c[0] for c in metrics.calls]
    assert kinds == ["counter", "histogram", "gauge"]


def test_execute_python_failure_classifies_stderr(tmp_path, tracker, monkeypatch):
    f = tmp_path / "bad.py"
    f.write_text("x = 1\n", encoding="utf-8")
    err = "Traceback\nModuleNotFoundError: No module named zz\n"
    monkeypatch.setattr(et.subprocess, "run", _fake_run(1, "", err))
    r = tracker.execute_python_file(f)
    assert r.status == et.ExecutionStatus.FAILED
    assert r.error_type == et.ErrorType.IMPORT_ERROR
    assert r.error_message == err
    assert r.exit_code == 1


def test_execute_python_timeout(tmp_path, tracker, monkeypatch):
    f = tmp_path / "slow.py"
    f.write_text("x = 1\n", encoding="utf-8")

    def run(cmd, **kwargs):
        raise et.subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    monkeypatch.setattr(et.subprocess, "run", run)
    r = tracker.execute_python_file(f)
    assert r.status == et.ExecutionStatus.TIMEOUT
    assert r.error_type == et.ErrorType.TIMEOUT_ERROR
    assert "5 seconds" in r.error_message


def test_execute_python_syntax_error_is_caught_before_run(tmp_path, tracker):
    f = tmp_path / "syn.py"
    f.write_text("def (:\n", encoding="utf-8")
    r = tracker.execute_python_file(f)
    assert r.status == et.ExecutionStatus.FAILED
    assert r.error_type == et.ErrorType.SYNTAX_ERROR
    assert "SyntaxError" in r.error_traceback


def test_execute_python_missing_file_generic_exception(tmp_path, tracker):
    r = tracker.execute_python_file(tmp_path / "nope.py")
    assert r.status == et.ExecutionStatus.FAILED
    assert r.error_type == et.ErrorType.FILE_NOT_FOUND
    assert r.error_traceback


def test_validate_vba_success_with_metrics(tmp_path):
    f = tmp_path / "ok.bas"
    f.write_text("' comment\nPublic Sub Foo()\n  x = 1\nEnd Sub\n", encoding="utf-8")
    metrics = FakeMetrics()
    tr = et.ExecutionTracker(tmp_path / "o", metrics_tracker=metrics)
    r = tr.validate_vba_file(f)
    assert r.status == et.ExecutionStatus.SUCCESS
    assert r.file_type == "vba"
    assert r.functions_count == 1
    assert r.lines_of_code == 3
    assert [c[1] for c in metrics.calls] == [
        "vba_files_validated",
        "vba_validation_time",
        "vba_lines_of_code",
    ]


def test_validate_vba_mismatched_blocks(tmp_path, tracker):
    f = tmp_path / "bad.bas"
    f.write_text(
        "Sub A()\nSub B()\nEnd Sub\nFunction C()\nFunction D()\nEnd Function\n",
        encoding="utf-8",
    )
    r = tracker.validate_vba_file(f)
    assert r.status == et.ExecutionStatus.FAILED
    assert r.error_type == et.ErrorType.VBA_SYNTAX_ERROR
    assert "Mismatched Sub/End Sub" in r.error_message
    assert "Mismatched Function/End Function" in r.error_message


def test_validate_vba_unreadable_path(tmp_path, tracker):
    r = tracker.validate_vba_file(tmp_path)  # a directory cannot be opened
    assert r.status == et.ExecutionStatus.FAILED
    assert r.error_type == et.ErrorType.VBA_VALIDATION_ERROR


@pytest.mark.parametrize(
    "msg,expected",
    [
        ("invalid syntax here", "SYNTAX_ERROR"),
        ("ImportError: x", "IMPORT_ERROR"),
        ("TypeError: bad", "TYPE_ERROR"),
        ("ValueError: bad", "VALUE_ERROR"),
        ("AttributeError: no", "ATTRIBUTE_ERROR"),
        ("NameError: q", "NAME_ERROR"),
        ("No such file or directory", "FILE_NOT_FOUND"),
        ("Permission denied", "PERMISSION_ERROR"),
        ("operation timeout", "TIMEOUT_ERROR"),
        ("something weird", "UNKNOWN_ERROR"),
    ],
)
def test_classify_error(tracker, msg, expected):
    assert tracker._classify_error(msg) == et.ErrorType[expected]


def test_scan_and_execute_aggregates_all_statuses(tmp_path, tracker, monkeypatch):
    root = tmp_path / "src"
    root.mkdir()
    for name in ("a.py", "b.py", "c.py", "d.py"):
        (root / name).write_text("x = 1\n", encoding="utf-8")
    (root / "e.bas").write_text("Sub A()\nEnd Sub\n", encoding="utf-8")
    (root / "notes.txt").write_text("hi", encoding="utf-8")
    (root / "sub.py").mkdir()  # directory matching the glob is filtered out

    outcomes = {
        "a.py": et.ExecutionStatus.SUCCESS,
        "b.py": et.ExecutionStatus.FAILED,
        "c.py": et.ExecutionStatus.TIMEOUT,
        "d.py": et.ExecutionStatus.SKIPPED,
    }

    def fake_exec(path):
        status = outcomes[path.name]
        err = None
        if status == et.ExecutionStatus.TIMEOUT:
            err = et.ErrorType.TIMEOUT_ERROR
        return et.ExecutionResult(
            str(path), "python", status, 0.5, error_type=err, lines_of_code=2
        )

    monkeypatch.setattr(tracker, "execute_python_file", fake_exec)
    stats = tracker.scan_and_execute(root, patterns=["*.py", "*.bas", "*.txt"])
    assert stats.total_files == 6
    assert stats.python_files == 4
    assert stats.vba_files == 1
    assert stats.successful_executions == 2
    assert stats.failed_executions == 1
    assert stats.timeout_executions == 1
    assert stats.skipped_executions == 1
    assert stats.error_breakdown == {"TimeoutError": 1}
    assert stats.total_execution_time > 0
    assert stats.average_execution_time == pytest.approx(stats.total_execution_time / 6)
    vc = stats.victory_conditions_met
    assert vc["python_execution"] is False
    assert vc["vba_validation"] is True
    assert vc["statistics_tracking"] is True
    assert vc["report_generation"] is False


def test_scan_failed_without_error_type_prints_unknown(
    tmp_path, tracker, monkeypatch, capsys
):
    root = tmp_path / "src"
    root.mkdir()
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")

    def fake_exec(path):
        return et.ExecutionResult(str(path), "python", et.ExecutionStatus.FAILED, 0.0)

    monkeypatch.setattr(tracker, "execute_python_file", fake_exec)
    tracker.scan_and_execute(root)
    assert "FAILED (Unknown)" in capsys.readouterr().out


def test_scan_empty_dir_keeps_zero_average(tmp_path, tracker):
    stats = tracker.scan_and_execute(tmp_path / "out")
    assert stats.total_files == 0
    assert stats.average_execution_time == 0.0
    assert stats.victory_conditions_met["python_execution"] is False
    assert stats.victory_conditions_met["statistics_tracking"] is False


def _populate(tracker):
    tracker.execution_results = [
        et.ExecutionResult("a.py", "python", et.ExecutionStatus.SUCCESS, 0.1),
        et.ExecutionResult(
            "b.py",
            "python",
            et.ExecutionStatus.FAILED,
            0.2,
            error_type=et.ErrorType.TYPE_ERROR,
            error_message="boom",
        ),
    ]
    tracker.statistics.total_files = 2
    tracker.statistics.python_files = 2
    tracker.statistics.successful_executions = 1
    tracker.statistics.failed_executions = 1
    tracker.statistics.error_breakdown = {"TypeError": 1, "NameError": 3}
    tracker.statistics.victory_conditions_met = tracker._check_victory_conditions()


def test_export_json_yaml_markdown(tracker):
    _populate(tracker)
    jpath = tracker.export_json()
    data = json.loads(jpath.read_text(encoding="utf-8"))
    assert data["metadata"]["version"] == "3.1.0"
    assert len(data["execution_results"]) == 2
    assert tracker.statistics.victory_conditions_met["report_generation"] is True

    ypath = tracker.export_yaml("r.yaml")
    ydata = yaml.safe_load(ypath.read_text(encoding="utf-8"))
    assert ydata["statistics"]["total_files"] == 2

    mpath = tracker.export_markdown()
    md = mpath.read_text(encoding="utf-8")
    assert "**Success Rate**: 50.0%" in md
    assert "## Error Breakdown" in md
    assert md.index("NameError") < md.index("TypeError")
    assert "### [FAIL] b.py" in md
    assert "`boom`" in md
    assert "Report Generation**: [OK] MET" in md


def test_export_markdown_empty_has_no_error_section(tracker):
    md = tracker.export_markdown("E.md").read_text(encoding="utf-8")
    assert "**Success Rate**: 0.0%" in md
    assert "Error Breakdown" not in md


def test_print_summary(tracker, capsys):
    _populate(tracker)
    tracker.print_summary()
    out = capsys.readouterr().out
    assert "Success Rate:       50.0%" in out
    assert "NOT MET" in out


def test_print_summary_empty(tracker, capsys):
    tracker.print_summary()
    assert "Success Rate:       0.0%" in capsys.readouterr().out


def check_production_defect_vba_end_sub_counted_as_function(tmp_path, tracker):
    # Pins a production_defect (execution_tracker.py:279): the Sub/Function regex
    # lets \s+ span the newline after "End Sub", so the first word of the next
    # line is counted as a procedure. Two procedures report three. This check
    # fails once the regex is fixed.
    f = tmp_path / "two.bas"
    f.write_text(
        "Public Sub Foo()\nEnd Sub\nPrivate Function Bar()\nEnd Function\n",
        encoding="utf-8",
    )
    r = tracker.validate_vba_file(f)
    assert r.status == et.ExecutionStatus.SUCCESS
    assert r.functions_count == 3
