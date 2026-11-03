"""Gap tests for runtime/execution/governed_recovery_wave.py (guards, main)."""

import json
import sys
from types import SimpleNamespace

import pytest
import yaml

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("runtime/execution/governed_recovery_wave.py", name="abn_w7_recovery_wave")

HEAD = "e" * 40


def _lane(key, owner, resource="technical", priority=0, needs=None):
    return {
        "id": key,
        "priority": priority,
        "source_owner": owner,
        "resource": resource,
        "needs": list(needs or []),
        "evidence": "ev_" + key.lower(),
    }


def _config(lanes, slots=2):
    return {
        "federated_execution_scheduler": {
            "moniker": "DELTA_1",
            "governed_recovery_wave": {
                "action_class": "STAGE_ONLY",
                "merge_admission": "HOLD",
                "auto_merge": False,
                "worker_dispatch_authorized": False,
                "resources": dict(
                    proposal_worker_slots=slots,
                    human_approval_slots=0,
                    secret_configuration_slots=0,
                    admission_slots=0,
                ),
                "lanes": lanes,
            },
        }
    }


def test_scheduler_drift_rejected():
    config = _config([_lane("AA", "a/b")])
    config["federated_execution_scheduler"]["moniker"] = "OTHER"
    with pytest.raises(ValueError, match="CANONICAL_SCHEDULER_DRIFT"):
        mod.plan(HEAD, config)


def test_empty_lanes_rejected():
    with pytest.raises(ValueError, match="NO_LANES"):
        mod.plan(HEAD, _config([]))


def test_malformed_lane_rejected():
    with pytest.raises(ValueError, match="MALFORMED_LANE"):
        mod.plan(HEAD, _config(["AA"]))


def test_invalid_lane_id_rejected():
    with pytest.raises(ValueError, match="INVALID_LANE_ID"):
        mod.plan(HEAD, _config([_lane("lower", "a/b")]))


def test_duplicate_lane_rejected():
    lanes = [_lane("AA", "a/b"), _lane("AA", "c/d")]
    with pytest.raises(ValueError, match="DUPLICATE_LANE"):
        mod.plan(HEAD, _config(lanes))


@pytest.mark.parametrize(
    "field, value",
    [("resource", "gpu"), ("priority", 3), ("priority", "0"), ("needs", "AA")],
)
def test_invalid_lane_contract_rejected(field, value):
    lane = _lane("AA", "a/b")
    lane[field] = value
    with pytest.raises(ValueError, match="INVALID_LANE_CONTRACT"):
        mod.plan(HEAD, _config([lane]))


def test_capacity_wait_when_slots_exhausted():
    lanes = [_lane("AA", "a/x"), _lane("BB", "b/y"), _lane("CC", "c/z")]
    result = mod.plan(HEAD, _config(lanes, slots=1))
    states = {row["id"]: row["state"] for row in result["lanes"]}
    assert states == {
        "AA": "DISJOINT_PROPOSAL_ONLY",
        "BB": "STAGED_CAPACITY_WAIT",
        "CC": "STAGED_CAPACITY_WAIT",
    }
    assert result["selected_disjoint_proposals"] == ["AA"]
    mod.verify(result)


@pytest.mark.parametrize("owner", ["UNALLOCATED_X", "AUTHORIZED_Y", "READ_ONLY_Z"])
def test_reserved_technical_owner_rejected(owner):
    with pytest.raises(ValueError, match="INVALID_TECHNICAL_SOURCE_OWNER"):
        mod.plan(HEAD, _config([_lane("AA", owner)]))


def _setup_root(tmp_path, config):
    root = tmp_path / "root"
    target = root / mod.SCHEDULER
    target.parent.mkdir(parents=True)
    target.write_text(yaml.safe_dump(config), encoding="utf-8")
    return root


def _fake_git(returncode, stdout, seen):
    def fake_run(cmd, **kwargs):
        seen.append((cmd, kwargs))
        return SimpleNamespace(returncode=returncode, stdout=stdout)

    return fake_run


def test_main_writes_verified_proposal(tmp_path, monkeypatch, capsys):
    config = _config([_lane("AA", "a/x"), _lane("BB", "b/y", needs=["AA"])])
    root = _setup_root(tmp_path, config)
    out = tmp_path / "out" / "stage.json"
    seen = []
    monkeypatch.setattr(mod.subprocess, "run", _fake_git(0, HEAD + "\n", seen))
    argv = ["w", "--root", str(root), "--expected-head", HEAD, "--out", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    assert mod.main() == 0
    assert seen[0][0] == ["git", "rev-parse", "--verify", "HEAD"]
    assert seen[0][1]["cwd"] == root
    payload = json.loads(out.read_bytes())
    mod.verify(payload)
    assert payload["source_head_sha"] == HEAD
    assert payload["edge_count"] == 1
    printed = json.loads(capsys.readouterr().out)
    assert printed == {
        "edges": 1,
        "lanes": 2,
        "merge_admission": "HOLD",
        "observed_dispatches": 0,
        "planned_workers": 1,
    }


@pytest.mark.parametrize(
    "returncode, stdout", [(1, "e" * 40), (0, "f" * 40)], ids=["fail", "other"]
)
def test_main_head_mismatch_exits(tmp_path, monkeypatch, returncode, stdout):
    root = _setup_root(tmp_path, _config([_lane("AA", "a/x")]))
    out = tmp_path / "stage.json"
    monkeypatch.setattr(mod.subprocess, "run", _fake_git(returncode, stdout, []))
    argv = ["w", "--root", str(root), "--expected-head", HEAD, "--out", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit, match="OWNER_EXACT_HEAD_MISMATCH"):
        mod.main()
    assert not out.exists()
