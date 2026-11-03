"""Behaviour tests for tools/everred_v3/scripts/cbd_260.py."""

import hashlib
import json
import runpy
import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/cbd_260.py"
mod = load(REL, name="abn_cbd_260")
SCRIPT = REPO_ROOT / REL

MAIN = "a" * 40
HEAD1 = "b" * 40
HEAD2 = "c" * 40


def _counts(failure, success=1, cancelled=0, nonterminal=0):
    return dict(
        success=success, failure=failure, cancelled=cancelled, nonterminal=nonterminal
    )


def _run(rid, workflow="a10-guard", wid=7):
    return dict(run_id=rid, workflow=workflow, workflow_id=wid)


def _row(pr, head, runs, state="open"):
    return dict(
        pr=pr,
        state=state,
        head_sha=head,
        base="main",
        counts=_counts(len(runs)),
        failed_runs=runs,
    )


def _doc(rows=None, main=MAIN):
    if rows is None:
        rows = [
            _row(10, HEAD1, [_run(101), _run(102, "Custom WF", 9)]),
            _row(11, HEAD2, [_run(103)], state="closed"),
        ]
    return dict(
        schema=mod.SCHEMA,
        scope="PR_TRIGGERED_FIRST_PAGE_ASSOCIATION",
        job_logs_read=False,
        run_attempts_covered=None,
        authority_transfer=False,
        security_waiver=False,
        merge_admission="HOLD",
        repository="GBOGEB/ABACUS",
        main_sha_at_observation=main,
        rows=rows,
    )


def _put(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(doc).encode("utf-8"))
    return path


# --- primitives ---------------------------------------------------------------------


def test_fail_sha_canonical_digest():
    mod.fail(True, "unused")
    with pytest.raises(ValueError, match="boom"):
        mod.fail(False, "boom")
    assert mod.sha(MAIN)
    assert not mod.sha("A" * 40)
    assert not mod.sha(123)
    assert mod.canonical({"b": 1, "a": [1, 2]}) == '{"a":[1,2],"b":1}'
    expected = hashlib.sha256(b'{"x":1}').hexdigest()
    assert mod.evidence_digest({"x": 1}) == expected


# --- read_n0 ------------------------------------------------------------------------


def test_read_n0_happy_path_with_alias(tmp_path):
    rows_a = [_row(10, HEAD1, [_run(101), _run(102, "Custom WF", 9)])]
    rows_b = [
        _row(11, HEAD2, [_run(103)], state="closed"),
        _row(12, HEAD1, [_run(101)]),
    ]
    p1 = _put(tmp_path / "a.json", _doc(rows_a))
    p2 = _put(tmp_path / "b.json", _doc(rows_b))
    snap = mod.read_n0([str(p2), p1])
    assert snap["repository"] == "GBOGEB/ABACUS"
    assert snap["main_sha_at_observation"] == MAIN
    assert set(snap["source_sha256"]) == {"a.json", "b.json"}
    assert snap["source_sha256"]["a.json"] == (
        hashlib.sha256(p1.read_bytes()).hexdigest()
    )
    assert [r["pr"] for r in snap["rows"]] == [12, 11, 10]
    assert sorted(snap["unique_failed_runs"]) == [101, 102, 103]
    assert snap["unique_failed_runs"][101]["pr"] == 12
    assert snap["duplicate_associations"] == [
        {"run_id": 101, "pr": 10, "original_pr": 12}
    ]


def _set(key, value):
    def apply(doc):
        doc[key] = value

    return apply


def _row0(key, value):
    def apply(doc):
        doc["rows"][0][key] = value

    return apply


def _run0(key, value):
    def apply(doc):
        doc["rows"][0]["failed_runs"][0][key] = value

    return apply


def _replace_row0(value):
    def apply(doc):
        doc["rows"][0] = value

    return apply


def _replace_run0(value):
    def apply(doc):
        doc["rows"][0]["failed_runs"][0] = value

    return apply


def _counts0(**kw):
    def apply(doc):
        doc["rows"][0]["counts"].update(kw)

    return apply


def _drop_count(doc):
    del doc["rows"][0]["counts"]["cancelled"]


def _repeat_run(doc):
    runs = doc["rows"][0]["failed_runs"]
    runs[1]["run_id"] = runs[0]["run_id"]


