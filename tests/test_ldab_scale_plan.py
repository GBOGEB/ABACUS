import importlib.util
import json
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
            "proposal_workers": {"min": 2, "max": 8, "mode": "READ_ONLY"},
        },
        "MEDIUM": {
            "max_findings": 4,
            "max_files": 1,
            "proposal_workers": {"min": 1, "max": 4, "mode": "READ_ONLY"},
        },
        "HIGH_OR_PROTECTED": {
            "max_findings": 1,
            "max_files": 1,
            "proposal_workers": {"min": 1, "max": 2, "mode": "READ_ONLY"},
        },
    },
}
CMD = "flake8 --exit-zero --max-line-length=120"
VER = "7.4.1"


def synth(n_files=60, seed=7):
    codes = ["E302", "W293", "E501", "F401", "F841", "E722", "E231"]
    rows = []
    for i in range(n_files):
        for j in range((i * 7 + seed) % 40 + 1):  # deterministic, no RNG
            code = codes[(i * 3 + j * 5 + seed) % len(codes)]
            rows.append((f"pkg{i % 5}/m{i}.py", (i * 31 + j * 17) % 500 + 1, code))
    rows.append(("pkg0/broken.py", 3, "E999"))
    rows.append(("pkg0/broken.py", 9, "E501"))  # same file as protected hold
    return sorted(rows)


def plan_of(workers=4, risk="ALL", sha="a" * 40, ident=True, rows=None):
    return L.build_plan(
        rows if rows is not None else synth(),
        sha,
        workers,
        POLICY,
        risk=risk,
        scan_command=CMD if ident else None,
        scanner_version=VER if ident else None,
    )


@pytest.mark.parametrize(
    "workers,risk", [(1, "ALL"), (2, "ALL"), (4, "ALL"), (8, "LOW_MECHANICAL")]
)
def test_disjoint_complete_and_within_policy(workers, risk):
    plan = plan_of(workers, risk)
    chk = plan["checks"]
    assert chk["disjoint_ownership"]
    assert chk["sum_lanes_plus_hold_plus_unassigned_equals_total"]
    assert chk["batched_plus_deferred_equals_lane_findings"]
    assert chk["workers_within_policy_cap"]
    assert plan["hold_files"] == ["pkg0/broken.py"]
    assert plan["hold_findings"] == 2  # both findings of the held file stay on HOLD


def test_balance_at_policy_cap():
    assert plan_of(4, "ALL")["metrics"]["imbalance_max_over_mean"] < 1.10


# --- review finding 5: worker count must respect the owner's DAB policy ------------
@pytest.mark.parametrize(
    "workers,risk",
    [
        (5, "ALL"),
        (8, "ALL"),
        (9, "LOW_MECHANICAL"),
        (5, "MEDIUM"),
        (32, "ALL"),
        (0, "ALL"),
    ],
)
def test_workers_beyond_policy_cap_rejected(workers, risk):
    with pytest.raises(ValueError, match="workers must be"):
        plan_of(workers, risk)


def test_cli_rejects_out_of_policy_plan(tmp_path):
    raw = tmp_path / "g.raw"
    raw.write_text("a.py|1|E501\n")
    pol = tmp_path / "p.json"
    pol.write_text(json.dumps(POLICY))
    argv = ["plan", "--raw", str(raw), "--sha", "a" * 40, "--workers", "32"]
    argv += ["--policy", str(pol), "--out", str(tmp_path / "o.json")]
    assert L.main(argv) == 2
    assert not (tmp_path / "o.json").exists()


def test_risk_scope_limits_batches_and_defers_the_rest():
    plan = plan_of(8, "LOW_MECHANICAL")
    assert {b["risk"] for ln in plan["lanes"] for b in ln["batches"]} == {
        "LOW_MECHANICAL"
    }
    assert sum(ln["deferred_findings"] for ln in plan["lanes"]) > 0
    only_medium = [("z.py", 1, "F401"), ("z.py", 2, "F841")]
    plan2 = plan_of(2, "LOW_MECHANICAL", rows=only_medium)
    assert plan2["unassigned_findings"] == 2 and all(
        not ln["files"] for ln in plan2["lanes"]
    )
    assert plan2["checks"]["sum_lanes_plus_hold_plus_unassigned_equals_total"]


