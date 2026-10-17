"""Synthetic positive, negative, reverse and source-bound diagnostics tests."""
import copy
import json

import pytest

from tools import mip_ci_portfolio_debug as mod

A = "a" * 40
B = "b" * 40


def job(run_id, identity, *, sha=A, attempt=1, log=None, result="failure"):
    return {
        "id": identity, "run_id": run_id, "attempt": attempt, "head_sha": sha,
        "name": "CI Job", "status": "completed" if result is not None else "queued",
        "conclusion": result,
        "steps": ([{"number": 3, "name": "Dependent summary", "conclusion": "failure"},
                   {"number": 2, "name": "Install requirements", "conclusion": "failure"}]
                  if result == "failure" else []),
        "log_excerpt": log,
    }


def run(pr, rid, *, sha=A, attempt=1, result="failure", log=None, coverage=None):
    return {
        "pr": pr, "head_sha": sha, "run_id": rid, "attempt": attempt,
        "workflow": "CI/CD Test Suite", "status": "completed" if result is not None else "queued",
        "conclusion": result,
        "jobs": [job(rid, rid + 9000, sha=sha, attempt=attempt, log=log, result=result)],
        "coverage": coverage,
    }


def payload(*rows):
    return {"schema": mod.SCHEMA, "repository": mod.REPO, "observations": list(rows)}


def test_first_red_points_to_native_job_and_exact_source_line():
    evidence = job(123, 456, log="ERROR: No matching distribution found for pylint<5.0\ntests/x.py:41: error")
    f = mod.first_red(evidence)
    assert f["root_candidate"] == "PIP:pylint"
    assert f["source_location"] == {"file": "tests/x.py", "line": 41}
    assert f["failed_step"] == "Install requirements"
    assert f["failed_step_number"] == 2
    assert f["debug_url"].endswith("/actions/runs/123/job/456")
    assert f["root_confirmed"] is False


def test_root_dedup_and_same_head_rerun_are_not_source_fix():
    log = "ERROR: No matching distribution found for pylint<5.0"
    result = mod.analyze(payload(
        run(2033, 100, log=log),
        run(2033, 100, attempt=2, log=log),
        run(2076, 101, sha=B, log=log),
    ))
    assert result["metrics"]["native_run_attempts"] == 3
    assert result["metrics"]["distinct_root_candidates_not_confirmed"] == 1
    assert result["root_candidates_by_manifestation"]["PIP:pylint"] == 3
    assert result["transitions"][0]["classification"] == "UNCHANGED_HEAD_SAME_FIRST_RED"
    assert result["accepted_root_closures"] is None
    assert result["admission"] == "HOLD"


def test_new_source_and_changed_first_red_are_not_auto_closed():
    old = run(2033, 100, log="ERROR: No matching distribution found for pylint")
    new = run(2033, 200, sha=B, log="unclassified workflows: new.yml")
    transition = mod.analyze(payload(old, new))["transitions"][0]
    assert transition["classification"] == "NEW_HEAD_ROOT_TRANSITION"
    assert transition["source_changed"] is True
    assert transition["before_roots"] == ["PIP:pylint"]
    assert transition["after_roots"] == ["GOVERNANCE_INVENTORY"]


def test_docker_transient_one_retry_candidate_is_never_executed():
    text = "HTTP 502 Bad Gateway manifest from Docker registry"
    res = mod.analyze(payload(run(2026, 200, log=text)))
    assert len(res["guarded_retry_candidates"]) == 1
    assert res["guarded_retry_candidates"][0]["execute"] is False
    assert res["executed_reruns"] == 0
    res2 = mod.analyze(payload(run(2026, 200, log=text), run(2026, 200, attempt=2, log=text)))
    assert res2["guarded_retry_candidates"] == []


def test_unknown_logs_and_censored_runs_never_fabricate_root():
    res = mod.analyze(payload(run(2033, 100, log=None), run(2033, 101, result=None)))
    assert res["metrics"]["first_red_jobs"] == 1
    assert res["metrics"]["failed_runs_with_candidate_fingerprint"] == 0
    assert res["metrics"]["nonterminal"] == 1
    assert res["transitions"][0]["classification"] == "CENSORED"


