#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "controls/QPS_W189_FEDERATION_SAMPLE4_CURRENT_v1.json"
MATRIX = ROOT / "triage/w189/QPS_W189_CROSS_SURFACE_FEATURE_MATRIX_v0.1.json"
PAIRWISE = ROOT / "triage/w189/QPS_W189_PAIRWISE_DISPOSITION_LEDGER_v0.1.json"
CENSUS = ROOT / "triage/w189/QPS_W189_FEDERATION_FLEET_CENSUS_v0.1.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(cond, msg):
    if not cond:
        raise SystemExit(f"W189 REJECT: {msg}")


def main():
    c, m, p, f = map(load, (CONTROL, MATRIX, PAIRWISE, CENSUS))
    require(c["wave"] == "W189", "wrong wave")
    require(c["namespace"]["w188"].startswith("OCCUPIED_"), "W188 collision guard missing")
    require(c["surface"]["repaired_carrier_head"] == "766f064e561c28e41cc70dd1a17a29cd71343da5", "carrier head mismatch")
    rr = c["observed_runtime"]["exact_hash_mirror_pass"]
    require(rr["run_id"] == 34868622367 and rr["job_id"] == 104058671463, "runtime vector mismatch")
    require(rr["runner_id"] > 0 and rr["result"] == "PASS", "real runner PASS missing")
    require(c["measurement"]["breadth"]["numerator"] == c["measurement"]["breadth"]["denominator"] == 30, "B denominator mismatch")
    require(c["measurement"]["depth_candidate"]["numerator"] == 7 and c["measurement"]["depth_candidate"]["denominator"] == 8, "D candidate mismatch")
    require(c["measurement"]["depth_candidate"]["value"] == 0.875, "D candidate value mismatch")
    require(all(v == 0 for v in c["formal_credit_delta"].values()), "formal credit changed")

    require(len(m["rows"]) == 4, "matrix must have four rows")
    require(sum(int(r["accepted_sample"]) for r in m["rows"]) == 3, "sample4 admitted before proof")
    s4 = next(r for r in m["rows"] if r["sample_id"] == c["sample_id"])
    require(s4["accepted_sample"] == 0 and s4["depth_ratio"] == 0.875, "sample4 candidate state weakened")
    require(m["analytics_gate"]["pca_state"].startswith("N4_STABILITY_CANDIDATE_WITHHELD_"), "n4 PCA admitted early")
    require(m["candidate_n4_stability"]["pc1_loading_congruence_abs"] > 0.99, "PC1 stability evidence missing")
    require(m["candidate_n4_stability"]["pc2_loading_congruence_abs"] < 0.20, "PC2 rotation evidence missing")

    require(len(p["outcomes"]) == 4, "pairwise outcome count mismatch")
    component = p["bt_gate"]["repeated_comparable_component"]
    require(component["observed_comparisons"] == 2, "transport repeat missing")
    require(component["graph_connected"] is True, "transport component not connected")
    require(component["unregularized_mle_state"] == "SEPARATED_2_TO_0_NO_FINITE_MLE", "complete separation guard missing")
    require(p["bt_gate"]["global_connected_comparison_graph"] is False, "global BT graph fabricated as connected")
    require(p["bt_gate"]["global_fit_state"].startswith("WITHHELD_"), "global BT fitted prematurely")

    require(f["denominator_model"]["accessible_repository_universe"]["value"] is None, "raw repo universe incorrectly frozen")
    require(f["denominator_model"]["mission_relevant_governed_surface_universe"]["value"] is None, "surface denominator fabricated")
    require(len(f["confirmed_core_repositories"]) >= 6, "core census unexpectedly incomplete")
    print("W189 PASS: sample4 candidate bound; n4 PC1 stable/PC2 rotating; repeated transport BT component captured; fleet denominator still fail-closed")


if __name__ == "__main__":
    main()
