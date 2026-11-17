"""Gap tests for scripts/cbd_rerun_wave_planner.py.

Builds a small valid snapshot and applies one mutation per fail-closed guard in
``validate``; also covers compare/plan paths (new observation, attempt rollback,
verified first-red replacement, rerun budget) and the CLI with ``--previous``.
"""

import copy
import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/cbd_rerun_wave_planner.py", name="abn_w7_cbd_rerun_wave_planner")

HEAD = "a" * 40
BASE = "b" * 40


def _url(run_id):
    return "https://github.com/GBOGEB/ABACUS/actions/runs/" + str(run_id)


def _row(run_id, pr=1, first_red=None, status="completed", conclusion="failure"):
    return {
        "pr": pr,
        "head_sha": HEAD,
        "run_id": run_id,
        "attempt": 1,
        "workflow": "ci",
        "status": status,
        "conclusion": conclusion,
        "url": _url(run_id),
        "first_red": first_red,
    }


def _first(run_id, kind="transient_runner", root="sig-a", job=7):
    return {
        "kind": kind,
        "verified": True,
        "job_id": job,
        "url": _url(run_id) + "/job/" + str(job),
        "root_signature": root,
    }


def _snapshot(rows=None, max_new_reruns=5):
    return {
        "schema": mod.SCHEMA,
        "repository": mod.REPO,
        "authority": dict(mod.AUTHORITY),
        "base_sha": BASE,
        "current_pr_heads": {"1": HEAD, "2": HEAD},
        "capacity": {
            "queued": 0,
            "in_progress": 0,
            "max_queued": 10,
            "max_in_progress": 10,
            "max_new_reruns": max_new_reruns,
            "max_attempts": 3,
        },
        "observations": rows if rows is not None else [_row(11, first_red=_first(11))],
    }


def _set(path, value):
    def apply(snap):
        node = snap
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value

    return apply


def _first_red(**changes):
    def apply(snap):
        snap["observations"][0]["first_red"].update(changes)

    return apply


@pytest.mark.parametrize(
    "mutate,message",
    [
        (_set(("repository",), "x/y"), "repository/authority mismatch"),
        (_set(("base_sha",), "nope"), "missing exact base SHA"),
        (_set(("current_pr_heads",), {}), "missing live PR heads"),
        (_set(("current_pr_heads",), {"01": HEAD}), "invalid PR source identity"),
        (_set(("capacity",), None), "missing capacity census"),
        (_set(("capacity", "queued"), -1), "invalid capacity field: queued"),
        (_set(("capacity", "max_attempts"), 0), "max_attempts cannot be zero"),
        (_set(("observations",), []), "no run observations"),
        (_set(("observations",), ["row"]), "invalid run row"),
        (_set(("observations", 0, "pr"), 9), "missing PR head binding"),
        (_set(("observations", 0, "head_sha"), "z"), "invalid run head"),
        (_set(("observations", 0, "attempt"), 0), "invalid run/attempt"),
        (_set(("observations", 0, "workflow"), ""), "missing workflow identity"),
        (_set(("observations", 0, "status"), "weird"), "invalid run state"),
        (_set(("observations", 0, "conclusion"), None), "missing terminal conclusion"),
        (_set(("observations", 0, "url"), "http://x"), "invalid native run URL"),
        (_set(("observations", 0, "first_red"), "x"), "unqualified first-red"),
        (_first_red(job_id=0), "missing native job ID"),
        (_first_red(url="http://x"), "invalid native job URL"),
        (_first_red(root_signature=""), "missing root signature"),
    ],
)
def test_validate_guards(mutate, message):
    snap = _snapshot()
    mutate(snap)
    with pytest.raises(ValueError, match=message):
        mod.validate(snap)


def test_validate_rejects_wrong_schema():
    snap = _snapshot()
    snap["schema"] = "other"
    with pytest.raises(ValueError, match="snapshot schema mismatch"):
        mod.validate(snap)
    with pytest.raises(ValueError, match="snapshot schema mismatch"):
        mod.validate(["not", "a", "dict"])