def _dup_pr(doc):
    doc["rows"][1]["pr"] = doc["rows"][0]["pr"]


def _conflict_alias(doc):
    doc["rows"][1]["failed_runs"][0]["run_id"] = 101


@pytest.mark.parametrize(
    "mutate,reason",
    [
        (_set("schema", "other"), "wrong N0 schema"),
        (_set("scope", "x"), "scope mismatch"),
        (_set("job_logs_read", True), "unproved first-page"),
        (_set("run_attempts_covered", 1), "unproved first-page"),
        (_set("authority_transfer", True), "authority promotion"),
        (_set("merge_admission", "GO"), "authority promotion"),
        (_set("repository", "x/y"), "invalid repo/main"),
        (_set("main_sha_at_observation", "short"), "invalid repo/main"),
        (_set("rows", {}), "missing cohort rows"),
        (_replace_row0([1]), "bad PR row"),
        (_row0("pr", 0), "PR head/state"),
        (_row0("pr", True), "PR head/state"),
        (_row0("state", "merged"), "PR head/state"),
        (_row0("head_sha", "zz"), "PR head/state"),
        (_row0("base", ""), "missing base ref"),
        (_row0("counts", []), "bad count shape"),
        (_drop_count, "bad count shape"),
        (_counts0(success=-1), "invalid count"),
        (_counts0(success=1.0), "invalid count"),
        (_counts0(failure=5), "denominator mismatch"),
        (_row0("failed_runs", None), "denominator mismatch"),
        (_replace_run0("x"), "bad failed run"),
        (_run0("run_id", 0), "invalid or repeated"),
        (_repeat_run, "invalid or repeated"),
        (_run0("workflow", "  "), "missing workflow"),
        (_run0("workflow", None), "missing workflow"),
        (_run0("run_attempt", 1), "forged first red"),
        (_run0("root_id", "R1"), "forged first red"),
        (_dup_pr, "duplicate PR across"),
        (_conflict_alias, "conflicting duplicate run"),
    ],
)
def test_read_n0_rejects(tmp_path, mutate, reason):
    doc = _doc()
    mutate(doc)
    path = _put(tmp_path / "n0.json", doc)
    with pytest.raises(ValueError, match=reason):
        mod.read_n0([path])


def test_read_n0_bounds_and_cross_file_checks(tmp_path):
    with pytest.raises(ValueError, match="bounded N0"):
        mod.read_n0([])
    with pytest.raises(ValueError, match="bounded N0"):
        mod.read_n0([tmp_path / ("f%d.json" % i) for i in range(33)])
    p1 = _put(tmp_path / "one" / "n0.json", _doc())
    p2 = _put(tmp_path / "two" / "n0.json", _doc())
    with pytest.raises(ValueError, match="duplicate N0 filename"):
        mod.read_n0([p1, p2])
    a = _put(tmp_path / "a.json", _doc([_row(1, HEAD1, [])]))
    b = _put(tmp_path / "b.json", _doc([_row(2, HEAD1, [])], main="d" * 40))
    with pytest.raises(ValueError, match="mixed repository"):
        mod.read_n0([a, b])


# --- project / wave_plan / render ---------------------------------------------------


def _snapshot(tmp_path):
    return mod.read_n0([_put(tmp_path / "n0.json", _doc())])


def test_project_without_native(tmp_path):
    proj = mod.project(_snapshot(tmp_path))
    assert proj["schema"] == mod.SUMMARY
    assert proj["native_job_readback_scope"] == "NOT_COLLECTED"
    m = proj["metrics"]
    assert m["prs_observed"] == 2
    assert m["prs_open_in_captured_readbacks"] == 1
    assert m["prs_closed_in_captured_readbacks"] == 1
    assert m["failed_workflow_associations"] == 3
    assert m["passed_associations"] == 2
    assert m["workflow_associations"] == 5
    assert m["distinct_failed_run_ids"] == 3
    assert m["workflow_name_buckets"] == 2
    assert m["job_readbacks_accepted"] == 0
    first, second = proj["families"]
    assert first["workflow"] == "a10-guard"
    assert first["failed_associations"] == 2
    assert first["affected_prs"] == [10, 11]
    assert first["run_ids"] == [101, 103]
    assert first["owner_scout_hint"] == mod.OWNER_HINTS["a10-guard"]
    assert first["candidate_signature"].startswith("WFL-")
    assert second["owner_scout_hint"] == "READER_SCOUT_UNALLOCATED"
    assert proj["safety"]["merge_admission"] == "HOLD"


