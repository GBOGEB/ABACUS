"""Lane-B wave 6: everred_v3 temporal_vector, ci_latency and obligation_lineage."""

import copy
import json

import pytest

from ._l2_loader import load

tv = load("tools/everred_v3/src/temporal_vector.py")
cl = load("tools/everred_v3/src/ci_latency.py")
ol = load("tools/everred_v3/src/obligation_lineage.py")

A, B, C = "a" * 40, "b" * 40, "c" * 40
PASS_ALL = {g: "PASS" for g in tv.GATES}


# --- temporal_vector ---------------------------------------------------------------------


def _metric(sha, value, unit="pct", **basis):
    return {
        "state": "MEASURED",
        "value": value,
        "unit": unit,
        "basis": basis or {"scope": "lane_b"},
        "source": {"sha": sha, "run_id": 1, "job_id": 2},
    }


def _state(sha, ordinal, cycle=0, repo="GBOGEB/ABACUS", coords=None, admission=None):
    return {
        "repository": repo,
        "sha": sha,
        "revision_ordinal": ordinal,
        "recovery_cycle": cycle,
        "coordinates": (
            {"coverage": _metric(sha, ordinal * 1.5)} if coords is None else coords
        ),
        "admission": dict(PASS_ALL) if admission is None else admission,
    }


def _payload(states, origin=10):
    return {"schema": tv.SCHEMA, "origin_ordinal": origin, "states": states}


def test_analyze_orders_and_differences():
    states = [
        _state(C, 14, cycle=1, admission=dict(PASS_ALL, security="RED")),
        _state(A, 11),
        _state(
            B,
            12,
            coords={
                "coverage": {"state": "UNKNOWN"},
                "lint": _metric(B, 3, unit="count"),
            },
        ),
        _state(A, 5, repo="GBOGEB/CODEX"),
    ]
    result = tv.analyze(_payload(states))
    abacus = result["repositories"]["GBOGEB/ABACUS"]
    assert [i["k"] for i in abacus["indices"]] == [1, 2, 4]
    assert abacus["indices"][2]["admission"] == "HOLD"
    assert abacus["indices"][0]["admission"] == "ELIGIBLE_FOR_AUTHORITY_REVIEW"
    assert abacus["difference_matrix_sparse"][1] == [
        {"column": 1, "coefficient": -1},
        {"column": 2, "coefficient": 1},
    ]
    first, second = abacus["deltas"]
    assert first["coordinates"]["coverage"]["reason"] == "MISSING_OBSERVATION"
    assert first["coordinates"]["lint"]["reason"] == "MISSING_COORDINATE"
    assert second["revision_span"] == 2 and second["cycle_transition"] == [0, 1]
    assert second["admission_transition"] == ["ELIGIBLE_FOR_AUTHORITY_REVIEW", "HOLD"]
    assert result["repositories"]["GBOGEB/CODEX"]["deltas"] == []
    assert result["merge_authorized"] is False


def test_analyze_comparable_and_incomparable_deltas():
    comparable = tv.analyze(_payload([_state(A, 1), _state(B, 2)]))
    delta = comparable["repositories"]["GBOGEB/ABACUS"]["deltas"][0]["coordinates"][
        "coverage"
    ]
    assert delta == {"status": "COMPARABLE", "unit": "pct", "delta": 1.5}
    other_basis = _state(B, 2, coords={"coverage": _metric(B, 9, scope="other")})
    incomparable = tv.analyze(_payload([_state(A, 1), other_basis]))
    reason = incomparable["repositories"]["GBOGEB/ABACUS"]["deltas"][0]["coordinates"][
        "coverage"
    ]["reason"]
    assert reason == "INCOMPARABLE_UNIT_OR_BASIS"


def _with_metric(**changes):
    metric = _metric(A, 1.0)
    metric.update(changes)
    return [_state(A, 1, coords={"m": metric})]


