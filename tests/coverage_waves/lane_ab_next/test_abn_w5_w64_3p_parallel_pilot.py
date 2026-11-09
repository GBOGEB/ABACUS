"""Behaviour tests for tools/w64_3p_parallel_pilot.py.

``generic_3pm_burndown`` is replaced by a deterministic in-memory stub so the
variant arms run without touching the repository. Thread pools are tiny and
are always joined by the module's own ``with`` block.
"""

import json
import sys
import threading
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import load


def _make_stub():
    stub = types.ModuleType("generic_3pm_burndown")
    stub.calls = []
    stub.plans = []
    lock = threading.Lock()

    def build_plan(payload, variant):
        stub.plans.append((payload, variant))
        items = [
            dict(item_id="ROOT-" + str(index), cluster=item["cluster"])
            for index, item in enumerate(payload["items"])
        ]
        return {"items": items + ["not-a-dict"]}

    def run_all_subtasks(root, item, variant):
        with lock:
            stub.calls.append((str(root), item["item_id"], variant))
        weight = len(variant)
        return {
            "root_item_id": item["item_id"],
            "wall_time_ms": 1.5,
            "median_subtask_ms": 0.5,
            "p95_subtask_ms": 0.9,
            "results": [
                {"evidence": {"evidence_yield": weight, "edge_yield": 1}},
                {"evidence": {"evidence_yield": None}},
                {"evidence": "not-a-dict"},
                "not-a-dict",
            ],
        }

    stub.build_plan = build_plan
    stub.run_all_subtasks = run_all_subtasks
    return stub


STUB = _make_stub()
_saved_path = list(sys.path)
mod = load(
    "tools/w64_3p_parallel_pilot.py",
    name="abn_w5_w64_3p_parallel_pilot",
    deps={"generic_3pm_burndown": STUB},
)
sys.path[:] = _saved_path


@pytest.fixture(autouse=True)
def _reset_stub():
    STUB.calls.clear()
    STUB.plans.clear()


def _p2():
    return {
        "findings": [
            dict(
                type="duplicate_or_competing_authority",
                family="fam-a",
                paths=["z/b.py", "a/a.py", 3],
            ),
            dict(type="other", family="fam-x", paths=["q.py"]),
            "not-a-dict",
            dict(type="duplicate_or_competing_authority", family="fam-b", paths=None),
        ]
    }


def test_p2_to_payload_filters_and_sorts():
    payload = mod.p2_to_payload(_p2())
    assert payload == {
        "items": [
            {
                "scope": "GBOGEB/ABACUS",
                "type": "duplicate_or_competing_authority",
                "cluster": "fam-a",
                "members": ["3", "a/a.py", "z/b.py"],
            },
            {
                "scope": "GBOGEB/ABACUS",
                "type": "duplicate_or_competing_authority",
                "cluster": "fam-b",
                "members": [],
            },
        ]
    }


def test_p2_to_payload_handles_missing_or_null_findings():
    assert mod.p2_to_payload({}) == {"items": []}
    assert mod.p2_to_payload({"findings": None}) == {"items": []}


def test_evidence_yield_sums_and_skips_malformed():
    run = {
        "results": [
            {"evidence": {"evidence_yield": 3, "edge_yield": "2"}},
            {"evidence": {"evidence_yield": 0, "edge_yield": None}},
            {"evidence": []},
            {},
            7,
        ]
    }
    assert mod.evidence_yield(run) == 5
    assert mod.evidence_yield({}) == 0
    assert mod.evidence_yield({"results": None}) == 0


def test_execute_variant_reports_timing_and_yield(tmp_path):
    result = mod.execute_variant(tmp_path, {"item_id": "ROOT-0"}, "3PE")
    assert result["root_item_id"] == "ROOT-0"
    assert result["variant"] == "3PE"
    assert result["wall_time_ms"] >= 0
    assert result["subtask_wall_time_ms"] == 1.5
    assert result["median_subtask_ms"] == 0.5
    assert result["p95_subtask_ms"] == 0.9
    assert result["yield"] == 4
    assert STUB.calls == [(str(tmp_path), "ROOT-0", "3PE")]