def test_coverage_priority_preserves_zero_low_and_denominators():
    rows = {"source_sha": A, "files": [
        {"path": "DMAIC_V3/quick_error_fix.py", "statements": 165, "missing": 165, "branches": 56, "missing_branches": 56},
        {"path": "tools/mip_ci_gate_collector.py", "statements": 127, "missing": 12, "branches": 66, "missing_branches": 15},
        {"path": "core/partial.py", "statements": 10, "missing": 6},
    ]}
    res = mod.analyze(payload(run(2033, 10, coverage=rows)))
    v = res["coverage_priority"]
    assert [(x["path"], x["priority"]) for x in v] == [
        ("DMAIC_V3/quick_error_fix.py", "ZERO"),
        ("core/partial.py", "LOW"),
    ]
    assert v[0]["covered_statements"] == 0
    assert v[0]["missing_total"] == 221


@pytest.mark.parametrize("kind", ["wrong_sha", "false_count", "negative", "duplicate_file", "no_files"])
def test_corrupt_coverage_never_creates_zero_or_delta(kind):
    coverage = {"source_sha": A, "files": [{"path": "x.py", "statements": 10, "missing": 5}]}
    if kind == "wrong_sha":
        coverage["source_sha"] = B
    if kind == "false_count":
        coverage["files"][0]["statements"] = True
    if kind == "negative":
        coverage["files"][0]["missing"] = -1
    if kind == "duplicate_file":
        coverage["files"][0]["missing"] = -1
    if kind == "duplicate_file":
        coverage["files"].append(copy.deepcopy(coverage["files"][0]))
    if kind == "no_files":
        coverage.pop("files")
    with pytest.raises(ValueError):
        mod.analyze(payload(run(2033, 10, coverage=coverage)))


@pytest.mark.parametrize("field,value", [
    ("head_sha", "short"), ("run_id", True), ("attempt", 0),
    ("status", "weird"), ("conclusion", "success"),
])
def test_observation_invalid_identity_status_or_result_rejected(field, value):
    o = run(2033, 10)
    o[field] = value
    with pytest.raises(ValueError):
        mod.analyze(payload(o))


def test_job_mixed_source_and_duplicate_attempt_rejected():
    row = run(2033, 10)
    row["jobs"][0]["head_sha"] = B
    with pytest.raises(ValueError, match="native job run/attempt/head"):
        mod.analyze(payload(row))
    row = run(2033, 10)
    with pytest.raises(ValueError, match="duplicate native run attempt"):
        mod.analyze(payload(row, copy.deepcopy(row)))


def test_live_collector_pages_and_binds_attempt_without_rerun():
    calls = []
    def fake(path, *, token):
        calls.append(path)
        assert token == "temporary-fake-token"
        if "/pulls?" in path:
            return [{"number": 2033, "head": {"sha": A}}]
        if "/actions/runs?" in path:
            return {"workflow_runs": [{"id": 10, "run_attempt": 2, "head_sha": A,
                                       "name": "CI", "status": "completed", "conclusion": "failure"}]}
        if "/attempts/2/jobs?" in path:
            native = job(10, 20, attempt=2, log=None)
            return {"total_count": 1, "jobs": [native]}
        raise AssertionError(path)
    captured = mod.collect_live(token="temporary-fake-token", getter=fake)
    assert len(calls) == 3
    assert len(captured["observations"]) == 1
    assert captured["observations"][0]["attempt"] == 2
    assert mod.analyze(captured)["metrics"]["native_run_attempts"] == 1
    assert captured["source"] == "native-gh-rest-readonly"


def test_live_rejects_mixed_source_or_truncated_native_jobs():
    def fake(path, *, token):
        if "/pulls?" in path:
            return [{"number": 2033, "head": {"sha": A}}]
        if "/actions/runs?" in path:
            return {"workflow_runs": [{"id": 10, "run_attempt": 1, "head_sha": A, "name": "CI",
                                       "status": "completed", "conclusion": "failure"}]}
        if "/jobs?" in path:
            return {"total_count": 2, "jobs": []}
        raise AssertionError(path)
    with pytest.raises(ValueError, match="partial native jobs page"):
        mod.collect_live(token="fake", getter=fake)


