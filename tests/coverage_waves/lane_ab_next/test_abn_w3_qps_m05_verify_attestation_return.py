"""Behaviour tests for scripts/qps_m05_verify_attestation_return.py."""

import copy
import hashlib
import json

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load(
    "scripts/qps_m05_verify_attestation_return.py",
    name="abn_qps_m05_verify_attestation_return",
)

RECEIPT_BYTES = b'{"receipt": "bytes"}'


def _valid_payloads():
    receipt = {
        "schema": "qps.m05.attestation_return_receipt.v1",
        "authority": mod.AUTHORITY,
        "action": {"sha": mod.EXPECTED_ACTION_SHA},
        "automatic_control_vector": {
            "run_id": mod.RUN_ID,
            "job_id": mod.EXPECTED_JOB_ID,
            "source_head_sha": mod.EXPECTED_HEAD,
            "carrier_sha": mod.EXPECTED_HEAD,
            "subject_sha256": mod.EXPECTED_SUBJECT_SHA256,
            "attestation_id": mod.EXPECTED_ATTESTATION_ID,
            "artifact": {
                "id": mod.EXPECTED_ARTIFACT_ID,
                "digest": mod.EXPECTED_ARTIFACT_DIGEST,
            },
            "result": "PASS",
        },
    }
    run = {
        "status": "completed",
        "conclusion": "success",
        "head_sha": mod.EXPECTED_HEAD,
        "event": "push",
        "head_branch": "main",
    }
    jobs = {
        "jobs": [
            {"id": 1, "status": "queued"},
            {
                "id": mod.EXPECTED_JOB_ID,
                "status": "completed",
                "conclusion": "success",
                "steps": [{"conclusion": "success"}, {"conclusion": "success"}],
            },
        ]
    }
    artifacts = {
        "artifacts": [
            {"id": 2},
            {
                "id": mod.EXPECTED_ARTIFACT_ID,
                "digest": mod.EXPECTED_ARTIFACT_DIGEST,
                "expired": False,
            },
        ]
    }
    return dict(receipt=receipt, run=run, jobs=jobs, artifacts=artifacts)


def _install_fetch(monkeypatch, payloads):
    seen = []

    def fake_fetch(url):
        seen.append(url)
        if url == mod.RECEIPT_URL:
            return RECEIPT_BYTES, payloads["receipt"]
        if url.endswith("/jobs"):
            return b"", payloads["jobs"]
        if url.endswith("/artifacts"):
            return b"", payloads["artifacts"]
        return b"", payloads["run"]

    monkeypatch.setattr(mod, "fetch_json", fake_fetch)
    return seen


class _FakeResponse:
    def __init__(self, raw):
        self.raw = raw

    def read(self):
        return self.raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_fetch_json_sends_user_agent_and_parses(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout):
        captured["req"] = req
        captured["timeout"] = timeout
        return _FakeResponse(b'{"a": [1, 2]}')

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)

    raw, data = mod.fetch_json("https://example.invalid/x.json")

    assert raw == b'{"a": [1, 2]}'
    assert data == {"a": [1, 2]}
    assert captured["timeout"] == 30
    assert captured["req"].full_url == "https://example.invalid/x.json"
    assert captured["req"].get_header("User-agent").startswith("QPS-M05")


def test_require_passes_and_raises():
    assert mod.require(True, "unused") is None
    with pytest.raises(SystemExit) as exc:
        mod.require(False, "boom")
    assert exc.value.code == "boom"


def test_receipt_url_is_pinned_to_commit():
    assert mod.CODEX_RECEIPT_SHA in mod.RECEIPT_URL
    assert mod.RECEIPT_URL.endswith(mod.CODEX_RECEIPT_PATH)


def test_main_happy_path_writes_receipt_and_digest(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    seen = _install_fetch(monkeypatch, _valid_payloads())

    assert mod.main() == 0

    assert seen[0] == mod.RECEIPT_URL
    assert seen[1].endswith("/runs/%d" % mod.RUN_ID)
    receipt_path = tmp_path / "artifacts" / "m05" / "dow_m05_consumer_receipt.json"
    out = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert out["status"] == "PASS"
    assert out["live_job_steps_verified_gt_zero"] == 2
    assert out["source_receipt_sha256"] == hashlib.sha256(RECEIPT_BYTES).hexdigest()
    assert out["dow_disposition"] == "ACCEPT_PROVENANCE_INTEGRITY_ONLY"
    digest = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    sha_file = tmp_path / "artifacts" / "m05" / "dow_m05_consumer_receipt.sha256"
    assert sha_file.read_text(encoding="utf-8").strip() == digest
    printed = capsys.readouterr().out
    assert "DOW_M05_CONSUMER_RECEIPT_SHA256=" + digest in printed


def _set(path, value):
    def mutate(payloads):
        target = payloads
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return mutate


MUTATIONS = [
    (_set(["receipt", "schema"], "other"), "receipt schema mismatch"),
    (_set(["receipt", "authority"], "ENGINEERING"), "authority boundary mismatch"),
    (_set(["receipt", "action", "sha"], "0"), "attest action SHA mismatch"),
    (_set(["receipt", "automatic_control_vector", "run_id"], 1), "run id mismatch"),
    (_set(["receipt", "automatic_control_vector", "job_id"], 1), "job id mismatch"),
    (
        _set(["receipt", "automatic_control_vector", "carrier_sha"], "x"),
        "carrier head mismatch",
    ),
    (
        _set(["receipt", "automatic_control_vector", "artifact", "digest"], "x"),
        "artifact digest mismatch",
    ),
    (
        _set(["receipt", "automatic_control_vector", "result"], "FAIL"),
        "source-owner result is not PASS",
    ),
    (_set(["run", "conclusion"], "failure"), "live run is not successful"),
    (_set(["run", "head_sha"], "x"), "live run head mismatch"),
    (_set(["run", "event"], "workflow_dispatch"), "live run is not automatic main"),
    (_set(["jobs", "jobs"], []), "expected job not found"),
    (_set(["jobs", "jobs", 1, "steps"], []), "zero-step execution cannot earn"),
    (
        _set(["jobs", "jobs", 1, "steps", 0, "conclusion"], "skipped"),
        "not all live steps passed",
    ),
    (_set(["artifacts", "artifacts"], []), "expected artifact not found"),
    (_set(["artifacts", "artifacts", 1, "digest"], "x"), "live artifact digest"),
    (_set(["artifacts", "artifacts", 1, "expired"], True), "already expired"),
]


@pytest.mark.parametrize("mutate,message", MUTATIONS)
def test_main_rejects_mismatches_without_writing(
    monkeypatch, tmp_path, mutate, message
):
    monkeypatch.chdir(tmp_path)
    payloads = copy.deepcopy(_valid_payloads())
    mutate(payloads)
    _install_fetch(monkeypatch, payloads)

    with pytest.raises(SystemExit) as exc:
        mod.main()

    assert message in str(exc.value.code)
    assert not (tmp_path / "artifacts").exists()
