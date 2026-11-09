"""Lane-B wave 9: everred_v3 federation_bridge receipt-only exchange checks."""

import hashlib

import pytest

from ._l2_loader import load

fp = load("tools/everred_v3/src/four_planes.py")
yc = load("tools/everred_v3/src/yaml_control.py", deps={"four_planes": fp})
fb = load(
    "tools/everred_v3/src/federation_bridge.py",
    deps={"four_planes": fp, "yaml_control": yc},
)

A, B = "a" * 40, "b" * 40
PRODUCER = "GBOGEB/CODEX"
CONSUMER = "GBOGEB/ABACUS"
ARTIFACT = b"artifact-bytes"
DIGEST = hashlib.sha256(ARTIFACT).hexdigest()


def _producer(**overrides):
    values = {"repository": PRODUCER, "source_sha": A, "run_id": 11, "job_id": 12}
    values.update(overrides)
    return fp.Source(**values)


def _policy():
    return {
        "schema": "abacus.everred.federation-policy.v1",
        "bindings": [
            {
                "producer": PRODUCER,
                "consumer": CONSUMER,
                "domain": "coverage",
                "action": "OBSERVATION_ONLY",
            },
            {
                "producer": PRODUCER,
                "consumer": CONSUMER,
                "domain": "bandit",
                "action": "OBSERVATION_ONLY",
            },
        ],
    }


def _receipt(**overrides):
    values = {
        "domain": "coverage",
        "producer_repo": PRODUCER,
        "source_sha": A,
        "executed_sha": A,
        "artifact_sha256": DIGEST,
        "receipt_id": "R-1",
    }
    values.update(overrides)
    return values


def _exchange(**kwargs):
    params = {
        "producer": _producer(),
        "consumer_repo": CONSUMER,
        "receipt": _receipt(),
    }
    params.update(kwargs)
    return fb.evaluate_exchange(_policy(), **params)


def test_exchange_declared_unverified_without_bytes():
    out = _exchange()
    assert out["integrity"] == "DECLARED_UNVERIFIED"
    assert out["schema"] == "abacus.everred.federation.exchange.v1"
    assert out["producer"] == PRODUCER
    assert out["consumer"] == CONSUMER
    assert out["producer_source_sha"] == A
    assert out["producer_executed_sha"] == A
    assert out["producer_run_id"] == 11
    assert out["producer_job_id"] == 12
    assert out["receipt_id"] == "R-1"
    assert out["domain"] == "coverage"
    assert out["consumer_disposition"] == "DEFER"
    assert out["independent_review"] is None
    assert out["source_ownership_changed"] is False
    assert out["authority_transfer"] is False
    assert out["admission"] == "HOLD"
    body = {k: v for k, v in out.items() if k != "exchange_id"}
    assert out["exchange_id"] == "X-" + fp.fingerprint(body)[:24]


def test_exchange_hash_matched_with_bytes_and_executed_sha():
    out = _exchange(
        producer=_producer(executed_sha=B),
        receipt=_receipt(executed_sha=B),
        artifact_bytes=ARTIFACT,
    )
    assert out["integrity"] == "LOCAL_BYTES_HASH_MATCHED_NOT_NATIVE_JOB_ATTESTED"
    assert out["producer_executed_sha"] == B


def test_exchange_empty_bytes_are_still_hashed():
    empty = hashlib.sha256(b"").hexdigest()
    out = _exchange(receipt=_receipt(artifact_sha256=empty), artifact_bytes=b"")
    assert out["integrity"] == "LOCAL_BYTES_HASH_MATCHED_NOT_NATIVE_JOB_ATTESTED"


@pytest.mark.parametrize(
    "kwargs,message",
    [
        ({"receipt": "receipt"}, "bad producer receipt"),
        ({"receipt": _receipt(domain="unknown")}, "producer not registered"),
        ({"consumer_repo": "GBOGEB/OTHER"}, "producer not registered"),
        ({"producer": _producer(repository="X/Y")}, "producer not registered"),
        (
            {"receipt": _receipt(producer_repo="GBOGEB/OTHER")},
            "producer repository mismatch",
        ),
        ({"receipt": _receipt(source_sha=B)}, "producer head mismatch"),
        ({"receipt": _receipt(executed_sha=B)}, "execution SHA mismatch"),
        (
            {"producer": _producer(executed_sha=B), "receipt": _receipt()},
            "execution SHA mismatch",
        ),
        ({"receipt": _receipt(artifact_sha256=None)}, "missing artifact checksum"),
        (
            {"receipt": _receipt(artifact_sha256="A" * 64)},
            "missing artifact checksum",
        ),
        ({"artifact_bytes": "text"}, "artifact bytes invalid"),
        ({"artifact_bytes": bytearray(ARTIFACT)}, "artifact bytes invalid"),
        ({"artifact_bytes": b"tampered"}, "artifact checksum mismatch"),
    ],
)
def test_exchange_rejections(kwargs, message):
    with pytest.raises(fp.EvidenceError, match=message):
        _exchange(**kwargs)


def test_exchange_rejects_oversized_bytes():
    big = b"\0" * (32 * 1024 * 1024 + 1)
    with pytest.raises(fp.EvidenceError, match="artifact bytes invalid"):
        _exchange(artifact_bytes=big)


def test_exchange_validates_policy_first():
    with pytest.raises(fp.EvidenceError, match="federation schema invalid"):
        fb.evaluate_exchange(
            {"schema": "x"},
            producer=_producer(),
            consumer_repo=CONSUMER,
            receipt=_receipt(),
        )


def test_exchange_rejects_duplicate_policy_binding():
    policy = _policy()
    policy["bindings"].append(dict(policy["bindings"][0]))
    with pytest.raises(fp.EvidenceError, match="duplicate federation binding"):
        fb.evaluate_exchange(
            policy, producer=_producer(), consumer_repo=CONSUMER, receipt=_receipt()
        )


def test_release_candidate_counts_exchanges():
    rows = [_exchange(), _exchange(receipt=_receipt(domain="bandit"))]
    out = fb.release_candidate(rows)
    assert out == {
        "schema": "abacus.everred.federation.review.v1",
        "observations": 2,
        "review_required": 2,
        "independently_accepted": None,
        "external_authority_required": True,
        "admission": "HOLD",
    }


def test_release_candidate_empty():
    out = fb.release_candidate([])
    assert out["observations"] == 0
    assert out["review_required"] == 0


@pytest.mark.parametrize(
    "value,message",
    [
        ("rows", "exchange set invalid"),
        ({"schema": "abacus.everred.federation.exchange.v1"}, "exchange set invalid"),
        ([{"schema": "other"}], "exchange schema invalid"),
        ([{}], "exchange schema invalid"),
    ],
)
def test_release_candidate_rejections(value, message):
    with pytest.raises(fp.EvidenceError, match=message):
        fb.release_candidate(value)
