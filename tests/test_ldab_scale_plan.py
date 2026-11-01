import importlib.util
import json
import random
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "ldab_scale_plan.py"
SPEC = importlib.util.spec_from_file_location("ldab_scale_plan", SOURCE)
L = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(L)

POLICY = {
    "protected_holds": {"E999": {}},
    "batch_policy": {
        "LOW_MECHANICAL": {
            "families": ["E302", "E303", "E305", "E501", "W291", "W293"],
            "max_findings": 12,
            "max_files": 3,
        },
        "MEDIUM": {"max_findings": 4, "max_files": 1},
        "HIGH_OR_PROTECTED": {"max_findings": 1, "max_files": 1},
    },
}


def synth(n_files=60, seed=7):
    rnd = random.Random(seed)
    codes = ["E302", "W293", "E501", "F401", "F841", "E722", "E231"]
    rows = []
    for i in range(n_files):
        for _ in range(rnd.randint(1, 40)):
            rows.append((f"pkg{i % 5}/m{i}.py", rnd.randint(1, 500), rnd.choice(codes)))
    rows.append(("pkg0/broken.py", 3, "E999"))
    rows.append(("pkg0/broken.py", 9, "E501"))  # same file as protected hold
    return sorted(rows)


@pytest.mark.parametrize("workers", [1, 2, 8, 32])
def test_disjoint_complete_and_balanced(workers):
    rows = synth()
    plan = L.build_plan(rows, "a" * 40, workers, POLICY)
    assert plan["checks"]["disjoint_ownership"]
    assert plan["checks"]["sum_lanes_plus_hold_equals_total"]
    assert plan["checks"]["batched_equals_lane_findings"]
    assert plan["hold_files"] == ["pkg0/broken.py"]
    assert plan["hold_findings"] == 2  # both findings of the held file stay on HOLD
    if workers == 8:
        assert plan["metrics"]["imbalance_max_over_mean"] < 1.10


def test_batch_caps_respected():
    plan = L.build_plan(synth(), "b" * 40, 4, POLICY)
    for lane in plan["lanes"]:
        for b in lane["batches"]:
            if b["risk"] == "LOW_MECHANICAL":
                assert b["findings"] <= 12 and len(b["files"]) <= 3
                assert len({i[2] for i in b["items"]}) == 1  # single family
            else:
                assert b["findings"] <= 4 and len(b["files"]) == 1


def test_deterministic_bytes():
    a = json.dumps(L.build_plan(synth(), "c" * 40, 8, POLICY), sort_keys=True)
    b = json.dumps(L.build_plan(synth(), "c" * 40, 8, POLICY), sort_keys=True)
    assert a == b


def test_port_leases_unique_and_unobserved():
    plan = L.build_plan(synth(), "d" * 40, 16, POLICY)
    ids = [ln["port_lease"]["port_lease_id"] for ln in plan["lanes"]]
    assert len(set(ids)) == 16
    assert all(
        ln["port_lease"]["host_port"] is None for ln in plan["lanes"]
    )  # never fabricated
    assert all(
        ln["port_lease"]["docker_publish"] == "127.0.0.1::4711" for ln in plan["lanes"]
    )


@pytest.mark.parametrize("bad", ["../x.py", "/etc/passwd", ""])
def test_unsafe_paths_rejected(bad):
    with pytest.raises(ValueError):
        L.norm_path(bad)


def test_verify_detects_foreign_write_and_collision():
    plan = L.build_plan(synth(), "e" * 40, 4, POLICY)
    w0 = plan["lanes"][0]
    ok = {"worker_id": "W00", "changed_paths": w0["files"][:1]}
    bad = {"worker_id": "W01", "changed_paths": w0["files"][:1]}  # W01 edits W00's file
    assert L.verify(plan, [ok], None, None)["proposal_valid"]
    rep = L.verify(plan, [ok, bad], None, None)
    assert (
        not rep["proposal_valid"]
        and rep["ownership_violations"]
        and rep["write_collisions"]
    )


def test_delta_unknown_without_scan_identity_and_known_with():
    rows = synth()
    plan = L.build_plan(rows, "f" * 40, 4, POLICY)
    assert L.verify(plan, [], "x.py|1|E501\n", "other cmd")["net"] is None
    kept = [r for r in rows if r[2] != "W293" and r[0] != "pkg0/broken.py"]
    after = "\n".join(f"{p}|{row}|{c}" for p, row, c in kept) + "\nnew.py|1|F401\n"
    rep = L.verify(plan, [], after, plan["scan_command"])
    removed = sum(1 for r in rows if r[2] == "W293" and r[0] != "pkg0/broken.py")
    assert (
        rep["resolved"] == removed and rep["opened"] == 1 and rep["net"] == removed - 1
    )


def test_lane_scan_reconciles_with_global_scan(tmp_path):
    """Partition completeness: sum of per-lane scans == one global scan."""
    if importlib.util.find_spec("flake8") is None:
        pytest.skip("flake8 not installed")
    repo = tmp_path / "r"
    (repo / "p").mkdir(parents=True)
    for i in range(12):
        (repo / "p" / f"m{i}.py").write_text(
            "import os\n\ndef f( a ):\n  x=1\n  return a\n" * (i % 3 + 1)
        )
    rows = L.run_scan(["."], repo)
    plan = L.build_plan(rows, "9" * 40, 5, POLICY)
    results = [L.lane_scan(plan, ln["worker_id"], repo) for ln in plan["lanes"]]
    rep = L.reduce_lanes(plan, results)
    assert (
        rep["reconciled"] and rep["all_lanes_reported"] and not rep["stray_path_lanes"]
    )
    assert rep["sum_of_lanes"] == len(rows)