def test_classify_success_and_other_terminal_conclusions():
    snap = _snapshot([_row(71, conclusion="success"), _row(72, conclusion="cancelled")])
    actions = [p["action"] for p in mod.plan(snap)["proposals"]]
    assert actions == ["COLLECT_PROOF", "REVIEW_TERMINAL"]


def test_validate_rejects_duplicate_run_and_nonterminal_conclusion():
    snap = _snapshot([_row(11), _row(11)])
    with pytest.raises(ValueError, match="duplicate latest run identity"):
        mod.validate(snap)
    pending = _snapshot([_row(12, status="pending", conclusion="failure")])
    with pytest.raises(ValueError, match="nonterminal run cannot"):
        mod.validate(pending)


def test_validate_verified_first_red_requires_failed_terminal():
    row = _row(13, conclusion="success", first_red=_first(13))
    with pytest.raises(ValueError, match="verified first-red without failed"):
        mod.validate(_snapshot([row]))


def test_unverified_first_red_is_accepted_and_inspected():
    first = {"kind": "unknown", "verified": False}
    snap = _snapshot([_row(14, first_red=first), _row(15, first_red=None)])
    mod.validate(snap)
    result = mod.plan(snap)
    assert [p["action"] for p in result["proposals"]] == [
        "INSPECT_FIRST_RED",
        "INSPECT_FIRST_RED",
    ]


def test_plan_rerun_budget_limits_new_reruns():
    rows = [
        _row(21, pr=1, first_red=_first(21, root="r1")),
        _row(22, pr=2, first_red=_first(22, root="r2")),
    ]
    result = mod.plan(_snapshot(rows, max_new_reruns=1))
    assert [p["action"] for p in result["proposals"]] == [
        "RERUN_FAILED_JOBS",
        "WAIT_RERUN_BUDGET",
    ]
    assert result["proposed_reruns"] == 1
    assert "changes" not in result


def test_plan_with_previous_reports_new_observation():
    previous = _snapshot([_row(31)])
    current = _snapshot([_row(31), _row(32)])
    result = mod.plan(current, previous)
    assert [(c["run_id"], c["event"]) for c in result["changes"]] == [
        (32, "NEW_OBSERVATION")
    ]


def test_compare_rejects_attempt_rollback():
    previous = _snapshot([_row(41)])
    previous["observations"][0]["attempt"] = 2
    current = _snapshot([_row(41)])
    with pytest.raises(ValueError, match="attempt rollback"):
        mod.compare(previous, current)


def test_compare_rejects_replacing_verified_first_red():
    previous = _snapshot([_row(51, first_red=_first(51, root="one"))])
    current = _snapshot([_row(51, first_red=_first(51, root="two"))])
    with pytest.raises(ValueError, match="verified first-red cannot be replaced"):
        mod.compare(previous, current)


def test_main_with_previous_writes_plan(monkeypatch, tmp_path, capsys):
    snap = _snapshot([_row(61), _row(62)])
    prev = copy.deepcopy(snap)
    prev["observations"] = [_row(61)]
    snap_path = tmp_path / "snap.json"
    prev_path = tmp_path / "prev.json"
    snap_path.write_text(json.dumps(snap), encoding="utf-8")
    prev_path.write_text(json.dumps(prev), encoding="utf-8")
    out = tmp_path / "out" / "plan.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["planner", str(snap_path), "--previous", str(prev_path), "--out", str(out)],
    )
    assert mod.main() == 0
    printed = json.loads(capsys.readouterr().out)
    written = json.loads(out.read_text(encoding="utf-8"))
    assert printed["sha256"] == written["input_sha256"] == mod.fingerprint(snap)
    assert printed["backpressure"] is False
    assert written["changes"][0]["event"] == "NEW_OBSERVATION"


def test_main_without_previous(monkeypatch, tmp_path, capsys):
    snap_path = tmp_path / "snap.json"
    snap_path.write_text(json.dumps(_snapshot()), encoding="utf-8")
    out = tmp_path / "plan.json"
    monkeypatch.setattr(sys, "argv", ["planner", str(snap_path), "--out", str(out)])
    assert mod.main() == 0
    assert json.loads(capsys.readouterr().out)["proposed_reruns"] == 1
    assert "changes" not in json.loads(out.read_text(encoding="utf-8"))
