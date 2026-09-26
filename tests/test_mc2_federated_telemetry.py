import json
import subprocess
import sys
from pathlib import Path

TOOL = Path("tools/mc2_federated_telemetry.py")
SEED = Path("fixtures/mc2_federated_telemetry_seed_v0.1.json")


def run_tool(tmp_path, source=SEED):
    out = tmp_path / "receipt.json"
    result = subprocess.run(
        [sys.executable, str(TOOL), str(source), "--out", str(out)],
        capture_output=True,
        text=True,
    )
    return result, out


def test_seed_runtime_pca_is_measured_but_allocation_is_withheld(tmp_path):
    result, out = run_tool(tmp_path)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(out.read_text())
    assert receipt["rows_total"] == 9
    assert receipt["runtime_state_counts"] == {"NOT_EXECUTED": 1, "PASS": 5}
    assert receipt["runtime_pca"]["status"] == "MEASURED_PCA_DIAGNOSTIC"
    assert receipt["runtime_pca"]["distinct_source_shas"] == 5
    assert receipt["runtime_pca"]["constant_features_excluded"] == [
        "runner_allocated_fraction"
    ]
    assert (
        receipt["runtime_pca"]["bt_status"]
        == "WITHHELD_NO_OBSERVED_PAIRWISE_EVIDENCE"
    )
    assert receipt["semantic_pca"]["status"] == "WITHHELD"
    assert receipt["semantic_pca"]["reason"] == "INSUFFICIENT_COMPARABLE_ROWS"
    assert receipt["zero_imputation_performed"] is False
    assert receipt["allocation_state"] == "WITHHELD_PARENT_TRANSITION_GATE"
    assert receipt["child_engineering_promotion_authority"] is False


def test_zero_step_application_fail_is_rejected(tmp_path):
    bad = json.loads(SEED.read_text())
    row = next(item for item in bad if item.get("execution_state") == "NOT_EXECUTED")
    row["execution_state"] = "FAIL"
    source = tmp_path / "bad.json"
    source.write_text(json.dumps(bad))
    result, _ = run_tool(tmp_path, source)
    assert result.returncode != 0
    assert "executed state requires >0 steps" in result.stderr


def test_duplicate_sha_cannot_fake_independent_pca(tmp_path):
    bad = json.loads(SEED.read_text())
    completed = [item for item in bad if item.get("execution_state") == "PASS"]
    completed[-1]["source_sha"] = completed[0]["source_sha"]
    source = tmp_path / "pseudo.json"
    source.write_text(json.dumps(bad))
    result, out = run_tool(tmp_path, source)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(out.read_text())
    assert receipt["runtime_pca"]["status"] == "WITHHELD"
    assert (
        receipt["runtime_pca"]["reason"]
        == "PSEUDOREPLICATION_DISTINCT_SHA_GATE"
    )
