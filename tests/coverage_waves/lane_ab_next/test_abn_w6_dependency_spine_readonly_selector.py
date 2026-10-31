"""Gap tests for runtime/execution/dependency_spine_readonly_selector.py.

Covers owner_head (subprocess faked), the scheduler contract check, the
remaining consume_codex rejections, verify drift and the CLI entry point.
"""

import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load(
    "runtime/execution/dependency_spine_readonly_selector.py",
    name="abn_w6_dependency_spine_selector",
)

HEAD = "a" * 40
CODEX = "b" * 40
CONTRACT_TEXT = "moniker: DELTA_1\nreconciliation_execution\ngovernance_execution\n"


class _Proc:
    def __init__(self, returncode, stdout):
        self.returncode = returncode
        self.stdout = stdout


def _receipt(**overrides):
    r = {
        "schema": "codex.mycelium.dependency_spine.stage.v1",
        "consumer_repo": "GBOGEB/CODEX",
        "consumer_head_sha": CODEX,
        "source_head_sha": "c" * 40,
        "child_disposition": "DEFER",
        "merge_admission": "HOLD",
        "formal_credit_delta": 0,
        "authenticated_remote_execution": False,
        "native_producer_run_job_attempt_bound": False,
        "mutation_enabled": False,
        "dispatch_authorized": False,
        "authority_transfer": False,
    }
    r.update(overrides)
    r["stage_digest_sha256"] = mod.checksum(mod.encode(r))
    return r


def _root(tmp_path, text=CONTRACT_TEXT):
    root = tmp_path / "root"
    sched = root / "runtime" / "execution"
    sched.mkdir(parents=True)
    (sched / "federated-execution-scheduler.yaml").write_bytes(text.encode())
    return root


def test_owner_head_success_and_failure(monkeypatch, tmp_path):
    seen = []

    def ok(cmd, **kwargs):
        seen.append((cmd, kwargs["cwd"]))
        return _Proc(0, HEAD + "\n")

    monkeypatch.setattr(mod.subprocess, "run", ok)
    assert mod.owner_head(tmp_path) == HEAD
    assert seen == [(["git", "rev-parse", "--verify", "HEAD"], tmp_path)]
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: _Proc(128, "junk"))
    assert mod.owner_head(tmp_path) == ""


def test_contract_missing_drift_and_ok(tmp_path):
    with pytest.raises(ValueError, match="CANONICAL_SCHEDULER_MISSING"):
        mod.contract(tmp_path)
    drift = _root(tmp_path, "moniker: DELTA_1\nreconciliation_execution\n")
    with pytest.raises(ValueError, match="CANONICAL_SCHEDULER_CONTRACT_DRIFT"):
        mod.contract(drift)
    (
        drift / "runtime" / "execution" / "federated-execution-scheduler.yaml"
    ).write_bytes(CONTRACT_TEXT.encode())
    assert mod.contract(drift) is None


def test_consume_codex_invalid_expected_sha():
    with pytest.raises(ValueError, match="EXPECTED_CODEX_SHA_INVALID"):
        mod.consume_codex(_receipt(), "XYZ")


@pytest.mark.parametrize(
    "overrides,code",
    [
        (dict(schema="other"), "CODEX_STAGE_SCHEMA"),
        (dict(consumer_repo="GBOGEB/ABACUS"), "CODEX_STAGE_SCHEMA"),
        (dict(child_disposition="ACCEPT"), "CODEX_FALSE_ACCEPT"),
        (dict(merge_admission="MERGE"), "CODEX_FALSE_ACCEPT"),
        (dict(dispatch_authorized=True), "CODEX_AUTHORITY_ESCALATION"),
        (dict(mutation_enabled=None), "CODEX_AUTHORITY_ESCALATION"),
        (dict(formal_credit_delta=1), "CODEX_FORMAL_CREDIT"),
    ],
)
def test_consume_codex_rejections(overrides, code):
    with pytest.raises(ValueError, match=code):
        mod.consume_codex(_receipt(**overrides), CODEX)


def test_consume_codex_accepts_valid_receipt():
    r = _receipt()
    assert mod.consume_codex(r, CODEX) == r["stage_digest_sha256"]


def test_select_rejects_bad_head_and_missing_codex_head():
    with pytest.raises(ValueError, match="ABACUS_HEAD_INVALID"):
        mod.select("short", None)
    with pytest.raises(ValueError, match="CODEX_HEAD_REQUIRED"):
        mod.select(HEAD, _receipt())


def test_verify_detects_hash_drift_and_false_dispatch():
    good = mod.select(HEAD, None)
    tampered = dict(good, observed_dispatches=1)
    with pytest.raises(ValueError, match="RETURN_HASH_DRIFT"):
        mod.verify(tampered)
    raw = {k: v for k, v in tampered.items() if k != "return_sha256"}
    tampered["return_sha256"] = mod.checksum(mod.encode(raw))
    with pytest.raises(ValueError, match="SCHEDULER_FALSE_DISPATCH_OR_ADMISSION"):
        mod.verify(tampered)


def _argv(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["selector"] + [str(a) for a in args])


def test_main_head_mismatch_exits(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "owner_head", lambda root: "f" * 40)
    _argv(monkeypatch, "--root", tmp_path, "--expected-head", HEAD, "--out", tmp_path)
    with pytest.raises(SystemExit, match="OWNER_EXACT_HEAD_MISMATCH"):
        mod.main()


def test_main_missing_receipt_exits(monkeypatch, tmp_path):
    root = _root(tmp_path)
    monkeypatch.setattr(mod, "owner_head", lambda r: HEAD)
    _argv(
        monkeypatch,
        "--root",
        root,
        "--expected-head",
        HEAD,
        "--codex-receipt",
        tmp_path / "absent.json",
        "--out",
        tmp_path / "out",
    )
    with pytest.raises(SystemExit, match="STAGED_CODEX_RECEIPT_MISSING"):
        mod.main()


def test_main_without_receipt_writes_defer(monkeypatch, tmp_path, capsys):
    root = _root(tmp_path)
    monkeypatch.setattr(mod, "owner_head", lambda r: HEAD)
    out = tmp_path / "out" / "nested"
    _argv(monkeypatch, "--root", root, "--expected-head", HEAD, "--out", out)
    assert mod.main() == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["selector_state"] == "DEFER_NO_CODEX_RECEIPT"
    written = json.loads(
        (out / "ABACUS_DEPENDENCY_SPINE_DOW_RETURN.json").read_text(encoding="utf-8")
    )
    mod.verify(written)
    assert written["owner_head_sha"] == HEAD


def test_main_with_receipt_writes_proposal(monkeypatch, tmp_path, capsys):
    root = _root(tmp_path)
    monkeypatch.setattr(mod, "owner_head", lambda r: HEAD)
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_bytes(mod.encode(_receipt()))
    out = tmp_path / "out"
    _argv(
        monkeypatch,
        "--root",
        root,
        "--expected-head",
        HEAD,
        "--codex-receipt",
        receipt_path,
        "--expected-codex-head",
        CODEX,
        "--out",
        out,
    )
    assert mod.main() == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed == {
        "merge_admission": "HOLD",
        "observed_dispatches": 0,
        "selector_state": "PROPOSAL_NOT_DISPATCHED",
    }
    written = json.loads(
        (out / "ABACUS_DEPENDENCY_SPINE_DOW_RETURN.json").read_text(encoding="utf-8")
    )
    assert written["source_codex_head_sha"] == CODEX
    assert written["source_qps_head_sha"] == "c" * 40
