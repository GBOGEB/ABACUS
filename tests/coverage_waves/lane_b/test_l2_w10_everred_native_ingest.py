"""Lane-B wave 10: everred_v3 native_ingest parsers (scope, run/job, zip, reports)."""

import io
import json
import types
import zipfile

import pytest

from ._l2_loader import load

fake_fcntl = types.SimpleNamespace(
    LOCK_EX=2, LOCK_UN=8, LOCK_SH=1, flock=lambda fd, op: None
)
mt = load("tools/everred_v3/src/metrics.py")
ev = load("tools/everred_v3/src/everred.py", deps={"fcntl": fake_fcntl, "metrics": mt})
ni = load("tools/everred_v3/src/native_ingest.py", deps={"everred": ev})

Err = ni.InvalidEvidence
A, B = "a" * 40, "b" * 40
REPO = "GBOGEB/ABACUS"
TS = "2026-10-01T00:00:00Z"
DIG = "d" * 64


def _scope(job_id=11):
    s = ni.checked_scope(REPO, A, 7, job_id)
    s["observed_at"] = TS
    return s


def _run(**over):
    r = {
        "id": 7,
        "head_sha": A,
        "repository": {"full_name": REPO},
        "status": "completed",
        "conclusion": "failure",
        "name": "CI",
        "run_attempt": 1,
        "created_at": TS,
    }
    r.update(over)
    return r


def _job(jid=11, **over):
    j = {
        "id": jid,
        "run_id": 7,
        "head_sha": A,
        "status": "completed",
        "conclusion": "failure",
        "name": "lint",
        "completed_at": "2026-10-01T00:05:00Z",
        "steps": [
            {"number": 1, "name": "setup", "conclusion": "success"},
            {"number": 2, "name": "flake8", "conclusion": "failure"},
            {"number": 3, "name": "slow", "conclusion": "timed_out"},
        ],
    }
    j.update(over)
    return j