def test_project_with_native_statuses(tmp_path):
    native = {
        101: {"status": "JOB_METADATA_BOUND"},
        102: {"status": "READBACK_WITHHELD"},
        103: {"status": "JOB_METADATA_BOUND"},
    }
    proj = mod.project(_snapshot(tmp_path), native)
    assert proj["native_job_readback_scope"].startswith("FULL_API")
    assert proj["metrics"]["job_readbacks_accepted"] == 2
    assert proj["metrics"]["job_readbacks_withheld"] == 1


def test_wave_plan_sums_top_families(tmp_path):
    proj = mod.project(_snapshot(tmp_path))
    plan = mod.wave_plan(proj)
    assert plan["source_projection_digest"] == mod.evidence_digest(proj)
    assert [p["wave"] for p in plan["p"]] == ["N0", "N1", "N2", "N3", "N4", "N5"]
    assert plan["top4_workflow_associations"] == 3
    assert plan["top6_workflow_associations"] == 3
    assert plan["independent_root_closure_forecast"] is None


def test_render_html_escapes_and_links(tmp_path):
    rows = [_row(5, HEAD1, [_run(55, "<b>evil</b>")])]
    snap = mod.read_n0([_put(tmp_path / "n0.json", _doc(rows))])
    page = mod.render_html(mod.project(snap))
    assert page.startswith("<!doctype html>")
    assert "&lt;b&gt;evil&lt;/b&gt;" in page
    assert "<b>evil</b>" not in page
    assert "actions/runs/55'>Run 55</a>" in page
    assert "pull/5'>#5</a>" in page
    assert "Failure associations" in page


# --- enrich_native ------------------------------------------------------------------


class FakeReader:
    def __init__(self, table):
        self.table = table
        self.calls = []

    def run_and_jobs(self, repo, rid, sha):
        self.calls.append((repo, rid, sha))
        value = self.table[rid]
        if isinstance(value, Exception):
            raise value
        return value


def _native_run(rid, head, name="a10-guard", **over):
    run = dict(
        id=rid,
        head_sha=head,
        name=name,
        conclusion="failure",
        run_attempt=2,
        created_at="c",
        run_started_at="s",
        updated_at="u",
    )
    run.update(over)
    return run


def test_enrich_native_bound_and_withheld(tmp_path):
    snap = _snapshot(tmp_path)
    jobs = [
        dict(id=9, conclusion="success", name="ok"),
        dict(
            id=8,
            conclusion="failure",
            name="tests",
            started_at="t0",
            completed_at="t1",
            steps=[
                dict(number=3, name="pytest", conclusion="failure"),
                dict(number="x", name="odd", conclusion="action_required"),
                dict(number=2, name="install", conclusion="timed_out"),
                dict(number=1, name="checkout", conclusion="success"),
            ],
        ),
        dict(id=7, conclusion="failure", name="nosteps", steps=None),
    ]
    reader = FakeReader(
        {
            101: (_native_run(101, HEAD1), jobs),
            102: (_native_run(102, HEAD1, name="other"), []),
            103: RuntimeError("api down"),
        }
    )
    out = mod.enrich_native(snap, reader, workers=1, limit=3)
    assert sorted(out) == [101, 102, 103]
    bound = out[101]
    assert bound["status"] == "JOB_METADATA_BOUND"
    assert bound["run_attempt"] == 2
    assert bound["failed_job_count"] == 2
    assert [j["job_id"] for j in bound["failed_jobs"]] == [7, 8]
    assert bound["failed_jobs"][0]["first_failed_step"] is None
    assert bound["failed_jobs"][1]["first_failed_step"] == {
        "number": 2,
        "name": "install",
    }
    assert bound["failed_jobs"][1]["step_causality"] == "UNATTRIBUTED"
    assert out[102]["status"] == "READBACK_WITHHELD"
    assert out[103]["status"] == "READBACK_WITHHELD"
    assert out[103]["trust"] == "NO_NATIVE_CUSTODY"
    assert ("GBOGEB/ABACUS", 103, HEAD2) in reader.calls