@pytest.mark.parametrize(
    "payload,message",
    [
        ("x", "incorrect temporal contract schema"),
        (
            {"schema": tv.SCHEMA, "origin_ordinal": 1.0, "states": []},
            "origin must be an integer",
        ),
        (
            {"schema": tv.SCHEMA, "origin_ordinal": 0, "states": {}},
            "states array required",
        ),
        (_payload(["x"]), "invalid state"),
        (_payload([_state("A" * 40, 1)]), "invalid repository, SHA"),
        (_payload([_state(A, -1)]), "invalid repository, SHA"),
        (_payload([_state(A, 1, repo="noslash")]), "invalid repository, SHA"),
        (_payload([_state(A, 1), _state(A, 2)]), "duplicate revision identity"),
        (_payload([_state(A, 1), _state(B, 1)]), "duplicate revision identity"),
        (
            _payload([dict(_state(A, 1), coordinates=[])]),
            "coordinates mapping required",
        ),
        (
            _payload([_state(A, 1, coords={"": _metric(A, 1)})]),
            "coordinate name must be nonempty",
        ),
        (
            _payload([_state(A, 1, coords={"m": {"state": "GUESS"}})]),
            "MEASURED or UNKNOWN",
        ),
        (
            _payload([_state(A, 1, coords={"m": {"state": "UNKNOWN", "value": 1}})]),
            "cannot carry a numeric",
        ),
        (_payload(_with_metric(value=True)), "finite numeric"),
        (_payload(_with_metric(value=float("inf"))), "finite numeric"),
        (_payload(_with_metric(unit="")), "requires unit"),
        (_payload(_with_metric(basis={})), "nonempty comparability basis"),
        (_payload(_with_metric(basis={"scope": "UNKNOWN"})), "cannot be UNKNOWN"),
        (
            _payload(_with_metric(source={"sha": B, "run_id": 1, "job_id": 2})),
            "exact-source SHA",
        ),
        (
            _payload(_with_metric(source={"sha": A, "run_id": 0, "job_id": 2})),
            "exact-source SHA",
        ),
        (
            _payload(_with_metric(source={"sha": A, "run_id": 1, "job_id": 0})),
            "exact-source SHA",
        ),
        (_payload([dict(_state(A, 1), admission=None)]), "four-way admission"),
        (_payload([_state(A, 1, admission={"security": "PASS"})]), "non-compensatory"),
        (
            _payload([_state(A, 1, cycle=2), _state(B, 2, cycle=1)]),
            "recovery cycle cannot go backwards",
        ),
    ],
)
def test_analyze_rejections(payload, message):
    with pytest.raises(ValueError, match=message):
        tv.analyze(payload)


# --- ci_latency primitives ---------------------------------------------------------------------


def test_timestamp_and_duration():
    assert (
        cl.timestamp("2026-10-27T10:00:00Z").isoformat() == "2026-10-27T10:00:00+00:00"
    )
    assert cl.timestamp("2026-10-27T12:00:00+02:00").hour == 10
    for bad, message in [
        ("", "timestamp missing"),
        (None, "timestamp missing"),
        ("nope", "malformed"),
        ("2026-10-27T10:00:00", "timezone-less"),
    ]:
        with pytest.raises(ValueError, match=message):
            cl.timestamp(bad)
    assert cl.duration("2026-10-27T10:00:00Z", "2026-10-27T10:01:30.5Z") == 90.5
    with pytest.raises(ValueError, match="negative duration"):
        cl.duration("2026-10-27T10:00:01Z", "2026-10-27T10:00:00Z")


def test_percentile_and_distribution():
    assert cl.percentile([1, 2, 3, 4], 0.5) == 2.5
    assert cl.percentile([7], 0.99) == 7
    assert cl.percentile([0, 10], 1) == 10
    for values, prob, message in [
        ([1], 1.5, "invalid quantile"),
        ([1], True, "invalid quantile"),
        ([], 0.5, "nonempty sample"),
        ([1, -1], 0.5, "invalid duration sample"),
        ([1, True], 0.5, "invalid duration sample"),
    ]:
        with pytest.raises(ValueError, match=message):
            cl.percentile(values, prob)
    empty = cl.distribution([])
    assert (
        empty["status"] == "UNKNOWN_NO_NATIVE_OBSERVATIONS" and empty["median"] is None
    )
    many = cl.distribution(list(range(100)))
    assert (
        many["p95_tail_qualified"]
        and many["p99_tail_qualified"]
        and many["median"] == 49.5
    )
    few = cl.distribution([1.0, 2.0])
    assert not few["p95_tail_qualified"] and few["n"] == 2