def test_cli_offline_is_deterministic_and_cannot_approve(tmp_path, capsys):
    p = tmp_path / "input.json"
    o = tmp_path / "report.json"
    p.write_text(json.dumps(payload(run(2033, 10, log="unclassified workflows"))))
    assert mod.main(["--input", str(p), "--out", str(o)]) == 0
    data = json.loads(o.read_text())
    assert data["admission"] == "HOLD" and data["executed_reruns"] == 0
    assert "admission=HOLD" in capsys.readouterr().out
    original = o.read_bytes()
    assert mod.main(["--input", str(p), "--out", str(o)]) == 0
    assert o.read_bytes() == original


def test_same_head_regression_is_not_misattributed_to_source():
    before = run(2033, 100, log="ERROR: No matching distribution found for pylint")
    after = run(2033, 100, attempt=2, log="unclassified workflows")
    result = mod.analyze(payload(before, after))
    assert result["transitions"][0]["classification"] == "SAME_HEAD_RETRY_RESULT_CHANGED"
    assert result["transitions"][0]["source_changed"] is False


def test_no_logs_in_two_runs_does_not_create_root_drift():
    result = mod.analyze(payload(run(2033, 100), run(2033, 100, attempt=2)))
    assert result["transitions"][0]["classification"] == "NO_ATTRIBUTABLE_ROOT_COMPARISON"


def test_new_head_same_root_remains_open():
    first = run(2033, 100, log="unclassified workflows")
    next_head = run(2033, 101, sha=B, log="unclassified workflows")
    result = mod.analyze(payload(first, next_head))
    assert result["transitions"][0]["classification"] == "NEW_HEAD_ROOT_PERSISTS"


def test_transport_does_not_follow_redirects_or_leak_token(monkeypatch):
    import io
    captured = []

    class Response:
        status = 200
        def read(self, size=-1):
            return io.BytesIO(b'{"workflow_runs":[]}').read(size)

    class Conn:
        def __init__(self, host, timeout):
            captured.append(self)
            assert host == "api.github.com" and timeout == 25
            self.closed = False
        def request(self, method, path, headers):
            assert method == "GET" and path.startswith("/repos/GBOGEB/ABACUS/")
            assert headers["Authorization"] == "Bearer ephemeral-not-saved"
        def getresponse(self):
            return Response()
        def close(self):
            self.closed = True

    monkeypatch.setattr(mod, "HTTPSConnection", Conn)
    result = mod.github_get("/repos/GBOGEB/ABACUS/actions/runs?event=pull_request", token="ephemeral-not-saved")
    assert result == {"workflow_runs": []}
    assert captured[-1].closed
    for bad in ("https://other.example", "/repos/GBOGEB/ABACUS/../issues", "/repos/GBOGEB/ABACUS/#frag"):
        with pytest.raises(ValueError, match="unsupported GitHub path"):
            mod.github_get(bad, token="not-executed")
    assert len(captured) == 1


def test_transport_http_failure_cannot_pass_as_empty_census(monkeypatch):
    class Response:
        status = 403
    class Conn:
        closed = False
        def __init__(self, host, timeout):
            pass
        def request(self, method, path, headers):
            pass
        def getresponse(self):
            return Response()
        def close(self):
            self.closed = True
    monkeypatch.setattr(mod, "HTTPSConnection", Conn)
    with pytest.raises(ValueError, match="HTTP 403"):
        mod.github_get("/repos/GBOGEB/ABACUS/pulls?state=open", token=None)


def test_live_two_job_pages_and_total_shift_detection():
    calls = []
    def fake(path, *, token):
        calls.append(path)
        if "/pulls?" in path:
            return [{"number": 2033, "head": {"sha": A}}]
        if "/actions/runs?" in path:
            return {"workflow_runs": [{"id": 10, "run_attempt": 1, "head_sha": A, "name": "CI",
                                       "status": "completed", "conclusion": "failure"}]}
        if path.endswith("&page=1"):
            return {"total_count": 101, "jobs": [job(10, i, result="failure") for i in range(1, 101)]}
        if path.endswith("&page=2"):
            return {"total_count": 101, "jobs": [job(10, 101)]}
        raise AssertionError(path)
    data = mod.collect_live(token="fake", getter=fake)
    assert len(data["observations"][0]["jobs"]) == 101
    assert len(calls) == 4

    def shifted(path, *, token):
        result = fake(path, token=token)
        if "/jobs?" in path and "page=2" in path:
            result["total_count"] = 102
        return result
    with pytest.raises(ValueError, match="native jobs changed"):
        mod.collect_live(token="fake", getter=shifted)