def test_batch_caps_respected():
    plan = plan_of(4)
    for lane in plan["lanes"]:
        for b in lane["batches"]:
            if b["risk"] == "LOW_MECHANICAL":
                assert b["findings"] <= 12 and len(b["files"]) <= 3
                assert len({i[2] for i in b["items"]}) == 1  # single family
            else:
                assert b["findings"] <= 4 and len(b["files"]) == 1


def test_deterministic_bytes():
    a = json.dumps(plan_of(4, sha="c" * 40), sort_keys=True)
    b = json.dumps(plan_of(4, sha="c" * 40), sort_keys=True)
    assert a == b


def test_port_leases_unique_and_unobserved():
    plan = plan_of(8, "LOW_MECHANICAL", sha="d" * 40)
    ids = [ln["port_lease"]["port_lease_id"] for ln in plan["lanes"]]
    assert len(set(ids)) == 8
    assert all(ln["port_lease"]["host_port"] is None for ln in plan["lanes"])
    assert all(
        ln["port_lease"]["docker_publish"] == "127.0.0.1::4711" for ln in plan["lanes"]
    )


# --- review finding 1: drive-qualified / UNC / NUL paths ---------------------------
@pytest.mark.parametrize(
    "bad",
    [
        "../x.py",
        "/etc/passwd",
        "",
        "C:/outside/a.py",
        "C:\\outside\\a.py",
        "d:rel.py",
        "//server/share/a.py",
        "\\\\server\\share\\a.py",
        "a\x00b.py",
    ],
)
def test_unsafe_paths_rejected(bad):
    with pytest.raises(ValueError):
        L.norm_path(bad)


def test_safe_paths_normalised():
    assert L.norm_path("./pkg\\sub/a.py") == "pkg/sub/a.py"


# --- review finding 4: ownership needs explicit evidence ---------------------------
def test_verify_detects_foreign_write_and_collision():
    plan = plan_of(4)
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


def test_verify_explicit_empty_changed_paths_is_valid_but_absent_is_not():
    plan = plan_of(4)
    assert L.verify(plan, [{"worker_id": "W00", "changed_paths": []}], None, None)[
        "proposal_valid"
    ]
    rep = L.verify(plan, [{"worker_id": "W00"}], None, None)
    assert not rep["proposal_valid"]
    assert rep["missing_evidence"] == [
        {"worker_id": "W00", "reason": "changed_paths_not_supplied"}
    ]
    rep = L.verify(plan, [{"worker_id": "W00", "changed_paths": None}], None, None)
    assert not rep["proposal_valid"]


def test_verify_unknown_worker_is_invalid_even_with_no_paths():
    rep = L.verify(plan_of(4), [{"worker_id": "W99", "changed_paths": []}], None, None)
    assert not rep["proposal_valid"]
    assert rep["missing_evidence"][0]["reason"] == "unknown_worker"


# --- review finding 2: delta needs producer-recorded scan identity -----------------
def _after_of(rows):
    return "\n".join(f"{p}|{row}|{c}" for p, row, c in rows) + "\n"


def test_delta_known_only_with_recorded_and_matching_identity():
    rows = synth()
    plan = plan_of(4, rows=rows)
    kept = [r for r in rows if r[2] != "W293" and r[0] != "pkg0/broken.py"]
    after = _after_of(kept) + "new.py|1|F401\n"
    removed = sum(1 for r in rows if r[2] == "W293" and r[0] != "pkg0/broken.py")
    # the extra file is not owned by any lane, so it is out of scope on both sides
    rep = L.verify(plan, [], after, CMD, VER)
    assert rep["delta_status"] == "COMPARABLE_count_by_file_and_code"
    assert rep["resolved"] == removed and rep["opened"] == 0 and rep["net"] == removed
    for cmd, ver in [("other cmd", VER), (CMD, "9.9.9"), (None, VER), (CMD, None)]:
        assert L.verify(plan, [], after, cmd, ver)["net"] is None


