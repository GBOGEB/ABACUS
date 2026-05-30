import subprocess
import sys
import json
from pathlib import Path

from src.qplant_presentation_engine import runtime


def test_run_runtime_reports_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    exit_code, report, metadata = runtime.run_runtime()

    assert exit_code == 0
    assert report == [
        "[OK] Runtime Started",
        "[OK] Metrics Loaded",
        "[OK] Truth Matrix Loaded",
        "[OK] Validation Ready",
    ]
    assert metadata["entrypoint"].startswith("python -m ")


def test_run_runtime_reports_failure_when_validation_fails(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
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


def test_top_level_module_entrypoint_executes(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, "-m", "qplant_presentation_engine"],
        cwd=str(tmp_path),
        env={**__import__("os").environ, "PYTHONPATH": str(repo_root)},
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


def test_truth_matrix_includes_ci_execution_principle():
    from src.qplant_presentation_engine.truth_matrix import TRUTH_RULES

    assert "exists_in_repo_is_not_ci_execution" in TRUTH_RULES


def test_runtime_generates_governance_metric_snapshots(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    exit_code, report, _metadata = runtime.run_runtime()

    assert exit_code == 0
    assert all(line.startswith("[OK]") for line in report)

    pca_snapshot = json.loads((tmp_path / "reports" / "pca_snapshot.json").read_text(encoding="utf-8"))
    geti_snapshot = json.loads((tmp_path / "reports" / "geti_snapshot.json").read_text(encoding="utf-8"))
    truth_snapshot = json.loads(
        (tmp_path / "reports" / "truth_matrix_snapshot.json").read_text(encoding="utf-8")
    )

    assert {"forward_pca", "backward_pca", "generated_at"} <= set(pca_snapshot)
    assert {"geti", "truth_score", "generated_at"} <= set(geti_snapshot)
    assert {"principles", "truth_score", "evidence", "generated_at"} <= set(truth_snapshot)
