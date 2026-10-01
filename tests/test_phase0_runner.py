import json
from pathlib import Path
import subprocess
import sys

from scripts.runners import phase0_runner


def test_phase0_smoke_executes_real_nonmutating_steps(tmp_path: Path):
    receipt = phase0_runner.run_smoke(phase0_runner.ROOT, tmp_path)

    assert receipt["status"] == "PASS"
    assert receipt["executed_steps"] == 3
    assert [step["name"] for step in receipt["steps"]] == [
        "phase0_environment",
        "phase0_canonical_files",
        "phase0_change_detection",
    ]
    assert all(step["status"] == "PASS" for step in receipt["steps"])
    assert receipt["authority_transfer"] is False
    assert receipt["formal_credit_delta"] == 0
    assert receipt["engineering_credit_delta"] == 0


def test_phase0_runner_executes_directly_like_ci(tmp_path: Path):
    receipt_path = tmp_path / "phase0-smoke.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(phase0_runner.ROOT / "scripts" / "runners" / "phase0_runner.py"),
            "--smoke",
            "--scratch",
            str(tmp_path / "scratch"),
            "--receipt",
            str(receipt_path),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["status"] == "PASS"
    assert receipt["executed_steps"] == 3
