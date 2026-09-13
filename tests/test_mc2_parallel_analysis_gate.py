import json
import subprocess
import sys
from pathlib import Path

TELEMETRY_TOOL = Path("tools/mc2_federated_telemetry.py")
PA_TOOL = Path("tools/mc2_parallel_analysis_gate.py")
SEED = Path("fixtures/mc2_federated_telemetry_seed_v0.1.json")


def test_runtime_pa95_retains_pc1_only_and_keeps_authority_withheld(tmp_path):
    telemetry = tmp_path / "telemetry.json"
    first = subprocess.run(
        [sys.executable, str(TELEMETRY_TOOL), str(SEED), "--out", str(telemetry)],
        capture_output=True,
        text=True,
    )
    assert first.returncode == 0, first.stderr

    out = tmp_path / "pa95.json"
    second = subprocess.run(
        [
            sys.executable,
            str(PA_TOOL),
            str(telemetry),
            "--out",
            str(out),
            "--simulations",
            "2000",
            "--seed",
            "20260913",
        ],
        capture_output=True,
        text=True,
    )
    assert second.returncode == 0, second.stderr
    receipt = json.loads(out.read_text())
    assert receipt["status"] == "PA95_DIAGNOSTIC"
    assert receipt["retained_pcs"] == [1]
    assert receipt["retained_component_count"] == 1
    assert receipt["pc2_diagnostic_not_retained"] is True
    assert receipt["small_sample_warning"] is True
    assert receipt["allocation_authority"] is False
    assert receipt["child_engineering_promotion_authority"] is False
    assert receipt["bt_status"] == "WITHHELD_NO_OBSERVED_PAIRWISE_EVIDENCE"


def test_pa95_is_deterministic_for_fixed_seed(tmp_path):
    telemetry = tmp_path / "telemetry.json"
    first = subprocess.run(
        [sys.executable, str(TELEMETRY_TOOL), str(SEED), "--out", str(telemetry)],
        capture_output=True,
        text=True,
    )
    assert first.returncode == 0, first.stderr

    outputs = []
    for index in range(2):
        out = tmp_path / f"pa95-{index}.json"
        result = subprocess.run(
            [sys.executable, str(PA_TOOL), str(telemetry), "--out", str(out)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        outputs.append(json.loads(out.read_text()))
    assert outputs[0] == outputs[1]


def test_pa95_rejects_too_few_simulations(tmp_path):
    telemetry = tmp_path / "telemetry.json"
    first = subprocess.run(
        [sys.executable, str(TELEMETRY_TOOL), str(SEED), "--out", str(telemetry)],
        capture_output=True,
        text=True,
    )
    assert first.returncode == 0, first.stderr

    out = tmp_path / "pa95.json"
    result = subprocess.run(
        [
            sys.executable,
            str(PA_TOOL),
            str(telemetry),
            "--out",
            str(out),
            "--simulations",
            "100",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "at least 500 simulations required" in result.stderr
