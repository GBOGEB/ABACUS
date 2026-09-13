import json
import subprocess
import sys
from pathlib import Path


TOOL = Path("tools/mc2_parallel_analysis_block_gate.py")


def run_gate(tmp_path, receipt, block="semantic_pca"):
    source = tmp_path / "telemetry.json"
    source.write_text(json.dumps(receipt), encoding="utf-8")
    out = tmp_path / "pa95.json"
    result = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            str(source),
            "--block",
            block,
            "--out",
            str(out),
            "--simulations",
            "500",
            "--seed",
            "20260913",
        ],
        capture_output=True,
        text=True,
    )
    return result, json.loads(out.read_text()) if out.exists() else None


def test_block_gate_fail_closes_when_semantic_pca_is_withheld(tmp_path):
    receipt = {
        "receipt_sha256": "source",
        "semantic_pca": {
            "status": "WITHHELD",
            "reason": "INSUFFICIENT_VARYING_FEATURES",
        },
    }
    result, output = run_gate(tmp_path, receipt)
    assert result.returncode == 0, result.stderr
    assert output["status"] == "WITHHELD_INPUT_PCA_NOT_MEASURED"
    assert output["input_pca_reason"] == "INSUFFICIENT_VARYING_FEATURES"
    assert output["retained_pcs"] == []
    assert output["allocation_authority"] is False


def test_block_gate_runs_pa95_for_measured_semantic_pca(tmp_path):
    # Unit-test-only PCA receipt. This is never production telemetry evidence.
    receipt = {
        "receipt_sha256": "source",
        "semantic_pca": {
            "status": "MEASURED_PCA_DIAGNOSTIC",
            "numeric_comparable_rows": 5,
            "components": [
                {"pc": 1, "eigenvalue": 3.0},
                {"pc": 2, "eigenvalue": 1.0},
            ],
        },
    }
    result, output = run_gate(tmp_path, receipt)
    assert result.returncode == 0, result.stderr
    assert output["status"] == "PA95_DIAGNOSTIC"
    assert output["pca_block"] == "semantic_pca"
    assert output["sample_size"] == 5
    assert output["varying_feature_count"] == 2
    assert output["allocation_authority"] is False
    assert output["child_engineering_promotion_authority"] is False
