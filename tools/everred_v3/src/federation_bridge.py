"""Receipt-only CODEX -> ABACUS federation, without semantic ownership transfer."""

from __future__ import annotations

import hashlib

from four_planes import HEX64, Source, demand, fingerprint
from yaml_control import validate_federation_policy


def evaluate_exchange(
    policy: dict,
    *,
    producer: Source,
    consumer_repo: str,
    receipt: dict,
    artifact_bytes: bytes | None = None,
) -> dict:
    """Check identity and hash, never self-authorize cross-repo ACCEPT."""
    validate_federation_policy(policy)
    demand(isinstance(receipt, dict), "bad producer receipt")
    matched = [
        b
        for b in policy["bindings"]
        if b["producer"] == producer.repository
        and b["consumer"] == consumer_repo
        and b["domain"] == receipt.get("domain")
    ]
    demand(len(matched) == 1, "producer not registered for this domain")
    demand(
        receipt.get("producer_repo") == producer.repository,
        "producer repository mismatch",
    )
    demand(receipt.get("source_sha") == producer.source_sha, "producer head mismatch")
    actual = receipt.get("executed_sha")
    demand(
        actual == (producer.executed_sha or producer.source_sha),
        "execution SHA mismatch",
    )
    expected = receipt.get("artifact_sha256")
    demand(
        isinstance(expected, str) and bool(HEX64.fullmatch(expected)),
        "missing artifact checksum",
    )
    integrity = "DECLARED_UNVERIFIED"
    if artifact_bytes is not None:
        demand(
            isinstance(artifact_bytes, bytes)
            and len(artifact_bytes) <= 32 * 1024 * 1024,
            "artifact bytes invalid",
        )
        demand(
            hashlib.sha256(artifact_bytes).hexdigest() == expected,
            "artifact checksum mismatch",
        )
        integrity = "LOCAL_BYTES_HASH_MATCHED_NOT_NATIVE_JOB_ATTESTED"
    out = {
        "schema": "abacus.everred.federation.exchange.v1",
        "producer": producer.repository,
        "consumer": consumer_repo,
        "producer_source_sha": producer.source_sha,
        "producer_executed_sha": actual,
        "producer_run_id": producer.run_id,
        "producer_job_id": producer.job_id,
        "receipt_id": receipt.get("receipt_id"),
        "domain": receipt["domain"],
        "integrity": integrity,
        "consumer_disposition": "DEFER",
        "independent_review": None,
        "source_ownership_changed": False,
        "authority_transfer": False,
        "admission": "HOLD",
    }
    out["exchange_id"] = "X-" + fingerprint(out)[:24]
    return out


def release_candidate(dispositions: list[dict]) -> dict:
    """Prepare human review queue, not a release gate or scheduling action."""
    demand(isinstance(dispositions, list), "exchange set invalid")
    for d in dispositions:
        demand(
            d.get("schema") == "abacus.everred.federation.exchange.v1",
            "exchange schema invalid",
        )
    return {
        "schema": "abacus.everred.federation.review.v1",
        "observations": len(dispositions),
        "review_required": len(dispositions),
        "independently_accepted": None,
        "external_authority_required": True,
        "admission": "HOLD",
    }