def test_union_seconds_merges_overlaps():
    t = cl.timestamp
    intervals = [
        (t("2026-01-01T00:00:10Z"), t("2026-01-01T00:00:20Z")),
        (t("2026-01-01T00:00:00Z"), t("2026-01-01T00:00:15Z")),
        (t("2026-01-01T00:01:00Z"), t("2026-01-01T00:01:05Z")),
    ]
    assert cl._union_seconds(intervals) == 25.0
    assert cl._union_seconds([]) == 0.0


@pytest.mark.parametrize(
    "name,stage",
    [
        ("actions/upload-artifact@v4", "artifact_transfer"),
        ("Run pip install -r req.txt", "dependency_install"),
        ("actions/checkout@abc", "environment_setup"),
        ("Set up job", "environment_setup"),
        ("Run pytest -q", "test"),
        ("Run bandit", "security_scan"),
        ("Governance inventory", "governance"),
        ("Post cleanup", "other"),
    ],
)
def test_stage_classification(name, stage):
    assert cl._stage(name) == stage


# --- ci_latency.measure_run / cohort ------------------------------------------------------------

REPO = "GBOGEB/ABACUS"


def _run(**overrides):
    run = {
        "id": 7,
        "run_attempt": 1,
        "head_sha": A,
        "repository": {"full_name": REPO},
        "status": "completed",
        "conclusion": "success",
        "name": "CI",
        "event": "pull_request",
        "created_at": "2026-10-27T10:00:00Z",
        "updated_at": "2026-10-27T10:10:00Z",
    }
    run.update(overrides)
    return run


def _job(jid, start="10:01:00", end="10:05:00", steps=None, **overrides):
    job = {
        "id": jid,
        "run_id": 7,
        "head_sha": A,
        "status": "completed",
        "conclusion": "success",
        "name": f"job{jid}",
        "created_at": "2026-10-27T10:00:30Z",
        "started_at": f"2026-10-27T{start}Z",
        "completed_at": f"2026-10-27T{end}Z",
        "steps": (
            steps
            if steps is not None
            else [
                {
                    "name": "Run pytest",
                    "started_at": f"2026-10-27T{start}Z",
                    "completed_at": f"2026-10-27T{end}Z",
                },
            ]
        ),
    }
    job.update(overrides)
    return job


def test_measure_run_complete():
    receipt = cl.measure_run(
        _run(), [_job(1), _job(2, start="10:02:00", end="10:06:00")], REPO, A
    )
    assert receipt["state"] == "MEASURED" and receipt["problems"] == []
    assert receipt["workflow_wall_seconds"] == 600.0
    assert (
        receipt["pre_first_job_seconds"] == 60.0
        and receipt["post_last_job_seconds"] == 240.0
    )
    assert (
        receipt["runner_sum_seconds"] == 480.0
        and receipt["active_union_seconds"] == 300.0
    )
    assert receipt["step_stage_seconds"] == {"test": 480.0}
    assert receipt["jobs"][0]["queue_seconds"] == 30.0


def test_measure_run_partial_problems():
    steps = [
        {"name": "no times"},
        {
            "name": "outside",
            "started_at": "2026-10-27T09:00:00Z",
            "completed_at": "2026-10-27T09:01:00Z",
        },
        {
            "name": "Run bandit",
            "started_at": "2026-10-27T10:01:00Z",
            "completed_at": "2026-10-27T10:02:00Z",
        },
    ]
    jobs = [
        _job(1, steps=steps),
        _job(2, status="in_progress"),
        _job(3, started_at="garbage"),
        _job(4, start="10:09:00", end="10:20:00"),
    ]
    receipt = cl.measure_run(_run(), jobs, REPO, A)
    assert receipt["state"] == "PARTIAL"
    assert receipt["timed_job_count"] == 1
    assert receipt["step_stage_seconds"] == {"security_scan": 60.0}
    assert "JOB_NONTERMINAL" in receipt["problems"]
    assert "STEP_TIME_UNKNOWN" in receipt["problems"]
    assert any(p.startswith("STEP_TIME_INVALID") for p in receipt["problems"])
    assert any(p.startswith("JOB_TIME_UNKNOWN:malformed") for p in receipt["problems"])
    assert any(
        p.startswith("JOB_TIME_UNKNOWN:job timeline invalid")
        for p in receipt["problems"]
    )