def test_delta_unknown_when_plan_never_recorded_identity():
    plan = plan_of(4, ident=False)
    assert plan["scan_identity"] == {"command": None, "scanner_version": None}
    rep = L.verify(plan, [], "x.py|1|E501\n", CMD, VER)  # matching text proves nothing
    assert rep["net"] is None and rep["delta_status"].startswith("UNKNOWN")


def test_delta_counts_new_findings_in_owned_files_only_in_scope():
    rows = synth()
    plan = plan_of(4, "LOW_MECHANICAL", rows=rows)
    owned = plan["lanes"][0]["files"][0]
    after = (
        _after_of([r for r in rows if r[0] != "pkg0/broken.py"]) + f"{owned}|999|E501\n"
    )
    after += f"{owned}|998|F401\n"  # MEDIUM code: out of the LOW scope
    rep = L.verify(plan, [], after, CMD, VER)
    assert rep["opened"] == 1


# --- review finding 3: reducer must check every receipt's SHA ----------------------
def _lane(plan, wid, **over):
    base = {
        "worker_id": wid,
        "exact_sha": plan["exact_sha"],
        "seconds": 1.0,
        "findings": next(
            ln["findings"] for ln in plan["lanes"] if ln["worker_id"] == wid
        ),
        "stray_paths": [],
        "scanner_version": VER,
    }
    base.update(over)
    return base


def test_reduce_accepts_complete_matching_lanes():
    plan = plan_of(4)
    rep = L.reduce_lanes(plan, [_lane(plan, ln["worker_id"]) for ln in plan["lanes"]])
    assert rep["reconciled"] and rep["scanner_version_status"] == "MATCH"
    assert rep["sha_mismatch_lanes"] == []


def test_reduce_rejects_receipt_from_another_commit():
    plan = plan_of(4)
    lanes = [_lane(plan, ln["worker_id"]) for ln in plan["lanes"]]
    lanes[1]["exact_sha"] = "b" * 40  # same worker id, same count, wrong commit
    rep = L.reduce_lanes(plan, lanes)
    assert not rep["reconciled"] and rep["sha_mismatch_lanes"] == ["W01"]
    assert rep["sum_of_lanes"] == rep["expected_in_lanes"]


def test_reduce_rejects_missing_sha_duplicates_and_version_mismatch():
    plan = plan_of(4)
    lanes = [_lane(plan, ln["worker_id"]) for ln in plan["lanes"]]
    no_sha = [dict(x) for x in lanes]
    del no_sha[0]["exact_sha"]
    assert not L.reduce_lanes(plan, no_sha)["reconciled"]
    dup = lanes[:3] + [dict(lanes[0])]
    rep = L.reduce_lanes(plan, dup)
    assert not rep["reconciled"] and rep["duplicate_worker_ids"] == ["W00"]
    other_ver = [
        _lane(plan, ln["worker_id"], scanner_version="9.9.9") for ln in plan["lanes"]
    ]
    rep = L.reduce_lanes(plan, other_ver)
    assert not rep["reconciled"] and rep["scanner_version_status"] == "MISMATCH"


def test_reduce_version_unknown_when_plan_did_not_record_it():
    plan = plan_of(4, ident=False)
    rep = L.reduce_lanes(plan, [_lane(plan, ln["worker_id"]) for ln in plan["lanes"]])
    assert rep["reconciled"] and rep["scanner_version_status"].startswith("UNKNOWN")


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
    plan = L.build_plan(
        rows, "9" * 40, 4, POLICY, scan_command=CMD, scanner_version=L.scanner_version()
    )
    results = [L.lane_scan(plan, ln["worker_id"], repo) for ln in plan["lanes"]]
    rep = L.reduce_lanes(plan, results)
    assert (
        rep["reconciled"] and rep["all_lanes_reported"] and not rep["stray_path_lanes"]
    )
    assert rep["scanner_version_status"] == "MATCH"
    assert rep["sum_of_lanes"] == len(rows)
