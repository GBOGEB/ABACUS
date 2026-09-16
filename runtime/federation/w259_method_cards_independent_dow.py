#!/usr/bin/env python3
"""Independent DOW challenge for W259 math method-card federation.

This module intentionally imports no gg_MATH or CODEX implementation. It validates
an exact-pinned KEB source receipt and independently challenges the normalized
method-card/dependency semantics carried by the federation transaction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "runtime/federation/fixtures/w259_p4_keb_source_receipt.json"
SNAPSHOT = ROOT / "runtime/federation/fixtures/w259_method_card_semantic_snapshot.json"

EXPECTED_CODEX_MERGE = "d41e709c93d8c73ba392478592dd75627743a2ad"
EXPECTED_CODEX_RECEIPT_BLOB = "384584243eaeb63c9f6f41fadc773b83174d6638"
EXPECTED_BUNDLE_DIGEST = "sha256:a5ea0c436bfb695245bed82a8275a5a775fea94cb3f8555e5cd89d44b5726012"
EXPECTED_THRESHOLD_KINDS = {
    "EXACT_IDENTITY", "DISTRIBUTION_DERIVED", "MODEL_DERIVED", "DATA_CALIBRATED",
    "HEURISTIC", "PROJECT_GOVERNED", "NO_UNIVERSAL_THRESHOLD", "RESEARCH_TODO",
}
EXPECTED_TOPIC_IDS = {f"M{i:02d}" for i in range(1, 17)}
DEPENDENCY_EDGE_TYPES = {"REQUIRES", "FEEDS", "CALIBRATES"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def acyclic(nodes: set[str], edges: list[list[str]]) -> bool:
    graph = {node: [] for node in nodes}
    indegree = {node: 0 for node in nodes}
    for src, dst, kind in edges:
        if kind not in DEPENDENCY_EDGE_TYPES:
            continue
        graph[src].append(dst)
        indegree[dst] += 1
    queue = sorted(node for node, degree in indegree.items() if degree == 0)
    seen = 0
    while queue:
        node = queue.pop(0)
        seen += 1
        for nxt in graph[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
                queue.sort()
    return seen == len(nodes)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--codex-sha", required=True)
    p.add_argument("--codex-receipt-blob", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    keb = json.loads(FIXTURE.read_text(encoding="utf-8"))
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}

    checks["codex_merge_exact"] = args.codex_sha == EXPECTED_CODEX_MERGE
    checks["codex_receipt_blob_exact"] = args.codex_receipt_blob == EXPECTED_CODEX_RECEIPT_BLOB
    checks["keb_object_type"] = keb.get("object_type") == "KEB_SOURCE_RECEIPT"
    checks["keb_item"] = keb.get("keb_item_id") == "KEB-ITEM-0003"
    checks["keb_accept"] = keb.get("status") == "ACCEPT" and keb.get("replay_status") == "PASS"
    checks["bundle_digest_exact"] = keb.get("source_digest") == EXPECTED_BUNDLE_DIGEST == keb.get("bundle", {}).get("canonical_bundle_digest")
    checks["downstream_is_dow"] = keb.get("downstream_consumer") == "GBOGEB/ABACUS/DOW"

    cards = snap["cards"]
    ids = [row[0] for row in cards]
    topics = [row[1] for row in cards]
    card_threshold_kinds = {row[2] for row in cards}
    checks["sixteen_unique_cards"] = len(cards) == 16 and len(set(ids)) == 16 and set(ids) == EXPECTED_TOPIC_IDS
    checks["sixteen_unique_topics"] = len(set(topics)) == 16
    checks["card_thresholds_known"] = card_threshold_kinds <= EXPECTED_THRESHOLD_KINDS
    checks["all_threshold_kinds_federated"] = set(keb["bundle"]["gg_math"]["threshold_kinds"]) == EXPECTED_THRESHOLD_KINDS
    checks["snapshot_source_blobs_exact"] = (
        snap["cards_blob"] == keb["bundle"]["gg_math"]["cards_blob"]
        and snap["graph_blob"] == keb["bundle"]["gg_math"]["graph_blob"]
        and snap["source_merge"] == keb["bundle"]["gg_math"]["merge_sha"]
    )

    edges = snap["edges"]
    node_set = set(ids)
    checks["edges_reference_known_nodes"] = all(src in node_set and dst in node_set for src, dst, _ in edges)
    checks["bounded_dependency_graph_acyclic"] = acyclic(node_set, edges)
    checks["pca_bt_anti_inference_bidirectional"] = (
        ["M04", "M08", "DOES_NOT_IMPLY"] in edges
        and ["M08", "M04", "DOES_NOT_IMPLY"] in edges
    )
    checks["pca_has_matrix_eigen_covariance_dependencies"] = all(
        edge in edges for edge in [
            ["M02", "M04", "REQUIRES"],
            ["M03", "M04", "REQUIRES"],
            ["M01", "M02", "FEEDS"],
            ["M01", "M03", "FEEDS"],
        ]
    )
    checks["resampling_challenges_pca_bt"] = (
        ["M11", "M04", "CHALLENGES"] in edges
        and ["M11", "M08", "CHALLENGES"] in edges
    )

    critical = snap["critical_semantics"]
    checks["ci_90_95_99_preserved"] = critical["confidence_levels"] == [90, 95, 99]
    checks["bt_parity_preserved"] = critical["bt_parity_probability"] == 0.5
    checks["pca_sign_guard_preserved"] = critical["pca_sign_requires_alignment_before_interpretation"] is True
    checks["project_threshold_read_only"] = critical["project_governed_threshold_read_only_to_provider"] is True
    checks["research_todo_zero_authority"] = critical["research_todo_has_zero_consumer_authority"] is True
    checks["global_cycle_bounded_dag_distinction"] = (
        critical["bounded_execution_dag_must_be_acyclic"] is True
        and critical["global_graph_may_cycle_through_feedback"] is True
    )

    expected_planes = {
        "P1": ["3PR", "METHOD_MATH"],
        "P2": ["MIP", "PROJECT_MATH_QPS"],
        "P3": ["3PC", "TRIAGE_GOVERNANCE"],
    }
    checks["three_plane_mapping"] = all(snap["planes"][key] == value for key, value in expected_planes.items())
    checks["p4_optional_federation_only"] = snap["planes"]["P4"] == ["3P3", "FEDERATION_ORCHESTRATION", "OPTIONAL_CROSS_REPO_OR_AUTHORITY_ONLY"]
    checks["keb_plane_mapping_matches"] = all(
        keb["transaction_semantics"][key]["operator"] == expected_planes[key][0]
        and keb["transaction_semantics"][key]["plane"] == expected_planes[key][1]
        for key in expected_planes
    ) and keb["transaction_semantics"]["P4"] == {
        "operator": "3P3", "plane": "FEDERATION_ORCHESTRATION", "optional": True
    }

    guards = keb["authority_guards"]
    anti = keb["anti_inference_guards"]
    checks["zero_authority_inversion"] = (
        guards["authority_transfer"] is False
        and guards["hard_gate_compensation_allowed"] is False
        and guards["formal_engineering_credit_delta"] == 0
        and guards["negotiation_credit_delta"] == 0
        and guards["runtime_gold_created"] is False
        and guards["release_authority_created"] is False
        and all(value is False for value in anti.values())
    )
    checks["stretch_set_present"] = set(snap["stretch_methods"]) == {
        "Tracy_Widom", "hierarchical_Bayesian_BT", "high_dimensional_MANOVA",
        "anytime_valid_confidence_sequences", "Grassmann_state_space_models"
    }

    passed = sum(checks.values())
    receipt = {
        "schema": "abacus.dow.w259_method_cards_independent_receipt.v1",
        "created_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "consumer": "GBOGEB/ABACUS/DOW",
        "semantic_source": "GBOGEB/CODEX/KEB",
        "provider": "GBOGEB/gg_MATH",
        "codex_merge_sha": args.codex_sha,
        "codex_source_receipt_blob": args.codex_receipt_blob,
        "canonical_bundle_digest": EXPECTED_BUNDLE_DIGEST,
        "independent_implementation": True,
        "imports_gg_math": False,
        "imports_codex_runtime": False,
        "checks": checks,
        "kpi": {
            "check_pass_count": passed,
            "check_total": len(checks),
            "semantic_parity": passed / len(checks),
            "threshold_kind_parity": 1.0 if checks["all_threshold_kinds_federated"] else 0.0,
            "plane_mapping_parity": 1.0 if checks["three_plane_mapping"] and checks["p4_optional_federation_only"] else 0.0,
            "authority_inversion_count": 0 if checks["zero_authority_inversion"] else 1,
            "independent_consumer_count": 1,
        },
        "dmaic": {
            "Define": "independently challenge method-card, threshold, dependency and 3+1-plane semantics",
            "Measure": "pin exact KEB merge/blob and enumerate semantic invariants",
            "Analyse": "test card/topic uniqueness, dependency DAG, anti-inference, threshold and authority parity",
            "Improve": "repair only observed semantic or lineage drift",
            "Control": "require all independent checks PASS before KEB atom promotion",
        },
        "authority_transfer": False,
        "formal_credit_delta": 0,
        "hard_gate_compensation_allowed": False,
    }
    receipt["status"] = "PASS" if passed == len(checks) else "FAIL"
    payload = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
    receipt["receipt_sha256"] = hashlib.sha256(payload).hexdigest()
    p_out = args.out
    p_out.parent.mkdir(parents=True, exist_ok=True)
    p_out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