def test_measure_run_without_timed_jobs():
    receipt = cl.measure_run(_run(), [_job(1, status="queued")], REPO, A)
    assert (
        receipt["runner_sum_seconds"] is None
        and receipt["active_union_seconds"] is None
    )
    assert (
        receipt["pre_first_job_seconds"] is None
        and receipt["post_last_job_seconds"] is None
    )


@pytest.mark.parametrize(
    "run,jobs,sha,message",
    [
        ("x", [], A, "invalid GitHub objects"),
        (_run(), [_job(1)], "short", "invalid SHA"),
        (_run(head_sha=B), [_job(1)], A, "run exact-head mismatch"),
        (
            _run(repository={"full_name": "x/y"}),
            [_job(1)],
            A,
            "run repository mismatch",
        ),
        (_run(id=0), [_job(1)], A, "invalid run ID"),
        (_run(run_attempt=0), [_job(1)], A, "invalid run attempt"),
        (_run(status="in_progress"), [_job(1)], A, "nonterminal run"),
        (_run(), [], A, "empty native job inventory"),
        (_run(), ["x"], A, "bad job record"),
        (_run(), [_job(1), _job(1)], A, "duplicate/bad job ID"),
        (_run(), [_job(1, run_id=8)], A, "cross-run job"),
        (_run(), [_job(1, head_sha=B)], A, "cross-source job"),
        (_run(), [_job(1, run_attempt=2)], A, "cross-attempt job"),
    ],
)
def test_measure_run_rejections(run, jobs, sha, message):
    with pytest.raises(ValueError, match=message):
        cl.measure_run(run, jobs, REPO, sha)


def test_cohort_and_digest():
    assert cl.cohort([])["status"] == "UNKNOWN_NO_RUNS"
    with pytest.raises(ValueError, match="invalid cohort"):
        cl.cohort("x")
    first = cl.measure_run(_run(), [_job(1)], REPO, A)
    second = cl.measure_run(_run(id=8), [_job(1, run_id=8)], REPO, A)
    summary = cl.cohort([first, second])
    assert summary["status"] == "DESCRIPTIVE_ONLY" and summary["eligible_runs"] == 2
    assert summary["population"] == [REPO, A, "CI", "pull_request"]
    assert summary["workflow_wall"]["median"] == 600.0
    other = dict(second, workflow="Other")
    assert cl.cohort([first, other])["status"] == "INCOMPARABLE_COHORT"
    with pytest.raises(ValueError, match="duplicate run attempt"):
        cl.cohort([first, copy.deepcopy(first)])
    partial = dict(first, state="PARTIAL")
    assert cl.cohort([partial])["status"] == "UNKNOWN_NO_COMPLETE_RUNS"
    assert cl.digest_receipt({"b": 1, "a": 2}) == cl.digest_receipt({"a": 2, "b": 1})
    assert len(cl.digest_receipt({})) == 64


# --- obligation_lineage -------------------------------------------------------------------------

BLOB1, BLOB2 = "1" * 40, "2" * 40
PROFILE = {
    "tool_version": "7.13.3",
    "config_digest": "cfg",
    "test_selection": "lane_b",
    "exclusions": "none",
    "instrumentation": "branch",
}


def _cov(executed, missing, arcs_hit, arcs_miss):
    return {
        "summary": {
            "num_statements": len(executed) + len(missing),
            "num_branches": len(arcs_hit) + len(arcs_miss),
        },
        "executed_lines": executed,
        "missing_lines": missing,
        "executed_branches": arcs_hit,
        "missing_branches": arcs_miss,
    }


def _report(files):
    return {"meta": {"version": "7.13.3"}, "files": files}


def _manifest(blobs, sha=A, digest="d" * 64, **overrides):
    manifest = {
        "schema": ol.SCHEMA + ".manifest",
        "repository": "GBOGEB/ABACUS",
        "source_sha": sha,
        "run_id": 5,
        "job_id": 6,
        "coverage_artifact_sha256": digest,
        "profile": dict(PROFILE),
        "file_blobs": blobs,
    }
    manifest.update(overrides)
    return manifest


