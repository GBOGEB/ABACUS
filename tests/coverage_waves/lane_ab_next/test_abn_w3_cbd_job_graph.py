"""Behaviour tests for tools/everred_v3/scripts/cbd_job_graph.py."""

import hashlib
import json
import runpy
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/cbd_job_graph.py"
cbd = load("tools/everred_v3/scripts/cbd_260.py", name="abn_jg_cbd_260")
mod = load(REL, name="abn_cbd_job_graph")
SCRIPT = REPO_ROOT / REL

MAIN = "a" * 40
SHA1 = "b" * 40
SHA2 = "c" * 40


def _snapshot():
    return {
        "repository": "GBOGEB/ABACUS",
        "main_sha_at_observation": MAIN,
        "source_sha256": {"n0.json": "f" * 64},
        "unique_failed_runs": {
            1: {"sha": SHA1, "workflow": "CI"},
            2: {"sha": SHA2, "workflow": "CI"},
            3: {"sha": SHA2, "workflow": "Docs"},
        },
        "rows": [
            {"pr": 20, "failed_runs": [{"run_id": 1}, {"run_id": 3}]},
            {"pr": 21, "failed_runs": [{"run_id": 2}]},
            {"pr": 22, "failed_runs": [{"run_id": 1}]},
        ],
    }


PYTEST_STEP = {"number": 4, "name": "pytest"}


def _job(jid, name="tests", step=PYTEST_STEP):
    return {
        "job_id": jid,
        "job_name": name,
        "first_failed_step": dict(step) if step else None,
        "step_causality": "UNATTRIBUTED",
    }


def _bound(sha, workflow, jobs, attempt=1):
    return {
        "status": mod.BOUND,
        "head_sha": sha,
        "workflow": workflow,
        "trust": mod.TRUST,
        "run_attempt": attempt,
        "failed_jobs": jobs,
        "failed_job_count": len(jobs),
        "first_red_causal_root": None,
        "full_log_read": False,
    }


def _withheld():
    return {
        "status": mod.WITHHELD,
        "failed_jobs": None,
        "first_red_causal_root": None,
        "full_log_read": False,
    }


def _native():
    return {
        "1": _bound(SHA1, "CI", [_job(11), _job(12, "Summary rollup", step=None)]),
        "2": _bound(SHA2, "CI", [_job(21)], attempt=3),
        "3": _withheld(),
    }


# --- primitives ---------------------------------------------------------------------


