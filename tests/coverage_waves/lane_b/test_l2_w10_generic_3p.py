"""Lane-B wave 10: generic 3P batch, rollup and pipeline (fake burndown engine)."""

import json
import sys
import types

import pytest

from ._l2_loader import load

SUBTASKS = ["identity", "relatives", "authority", "information", "risk"]
CALLS = []
GATE_KEYS = (
    "robust_distribution",
    "paired_pre_post",
    "paired_pre_post_preferred",
    "runner_arm_comparison",
    "runner_arm_preferred",
    "covariance",
    "empirical_PCA",
    "empirical_BT",
    "empirical_BT_preferred",
    "multivariable_model",
)


def _stable_item_id(item):
    return "root-" + str(item.get("name", "?"))


def _run_subtask(root, item, subtask):
    CALLS.append(("one", item["item_id"], subtask))
    return {
        "item_id": item["item_id"],
        "subtask": subtask,
        "duration_ms": 2.0,
        "evidence": {"evidence_yield": 1, "edge_yield": 0.5},
    }


def _run_all_subtasks(root, item):
    CALLS.append(("all", item["item_id"]))
    return {
        "item_id": item["item_id"],
        "results": [_run_subtask(root, item, s) for s in SUBTASKS],
    }


def _build_plan(payload):
    return {"plan_items": len(payload.get("items", []))}


fake_burndown = types.ModuleType("generic_3pm_burndown")
fake_burndown.SUBTASKS = SUBTASKS
fake_burndown.stable_item_id = _stable_item_id
fake_burndown.run_subtask = _run_subtask
fake_burndown.run_all_subtasks = _run_all_subtasks
fake_burndown.build_plan = _build_plan

fake_w64 = types.ModuleType("w64_duplicate_queue_to_3p")
fake_w64.convert = lambda p2: {"items": [{"name": n} for n in p2["names"]]}

batch = load("tools/generic_3p_batch.py", deps={"generic_3pm_burndown": fake_burndown})
rollup = load("tools/generic_3p_rollup.py")
pipe = load(
    "tools/generic_3p_pipeline.py",
    deps={
        "generic_3pm_burndown": fake_burndown,
        "generic_3p_batch": batch,
        "generic_3p_rollup": rollup,
        "w64_duplicate_queue_to_3p": fake_w64,
    },
)


@pytest.fixture(autouse=True)
def _reset_calls():
    CALLS.clear()


def _write_items(tmp_path, items):
    path = tmp_path / "items.json"
    path.write_text(json.dumps({"items": items}), encoding="utf-8")
    return path


# --------------------------------------------------------------------- batch


def test_load_items_keeps_only_dicts(tmp_path):
    path = _write_items(tmp_path, [{"name": "a"}, "junk", 3, {"name": "b"}])
    assert batch.load_items(path) == [{"name": "a"}, {"name": "b"}]


def test_load_items_missing_key_is_empty(tmp_path):
    path = tmp_path / "x.json"
    path.write_text("{}", encoding="utf-8")
    assert batch.load_items(path) == []


def test_load_items_rejects_non_list(tmp_path):
    path = tmp_path / "x.json"
    path.write_text(json.dumps({"items": {"a": 1}}), encoding="utf-8")
    with pytest.raises(TypeError, match="items must be a list"):
        batch.load_items(path)


def test_aggregate_all_mode_skips_bad_results_and_evidence():
    records = [
        {
            "results": [
                {"duration_ms": 4, "evidence": {"evidence_yield": 2, "edge_yield": 1}},
                "not-a-dict",
                {"duration_ms": None, "evidence": "bad"},
                {"duration_ms": 10, "evidence": {"evidence_yield": None}},
            ]
        },
        {"results": None},
        {},
    ]
    out = batch.aggregate(records, "all", None)
    assert out == {
        "mode": "all",
        "subtask": None,
        "record_count": 3,
        "subtask_observations": 3,
        "median_subtask_ms": 4.0,
        "p95_subtask_ms": 10.0,
        "evidence_yield": 2.0,
        "edge_yield": 1.0,
    }


def test_aggregate_single_mode_and_bad_evidence():
    records = [
        {"duration_ms": 3, "evidence": {"evidence_yield": 1, "edge_yield": 2}},
        {"duration_ms": 5, "evidence": None},
    ]
    out = batch.aggregate(records, "single_subtask", "risk")
    assert out["subtask"] == "risk"
    assert out["median_subtask_ms"] == 4.0
    assert out["p95_subtask_ms"] == 5.0
    assert (out["evidence_yield"], out["edge_yield"]) == (1.0, 2.0)