def _snap(files, blobs, sha=A, **overrides):
    return ol.snapshot(_report(files), _manifest(blobs, sha=sha, **overrides))


def test_valid_path():
    assert ol.valid_path("src" + chr(92) + "pkg" + chr(92) + "m.py") == "src/pkg/m.py"
    for bad, message in [
        ("", "missing coverage path"),
        ("/abs.py", "absolute"),
        ("C:/x.py", "absolute"),
        ("a/../b.py", "unsafe"),
        ("a//b.py", "unsafe"),
    ]:
        with pytest.raises(ValueError, match=message):
            ol.valid_path(bad)


def test_snapshot_totals():
    snap = _snap(
        {"a.py": _cov([1, 2], [3], [[1, 2]], [[1, -1]]), "b.py": _cov([1], [], [], [])},
        {"a.py": BLOB1, "b.py": BLOB2},
    )
    assert snap["totals"] == {
        "statements": {"covered": 3, "eligible": 4},
        "branches": {"covered": 1, "eligible": 2},
    }
    assert snap["files"]["a.py"]["branches"]["missing"] == [[1, -1]]
    assert snap["source"]["run_id"] == 5 and snap["merge_authorized"] is False


def _file_case(**changes):
    raw = _cov([1], [2], [[1, 2]], [])
    raw.update(changes)
    return {"a.py": raw}


@pytest.mark.parametrize(
    "files,message",
    [
        ({"a.py": "x"}, "coverage file must be object"),
        (_file_case(summary=None), "missing file coverage summary"),
        (_file_case(executed_lines="x"), "invalid executed_lines"),
        (_file_case(executed_lines=[1.0]), "noninteger executed_lines"),
        (_file_case(executed_lines=[0]), "invalid executed_lines"),
        (_file_case(missing_lines=[2, 2]), "duplicate missing_lines"),
        (_file_case(executed_branches="x"), "invalid executed_branches"),
        (_file_case(executed_branches=[[1]]), "invalid arc shape"),
        (_file_case(executed_branches=[[1, "2"]]), "noninteger arc"),
        (_file_case(executed_branches=[[1, 2], [1, 2]]), "duplicate arc"),
        (_file_case(missing_lines=[1]), "contradictory statement coverage"),
        (_file_case(missing_branches=[[1, 2]]), "contradictory arc coverage"),
        (
            _file_case(summary={"num_statements": 5, "num_branches": 1}),
            "statement denominator",
        ),
        (
            _file_case(summary={"num_statements": 2, "num_branches": 4}),
            "branch denominator",
        ),
    ],
)
def test_snapshot_file_rejections(files, message):
    with pytest.raises(ValueError, match=message):
        _snap(files, {"a.py": BLOB1})


def _three_paths():
    raw = _file_case()["a.py"]
    return _report({"a.py": raw, "a" + chr(92) + "b.py": raw, "a/b.py": raw})


@pytest.mark.parametrize(
    "report,manifest,message",
    [
        ("x", {}, "invalid snapshot inputs"),
        (_report({}), _manifest({}, schema="x"), "bad manifest schema"),
        (_report({}), _manifest({}, repository="noslash"), "invalid repository"),
        (_report({}), _manifest({}, sha="short"), "invalid source SHA"),
        (_report({}), _manifest({}, run_id=0), "invalid run_id"),
        (_report({}), _manifest({}, job_id="6"), "invalid job_id"),
        (_report({}), _manifest({}, digest="x"), "invalid coverage digest"),
        (_report({}), _manifest({}, profile=None), "missing coverage comparability"),
        (
            _report({}),
            _manifest({}, profile=dict(PROFILE, exclusions="")),
            "incomplete coverage",
        ),
        (
            _report({}),
            _manifest({}, profile=dict(PROFILE, instrumentation="line")),
            "branch mode",
        ),
        ({"files": None}, _manifest({}), "coverage files missing"),
        (_report({}), _manifest({}), "empty coverage scope"),
        (
            {"files": _file_case()},
            _manifest({"a.py": BLOB1}),
            "missing Coverage.py metadata",
        ),
        (
            {"meta": {"version": "6"}, "files": _file_case()},
            _manifest({"a.py": BLOB1}),
            "instrumentor version mismatch",
        ),
        (
            _three_paths(),
            _manifest({"a.py": BLOB1, "a/b.py": BLOB1}),
            "duplicate normalized path",
        ),
        (
            _report(_file_case()),
            _manifest({"b.py": BLOB1}),
            "source blob scope mismatch",
        ),
        (_report(_file_case()), _manifest({"a.py": "nope"}), "Git blob ID missing"),
    ],
)
def test_snapshot_manifest_rejections(report, manifest, message):
    with pytest.raises(ValueError, match=message):
        ol.snapshot(report, manifest)