def _zip(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries:
            info = name
            if not isinstance(info, zipfile.ZipInfo):
                # set the raw name after construction so no platform rewrites it
                info = zipfile.ZipInfo("placeholder")
                info.filename = name
                info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    return buf.getvalue()


# ---------------------------------------------------------------- checked_scope


def test_checked_scope_ok():
    s = ni.checked_scope(REPO, A, 7, 3)
    assert s == {
        "repository": REPO,
        "source_sha": A,
        "run_id": 7,
        "job_id": 3,
        "run_url": "https://github.com/GBOGEB/ABACUS/actions/runs/7",
    }
    assert ni.checked_scope(REPO, A, 7)["job_id"] is None


@pytest.mark.parametrize(
    "args,match",
    [
        (("bad repo", A, 7, None), "invalid repository"),
        ((None, A, 7, None), "invalid repository"),
        ((REPO, "xyz", 7, None), "invalid exact source SHA"),
        ((REPO, A, True, None), "invalid run ID"),
        ((REPO, A, 0, None), "invalid run ID"),
        ((REPO, A, 7, 0), "invalid job ID"),
        ((REPO, A, 7, "1"), "invalid job ID"),
    ],
)
def test_checked_scope_rejects(args, match):
    with pytest.raises(Err, match=match):
        ni.checked_scope(*args)


# ----------------------------------------------------------------------- _event


def test_event_uses_observed_at_and_trust_levels():
    s = _scope()
    manual = ni._event("note", s, {"x": 1}, "t")
    assert manual["occurred_at"] == TS
    assert manual["provenance"] == "manual"
    assert manual["evidence"]["trust"] == "MANUAL_UNVERIFIED"
    assert manual["evidence"]["x"] == 1
    assert manual["id"].startswith("NATIVE-") and len(manual["id"]) == 39
    obs = ni._event(
        "note", s, {}, "t", verified=True, timestamp="2026-10-02T00:00:00+02:00"
    )
    assert obs["provenance"] == "observed"
    assert obs["evidence"]["trust"] == "API_AUTHENTICATED_METADATA"
    assert obs["occurred_at"] == "2026-10-02T00:00:00+02:00"
    ev.validate_event(obs)


@pytest.mark.parametrize(
    "ts,match",
    [
        (None, "never fabricate"),
        ("2026-10-01T00:00:00", "never fabricate"),
        ("not-a-dateZ", "invalid occurrence timestamp"),
    ],
)
def test_event_timestamp_rejects(ts, match):
    s = ni.checked_scope(REPO, A, 7)
    with pytest.raises(Err, match=match):
        ni._event("note", s, {}, "t", timestamp=ts)


# -------------------------------------------------------------- events_from_run


def test_events_from_run_full():
    jobs = [
        _job(),
        _job(
            12,
            head_sha=None,
            status="in_progress",
            conclusion=None,
            completed_at=None,
            started_at="2026-10-01T00:01:00Z",
            steps=None,
        ),
        _job(13, conclusion="success", completed_at=None, steps=[]),
    ]
    out = ni.events_from_run(_run(), jobs, REPO, A, trusted=True)
    kinds = [e["kind"] for e in out]
    assert kinds == [
        "note",
        "verification",
        "occurrence",
        "occurrence",
        "verification",
        "verification",
    ]
    run_evt = out[0]
    assert run_evt["evidence"]["jobs_count"] == 3
    assert run_evt["evidence"]["complete_jobs_enumeration"] is True
    assert run_evt["provenance"] == "observed"
    j1 = out[1]["evidence"]
    assert [s["number"] for s in j1["first_red_steps"]] == [2, 3]
    assert out[1]["occurred_at"] == "2026-10-01T00:05:00Z"
    assert out[2]["evidence"]["causal_status"] == "UNCLASSIFIED"
    assert out[2]["evidence"]["identity"] == "job:11:step:2"
    assert out[4]["occurred_at"] == "2026-10-01T00:01:00Z"
    assert out[4]["evidence"]["first_red_steps"] == []
    # neither completed_at nor started_at: falls back to run created_at
    assert out[5]["occurred_at"] == TS
    for e in out:
        ev.validate_event(e)


def test_events_from_run_untrusted_and_step_occurrence_fallback():
    out = ni.events_from_run(_run(), [_job(completed_at=None)], REPO, A)
    assert all(e["provenance"] == "manual" for e in out)
    assert out[2]["occurred_at"] == TS


@pytest.mark.parametrize(
    "run,jobs,match",
    [
        ([], [], "invalid workflow run"),
        (_run(), {}, "invalid workflow run"),
        (_run(id=0), [], "invalid run ID"),
        (_run(head_sha=B), [], "run source identity mismatch"),
        (_run(repository={"full_name": "x/y"}), [], "run source identity mismatch"),
        (_run(status="weird"), [], "unrecognized run status"),
        (_run(), [_job(), _job()], "duplicate/missing job identity"),
        (_run(), [_job(jid=None)], "duplicate/missing job identity"),
        (_run(), [_job(run_id=8)], "run/job mismatch"),
        (_run(), [_job(head_sha=B)], "job SHA mismatch"),
        (_run(), [_job(status="done")], "bad job status"),
        (_run(), [_job(status="queued")], "nonterminal job cannot conclude"),
        (_run(), [_job(steps="abc")], "invalid job steps"),
    ],
)
def test_events_from_run_rejects(run, jobs, match):
    with pytest.raises(Err, match=match):
        ni.events_from_run(run, jobs, REPO, A)


# ------------------------------------------------------------- safe_zip_entries


def test_safe_zip_entries_ok_normalizes_backslash():
    data = _zip([("dir\\a.json", b"{}"), ("b.xml", b"<x/>")])
    assert ni.safe_zip_entries(data) == {"dir/a.json": b"{}", "b.xml": b"<x/>"}


@pytest.mark.parametrize(
    "name",
    ["/abs.txt", "C:/x.txt", "a/../b.txt", "a//b.txt", "dir/", ".."],
)
def test_safe_zip_entries_unsafe_paths(name):
    with pytest.raises(Err, match="unsafe artifact path"):
        ni.safe_zip_entries(_zip([(name, b"x")]))


def test_safe_zip_entries_duplicate_after_normalization():
    with pytest.raises(Err, match="duplicate artifact path"):
        ni.safe_zip_entries(_zip([("a/b", b"1"), ("a\\b", b"2")]))


def test_safe_zip_entries_symlink():
    info = zipfile.ZipInfo("link")
    info.external_attr = 0o120777 << 16
    with pytest.raises(Err, match="zip symlink prohibited"):
        ni.safe_zip_entries(_zip([(info, b"target")]))


def test_safe_zip_entries_too_many():
    data = _zip([(f"f{i}", b"") for i in range(257)])
    with pytest.raises(Err, match="too many artifact entries"):
        ni.safe_zip_entries(data)


def test_safe_zip_entries_size_limits(monkeypatch):
    with pytest.raises(Err, match="zip input too large"):
        ni.safe_zip_entries("not bytes")
    data = _zip([("big", b"\0" * 20000)])
    assert len(data) < 1000
    monkeypatch.setattr(ni, "MAX_ARTIFACT", 1000)
    with pytest.raises(Err, match="uncompressed artifact too large"):
        ni.safe_zip_entries(data)
    monkeypatch.setattr(ni, "MAX_ARTIFACT", 10)
    with pytest.raises(Err, match="zip input too large"):
        ni.safe_zip_entries(data)


# ----------------------------------------------------------------- bandit_event


def _bandit_blob(results):
    return json.dumps({"results": results}).encode()


GOOD_FINDING = {
    "filename": "src\\x.py",
    "test_id": "B101",
    "code": " assert x \n",
    "issue_text": "Use of assert",
}


def _bandit(blob, **kw):
    args = {"config_digest": DIG, "tool_version": "1.7.9", "rule_profile": "default"}
    args.update(kw)
    return ni.bandit_event(blob, _scope(), **args)


def test_bandit_event_counts_raw_and_unique():
    blob = _bandit_blob(
        [
            GOOD_FINDING,
            dict(GOOD_FINDING, filename="src/x.py"),
            dict(GOOD_FINDING, test_id="B102"),
        ]
    )
    e = _bandit(blob, trusted=True)
    evd = e["evidence"]
    assert e["kind"] == "security_census"
    assert evd["raw_findings"] == 3
    assert evd["unique_findings"] == 2
    assert evd["fingerprints"] == sorted(evd["fingerprints"])
    assert evd["normalization_version"] == "bandit-v3-fingerprint-v1"
    assert evd["verification_status"] == "SCANNER_OBSERVATION_NOT_SECURITY_DISPOSITION"
    assert e["provenance"] == "observed"
    ev.validate_event(e)


def test_bandit_event_empty_results():
    e = _bandit(_bandit_blob([]))
    assert e["evidence"]["raw_findings"] == 0
    assert e["evidence"]["fingerprints"] == []


@pytest.mark.parametrize(
    "kw,blob,match",
    [
        ({"config_digest": "abc"}, None, "config digest required"),
        ({"config_digest": None}, None, "config digest required"),
        ({"tool_version": "UNKNOWN"}, None, "scanner version required"),
        ({"tool_version": 1}, None, "scanner version required"),
        ({"rule_profile": "UNKNOWN"}, None, "rule profile required"),
        ({}, b"[]", "invalid Bandit report"),
        ({}, b'{"results": {}}', "invalid Bandit report"),
        ({}, _bandit_blob([1]), "invalid Bandit finding"),
        ({}, _bandit_blob([{"test_id": "B1"}]), "unsafe Bandit file path"),
        ({}, _bandit_blob([dict(GOOD_FINDING, filename="/etc/x")]), "unsafe Bandit"),
        ({}, _bandit_blob([dict(GOOD_FINDING, filename="D:\\x")]), "unsafe Bandit"),
        ({}, _bandit_blob([dict(GOOD_FINDING, filename="a/../x")]), "unsafe Bandit"),
        ({}, _bandit_blob([dict(GOOD_FINDING, test_id="X1")]), "missing Bandit rule"),
        ({}, _bandit_blob([dict(GOOD_FINDING, test_id=None)]), "missing Bandit rule"),
    ],
)
def test_bandit_event_rejects(kw, blob, match):
    with pytest.raises(Err, match=match):
        _bandit(blob if blob is not None else _bandit_blob([]), **kw)


# --------------------------------------------------------------- coverage_event

COV_OK = (
    b'<?xml version="1.0"?><coverage><packages><package><classes>'
    b'<class filename="a.py"><lines><line number="1" hits="3"/>'
    b'<line number="2" hits="0"/></lines></class>'
    b'<class filename="b.py"><lines><line number="1" hits="1"/></lines></class>'
    b"</classes></package></packages></coverage>"
)


def _cov(blob, **kw):
    args = {
        "config_id": "cfg",
        "selection": "all",
        "exclusions": "none",
        "tool_version": "7.6",
    }
    args.update(kw)
    return ni.coverage_event(blob, _scope(), **args)


def test_coverage_event_ok():
    e = _cov(COV_OK, trusted=True)
    evd = e["evidence"]
    assert (evd["covered"], evd["eligible"]) == (2, 3)
    assert evd["scope"] == "broad" and evd["unit"] == "lines"
    assert evd["producer"] == "cobertura_xml"
    assert e["evidence"]["identity"].startswith("coverage:")
    ev.validate_event(e)


def _cls(lines, fname='filename="a.py"'):
    return (
        b"<coverage><classes><class "
        + fname.encode()
        + b"><lines>"
        + lines
        + b"</lines></class></classes></coverage>"
    )


@pytest.mark.parametrize(
    "kw,blob,match",
    [
        ({"unit": "branches"}, COV_OK, "only Cobertura source line"),
        ({"config_id": ""}, COV_OK, "incomplete coverage scope"),
        ({"tool_version": "UNKNOWN"}, COV_OK, "incomplete coverage scope"),
        ({"selection": None}, COV_OK, "incomplete coverage scope"),
        ({}, b"<!doctype x><coverage/>", "XML entities prohibited"),
        ({}, b'<coverage><!ENTITY x "y"></coverage>', "XML entities prohibited"),
        ({}, b"<report/>", "expected Cobertura coverage XML"),
        ({}, b"<coverage/>", "coverage XML lacks classes"),
        ({}, _cls(b"", 'x="1"'), "class filename missing/unsafe"),
        ({}, _cls(b"", 'filename="/abs.py"'), "class filename missing/unsafe"),
        (
            {},
            _cls(b'<line number="1" hits="1"/><line number="1" hits="0"/>'),
            "duplicate source line",
        ),
        ({}, _cls(b""), "coverage XML lacks line evidence"),
        ({}, _cls(b'<line number="1"/>'), "invalid line hits/number"),
        ({}, _cls(b'<line number="x" hits="1"/>'), "invalid line hits/number"),
        ({}, _cls(b'<line number="1" hits="-1"/>'), "invalid line coverage counters"),
        ({}, _cls(b'<line number="0" hits="1"/>'), "invalid line coverage counters"),
    ],
)
def test_coverage_event_rejects(kw, blob, match):
    with pytest.raises(Err, match=match):
        _cov(blob, **kw)


# ----------------------------------------------------------------- junit_events

JUNIT = (
    b'<testsuites><testsuite name="s">'
    b'<testcase classname="m" name="ok"/>'
    b'<testcase classname="m" name="bad"><failure message="boom"/></testcase>'
    b'<testcase name="err"><error/></testcase>'
    b'<testcase classname="m" name="sk"><skipped/><failure message="x"/></testcase>'
    b'<testcase classname="m" name="only_skip"><skipped/></testcase>'
    b"</testsuite></testsuites>"
)


def test_junit_events_failures_only():
    out = ni.junit_events(JUNIT, _scope(), trusted=True)
    assert [e["evidence"]["test_id"] for e in out] == ["m::bad", "::err", "m::sk"]
    assert [e["evidence"]["failure_message"] for e in out] == ["boom", "", "x"]
    assert [e["evidence"]["skipped"] for e in out] == [False, False, True]
    assert [e["evidence"]["identity"] for e in out] == ["junit:1", "junit:2", "junit:3"]
    assert all(e["kind"] == "occurrence" and e["provenance"] == "observed" for e in out)


def test_junit_events_single_suite_truncates_message():
    blob = (
        b'<testsuite><testcase name="t"><failure message="'
        + b"m" * 600
        + b'"/></testcase></testsuite>'
    )
    out = ni.junit_events(blob, _scope())
    assert len(out[0]["evidence"]["failure_message"]) == 512
    assert out[0]["provenance"] == "manual"


@pytest.mark.parametrize(
    "blob,match",
    [
        (b"<!DOCTYPE t><testsuite/>", "XML entities prohibited"),
        (b"<results/>", "invalid JUnit XML root"),
    ],
)
def test_junit_events_rejects(blob, match):
    with pytest.raises(Err, match=match):
        ni.junit_events(blob, _scope())


# ---------------------------------------------------------------- runtime_event


def _rt(backend="Docker", **over):
    s = _scope()
    obj = {
        "schema": "abacus.everred.runtime.v1",
        "repository": s["repository"],
        "source_sha": s["source_sha"],
        "run_id": s["run_id"],
        "job_id": s["job_id"],
        "backend": backend,
        "exit_code": 0,
        "runner_id": "r1",
        "command_digest": DIG,
        "container_id": "c1",
        "image_digest": "sha256:" + DIG,
        "os_release": "9.4",
        "uname_release": "5.14",
    }
    obj.update(over)
    return obj


@pytest.mark.parametrize(
    "backend,over,complete",
    [
        ("Docker", {}, True),
        ("LDAB", {"container_id": None}, False),
        ("LLDB", {"exit_code": 1}, False),
        ("RHEL9", {}, True),
        ("UBI8", {"uname_release": ""}, False),
        ("RHEL8", {"command_digest": "short"}, False),
        ("UBI9", {"command_digest": 5}, False),
        ("Docker", {"runner_id": None}, False),
    ],
)
def test_runtime_event_completeness(backend, over, complete):
    e = ni.runtime_event(_rt(backend, **over), _scope(), trusted=True)
    evd = e["evidence"]
    assert evd["reported_complete"] is complete
    assert evd["backend"] == backend
    assert evd["runtime_trust"] == "GITHUB_ARTIFACT_BOUND"
    assert set(evd["identity"]) == {
        "runner_id",
        "session_id",
        "container_id",
        "image_digest",
        "os_release",
        "uname_release",
        "port_bindings",
    }
    ev.validate_event(e)


def test_runtime_event_untrusted():
    e = ni.runtime_event(_rt(), _scope())
    assert e["evidence"]["runtime_trust"] == "SELF_REPORTED_UNVERIFIED"
    assert e["provenance"] == "manual"


@pytest.mark.parametrize(
    "obj,match",
    [
        ([], "invalid runtime receipt schema"),
        (_rt(schema="v0"), "invalid runtime receipt schema"),
        (_rt(repository="x/y"), "runtime repository source mismatch"),
        (_rt(source_sha=B), "runtime source_sha source mismatch"),
        (_rt(run_id=8), "runtime run_id source mismatch"),
        (_rt(job_id=None), "runtime job_id source mismatch"),
        (_rt(backend="Windows"), "unsupported runtime backend"),
    ],
)
def test_runtime_event_rejects(obj, match):
    with pytest.raises(Err, match=match):
        ni.runtime_event(obj, _scope())
