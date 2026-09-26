#!/usr/bin/env python3
"""Fail-closed ABACUS/DOW consumer for CODEX/KEB gg_MATH temporal-PCA bindings."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runtime" / "federation" / "generated"
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

REQUIRED_CHALLENGES = {
    "C01_SIGN_FLIP",
    "C02_COMPONENT_SWAP",
    "C03_SMALL_EIGENGAP_INTERNAL_ROTATION",
    "C04_TRUE_SUBSPACE_ROTATION",
    "C05_ATTENUATION_WITHOUT_REVERSAL",
    "C06_IRREGULAR_WALL_TIME",
    "C07_DISTINCT_AGE_CLOCK",
}
REQUIRED_DIAGNOSTICS = {
    "COMPONENT_ASSIGNMENT",
    "SIGN_ALIGNMENT",
    "TUCKER_CONGRUENCE",
    "EIGENGAP_CONTEXT",
    "PRINCIPAL_ANGLES",
    "ORTHOGONAL_PROCRUSTES",
    "PROJECTION_DISTANCE",
    "GRASSMANN_GEODESIC_DISTANCE",
    "EVENT_WALL_AGE_MULTICLOCK_RATES",
    "SIGNED_EFFECT_ATTENUATION_VS_REVERSAL",
}
EXPECTED_FEDERATION_FOLLOWUP = {
    "mission": "GRANDMISSION-I-B-TEMPORAL-PCA-FEDERATION",
    "exact_head_sha": "a5f32ef2b65caa9b49270d7fe8134acd6f1e71d8",
    "workflow_run_id": 35139956561,
    "artifact_id": 10464776497,
    "artifact_digest": "sha256:2c7cbcddffc6c3830ab02a212563ef390e7fe189ce24214f4313e6e5bccd2921",
    "receipt_digest": "sha256:84a2869fca566eb14879e85b5777af8027c6aa096c3bcc746f8eb838b69ac053",
    "named_clocks_roundtrip": ["k", "t", "a", "wave", "pulse", "pr", "run", "release"],
    "formal_credit_delta": 0,
}


def load_binding(path: Path | None) -> dict | None:
    if path and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    raw = os.getenv("CODEX_GG_MATH_TEMPORAL_PCA_BINDING_JSON")
    return json.loads(raw) if raw else None


def federation_followup_valid(binding: dict) -> bool:
    if "federation_followup" not in binding:
        return True
    followup = binding.get("federation_followup")
    return isinstance(followup, dict) and all(
        followup.get(key) == expected for key, expected in EXPECTED_FEDERATION_FOLLOWUP.items()
    )


def evaluate(binding: dict | None) -> tuple[bool, dict]:
    if not binding:
        return False, {"binding_present": False}
    challenges = set(binding.get("provider_challenges", []))
    diagnostics = set(binding.get("provider_diagnostics", []))
    checks = {
        "binding_present": True,
        "semantic_owner_valid": binding.get("semantic_owner") == "CODEX/KEB",
        "keb_status_accept": binding.get("status") == "ACCEPT",
        "provider_exact_sha_valid": bool(SHA_RE.fullmatch(str(binding.get("source_sha", "")))),
        "provider_artifact_digest_valid": bool(SHA256_RE.fullmatch(str(binding.get("source_artifact_digest", "")))),
        "provider_runtime_pass": binding.get("provider_runtime_result") == "PASS",
        "all_required_challenges_present": REQUIRED_CHALLENGES <= challenges,
        "all_required_diagnostics_present": REQUIRED_DIAGNOSTICS <= diagnostics,
        "authority_transfer_false": binding.get("authority_transfer") is False,
        "hard_gate_compensation_false": binding.get("hard_gate_compensation_allowed") is False,
        "authority_cap_a3": binding.get("authority_cap") == "A3_SYNTHETIC_ONLY",
    }
    if "federation_followup" in binding:
        checks["federation_followup_exact_lineage"] = federation_followup_valid(binding)
    return all(checks.values()), checks


def consume(binding: dict | None) -> dict:
    accept, checks = evaluate(binding)
    source_sha = binding.get("source_sha") if binding else None
    source_digest = binding.get("source_artifact_digest") if binding else None
    dow = {
        "schema": "abacus.dow.gg_math_temporal_pca_binding.v1",
        "receipt_id": "DOW-GG-MATH-TEMPORAL-PCA-001",
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "consumer": "ABACUS/DOW",
        "semantic_source": "CODEX/KEB",
        "provider": "GBOGEB/gg_MATH",
        "producer_exact_head_sha": source_sha,
        "source_artifact_digest": source_digest,
        "status": "ACCEPT" if accept else "DEFER",
        "reason": "EXACT_KEB_TEMPORAL_PCA_BINDING_ACCEPT" if accept else "KEB_TEMPORAL_PCA_BINDING_NOT_PROMOTABLE",
        "checks": checks,
        "emit_for_qps_bounded_consumption": accept,
        "interpretation_guards": {
            "pca_loading_sign_is_policy_direction": False,
            "attenuation_equals_direction_reversal": False,
            "component_order_is_identity_without_assignment": False,
            "event_step_equals_wall_time_step": False,
        },
        "authority_guards": {
            "qps_engineering_authority_transfer": False,
            "formal_engineering_credit_delta": 0,
            "negotiation_credit_delta": 0,
            "dow_accept_is_evidence_binding_only": True,
            "synthetic_provider_receipt_cannot_create_acceptance_credit": True,
        },
    }
    if binding and "federation_followup" in binding:
        dow["federation_followup"] = binding["federation_followup"]
    dow["receipt_sha256"] = hashlib.sha256(json.dumps(dow, sort_keys=True).encode()).hexdigest()
    return dow


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binding", type=Path)
    args = parser.parse_args()
    dow = consume(load_binding(args.binding))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "gg_math_temporal_pca_dow_binding.json").write_text(
        json.dumps(dow, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(dow, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
