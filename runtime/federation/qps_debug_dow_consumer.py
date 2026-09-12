#!/usr/bin/env python3
"""Consume CODEX/KEB QPS-debug binding into ABACUS/DOW fail-closed.

The original QPS_REPO_LOCAL mode remains unchanged. A separate
FEDERATED_EXACT_PAYLOAD mode is accepted only when CODEX/KEB has already bound
exact source SHA, exact payload hash, real debugger steps, and adapter readiness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runtime" / "federation" / "generated"


def load_binding(path: Path | None) -> dict | None:
    if path and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    raw = os.getenv("CODEX_QPS_DEBUG_BINDING_JSON")
    if raw:
        return json.loads(raw)
    return None


def evidence_ok_for_mode(binding: dict | None) -> tuple[str, bool, dict]:
    if not binding:
        return "NONE", False, {}
    mode = binding.get("evidence_mode") or "QPS_REPO_LOCAL"
    checks = binding.get("checks", {})
    steps = bool(checks.get("runtime_steps_gt_zero"))
    if mode == "QPS_REPO_LOCAL":
        ok = bool(steps and checks.get("recursive_audit_pass"))
    elif mode == "FEDERATED_EXACT_PAYLOAD":
        ok = bool(
            steps
            and checks.get("source_payload_hash_match")
            and checks.get("adapter_surface_ready")
            and checks.get("repo_local_runner_recovered") is False
        )
    else:
        ok = False
    return mode, ok, checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binding", type=Path)
    args = parser.parse_args()
    binding = load_binding(args.binding)

    owner_ok = bool(binding and binding.get("semantic_owner") == "CODEX/KEB")
    status_ok = bool(binding and binding.get("status") == "ACCEPT")
    exact_sha = binding.get("producer_exact_head_sha") if binding else None
    mode, evidence_ok, source_checks = evidence_ok_for_mode(binding)
    accept = bool(
        owner_ok
        and status_ok
        and exact_sha
        and exact_sha != "UNKNOWN"
        and evidence_ok
    )

    dow = {
        "schema": "abacus.dow.qps_debug_binding.v2",
        "receipt_id": "DOW-QPS-DEBUG-DAG-001",
        "created_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "consumer": "ABACUS/DOW",
        "semantic_source": "CODEX/KEB",
        "producer_exact_head_sha": exact_sha,
        "evidence_mode": mode,
        "status": "ACCEPT" if accept else "DEFER",
        "reason": (
            f"EXACT_KEB_{mode}_RUNTIME_BINDING_ACCEPT"
            if accept
            else f"KEB_{mode}_RUNTIME_BINDING_NOT_ACCEPTABLE_OR_ABSENT"
        ),
        "source_binding_sha256": binding.get("binding_sha256") if binding else None,
        "checks": {
            "semantic_owner_valid": owner_ok,
            "keb_status_accept": status_ok,
            "exact_producer_sha_present": bool(exact_sha and exact_sha != "UNKNOWN"),
            "runtime_evidence_valid": evidence_ok,
            "runtime_steps_gt_zero": bool(source_checks.get("runtime_steps_gt_zero")),
            "recursive_audit_pass": source_checks.get("recursive_audit_pass"),
            "source_payload_hash_match": source_checks.get("source_payload_hash_match"),
            "adapter_surface_ready": source_checks.get("adapter_surface_ready"),
            "repo_local_runner_recovered": source_checks.get("repo_local_runner_recovered"),
        },
        "emit_for_child_disposition": accept,
        "authority_guards": {
            "qps_engineering_authority_transfer": False,
            "formal_engineering_credit_delta": 0,
            "negotiation_credit_delta": 0,
            "dow_accept_is_runtime_evidence_only": True,
            "federated_mode_does_not_claim_repo_local_runner_recovery": True,
        },
    }
    dow["receipt_sha256"] = hashlib.sha256(
        json.dumps(dow, sort_keys=True).encode()
    ).hexdigest()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "qps_debug_dow_binding.json").write_text(
        json.dumps(dow, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(dow, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
