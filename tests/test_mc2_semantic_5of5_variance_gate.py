import json
import subprocess
import sys
from pathlib import Path

TOOL = Path("tools/mc2_federated_telemetry.py")
FIXTURE = Path("fixtures/mc2_semantic_5of5_variance_gate_v0.1.json")


def test_semantic_5of5_passes_denominator_but_withholds_pca_without_second_varying_axis(tmp_path):
    out = tmp_path / "receipt.json"
    result = subprocess.run(
        [sys.executable, str(TOOL), str(FIXTURE), "--out", str(out)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    receipt = json.loads(out.read_text())
    semantic = receipt["semantic_pca"]

    assert semantic["numeric_comparable_rows"] == 5
    assert semantic["distinct_source_shas"] == 5
    assert semantic["required_rows"] == 5
    assert semantic["required_distinct_source_shas"] == 5
    assert semantic["status"] == "WITHHELD"
    assert semantic["reason"] == "INSUFFICIENT_VARYING_FEATURES"
    assert semantic["constant_features_excluded"] == [
        "registry_gap_rate",
        "unresolved_reference_rate",
        "graph_drop_rate",
        "lineage_gap_rate",
    ]
    assert receipt["global_allocation_authority"] is False
    assert receipt["child_engineering_promotion_authority"] is False
    assert receipt["allocation_state"] == "WITHHELD_PARENT_TRANSITION_GATE"
