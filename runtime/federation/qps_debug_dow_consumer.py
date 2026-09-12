#!/usr/bin/env python3
"""Consume CODEX/KEB QPS-debug binding into ABACUS/DOW fail-closed."""
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binding", type=Path)
    args = parser.parse_args()
    binding = load_binding(args.binding)

    owner_ok = bool(binding and binding.get("semantic_owner") == "CODEX/KEB")
    status_ok = bool(binding and binding.get("status") == "ACCEPT")
    exact_sha = binding.get("producer_exact_head_sha") if binding else None
    checks = (binding or {}).get("checks", {})
    evidence_ok = bool(checks.get("runtime_steps_gt_zero") and checks.get("recursive_audit_pass"))
    accept = bool(owner_ok and status_ok and exact_sha and exact_sha != "UNKNOWN" and evidence_ok)

    dow = {
        "schema": "abacus.dow.qps_debug_binding.v1",
        "receipt_id": "DOW-QPS-DEBUG-DAG-001",
        "created_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "consumer": "ABACUS/DOW",
        "semantic_source": "CODEX/KEB",
        "producer_exact_head_sha": exact_sha,
        "status": "ACCEPT" if accept else "DEFER",
        "reason": "EXACT_KEB_RUNTIME_BINDING_ACCEPT" if accept else "KEB_RUNTIME_BINDING_NOT_ACCEPTABLE_OR_ABSENT",
        "source_binding_sha256": binding.get("binding_sha256") if binding else None,
        "checks": {
            "semantic_owner_valid": owner_ok,
            "keb_status_accept": status_ok,
            "exact_producer_sha_present": bool(exact_sha and exact_sha != "UNKNOWN"),
            "runtime_evidence_valid": evidence_ok,
        },
        "emit_for_child_disposition": accept,
        "authority_guards": {
            "qps_engineering_authority_transfer": False,
            "formal_engineering_credit_delta": 0,
            "negotiation_credit_delta": 0,
            "dow_accept_is_runtime_evidence_only": True,
        },
    }
    dow["receipt_sha256"] = hashlib.sha256(json.dumps(dow, sort_keys=True).encode()).hexdigest()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "qps_debug_dow_binding.json").write_text(json.dumps(dow, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(dow, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
