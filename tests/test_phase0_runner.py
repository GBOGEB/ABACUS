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