def test_live_mode_requires_token_and_offline_snapshot_export(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    with pytest.raises(ValueError, match="GitHub read token"):
        mod.main(["--live", "--out", str(tmp_path / "out.json")])
    p = tmp_path / "input.json"
    p.write_text(json.dumps(payload(run(2033, 10))))
    report = tmp_path / "report.json"
    copy_path = tmp_path / "snapshot.json"
    assert mod.main(["--input", str(p), "--out", str(report), "--snapshot-out", str(copy_path)]) == 0
    assert json.loads(copy_path.read_text())["observations"][0]["run_id"] == 10
    with pytest.raises(ValueError, match="snapshot and report paths differ"):
        mod.main(["--input", str(p), "--out", str(report), "--snapshot-out", str(report)])


def test_advanced_head_without_native_run_is_explicit_hold():
    data = payload(run(2033, 10, sha=A))
    data["pr_heads"] = [{"pr": 2033, "head_sha": B}, {"pr": 2026, "head_sha": A}]
    result = mod.analyze(data)
    assert result["metrics"]["current_head_census_observed"] == 2
    assert result["metrics"]["current_heads_without_matching_run"] == 2
    assert [x["status"] for x in result["stale_current_heads"]] == [
        "NO_NATIVE_RUN_FOR_CURRENT_HEAD", "NO_NATIVE_RUN_FOR_CURRENT_HEAD",
    ]
    assert result["admission"] == "HOLD"


def test_current_head_native_exact_run_removes_only_matching_stale_flag():
    data = payload(run(2033, 10, sha=A))
    data["pr_heads"] = [{"pr": 2033, "head_sha": A}, {"pr": 2026, "head_sha": B}]
    result = mod.analyze(data)
    assert result["metrics"]["current_heads_without_matching_run"] == 1
    assert result["stale_current_heads"][0]["pr"] == 2026


def test_history_deduplicates_old_nonterminal_and_preserves_terminal_verdict():
    earlier = payload(run(2033, 10, result=None))
    later = payload(run(2033, 10, result="failure", log="unclassified workflows"))
    later["pr_heads"] = [{"pr": 2033, "head_sha": A}]
    merged = mod.combine_history(earlier, later)
    assert merged["history_deduplicated_attempts"] == 1
    assert mod.analyze(merged)["metrics"]["failure"] == 1
    old = payload(run(2033, 10, result="failure"))
    contradictory = payload(run(2033, 10, result="success"))
    with pytest.raises(ValueError, match="terminal historical attempt cannot change"):
        mod.combine_history(old, contradictory)


def test_history_rejects_head_swap_with_same_run_attempt():
    old = payload(run(2033, 10, sha=A))
    new = payload(run(2033, 10, sha=B))
    with pytest.raises(ValueError, match="rebound"):
        mod.combine_history(old, new)


def test_cli_previous_history_binds_run_and_current_sha(tmp_path):
    before = tmp_path / "before.json"
    current = tmp_path / "current.json"
    out = tmp_path / "out.json"
    before.write_text(json.dumps(payload(run(2033, 10, sha=A))))
    now = payload(run(2033, 20, sha=B, log="unclassified workflows"))
    now["pr_heads"] = [{"pr": 2033, "head_sha": B}]
    current.write_text(json.dumps(now))
    assert mod.main(["--input", str(current), "--previous", str(before), "--out", str(out)]) == 0
    result = json.loads(out.read_text())
    assert result["metrics"]["native_run_attempts"] == 2
    assert result["transitions"][0]["source_changed"] is True
    assert result["metrics"]["current_heads_without_matching_run"] == 0