def test_compare_stable_gain_and_regression():
    before = _snap({"a.py": _cov([1], [2], [[1, 2]], [[1, 3]])}, {"a.py": BLOB1})
    after = _snap({"a.py": _cov([2], [1], [[1, 3]], [[1, 2]])}, {"a.py": BLOB1}, sha=B)
    delta = ol.compare(before, after)
    assert delta["status"] == "FULLY_STABLE_SOURCE_BLOB_MAPPING"
    stmts = delta["families"]["statements"]
    assert stmts["true_gain_obligation_keys"] == [{"path": "a.py", "obligation": 2}]
    assert stmts["regression_obligation_keys"] == [{"path": "a.py", "obligation": 1}]
    assert stmts["rate_delta_points_descriptive"] == 0.0
    assert stmts["source_matched_scope_percent_after"] == 100.0
    branches = delta["families"]["branches"]
    assert branches["true_gain_obligation_keys"] == [
        {"path": "a.py", "obligation": [1, 3]}
    ]


def test_compare_partial_profile_and_errors():
    before = _snap(
        {"a.py": _cov([1], [2], [], []), "old.py": _cov([1], [], [], [])},
        {"a.py": BLOB1, "old.py": BLOB1},
    )
    after = _snap(
        {"a.py": _cov([1, 2], [], [], []), "new.py": _cov([], [1], [], [])},
        {"a.py": BLOB2, "new.py": BLOB2},
        sha=B,
    )
    delta = ol.compare(before, after)
    assert delta["status"] == "PARTIALLY_ATTRIBUTABLE"
    assert delta["changed_blob_files"] == ["a.py"]
    assert (delta["added_files"], delta["retired_files"]) == (["new.py"], ["old.py"])
    assert delta["families"]["branches"]["rate_before"] is None
    assert delta["families"]["branches"]["source_matched_scope_percent_before"] is None

    other_profile = _snap(
        {"a.py": _cov([1], [2], [], [])},
        {"a.py": BLOB1},
        sha=B,
        profile=dict(PROFILE, test_selection="all"),
    )
    changed = ol.compare(before, other_profile)
    assert changed["status"] == "PROFILE_CHANGED_NO_OLD_DEBT_CREDIT"
    stmts = changed["families"]["statements"]
    assert stmts["previously_uncovered_now_covered_verified"] is None
    assert stmts["source_matched_eligible_obligations"] is None

    with pytest.raises(ValueError, match="invalid obligation snapshot"):
        ol.compare({}, before)
    foreign = copy.deepcopy(after)
    foreign["source"]["repository"] = "GBOGEB/CODEX"
    with pytest.raises(ValueError, match="cross-repository comparison"):
        ol.compare(before, foreign)
    inconsistent = _snap(
        {"a.py": _cov([1, 2, 3], [], [], []), "old.py": _cov([1], [], [], [])},
        {"a.py": BLOB1, "old.py": BLOB1},
        sha=B,
    )
    with pytest.raises(ValueError, match="inconsistent eligible obligations"):
        ol.compare(before, inconsistent)


def test_parse_artifact_verifies_digest():
    report = _report({"a.py": _cov([1], [], [], [])})
    raw = json.dumps(report).encode("utf-8")
    snap = ol.parse_artifact(
        raw, _manifest({"a.py": BLOB1}, digest=ol.source_digest(raw))
    )
    assert snap["totals"]["statements"] == {"covered": 1, "eligible": 1}
    with pytest.raises(ValueError, match="digest mismatch"):
        ol.parse_artifact(raw, _manifest({"a.py": BLOB1}))
    with pytest.raises(ValueError, match="artifact must be bytes"):
        ol.source_digest("text")
