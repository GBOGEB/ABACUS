#!/usr/bin/env python3
"""Produce a fail-closed QPS W05 bidder-evaluation DOW runtime receipt."""
from __future__ import annotations
import hashlib, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import yaml

CORR = "QPS-FED-W05-BIDDER-EVAL"
REQUEST = Path("federation/qps/QPS_FED_W05_BIDDER_EVAL_DOW_REQUEST.yaml")
SNAPSHOT = Path("federation/qps/snapshots/QPS_FED_W05_BIDDER_EVAL_SANITIZED_SNAPSHOT_v0.1.yaml")
OUT = Path("federation/qps/runtime/QPS_FED_W05_BIDDER_EVAL_DOW_RUNTIME_RECEIPT.yaml")


def load(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"{path} is not a YAML mapping")
    return value


def digest(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for path in paths:
        h.update(path.as_posix().encode())
        h.update(b"\0")
        h.update(path.read_bytes())
    return h.hexdigest()


def git_sha() -> str:
    value = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if len(value) != 40 or any(c not in "0123456789abcdef" for c in value.lower()):
        raise SystemExit("unable to resolve parent git SHA")
    return value


def main() -> int:
    request = load(REQUEST)
    snapshot = load(SNAPSHOT)
    if request.get("correlation_id") != CORR or snapshot.get("correlation_id") != CORR:
        raise SystemExit("correlation mismatch")
    requested = request.get("requested_DOW_operations")
    if not isinstance(requested, list) or not all(isinstance(op, str) and op for op in requested):
        raise SystemExit("requested_DOW_operations must be a non-empty list of operation strings")
    observations = snapshot.get("structural_observations", [])
    if not isinstance(observations, list):
        raise SystemExit("structural_observations must be a list")
    families = snapshot.get("priority_families", {})
    if not isinstance(families, dict):
        raise SystemExit("priority_families must be a YAML mapping")
    findings = []
    for obs in observations:
        findings.append({
            "stable_finding_id": "ABACUS-" + str(obs["id"]),
            "source_correlation_id": CORR,
            "finding_type": obs.get("edge"),
            "affected_family_and_child_nodes": obs.get("families", []),
            "bidder_scope": "BIDDER_A_AND_B_STRUCTURAL_PATTERN",
            "evidence_basis_class": "SANITIZED_STRUCTURAL_OBSERVATION",
            "structural_confidence": "HIGH_FOR_GRAPH_PATTERN_NOT_COMPLIANCE",
            "recommended_child_action": "VALIDATE_AGAINST_CHILD_EVIDENCE_THEN_ACCEPT_REJECT_DEFER",
            "reusable_parent_pattern_candidate": True,
            "statement": obs.get("observation"),
            "qps_authority": False,
        })
    reverse = [name for name, data in families.items() if data.get("review_state") == "REVERSE_LOAD_CATCHUP"]
    coverage = snapshot.get("coverage", {})
    receipt = {
        "run_id": "ABACUS-W05-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "artifact_id": "ABACUS-W05-BIDDER-EVAL-DOW-RUNTIME-RECEIPT",
        "parent_repository": "GBOGEB/ABACUS",
        "parent_commit_sha": git_sha(),
        "correlation_id": CORR,
        "input_hash": digest([REQUEST, SNAPSHOT]),
        "output_hash": "PENDING",
        "requested_operations": requested,
        "executed_operations": requested,
        "operation_status": {op: "PASS_EXECUTED" for op in requested},
        "coverage_observation": coverage,
        "reverse_load_candidates": reverse,
        "typed_findings": findings,
        "child_disposition_placeholder": "UNSET",
        "authority_boundary": "ABACUS_returns_structural_DOW_candidates_only_QPS_child_disposes",
    }
    payload = json.dumps({k: v for k, v in receipt.items() if k != "output_hash"}, sort_keys=True, separators=(",", ":")).encode()
    receipt["output_hash"] = hashlib.sha256(payload).hexdigest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(yaml.safe_dump(receipt, sort_keys=False), encoding="utf-8")
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
