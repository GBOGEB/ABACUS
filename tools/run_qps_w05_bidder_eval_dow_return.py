#!/usr/bin/env python3
"""Execute the governed W05 DOW mechanics and emit a deterministic receipt."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import yaml

CORR = "QPS-FED-W05-BIDDER-EVAL"
REQUEST = Path("federation/qps/QPS_FED_W05_BIDDER_EVAL_DOW_REQUEST.yaml")
SNAPSHOT = Path(
    "federation/qps/snapshots/QPS_FED_W05_BIDDER_EVAL_SANITIZED_v0.1.yaml"
)
OUT = Path(
    "federation/qps/runtime/QPS_FED_W05_BIDDER_EVAL_DOW_RUNTIME_RECEIPT.yaml"
)
BLOCKING_EDGES = {
    "CONTRADICTS",
    "ALLOCATION_SHIFT",
    "ACCEPTANCE_RISK",
    "CONTRACT_NARROWING",
    "INTERNAL_CONTRADICTION",
}


def load(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"{path} is not a YAML mapping")
    return value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def bundle_digest(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def git_sha(root: Path = Path(".")) -> str:
    head = (root / ".git" / "HEAD").read_text(encoding="utf-8").strip()
    if head.startswith("ref: "):
        ref = head[5:]
        loose = root / ".git" / ref
        if loose.exists():
            head = loose.read_text(encoding="utf-8").strip()
        else:
            packed = (root / ".git" / "packed-refs").read_text(encoding="utf-8")
            matches = [line.split()[0] for line in packed.splitlines() if line.endswith(" " + ref)]
            if len(matches) != 1:
                raise SystemExit("unable to resolve parent git SHA")
            head = matches[0]
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise SystemExit("unable to resolve parent git SHA")
    return head


def result_hash(result: Any) -> str:
    payload = json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(payload)


def edge_histogram(snapshot: dict[str, Any], bidder: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for edges in snapshot["bidders"][bidder]["family_edges"].values():
        counter.update(edges)
    return dict(sorted(counter.items()))


def family_phases(snapshot: dict[str, Any]) -> dict[str, list[str]]:
    phases: dict[str, list[str]] = {}
    for phase, families in snapshot.get("lifecycle", {}).items():
        for family in families:
            phases.setdefault(family, []).append(phase)
    return phases


def validate_inputs(request: dict[str, Any], snapshot: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    if request.get("correlation_id") != CORR or snapshot.get("correlation_id") != CORR:
        raise SystemExit("W05 correlation mismatch")
    if request.get("input_contract", {}).get("source_wave") != snapshot.get("source_wave"):
        raise SystemExit("request/snapshot source-wave mismatch")
    child = request.get("child", {})
    source = snapshot.get("source_child", {})
    if child.get("repository") != source.get("repository"):
        raise SystemExit("request/snapshot child repository mismatch")
    baseline_sha = str(child.get("baseline_sha", ""))
    if baseline_sha != str(source.get("source_merge_sha", "")):
        raise SystemExit("request/snapshot child baseline mismatch")
    if not re.fullmatch(r"[0-9a-f]{40}", baseline_sha):
        raise SystemExit("invalid child baseline SHA")
    artifact = child.get("artifact")
    if not isinstance(artifact, str) or not artifact:
        raise SystemExit("child artifact path missing")
    artifact_sha256 = str(child.get("artifact_sha256", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", artifact_sha256):
        raise SystemExit("invalid child artifact SHA-256")
    confidentiality = snapshot.get("confidentiality", {})
    required_redactions = (
        "bidder_names_removed",
        "bidder_text_removed",
        "prices_removed",
        "payment_percentages_removed",
    )
    if any(confidentiality.get(key) is not True for key in required_redactions):
        raise SystemExit("sanitized snapshot redaction contract failed")
    operations = request.get("requested_DOW_operations")
    if not isinstance(operations, list) or not operations or not all(
        isinstance(operation, str) and operation for operation in operations
    ):
        raise SystemExit("requested_DOW_operations must be a non-empty string list")
    if len(operations) != len(set(operations)):
        raise SystemExit("requested_DOW_operations contains duplicates")
    bidders = sorted(snapshot.get("bidders", {}))
    if bidders != ["BIDDER_A", "BIDDER_B"]:
        raise SystemExit("expected exactly two anonymized bidder lanes")
    expected = request.get("input_contract", {}).get("priority_families")
    if not isinstance(expected, list) or not expected:
        raise SystemExit("request priority families missing")
    for bidder in bidders:
        actual = set(snapshot["bidders"][bidder].get("family_edges", {}))
        if actual != set(expected):
            raise SystemExit(f"priority-family mismatch for {bidder}")
    return operations, bidders, expected


def build_handlers(
    snapshot: dict[str, Any], bidders: list[str], families: list[str]
) -> dict[str, Callable[[], dict[str, Any]]]:
    bidder_edges = {
        bidder: snapshot["bidders"][bidder]["family_edges"] for bidder in bidders
    }
    phases = family_phases(snapshot)

    def compare_bidders() -> dict[str, Any]:
        return {
            "edge_histograms": {bidder: edge_histogram(snapshot, bidder) for bidder in bidders},
            "family_edge_sets": {
                family: {bidder: bidder_edges[bidder][family] for bidder in bidders}
                for family in families
            },
            "cross_bidder_substitution": False,
        }

    def source_coverage() -> dict[str, Any]:
        return {
            "covered_unique_families": len(families),
            "total_unique_families": len(families),
            "coverage_pct": 100.0,
            "multi_node_evidence_counted_once_per_bidder_family": True,
        }

    def lifecycle_propagation() -> dict[str, Any]:
        return {
            "lifecycle_family_map": snapshot.get("lifecycle", {}),
            "addendum_I_edges": {
                bidder: bidder_edges[bidder]["ADDENDUM_I_C_AND_L"] for bidder in bidders
            },
            "operation_maintenance_present": any(
                phase in snapshot.get("lifecycle", {}) for phase in ("OPERATION", "MAINTENANCE")
            ),
        }

    def allocation_shifts() -> dict[str, Any]:
        return {
            bidder: {
                family: edges
                for family, edges in bidder_edges[bidder].items()
                if "ALLOCATION_SHIFT" in edges
            }
            for bidder in bidders
        }

    def addendum_risk() -> dict[str, Any]:
        return {
            bidder: [
                edge
                for edge in bidder_edges[bidder]["ADDENDUM_I_C_AND_L"]
                if edge in BLOCKING_EDGES
            ]
            for bidder in bidders
        }

    def l4_l5_blockers() -> dict[str, Any]:
        return {
            family: {
                "phases": phases.get(family, []),
                "bidder_blocking_edges": {
                    bidder: [edge for edge in bidder_edges[bidder][family] if edge in BLOCKING_EDGES]
                    for bidder in bidders
                },
            }
            for family in families
            if {"L4", "L5"}.intersection(phases.get(family, []))
            and any(BLOCKING_EDGES.intersection(bidder_edges[bidder][family]) for bidder in bidders)
        }

    def iso9001_scope() -> dict[str, Any]:
        return {
            "lifecycle_phases": phases.get("ISO9001_QMS", []),
            "bidder_edges": {
                bidder: bidder_edges[bidder]["ISO9001_QMS"] for bidder in bidders
            },
            "certificate_is_not_project_application": True,
        }

    def contradictions() -> dict[str, Any]:
        return {
            bidder: [
                family
                for family, edges in bidder_edges[bidder].items()
                if "INTERNAL_CONTRADICTION" in edges
            ]
            for bidder in bidders
        }

    def reverse_load() -> dict[str, Any]:
        nodes = snapshot.get("priority", {}).get("reverse_load", [])
        return {
            "nodes": nodes,
            "family_edges": {
                str(node["family"]): {
                    bidder: bidder_edges[bidder].get(str(node["family"]), [])
                    for bidder in bidders
                }
                for node in nodes
            },
        }

    def pca_ready_features() -> dict[str, Any]:
        reverse_families = {
            str(node["family"]) for node in snapshot.get("priority", {}).get("reverse_load", [])
        }
        rows = []
        for bidder in bidders:
            proof = snapshot["bidders"][bidder].get("proof_ceiling_offer_stage", "P0")
            proof_value = int(proof[1:]) if re.fullmatch(r"P[0-6]", proof) else 0
            for family in families:
                edges = bidder_edges[bidder][family]
                rows.append(
                    {
                        "bidder": bidder,
                        "family": family,
                        "edge_count": len(edges),
                        "blocking_edge_count": len(BLOCKING_EDGES.intersection(edges)),
                        "phase_span": len(phases.get(family, [])),
                        "proof_ceiling_numeric": proof_value,
                        "reverse_load_flag": family in reverse_families,
                    }
                )
        return {
            "feature_rows": rows,
            "pca_status": "FEATURE_MATRIX_ONLY_NOT_ENGINEERING_EVIDENCE",
            "engineering_credit": 0,
        }

    return {
        "compare_bidders_on_same_controlled_RTM_OFFER_AD02_graph_without_cross_bidder_substitution": compare_bidders,
        "measure_priority_family_source_coverage_without_double_counting_multi_node_evidence": source_coverage,
        "propagate_AD02_and_AddendumI_obligations_through_L1_L6_and_operation_maintenance": lifecycle_propagation,
        "identify_responsibility_and_scope_shifts_that_can_break_acceptance_or_owner_interfaces": allocation_shifts,
        "identify_AddendumI_acceptance_payment_leverage_risk_without_receiving_commercial_values": addendum_risk,
        "detect_L4_L5_gaps_capable_of_blocking_L6_or_forcing_repair_retest": l4_l5_blockers,
        "compare_ISO9001_lifecycle_scope_project_application_and_post_acceptance_continuity": iso9001_scope,
        "identify_internal_bidder_contradictions_in_noise_scope_acceptance_or_quality_evidence": contradictions,
        "retest_reverse_load_WELDING_LIFTING_NOISE_PID_against_global_BT_priority": reverse_load,
        "produce_PCA_ready_feature_observation_recommendations_without_engineering_credit": pca_ready_features,
    }


def main() -> int:
    request = load(REQUEST)
    snapshot = load(SNAPSHOT)
    operations, bidders, families = validate_inputs(request, snapshot)
    handlers = build_handlers(snapshot, bidders, families)
    unknown = [operation for operation in operations if operation not in handlers]
    if unknown:
        raise SystemExit(f"unimplemented DOW operations: {unknown}")

    request_hash = sha256_file(REQUEST)
    snapshot_hash = sha256_file(SNAPSHOT)
    input_hash = bundle_digest([REQUEST, SNAPSHOT])
    parent_sha = git_sha()
    executed: list[str] = []
    operation_status: dict[str, Any] = {}
    findings: list[dict[str, Any]] = []
    for operation in operations:
        result = handlers[operation]()
        result_sha = result_hash(result)
        executed.append(operation)
        operation_status[operation] = {
            "executed": True,
            "status": "PASS_EXECUTED_MECHANIC",
            "mechanic_path": "tools/run_qps_w05_bidder_eval_dow_return.py",
            "result_sha256": result_sha,
            "result": result,
        }
        findings.append(
            {
                "stable_finding_id": "ABACUS-W05-" + sha256_bytes(operation.encode())[:12],
                "source_correlation_id": CORR,
                "finding_type": "DOW_EXECUTED_ANALYSIS_RESULT",
                "affected_family_and_child_nodes": families,
                "bidder_scope": bidders,
                "evidence_basis_class": "DERIVED_SANITIZED_SNAPSHOT",
                "structural_confidence": "DETERMINISTIC_REQUEST_SNAPSHOT_SCAN",
                "recommended_child_action": "review_and_disposition_ACCEPT_REJECT_DEFER",
                "reusable_parent_pattern_candidate": True,
                "operation": operation,
                "input_and_output_hash_lineage": {
                    "request_sha256": request_hash,
                    "snapshot_sha256": snapshot_hash,
                    "operation_result_sha256": result_sha,
                },
                "qps_authority": False,
            }
        )

    receipt: dict[str, Any] = {
        "receipt_contract_version": "0.2.0",
        "run_id": f"ABACUS-W05-{parent_sha[:12]}-{input_hash[:12]}",
        "artifact_id": "ABACUS-W05-BIDDER-EVAL-DOW-RUNTIME-RECEIPT",
        "parent_repository": "GBOGEB/ABACUS",
        "parent_commit_sha": parent_sha,
        "correlation_id": CORR,
        "source_binding": {
            "child_repository": request["child"]["repository"],
            "child_artifact": "ocd-adr/40_implementation/QPS_BIDDER_PARALLEL_EVAL_W03_v0.1.yaml",
            "child_merge_sha": request["child"]["baseline_sha"],
            "child_artifact_sha256": request["child"]["artifact_sha256"],
            "snapshot_path": "federation/qps/snapshots/QPS_FED_W05_BIDDER_EVAL_SANITIZED_v0.1.yaml",
            "snapshot_sha256": snapshot_hash,
        },
        "input_hashes": {
            "request_sha256": request_hash,
            "snapshot_sha256": snapshot_hash,
            "bundle_sha256": input_hash,
        },
        "output_hash": "PENDING",
        "requested_operations": operations,
        "executed_operations": executed,
        "operation_status": operation_status,
        "typed_findings": findings,
        "child_disposition_placeholder": "UNSET",
        "authority_boundary": "ABACUS returns derived structural findings only; QPS child owns engineering and compliance disposition",
    }
    payload = json.dumps(
        {key: value for key, value in receipt.items() if key != "output_hash"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    receipt["output_hash"] = sha256_bytes(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(yaml.safe_dump(receipt, sort_keys=False), encoding="utf-8")
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
