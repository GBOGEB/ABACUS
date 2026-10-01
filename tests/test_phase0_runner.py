import json
import subprocess
import sys
from pathlib import Path

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


def test_phase0_smoke_direct_cli_from_repo_root(tmp_path: Path):
    receipt_path = tmp_path / "phase0-smoke.json"
    runner = phase0_runner.ROOT / "scripts" / "runners" / "phase0_runner.py"

    result = subprocess.run(
        [
            sys.executable,
            str(runner),
            "--smoke",
            "--receipt",
            str(receipt_path),
        ],
        cwd=phase0_runner.ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    assert payload["executed_steps"] == 3
