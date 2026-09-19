#!/usr/bin/env python3
"""Fail-closed GM-I-A CoolProp FAST/HEAVY federation consumer."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "triage" / "GM_I_A_COOLPROP_RUNTIME_BRIDGE_v1.json"


def canonical_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest() -> dict:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert value["schema"] == "abacus.gm_i_a.coolprop_runtime_bridge.v1"
    assert value["consumer_repo"] == "GBOGEB/ABACUS"
    assert value["authority_transfer"] is False
    assert value["engineering_promotion_forbidden"] is True
    provider = value["provider"]
    assert provider["repo"] == "GBOGEB/CoolProp"
    assert len(provider["attestation_commit_sha"]) == 40
    assert len(provider["attestation_sha256"]) == 64
    return value


def fetch_provider(manifest: dict) -> tuple[dict, str]:
    p = manifest["provider"]
    url = (
        "https://raw.githubusercontent.com/GBOGEB/CoolProp/"
        f"{p['attestation_commit_sha']}/{p['attestation_path']}"
    )
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read()
    digest = sha256_bytes(raw)
    if digest != p["attestation_sha256"]:
        raise ValueError("provider attestation digest mismatch")
    value = json.loads(raw)
    return value, digest


def validate_provider(manifest: dict, att: dict) -> None:
    p = manifest["provider"]
    assert att["schema"] == "qps.gm_i_a.fast_heavy.federation_attestation.v1"
    assert att["provider_repo"] == "GBOGEB/CoolProp"
    assert att["source_head_sha"] == p["source_head_sha"]
    assert att["workflow"]["run_id"] == p["workflow_run_id"]
    assert att["workflow"]["conclusion"] == "success"
    assert att["heavy"]["conclusion"] == "success"
    assert att["fast"]["conclusion"] == "success"
    assert att["heavy"]["artifact"]["digest"] == p["heavy_artifact_digest"]
    assert att["fast"]["artifact"]["digest"] == p["fast_artifact_digest"]
    assert att["fast"]["build_invoked"] is False
    assert att["fast"]["source_checkout_performed"] is False
    assert att["authority"]["authority_transfer"] is False
    assert att["authority"]["engineering_promotion"] == "WITHHELD"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()

    manifest = load_manifest()
    att, digest = fetch_provider(manifest)
    validate_provider(manifest, att)
    receipt = {
        "schema": "abacus.gm_i_a.coolprop_runtime_bridge_receipt.v1",
        "consumer_repo": "GBOGEB/ABACUS",
        "provider_repo": "GBOGEB/CoolProp",
        "provider_source_head_sha": att["source_head_sha"],
        "provider_attestation_commit_sha": manifest["provider"]["attestation_commit_sha"],
        "provider_attestation_sha256": digest,
        "provider_workflow_run_id": att["workflow"]["run_id"],
        "heavy_artifact_digest": att["heavy"]["artifact"]["digest"],
        "fast_artifact_digest": att["fast"]["artifact"]["digest"],
        "fast_calculation_count": att["fast"]["calculations_passed"],
        "runtime_economics": att["runtime_economics"],
        "status": "PASS",
        "authority_transfer": False,
        "engineering_promotion_forbidden": True,
        "return_to": "GBOGEB/pipeline-automation-hub",
    }
    pathlib.Path(args.receipt).write_bytes(canonical_bytes(receipt))


if __name__ == "__main__":
    main()
