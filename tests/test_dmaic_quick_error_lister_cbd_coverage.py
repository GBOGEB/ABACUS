"""Isolated positive and negative coverage for the legacy DMAIC error lister.

No real pipelines or repository files are modified by these tests.
"""

import importlib.util
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "DMAIC_V3" / "quick_error_lister.py"


def load():
    spec = importlib.util.spec_from_file_location("_cbd_quick_error_lister", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_log_returns_no_unverified_finding(tmp_path):
    assert load().scan_pipeline_log(tmp_path / "absent.log") == []


@pytest.mark.parametrize(
    "marker", ["ERROR", "FAIL", "Exception", "Traceback", "Error:"]
)
def test_runtime_first_red_has_one_based_line(marker, tmp_path):
    path = tmp_path / "pipeline.log"
    path.write_text("preceding\n" + marker + " root\nfollowing\n")
    found = load().scan_pipeline_log(path)
    assert found == [{"line": 2, "message": marker + " root", "type": "runtime"}]


def test_normal_log_never_fabricates_failure(tmp_path):
    path = tmp_path / "quiet.log"
    path.write_text("INFO ready\nno failure present\n")
    assert load().scan_pipeline_log(path) == []


def test_missing_source_directory_returns_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load().scan_python_files() == []


def test_source_scanner_separates_three_findings(tmp_path, monkeypatch):
    (tmp_path / "DMAIC_V3").mkdir()
    (tmp_path / "DMAIC_V3" / "example.py").write_text(
        "a: Dict[str, int] = {}\nb: List[Dict] = []\nroot = config.workspace_root\n"
    )
    monkeypatch.chdir(tmp_path)
    found = load().scan_python_files()
    assert [(row["type"], row["line"]) for row in found] == [
        ("type_hint", 1),
        ("type_hint", 2),
        ("attribute", 3),
    ]


def test_bad_file_read_emits_file_error_not_green(tmp_path, monkeypatch):
    module = load()
    (tmp_path / "DMAIC_V3").mkdir()
    (tmp_path / "DMAIC_V3" / "blocked.py").write_text("x=1\n")
    real_open = open

    def bad_open(path, *args, **kwargs):
        if Path(path).name == "blocked.py":
            raise OSError("deliberately unreadable")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(module, "open", bad_open, raising=False)
    monkeypatch.chdir(tmp_path)
    found = module.scan_python_files()
    assert len(found) == 1 and found[0]["type"] == "file_error"
    assert "deliberately unreadable" in found[0]["message"]


def test_empty_report_preserves_zero_denominator(tmp_path):
    output = tmp_path / "report.md"
    assert load().generate_report([], [], output) == 0
    text = output.read_text()
    assert "Runtime Errors:** 0" in text and "Code Issues:** 0" in text


def test_report_truncation_retains_total_counts(tmp_path):
    output = tmp_path / "report.md"
    errors = [{"line": n, "message": "error " + str(n)} for n in range(1, 23)]
    issues = [
        {"type": "type_hint", "file": "a.py", "line": n, "message": "bad"}
        for n in range(12)
    ]
    assert load().generate_report(errors, issues, output) == 34
    text = output.read_text()
    assert "and 2 more errors" in text
    assert "and 2 more" in text
    assert "Runtime Errors:** 22" in text


def test_main_clean_path_remains_green(tmp_path, monkeypatch):
    module = load()
    (tmp_path / "DMAIC_V3").mkdir()
    monkeypatch.chdir(tmp_path)
    assert module.main() == 0
    assert (tmp_path / "DMAIC_V3" / "ERROR_DETECTION_REPORT.md").exists()


def test_main_with_detected_issue_returns_red(tmp_path, monkeypatch):
    module = load()
    (tmp_path / "DMAIC_V3").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        module,
        "scan_python_files",
        lambda: [
            {"type": "type_hint", "file": "a.py", "line": 1, "message": "bad type"}
        ],
    )
    assert module.main() == 1
    assert (
        "bad type" in (tmp_path / "DMAIC_V3" / "ERROR_DETECTION_REPORT.md").read_text()
    )