def test_execute_arm_runs_every_item_variant_pair(tmp_path):
    items = [{"item_id": "ROOT-1"}, {"item_id": "ROOT-0"}]
    arm = mod.execute_arm(tmp_path, items, "ARM_DISCRIMINATION", 2)
    assert arm["arm"] == "ARM_DISCRIMINATION"
    assert arm["chain"] == ["3PC", "3PV"]
    assert arm["workers"] == 2
    assert arm["root_item_count"] == 2
    assert arm["variant_job_count"] == 4
    assert arm["total_yield"] == 16
    order = [(r["root_item_id"], r["variant"]) for r in arm["results"]]
    assert order == [
        ("ROOT-0", "3PC"),
        ("ROOT-0", "3PV"),
        ("ROOT-1", "3PC"),
        ("ROOT-1", "3PV"),
    ]
    assert arm["p95_variant_job_ms"] >= arm["median_variant_job_ms"] >= 0
    assert sorted(STUB.calls) == sorted((str(tmp_path), r, v) for r, v in order)


def test_execute_arm_empty_items_and_zero_workers(tmp_path):
    arm = mod.execute_arm(tmp_path, [], "ARM_DISCOVERY", 0)
    assert arm["variant_job_count"] == 0
    assert arm["AHT_variant_job_ms"] == 0.0
    assert arm["median_variant_job_ms"] == 0.0
    assert arm["p95_variant_job_ms"] == 0.0
    assert arm["total_yield"] == 0
    assert arm["results"] == []


def test_execute_arm_unknown_arm_raises(tmp_path):
    with pytest.raises(KeyError):
        mod.execute_arm(tmp_path, [], "ARM_NOPE", 1)


def test_main_writes_comparison(tmp_path, monkeypatch, capsys):
    p2 = tmp_path / "p2.json"
    p2.write_text(json.dumps(_p2()), encoding="utf-8")
    out = tmp_path / "deep" / "pilot.json"
    argv = [
        "w64",
        "--p2",
        str(p2),
        "--root",
        str(tmp_path),
        "--out",
        str(out),
        "--sample",
        "1",
        "--discovery-workers",
        "1",
        "--discrimination-workers",
        "2",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    assert mod.main() == 0
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["schema_version"] == "W64-3P-PARALLEL-PILOT-1.0.0"
    assert result["mutation_allowed"] is False
    assert result["sample_root_items"] == 1
    assert result["stable_root_ids"] == ["ROOT-0"]
    assert [a["arm"] for a in result["arms"]] == ["ARM_DISCOVERY", "ARM_DISCRIMINATION"]
    assert result["comparison"]["discovery_total_yield"] == 8
    assert result["comparison"]["discrimination_total_yield"] == 8
    assert all(result["DoD"].values())
    assert STUB.plans[0][1] == "3PM"
    assert len(STUB.plans[0][0]["items"]) == 2
    printed = json.loads(capsys.readouterr().out)
    assert printed == result["comparison"]


def test_main_sample_floor_is_one(tmp_path, monkeypatch, capsys):
    p2 = tmp_path / "p2.json"
    p2.write_text(json.dumps(_p2()), encoding="utf-8")
    out = tmp_path / "pilot.json"
    argv = ["w64", "--p2", str(p2), "--root", str(tmp_path), "--out", str(out)]
    argv += ["--sample", "0", "--discovery-workers", "1"]
    argv += ["--discrimination-workers", "1"]
    monkeypatch.setattr(sys, "argv", argv)
    assert mod.main() == 0
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["sample_root_items"] == 1
    assert "discovery_wall_time_ms" in capsys.readouterr().out