def test_aggregate_empty_records():
    out = batch.aggregate([], "all", None)
    assert out["median_subtask_ms"] == 0.0 and out["p95_subtask_ms"] == 0.0
    assert out["subtask_observations"] == 0


def test_batch_main_all_subtasks(tmp_path, capsys):
    inp = _write_items(tmp_path, [{"name": "a"}, {"name": "b"}])
    out = tmp_path / "deep" / "out.json"
    argv = ["--input", str(inp), "--root", str(tmp_path), "--out", str(out)]
    assert batch.main(argv + ["--all-subtasks"]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["mode"] == "all" and data["subtask"] is None
    assert data["schema_version"] == "GENERIC-3P-BATCH-1.0.0"
    assert data["item_count"] == 2 and data["read_only"] is True
    assert data["subtask_observations"] == 10
    assert data["evidence_yield"] == 10.0 and data["edge_yield"] == 5.0
    assert [r["item_id"] for r in data["records"]] == ["root-a", "root-b"]
    printed = json.loads(capsys.readouterr().out)
    assert printed["item_count"] == 2 and printed["out"] == str(out)


def test_batch_main_single_subtask(tmp_path):
    inp = _write_items(tmp_path, [{"name": "a"}])
    out = tmp_path / "out.json"
    argv = ["--input", str(inp), "--out", str(out), "--subtask", "risk"]
    assert batch.main(argv) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["mode"] == "single_subtask" and data["subtask"] == "risk"
    assert CALLS == [("one", "root-a", "risk")]


def test_batch_main_requires_mode(tmp_path):
    inp = _write_items(tmp_path, [])
    with pytest.raises(SystemExit):
        batch.main(["--input", str(inp), "--out", str(tmp_path / "o.json")])


def test_batch_main_reads_sys_argv(tmp_path, monkeypatch):
    inp = _write_items(tmp_path, [])
    out = tmp_path / "o.json"
    argv = ["batch", "--input", str(inp), "--out", str(out), "--subtask", "identity"]
    monkeypatch.setattr(sys, "argv", argv)
    assert batch.main() == 0
    assert json.loads(out.read_text(encoding="utf-8"))["item_count"] == 0


# -------------------------------------------------------------------- rollup


def test_load_jsonl_missing_file(tmp_path):
    assert rollup.load_jsonl(tmp_path / "nope.jsonl") == []


def test_load_jsonl_skips_blank_and_non_dict(tmp_path):
    path = tmp_path / "h.jsonl"
    path.write_text('{"a": 1}\n\n   \n[1, 2]\n{"b": 2}\n', encoding="utf-8")
    assert rollup.load_jsonl(path) == [{"a": 1}, {"b": 2}]


@pytest.mark.parametrize("num, den, expected", [(1, 2, 0.5), (5, 0, 0.0), (0, 0, 0.0)])
def test_safe_rate(num, den, expected):
    assert rollup.safe_rate(num, den) == expected


@pytest.mark.parametrize(
    "values, q, expected",
    [
        ([], 0.5, None),
        ([7.0], 0.95, 7.0),
        ([3.0, 1.0, 2.0, 5.0, 4.0], 0.5, 3.0),
        ([1.0, 2.0], 0.5, 1.5),
        ([0.0, 10.0], 0.95, 9.5),
    ],
)
def test_percentile(values, q, expected):
    assert rollup.percentile(values, q) == expected


def test_statistical_eligibility_low():
    low = rollup.statistical_eligibility(0, 0, 0, 0, 5, 0)
    assert low["descriptive"] is True
    assert [k for k in GATE_KEYS if low[k]] == []
    assert low["covariance_required_n"] == 50 and low["pca_required_n"] == 50
    assert low["multivariable_required_n"] == 50


def test_statistical_eligibility_high():
    high = rollup.statistical_eligibility(60, 30, 30, 100, 2, 5)
    assert [k for k in GATE_KEYS if not high[k]] == []
    assert high["covariance_required_n"] == 30


def test_statistical_eligibility_bt_needs_positives():
    assert rollup.statistical_eligibility(60, 0, 0, 0, 5, 4)["empirical_BT"] is False


def test_build_rollup_empty():
    out = rollup.build_rollup([])
    assert out["history_records"] == 0 and out["pulse_records"] == 0
    assert out["DMAIC"]["D"] == {"initial_queue": 0.0, "root_scope_frozen": False}
    assert out["AHT"]["AHT_item_ms"] is None and out["AHT"]["p95_item_ms"] is None
    assert out["quality"]["mean_rework_rate"] is None
    assert out["progress"]["mean_queue_delta_per_pulse"] == 0.0
    assert out["DoV"]["queue_DoV_candidate"] is False
    assert out["convergence_signal"] == "NOT_YET_ACCELERATING"


def _pulse(ids, wall, qb, qa, **extra):
    row = {
        "event": "PULSE",
        "root_item_ids": ids,
        "median_item_ms": 10,
        "wall_time_ms": wall,
        "rework_rate": 0.1,
        "false_positive_rate": 0.0,
        "evidence_yield": 2,
        "edge_yield": 1,
        "queue_before": qb,
        "queue_after": qa,
        "blockers_before": qb,
        "blockers_after": qa,
        "positive_outcome": True,
        "paired_pre_post": True,
        "runner_arm_comparison": True,
    }
    row.update(extra)
    return row


def test_build_rollup_accelerating_to_queue_zero():
    rows = [
        {"event": "baseline", "queue_before": 4},
        _pulse(["r1"], 3_600_000, 4, 3),
        _pulse(["r2", "r3", "r4"], 3_600_000, 3, 0),
    ]
    out = rollup.build_rollup(rows, variables=2)
    prog = out["progress"]
    assert out["history_records"] == 3 and out["pulse_records"] == 2
    assert prog["initial_queue"] == 4.0 and prog["current_queue"] == 0.0
    assert prog["queue_burndown_fraction"] == 1.0
    assert prog["terminal_sample_n"] == 4
    assert prog["convergence_velocity_items_per_hour"] == 2.0
    assert prog["convergence_acceleration_items_per_hour2"] == 1.0
    assert prog["mean_queue_delta_per_pulse"] == 2.0
    assert prog["mean_blocker_delta_per_pulse"] == 2.0
    assert out["AHT"]["AHT_item_ms"] == 10
    assert out["AHT"]["p95_wall_time_ms"] == 3_600_000
    assert out["quality"]["mean_evidence_yield"] == 2
    assert out["DoV"]["queue_DoV_candidate"] is True
    assert out["convergence_signal"] == "IMPROVING"
    assert out["DMAIC"]["C"]["velocity_items_per_hour"] == 2.0
    assert out["DMAIC"]["D"]["root_scope_frozen"] is True


def test_build_rollup_tolerates_missing_and_non_numeric_fields():
    rows = [
        {
            "event": "PULSE",
            "root_item_ids": None,
            "wall_time_ms": "slow",
            "queue_before": None,
            "queue_after": 1,
            "blockers_before": 1,
            "blockers_after": None,
            "positive_outcome": "yes",
        }
    ]
    out = rollup.build_rollup(rows)
    assert out["progress"]["terminal_sample_n"] == 0
    assert out["progress"]["current_queue"] == 1.0
    assert out["progress"]["mean_queue_delta_per_pulse"] == 0.0
    assert out["statistical_eligibility"]["empirical_BT"] is False
    assert out["AHT"]["median_wall_time_ms"] is None


def test_build_rollup_non_numeric_baseline_queue_crashes():
    """production_defect: build_rollup skips a non-numeric queue_before inside
    the pulse loop but then calls float() on rows[0]["queue_before"] without a
    type check, so a string value crashes with ValueError; this test fails once
    fixed."""
    rows = [{"event": "PULSE", "queue_before": "x", "queue_after": 1}]
    with pytest.raises(ValueError, match="could not convert string to float"):
        rollup.build_rollup(rows)


def test_build_rollup_baseline_only_keeps_initial_queue():
    out = rollup.build_rollup([{"event": "BASELINE", "queue_before": 9}])
    assert out["pulse_records"] == 0
    assert out["progress"]["current_queue"] == 9.0
    assert out["progress"]["queue_burndown_fraction"] == 0.0


def test_rollup_main(tmp_path, capsys):
    hist = tmp_path / "h.jsonl"
    hist.write_text(json.dumps(_pulse(["a", "b"], 1000, 2, 0)) + "\n", encoding="utf-8")
    out = tmp_path / "sub" / "r.json"
    rc = rollup.main(["--history", str(hist), "--out", str(out), "--variables", "3"])
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "GENERIC-3P-ROLLUP-1.0.0"
    assert data["statistical_eligibility"]["covariance_required_n"] == 30
    assert json.loads(capsys.readouterr().out) == {"out": str(out), "sample_n": 2}


def test_rollup_main_reads_sys_argv(tmp_path, monkeypatch):
    out = tmp_path / "r.json"
    argv = ["rollup", "--history", str(tmp_path / "none.jsonl"), "--out", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    assert rollup.main() == 0
    assert json.loads(out.read_text(encoding="utf-8"))["history_records"] == 0


# ------------------------------------------------------------------ pipeline


class _Future:
    def __init__(self, value):
        self._value = value

    def result(self):
        return self._value


class _InlinePool:
    instances = []

    def __init__(self, max_workers):
        self.max_workers = max_workers
        _InlinePool.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def submit(self, fn, *args):
        return _Future(fn(*args))


@pytest.fixture
def inline_pool(monkeypatch):
    _InlinePool.instances.clear()
    futures = types.SimpleNamespace(ProcessPoolExecutor=_InlinePool)
    monkeypatch.setattr(pipe, "concurrent", types.SimpleNamespace(futures=futures))
    return _InlinePool


def test_run_python_invokes_interpreter(monkeypatch, tmp_path):
    seen = {}

    def fake_run(cmd, cwd, check):
        seen.update(cmd=cmd, cwd=cwd, check=check)

    monkeypatch.setattr(pipe.subprocess, "run", fake_run)
    pipe.run_python(tmp_path / "s.py", ["--x", "1"], tmp_path)
    assert seen == {
        "cmd": [pipe.sys.executable, str(tmp_path / "s.py"), "--x", "1"],
        "cwd": tmp_path,
        "check": True,
    }


def test_arm_a_runs_all_subtasks_sequentially(tmp_path):
    out = pipe.arm_a(tmp_path, [{"name": "a"}, {"name": "b"}])
    assert out["arm"] == "A" and out["item_count"] == 2
    assert out["runner_model"] == "1_runner_x_5_sequential_subtasks"
    assert out["evidence_yield"] == 10.0 and out["edge_yield"] == 5.0
    assert [r["item_id"] for r in out["records"]] == ["root-a", "root-b"]


def test_run_subtask_batch(tmp_path):
    out = pipe._run_subtask_batch(str(tmp_path), [{"name": "a"}], "risk")
    assert out["subtask"] == "risk" and out["mode"] == "single_subtask"
    assert out["records"][0]["item_id"] == "root-a"
    assert out["median_subtask_ms"] == 2.0


def test_arm_b_fans_out_one_batch_per_subtask(tmp_path, inline_pool):
    out = pipe.arm_b(tmp_path, [{"name": "a"}])
    assert inline_pool.instances[0].max_workers == 5
    assert out["arm"] == "B" and out["item_count"] == 1
    assert [b["subtask"] for b in out["batches"]] == SUBTASKS
    assert out["median_subtask_ms"] == 2.0 and out["p95_subtask_ms"] == 2.0
    assert out["evidence_yield"] == 5.0 and out["edge_yield"] == 2.5


def test_arm_b_with_no_subtasks(tmp_path, inline_pool, monkeypatch):
    monkeypatch.setattr(pipe, "SUBTASKS", [])
    out = pipe.arm_b(tmp_path, [{"name": "a"}])
    assert out["batches"] == []
    assert out["median_subtask_ms"] == 0.0 and out["p95_subtask_ms"] == 0.0
    assert out["evidence_yield"] == 0 and out["edge_yield"] == 0


def _arm(wall, ev=1, edge=2):
    return {"wall_time_ms": wall, "evidence_yield": ev, "edge_yield": edge}


@pytest.mark.parametrize(
    "a, b, speedup, pool, regression",
    [
        (_arm(300), _arm(100), 3.0, 5, False),
        (_arm(105), _arm(100), 1.05, 1, False),
        (_arm(300), _arm(100, ev=9), 3.0, 1, True),
        (_arm(300), _arm(100, edge=3), 3.0, 1, True),
        ({"wall_time_ms": 300}, {"wall_time_ms": 0}, 0.0, 1, False),
    ],
)
def test_compare_arms(a, b, speedup, pool, regression):
    out = pipe.compare_arms(a, b)
    assert out["speedup_A_over_B"] == pytest.approx(speedup)
    assert out["recommended_pool"] == pool
    assert out["recommendation"] == ("ARM_B" if pool == 5 else "ARM_A_OR_HOLD")
    assert out["quality_regression_detected"] is regression


@pytest.mark.parametrize(
    "comparison, chosen_wall, positive",
    [
        ({"recommended_pool": 5, "speedup_A_over_B": 2.0}, 50, True),
        ({"recommended_pool": 1, "speedup_A_over_B": 1.0}, 100, False),
        ({"recommended_pool": 1, "speedup_A_over_B": None}, 100, False),
    ],
)
def test_pulse_history_record_picks_arm(comparison, chosen_wall, positive):
    a = {"wall_time_ms": 100, "median_subtask_ms": 1, "p95_subtask_ms": 2}
    a["evidence_yield"] = 3
    b = {"wall_time_ms": 50, "median_subtask_ms": 4, "p95_subtask_ms": 5}
    rec = pipe.pulse_history_record(2, "abc", 3, a, b, comparison)
    assert rec["pulse"] == 2 and rec["source_sha"] == "abc"
    assert rec["sample_size_subtasks"] == 15
    assert rec["wall_time_ms"] == chosen_wall
    assert rec["runner_pool_active"] == comparison["recommended_pool"]
    assert rec["positive_outcome"] is positive
    assert rec["edge_yield"] == 0


def _fake_census_run(calls):
    def fake_run(cmd, cwd, check):
        calls.append(cmd)
        if cmd[1].endswith("w64_census_reverse_pressure.py"):
            out = cmd[cmd.index("--out") + 1]
            with open(out, "w", encoding="utf-8") as fh:
                json.dump({"names": ["a", "b"]}, fh)

    return fake_run


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_pipeline_main_end_to_end(tmp_path, monkeypatch, inline_pool, capsys):
    calls = []
    monkeypatch.setattr(pipe.subprocess, "run", _fake_census_run(calls))
    hist = tmp_path / "hist.jsonl"
    baseline = {"event": "BASELINE", "queue_before": 2}
    hist.write_text(json.dumps(baseline) + "\n", encoding="utf-8")
    argv = ["--root", str(tmp_path), "--out-dir", "out", "--history", "hist.jsonl"]
    argv += ["--repeat", "2", "--source-sha", "deadbeef"]
    assert pipe.main(argv) == 0
    out_dir = tmp_path / "out"
    assert [c[1] for c in calls] == [
        str(tmp_path / "tools" / "w64_total_repo_census.py"),
        str(tmp_path / "tools" / "w64_census_reverse_pressure.py"),
    ]
    items = _read(out_dir / "duplicate_items.json")
    assert items == {"items": [{"name": "a"}, {"name": "b"}]}
    assert _read(out_dir / "plan.json") == {"plan_items": 2}
    for n in (1, 2):
        pulse = _read(out_dir / ("pulse_%03d.json" % n))
        assert pulse["pulse"] == n
        assert pulse["arm_A"]["evidence_yield"] == 10.0
        assert pulse["arm_B"]["evidence_yield"] == 10.0
        assert pulse["history_record"]["source_sha"] == "deadbeef"
    history_text = (out_dir / "PROPOSED_HISTORY.jsonl").read_text(encoding="utf-8")
    history = history_text.splitlines()
    assert len(history) == 3
    assert json.loads(history[0])["event"] == "BASELINE"
    receipt = _read(out_dir / "PIPELINE_RECEIPT.json")
    assert receipt["repeat_count"] == 2 and receipt["root_item_count"] == 2
    assert receipt["mutation_performed"] is False
    assert [p["pulse"] for p in receipt["pulse_results"]] == [1, 2]
    assert receipt["rollup"]["history_records"] == 3
    assert _read(out_dir / "ROLLUP.json")["pulse_records"] == 2
    printed = json.loads(capsys.readouterr().out)
    assert printed == {"out_dir": str(out_dir), "repeat_count": 2, "root_item_count": 2}


def test_pipeline_main_rejects_zero_repeat(tmp_path):
    with pytest.raises(ValueError, match="--repeat must be >= 1"):
        pipe.main(["--root", str(tmp_path), "--repeat", "0"])


def test_pipeline_main_reads_sys_argv(tmp_path, monkeypatch, inline_pool):
    monkeypatch.setattr(pipe.subprocess, "run", _fake_census_run([]))
    monkeypatch.setattr(sys, "argv", ["pipe", "--root", str(tmp_path)])
    assert pipe.main() == 0
    default_out = tmp_path / "architecture" / "w64" / "pulses" / "latest"
    receipt = _read(default_out / "PIPELINE_RECEIPT.json")
    assert receipt["source_sha"] == "WORKTREE" and receipt["repeat_count"] == 1
    assert receipt["rollup"]["history_records"] == 1
