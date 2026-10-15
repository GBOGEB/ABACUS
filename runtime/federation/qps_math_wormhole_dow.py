#!/usr/bin/env python3
"""ABACUS/DOW independent observer for gg_MATH -> KEB -> DOW -> QPS P4.

This records comparable error/fingerprint telemetry only. It cannot attest
CODEX/KEB actions, QPS engineering acceptance or externally executed runs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

ROUTE = ["GBOGEB/gg_MATH", "GBOGEB/CODEX", "GBOGEB/ABACUS", "GBOGEB/cryoplant-project"]
SHA = re.compile(r"^[a-f0-9]{40}$")
DIGEST = re.compile(r"^[a-f0-9]{64}$")
MAX_SIZE = 1_048_576
ZERO_AUTHORITY = {"authority_transfer": False, "formal_credit_delta": 0,
                  "engineering_acceptance": False,
                  "hard_gate_compensation_allowed": False, "release_credit": False}
EMPTY_RUNTIME = {"state": "PROPOSED_UNVERIFIED", "run_id": None,
                 "job_id": None, "positive_steps": None}
ALLOWED_METHODS = {"M03_COVARIANCE", "M04_PCA", "M05_CONFIDENCE_INTERVALS",
                   "M08_BRADLEY_TERRY", "M12_TEMPORAL_STATE"}


def sha256_json(data: dict[str, Any]) -> str:
    raw = json.dumps(data, sort_keys=True, ensure_ascii=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def classify(payload: Any, *, expected_sha: str,
             expected_artifact_digest: str) -> list[str]:
    """Emit normalized root signatures; do not silently skip malformed data."""
    if not isinstance(payload, dict):
        return ["MALFORMED_RECEIPT"]
    names = {"schema", "route_id", "route", "producer", "method", "lineage",
             "execution", "authority", "completed_hops", "receipt_sha256"}
    if set(payload) != names:
        return ["UNEXPECTED_FIELDS_OR_PRIVATE_DATA"]
    errors: list[str] = []
    try:
        body = {k: v for k, v in payload.items() if k != "receipt_sha256"}
        if sha256_json(body) != payload["receipt_sha256"]:
            errors.append("RECEIPT_DIGEST_MISMATCH")
    except (ValueError, TypeError, OverflowError):
        errors.append("NONCANONICAL_RECEIPT")
    if payload["schema"] != "gg-math-qps-wormhole/v1" or payload["route_id"] != "QPS-MATH-P4-3P3-V1":
        errors.append("SCHEMA_VERSION_MISMATCH")
    if payload["route"] != ROUTE or payload["completed_hops"] != []:
        errors.append("INVALID_P4_ROUTE_OR_FAKE_HOP")
    p = payload["producer"]
    if not isinstance(p, dict) or set(p) != {"repo", "source_sha", "artifact_path", "artifact_sha256"}:
        errors.append("PROVIDER_IDENTITY_MISSING")
    else:
        path = p.get("artifact_path")
        safe = isinstance(path, str) and bool(path) and ":" not in path and "\\" not in path and not PurePosixPath(path).is_absolute() and all(v not in (".", "..") for v in path.split("/"))
        if p["repo"] != ROUTE[0] or not isinstance(p["source_sha"], str) or not SHA.fullmatch(p["source_sha"]):
            errors.append("PROVIDER_SHA_INVALID")
        if p["source_sha"] != expected_sha or not isinstance(expected_sha, str) or not SHA.fullmatch(expected_sha):
            errors.append("EXACT_PROVIDER_SHA_DIFFERENCE")
        if not safe or not isinstance(p["artifact_sha256"], str) or not DIGEST.fullmatch(p["artifact_sha256"]):
            errors.append("ARTIFACT_IDENTITY_INVALID")
        if p["artifact_sha256"] != expected_artifact_digest or not isinstance(expected_artifact_digest, str) or not DIGEST.fullmatch(expected_artifact_digest):
            errors.append("ARTIFACT_DIGEST_DIFFERENCE")
    method = payload["method"]
    if not isinstance(method, dict) or set(method) != {"id", "population_id", "data_class", "threshold_authority", "observed_pairwise_fitted"}:
        errors.append("METHOD_SCHEMA_INVALID")
    else:
        ident = method.get("id")
        population = method.get("population_id")
        if not isinstance(ident, str) or ident not in ALLOWED_METHODS or method["data_class"] != "SYNTHETIC_REFERENCE" or method["threshold_authority"] != "QPS_ONLY" or method["observed_pairwise_fitted"] is not False:
            errors.append("METHOD_AUTHORITY_OR_BT_INVALID")
        if not isinstance(population, str) or not population.startswith("SYNTHETIC_") or not population.isascii():
            errors.append("UNSAFE_POPULATION")
    if payload["authority"] != ZERO_AUTHORITY:
        errors.append("AUTHORITY_INVERSION")
    if payload["execution"] != EMPTY_RUNTIME:
        errors.append("UNAUTHENTICATED_RUNTIME_CREDIT")
    lineage = payload["lineage"]
    if not isinstance(lineage, dict) or set(lineage) != {"wave", "pulse", "qps_child_state"} or lineage.get("qps_child_state") != "UNKNOWN" or not all(isinstance(lineage.get(k), str) and lineage[k] for k in ("wave", "pulse")):
        errors.append("PROJECT_DECISION_INJECTION")
    return sorted(set(errors))


def observe(payload: Any, *, expected_sha: str,
            expected_artifact_digest: str) -> dict[str, Any]:
    causes = classify(payload, expected_sha=expected_sha,
                      expected_artifact_digest=expected_artifact_digest)
    roots = [{
        "cause": cause,
        "fingerprint": hashlib.sha256(
            ("qps-p4-v1|" + expected_sha + "|" + cause).encode()
        ).hexdigest(),
        "owner": "ABACUS/DOW" if cause == "RECEIPT_DIGEST_MISMATCH" else "PROVIDER_OR_QPS_REVIEW",
        "disposition": "DEFER",
    } for cause in causes]
    body = {
        "schema": "abacus.dow.qps_math_wormhole_observation/v1",
        "provider_repo": ROUTE[0],
        "provider_source_sha": expected_sha,
        "provider_artifact_sha256": expected_artifact_digest,
        "consumer": "ABACUS/DOW",
        "status": "VALID_PROPOSAL_ONLY" if not causes else "DEFER_INVALID_CONTRACT",
        "measurement": {"received": 1, "contract_valid": 0 if causes else 1,
                        "invalid": int(bool(causes)), "unique_roots": len(roots),
                        "runtime_authenticated": 0, "qps_dispositions": 0},
        "roots": roots,
        "replay_status": "UNVERIFIED",
        "qps_acceptance": False,
        "authority_transfer": False,
        "formal_credit_delta": 0,
    }
    return {**body, "receipt_sha256": sha256_json(body)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider-receipt", type=Path, required=True)
    ap.add_argument("--provider-sha", required=True)
    ap.add_argument("--artifact-sha256", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    contents = args.provider_receipt.read_bytes()
    if len(contents) > MAX_SIZE:
        raise ValueError("provider envelope exceeds 1 MiB")
    record = observe(json.loads(contents), expected_sha=args.provider_sha,
                     expected_artifact_digest=args.artifact_sha256)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "measurement": record["measurement"]}, sort_keys=True))
    return 0 if record["status"] == "VALID_PROPOSAL_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