def test_require_canonical_digest():
    mod.require(True, "unused")
    with pytest.raises(ValueError, match="nope"):
        mod.require(False, "nope")
    assert mod.canonical({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    assert mod.digest([1]) == hashlib.sha256(b"[1]").hexdigest()


# --- analyze ------------------------------------------------------------------------


def test_analyze_projects_signatures_metrics_and_graph():
    dag = mod.analyze(_snapshot(), _native())
    assert dag["repository"] == "GBOGEB/ABACUS"
    assert dag["main_sha_at_N0"] == MAIN
    m = dag["metrics"]
    assert m["runs_requested"] == 3
    assert m["runs_bound"] == 2
    assert m["runs_withheld"] == 1
    assert m["failed_job_observations"] == 3
    assert m["jobs_with_failed_step"] == 2
    assert m["jobs_without_failed_step"] == 1
    assert m["bound_runs_without_failure_job"] == 0
    assert m["candidate_step_signatures"] == 2
    assert m["run_attempt_histogram"] == {"1": 1, "3": 1}
    assert m["formal_closures_delta"] == 0
    top, second = dag["candidate_signatures"]
    assert top["manifestations"] == 2
    assert top["run_ids"] == [1, 2]
    assert top["affected_prs"] == [20, 21, 22]
    assert top["pr_reach_upper_bound"] == 3
    assert top["treatment"] == "REQUIRES_LOG_LEVEL_CAUSAL_REVIEW"
    assert top["priority_rank_by_observation_frequency"] == 1
    assert second["first_failed_step"] == "UNKNOWN_FIRST_FAILED_STEP"
    assert second["treatment"] == "DOWNSTREAM_SUSPECT"
    assert second["priority_rank_by_observation_frequency"] == 2
    ids = [n["id"] for n in dag["graph"]["nodes"]]
    assert ids == sorted(ids)
    assert "run:3" in ids and "pr:21" in ids and "job:21" in ids
    edge_types = {e["type"] for e in dag["graph"]["edges"]}
    assert edge_types == {
        "PR_HAS_RUN_ASSOCIATION",
        "RUN_HAS_FAILED_JOB",
        "FIRST_FAILED_STEP_SIGNATURE",
    }
    assert dag["safety"]["candidate_is_not_confirmed_root"] is True


def test_analyze_feedback_gate_and_empty_job_list():
    snap = _snapshot()
    native = _native()
    native["1"] = _bound(SHA1, "CI", [_job(11, "Feedback Gate check")])
    native["2"] = _bound(SHA2, "CI", [])
    dag = mod.analyze(snap, native)
    assert dag["metrics"]["bound_runs_without_failure_job"] == 1
    (only,) = dag["candidate_signatures"]
    assert only["treatment"] == "DOWNSTREAM_SUSPECT"


def _mut_obs(rid, key, value):
    def apply(native):
        native[rid][key] = value

    return apply


def _mut_job(key, value):
    def apply(native):
        native["1"]["failed_jobs"][0][key] = value

    return apply


def _dup_job(native):
    native["2"]["failed_jobs"][0]["job_id"] = 11


def _job_not_dict(native):
    native["1"]["failed_jobs"][0] = "job"


@pytest.mark.parametrize(
    "mutate,reason",
    [
        (_mut_obs("1", "status", "OK"), "invalid native status"),
        (_mut_obs("1", "first_red_causal_root", "R"), "root confirmation"),
        (_mut_obs("1", "full_log_read", True), "full-log claim"),
        (_mut_obs("3", "failed_jobs", []), "withheld readback carries"),
        (_mut_obs("3", "failed_job_count", 0), "withheld readback carries"),
        (_mut_obs("1", "head_sha", SHA2), "source or trust"),
        (_mut_obs("1", "workflow", "Docs"), "source or trust"),
        (_mut_obs("1", "trust", "TRUSTED"), "source or trust"),
        (_mut_obs("1", "run_attempt", 0), "invalid run attempt"),
        (_mut_obs("1", "run_attempt", True), "invalid run attempt"),
        (_mut_obs("1", "failed_job_count", 9), "job denominator"),
        (_mut_obs("1", "failed_jobs", "x"), "job denominator"),
        (_job_not_dict, "invalid failure job"),
        (_mut_job("job_id", 0), "missing or duplicate job"),
        (_dup_job, "missing or duplicate job"),
        (_mut_job("step_causality", "ROOT"), "forged causal"),
        (_mut_job("job_name", " "), "missing job name"),
        (_mut_job("first_failed_step", {"number": 0, "name": "x"}), "malformed"),
        (_mut_job("first_failed_step", {"number": 1, "name": ""}), "malformed"),
        (_mut_job("first_failed_step", ["x"]), "malformed"),
    ],
)
def test_analyze_rejects(mutate, reason):
    native = _native()
    mutate(native)
    with pytest.raises(ValueError, match=reason):
        mod.analyze(_snapshot(), native)


def test_analyze_rejects_bad_native_container():
    with pytest.raises(ValueError, match="native must be mapping"):
        mod.analyze(_snapshot(), [])
    native = _native()
    del native["3"]
    with pytest.raises(ValueError, match="census mismatch"):
        mod.analyze(_snapshot(), native)
    native = _native()
    native["3"] = None
    with pytest.raises(ValueError, match="invalid native observation"):
        mod.analyze(_snapshot(), native)


# --- render / write -----------------------------------------------------------------


def test_render_html_escapes_and_handles_missing_run():
    dag = mod.analyze(_snapshot(), _native())
    dag["candidate_signatures"][0]["job"] = "<script>x</script>"
    dag["candidate_signatures"][1]["run_ids"] = []
    page = mod.render_html(dag)
    assert "&lt;script&gt;x&lt;/script&gt;" in page
    assert "<script>x" not in page
    assert "actions/runs/1'>Run</a>" in page
    assert "href='#'>Run</a>" in page
    assert page.count("<tr><td>") == 2


def test_write_outputs_and_hashes(tmp_path):
    dag = mod.analyze(_snapshot(), _native())
    out = tmp_path / "x" / "y"
    mod.write(dag, out)
    names = sorted(p.name for p in out.iterdir())
    assert names == [
        "candidate_dag.json",
        "candidate_index.html",
        "candidate_metrics.json",
        "candidate_sipoc.json",
        "sha256.json",
    ]
    hashes = json.loads((out / "sha256.json").read_text(encoding="utf-8"))
    metrics_text = (out / "candidate_metrics.json").read_text(encoding="utf-8")
    assert hashes["candidate_metrics.json"] == (
        hashlib.sha256(metrics_text.encode("utf-8")).hexdigest()
    )
    assert json.loads(metrics_text)["runs_bound"] == 2


# --- main via real cbd_260.read_n0 --------------------------------------------------


def _n0_file(tmp_path):
    doc = dict(
        schema=cbd.SCHEMA,
        scope="PR_TRIGGERED_FIRST_PAGE_ASSOCIATION",
        job_logs_read=False,
        run_attempts_covered=None,
        authority_transfer=False,
        security_waiver=False,
        merge_admission="HOLD",
        repository="GBOGEB/ABACUS",
        main_sha_at_observation=MAIN,
        rows=[
            dict(
                pr=7,
                state="open",
                head_sha=SHA1,
                base="main",
                counts=dict(success=0, failure=1, cancelled=0, nonterminal=0),
                failed_runs=[dict(run_id=1, workflow="CI", workflow_id=3)],
            )
        ],
    )
    path = tmp_path / "n0.json"
    path.write_bytes(json.dumps(doc).encode("utf-8"))
    native = tmp_path / "native.json"
    native.write_bytes(
        json.dumps({"1": _bound(SHA1, "CI", [_job(5, "lint")])}).encode("utf-8")
    )
    return path, native


def test_main_end_to_end(tmp_path, capsys, monkeypatch):
    n0, native = _n0_file(tmp_path)
    monkeypatch.setitem(sys.modules, "cbd_260", cbd)
    out = tmp_path / "out"
    mod.main([str(n0), "--native-jobs", str(native), "--output-dir", str(out)])
    printed = json.loads(capsys.readouterr().out)
    assert printed["admission"] == "HOLD"
    assert printed["root_confirmation"] == "UNKNOWN"
    assert printed["metrics"]["failed_job_observations"] == 1
    dag = json.loads((out / "candidate_dag.json").read_text(encoding="utf-8"))
    assert dag["N0_source_sha256"]["n0.json"] == (
        hashlib.sha256(n0.read_bytes()).hexdigest()
    )


def test_script_entry_point(tmp_path, capsys, monkeypatch):
    n0, native = _n0_file(tmp_path)
    monkeypatch.setitem(sys.modules, "cbd_260", cbd)
    out = tmp_path / "out"
    argv = [str(SCRIPT), str(n0), "--native-jobs", str(native), "--output-dir"]
    monkeypatch.setattr(sys, "argv", argv + [str(out)])
    runpy.run_path(str(SCRIPT), run_name="__main__")
    assert json.loads(capsys.readouterr().out)["scope"].startswith("HISTORICAL")
    assert (out / "candidate_index.html").exists()
