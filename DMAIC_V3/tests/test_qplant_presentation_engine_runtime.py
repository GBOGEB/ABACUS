import subprocess
import sys
from pathlib import Path

from src.qplant_presentation_engine import runtime


def test_run_runtime_reports_success():
    exit_code, report, metadata = runtime.run_runtime()

    assert exit_code == 0
    assert report == [
        "[OK] Runtime Started",
        "[OK] Metrics Loaded",
        "[OK] Truth Matrix Loaded",
        "[OK] Validation Ready",
    ]
    assert metadata["entrypoint"].startswith("python -m ")


def test_run_runtime_reports_failure_when_validation_fails(monkeypatch):
    monkeypatch.setattr(
        runtime,
        "validate_runtime",
        lambda: {
            "package_import": True,
            "runtime_entry": False,
            "metrics_availability": True,
            "truth_matrix_availability": True,
        },
    )

    exit_code, report, _metadata = runtime.run_runtime()

    assert exit_code == 1
    assert report[-1] == "[FAIL] Validation Ready"


def test_top_level_module_entrypoint_executes():
    repo_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, "-m", "qplant_presentation_engine"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout.strip().splitlines() == [
        "[OK] Runtime Started",
        "[OK] Metrics Loaded",
        "[OK] Truth Matrix Loaded",
        "[OK] Validation Ready",
    ]
