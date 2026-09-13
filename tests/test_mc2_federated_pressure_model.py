import json
import subprocess
import sys
from pathlib import Path


TOOL = Path("tools/mc2_federated_pressure_model.py")


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def run_model(tmp_path: Path, semantic_retained: bool):
    runtime_t = tmp_path / "runtime.json"
    runtime_pa = tmp_path / "runtime_pa.json"
    semantic_t = tmp_path / "semantic.json"
    semantic_pa = tmp_path / "semantic_pa.json"
    out = tmp_path / "out.json"
    write(
        runtime_t,
        {
            "runtime_pca": {
                "status": "MEASURED_PCA_DIAGNOSTIC",
                "numeric_comparable_rows": 5,
                "components": [
                    {
                        "pc": 1,
                        "eigenvalue": 3.0,
                        "explained_variance_ratio": 0.75,
                        "loadings": {"steps": 0.9},
                    }
                ],
            }
        },
    )
    write(runtime_pa, {"status": "PA95_DIAGNOSTIC", "retained_pcs": [1]})
    write(
        semantic_t,
        {
            "semantic_pca": {
                "status": "MEASURED_PCA_DIAGNOSTIC",
                "numeric_comparable_rows": 5,
                "components": [
                    {
                        "pc": 1,
                        "eigenvalue": 2.5,
                        "explained_variance_ratio": 0.83,
                        "loadings": {"coverage": 0.8},
                    }
                ],
            }
        },
    )
    write(
        semantic_pa,
        {
            "status": "PA95_DIAGNOSTIC",
            "retained_pcs": [1] if semantic_retained else [],
        },
    )
    result = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--runtime-telemetry",
            str(runtime_t),
            "--runtime-pa95",
            str(runtime_pa),
            "--semantic-telemetry",
            str(semantic_t),
            "--semantic-pa95",
            str(semantic_pa),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
    )
    return result, json.loads(out.read_text())


def test_federated_model_requires_both_pa95_retained_axes(tmp_path):
    result, receipt = run_model(tmp_path, semantic_retained=False)
    assert result.returncode == 0, result.stderr
    assert receipt["status"] == "WITHHELD_AXIS_RETENTION_GATE"
    assert receipt["global_allocation_authority"] is False
    assert receipt["coupling"]["joint_score_authority"] is False


def test_federated_model_emits_two_axis_diagnostic_not_joint_score(tmp_path):
    result, receipt = run_model(tmp_path, semantic_retained=True)
    assert result.returncode == 0, result.stderr
    assert receipt["status"] == "MEASURED_TWO_AXIS_DIAGNOSTIC"
    assert receipt["runtime_axis"]["pa95_retained"] is True
    assert receipt["semantic_axis"]["pa95_retained"] is True
    assert receipt["coupling"]["paired_observations"] is False
    assert receipt["coupling"]["joint_score_authority"] is False
    assert receipt["bt_status"] == "WITHHELD_NO_OBSERVED_PAIRWISE_EVIDENCE"