def test_enrich_native_rejects_bad_attempt_as_withheld(tmp_path):
    snap = mod.read_n0([_put(tmp_path / "n0.json", _doc([_row(1, HEAD1, [_run(5)])]))])
    reader = FakeReader({5: (_native_run(5, HEAD1, run_attempt=0), [])})
    out = mod.enrich_native(snap, reader)
    assert out[5]["status"] == "READBACK_WITHHELD"


@pytest.mark.parametrize(
    "kwargs,reason",
    [
        (dict(workers=0), "worker cap"),
        (dict(workers=9), "worker cap"),
        (dict(workers=2.0), "worker cap"),
        (dict(limit=0), "run bound"),
        (dict(limit=513), "run bound"),
        (dict(limit=2), "run bound exceeded"),
    ],
)
def test_enrich_native_bounds(tmp_path, kwargs, reason):
    with pytest.raises(ValueError, match=reason):
        mod.enrich_native(_snapshot(tmp_path), FakeReader({}), **kwargs)


# --- build / main -------------------------------------------------------------------


def _hash_file(path):
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def test_build_writes_outputs_and_hashes(tmp_path):
    src = _put(tmp_path / "in" / "n0.json", _doc())
    out_dir = tmp_path / "out" / "deep"
    proj = mod.build([src], out_dir)
    names = sorted(p.name for p in out_dir.iterdir())
    assert names == ["index.html", "sha256.json", "summary.json", "wave_plan.json"]
    hashes = json.loads((out_dir / "sha256.json").read_text(encoding="utf-8"))
    assert hashes["summary.json"] == _hash_file(out_dir / "summary.json")
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary == json.loads(mod.canonical(proj))


def test_build_with_native_writes_native_jobs(tmp_path):
    src = _put(tmp_path / "n0.json", _doc())
    native = {"101": {"status": "READBACK_WITHHELD"}}
    mod.build([src], tmp_path / "out", native)
    written = json.loads((tmp_path / "out" / "native_jobs.json").read_text("utf-8"))
    assert written == native
    hashes = json.loads((tmp_path / "out" / "sha256.json").read_text("utf-8"))
    assert "native_jobs.json" in hashes


def test_main_without_native(tmp_path, capsys):
    src = _put(tmp_path / "n0.json", _doc())
    mod.main([str(src), "--output-dir", str(tmp_path / "o")])
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "READ_ONLY"
    assert printed["admission"] == "HOLD"
    assert printed["metrics"]["prs_observed"] == 2
    assert not (tmp_path / "o" / "native_jobs.json").exists()


def test_main_with_native_uses_github_reader(tmp_path, capsys, monkeypatch):
    rows = [_row(1, HEAD1, [_run(5)])]
    src = _put(tmp_path / "n0.json", _doc(rows))
    fake = types.ModuleType("native_ingest")

    class GitHubReadOnly(FakeReader):
        def __init__(self):
            super().__init__({5: (_native_run(5, HEAD1), [])})

    fake.GitHubReadOnly = GitHubReadOnly
    monkeypatch.setitem(sys.modules, "native_ingest", fake)
    monkeypatch.setattr(sys, "path", list(sys.path))
    argv = [str(src), "--output-dir", str(tmp_path / "o"), "--enrich-native"]
    mod.main(argv + ["--workers", "1", "--max-native-runs", "4"])
    printed = json.loads(capsys.readouterr().out)
    assert printed["metrics"]["job_readbacks_accepted"] == 1
    native = json.loads((tmp_path / "o" / "native_jobs.json").read_text("utf-8"))
    assert native["5"]["status"] == "JOB_METADATA_BOUND"


def test_script_entry_point(tmp_path, capsys, monkeypatch):
    src = _put(tmp_path / "n0.json", _doc())
    out_dir = tmp_path / "o"
    monkeypatch.setattr(
        sys, "argv", [str(SCRIPT), str(src), "--output-dir", str(out_dir)]
    )
    runpy.run_path(str(SCRIPT), run_name="__main__")
    assert json.loads(capsys.readouterr().out)["root_closure_credit"] == 0
    assert (out_dir / "index.html").exists()
