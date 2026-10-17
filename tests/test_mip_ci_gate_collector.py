"""Native collector contract: exact source, attempt, pages and missing evidence."""

import copy
import io
import json

import pytest

from tools import mip_ci_gate_collector as collector


SHA = "a" * 40


def native_run(identity, path, name, conclusion="success", *, sha=SHA):
    return {
        "id": identity,
        "run_attempt": 1,
        "head_sha": sha,
        "name": name,
        "path": path,
        "html_url": f"https://github.com/GBOGEB/ABACUS/actions/runs/{identity}",
        "created_at": "2026-10-16T08:00:00Z",
        "status": "completed" if conclusion is not None else "queued",
        "conclusion": conclusion,
    }


def native_job(identity, run_id, name, conclusion="success", *, steps=None):
    item = {
        "id": identity,
        "run_id": run_id,
        "run_attempt": 1,
        "head_sha": SHA,
        "name": name,
        "status": "completed" if conclusion is not None else "queued",
        "conclusion": conclusion,
        "started_at": "2026-10-16T08:01:00Z",
        "completed_at": "2026-10-16T08:02:00Z" if conclusion is not None else None,
    }
    if steps is not None:
        item["steps"] = [
            {"name": label, "status": "completed", "conclusion": "success"}
            for label in steps
        ]
    return item


def enterprise_jobs():
    items = []
    count = 0
    for py in ("3.9", "3.10", "3.11", "3.12"):
        for operating_system in ("ubuntu-latest", "windows-latest", "macos-latest"):
            items.append(
                native_job(
                    500 + count,
                    10,
                    f"Test Python {py} on {operating_system}",
                    steps=["Run pytest --benchmark-disable with coverage"],
                )
            )
            count += 1
    items.append(native_job(520, 10, "CI Summary"))
    return items


def build_getter(*, e="success", g="failure"):
    run_data = {
        10: native_run(
            10, collector.EXPECTED_PATHS["enterprise_ci"],
            "DMAIC V3 Enterprise CI", e,
        ),
        11: native_run(
            11, collector.EXPECTED_PATHS["workflow_governance"],
            "CI Workflow Governance", g,
        ),
    }
    job_data = {
        10: enterprise_jobs(),
        11: [
            native_job(
                522, 11, "policy-and-inventory", g,
                steps=["Fail closed on governance red"],
            )
        ],
    }
    calls = []

    def get(url):
        calls.append(url)
        pieces = url.split("/")
        run_id = int(pieces[6])
        if url.endswith(f"/runs/{run_id}"):
            return copy.deepcopy(run_data[run_id])
        if "/jobs?" in url:
            return {
                "total_count": len(job_data[run_id]),
                "jobs": copy.deepcopy(job_data[run_id]),
            }
        raise AssertionError("unknown endpoint " + url)

    return get, run_data, job_data, calls


def test_native_transport_fixed_https_origin_no_redirects(monkeypatch):
    connections = []

    class FakeResponse:
        def __init__(self, status):
            self.status = status

        def read(self, size=-1):
            return io.BytesIO(b'{"id":123}').read(size)

    class FakeConnection:
        def __init__(self, host, timeout):
            self.host = host
            self.timeout = timeout
            self.status = 200
            self.closed = False
            connections.append(self)

        def request(self, method, path, headers):
            self.method, self.path, self.headers = method, path, headers

        def getresponse(self):
            return FakeResponse(self.status)

        def close(self):
            self.closed = True

    monkeypatch.setattr(collector, "HTTPSConnection", FakeConnection)
    # Ephemeral test-only token: no credential value is embedded in source.
    from secrets import token_hex
    ephemeral = token_hex(16)
    result = collector.github_get("/repos/GBOGEB/ABACUS/actions/runs/123", token=ephemeral)
    assert result == {"id": 123}
    connection = connections[0]
    assert connection.host == "api.github.com"
    assert connection.method == "GET"
    assert connection.path == "/repos/GBOGEB/ABACUS/actions/runs/123"
    assert connection.closed

    for forbidden in (
        "http://not-github.example/actions/runs/123",
        "/repos/GBOGEB/ABACUS/actions/../issues/123",
        "/repos/GBOGEB/ABACUS/actions/runs/123/redirect",
    ):
        with pytest.raises(ValueError, match="unsupported GitHub evidence endpoint"):
            collector.github_get(forbidden)
    assert len(connections) == 1

    def redirect_connection(host, timeout):
        instance = FakeConnection(host, timeout)
        instance.status = 302
        return instance

    monkeypatch.setattr(collector, "HTTPSConnection", redirect_connection)
    with pytest.raises(ValueError, match="HTTP 302"):
        collector.github_get("/repos/GBOGEB/ABACUS/actions/runs/123", token=ephemeral)
    assert connections[-1].closed


def test_true_native_enterprise_green_governance_red():
    getter, _runs, _jobs, calls = build_getter()
    source, result = collector.collect_gate_input(
        SHA,
        {"enterprise_ci": (10, 1), "workflow_governance": (11, 1)},
        getter=getter,
    )
    assert len(source["jobs"]) == 14
    assert len(source["runs"]) == 2
    assert len(calls) == 4
    assert source["acquisition"] == "github-actions-rest-attempt-jobs"
    gates = result["independent_gates"]
    assert gates["domains"]["enterprise_ci"]["status"] == "PASS"
    assert gates["domains"]["workflow_governance"]["status"] == "FAIL"
    assert gates["domains"]["bandit"]["status"] == "UNKNOWN"
    assert gates["domains"]["safety"]["status"] == "UNKNOWN"
    assert gates["domains"]["independent_review"]["status"] == "UNKNOWN"
    assert gates["admission"] == "HOLD"
    assert result["merge_authorized"] is False


def test_collector_cannot_borrow_proof_from_second_head():
    getter, runs, _jobs, _calls = build_getter()
    runs[10]["head_sha"] = "b" * 40
    with pytest.raises(ValueError, match="identity/SHA/workflow mismatch"):
        collector.collect_gate_input(SHA, {"enterprise_ci": (10, 1)}, getter=getter)


def test_native_attempt_mismatch_rejected():
    getter, runs, _jobs, _calls = build_getter()
    runs[10]["run_attempt"] = 2
    with pytest.raises(ValueError, match="mismatch"):
        collector.collect_gate_input(SHA, {"enterprise_ci": (10, 1)}, getter=getter)


def test_native_workflow_path_mismatch_rejected():
    getter, runs, _jobs, _calls = build_getter()
    runs[10]["path"] = collector.EXPECTED_PATHS["workflow_governance"]
    with pytest.raises(ValueError, match="mismatch"):
        collector.collect_gate_input(SHA, {"enterprise_ci": (10, 1)}, getter=getter)


def test_native_job_at_different_sha_rejected():
    getter, _runs, jobs, _calls = build_getter()
    jobs[10][0]["head_sha"] = "b" * 40
    with pytest.raises(ValueError, match="native job identity"):
        collector.collect_gate_input(SHA, {"enterprise_ci": (10, 1)}, getter=getter)


def test_duplicate_job_ids_rejected():
    getter, _runs, jobs, _calls = build_getter()
    jobs[10][1]["id"] = jobs[10][0]["id"]
    with pytest.raises(ValueError, match="duplicate mismatch"):
        collector.collect_gate_input(SHA, {"enterprise_ci": (10, 1)}, getter=getter)


def test_partial_job_page_rejected_not_silently_credited():
    getter, _runs, _jobs, _calls = build_getter()

    def short_get(url):
        r = getter(url)
        if "/jobs?" in url:
            r["total_count"] = 1000
            r["jobs"] = []
        return r

    with pytest.raises(ValueError, match="incomplete native jobs page"):
        collector.collect_gate_input(
            SHA, {"enterprise_ci": (10, 1)}, getter=short_get
        )


def test_no_jobs_is_unknown_even_for_green_workflow():
    getter, _runs, jobs, _calls = build_getter()
    jobs[10].clear()
    _, metrics = collector.collect_gate_input(
        SHA, {"enterprise_ci": (10, 1)}, getter=getter
    )
    assert (
        metrics["independent_gates"]["domains"]["enterprise_ci"]["status"]
        == "UNKNOWN"
    )
    assert metrics["independent_gates"]["admission"] == "HOLD"


def test_queued_run_preserves_pending_without_fabricating_fail():
    getter, runs, jobs, _calls = build_getter()
    runs[10]["status"] = "queued"
    runs[10]["conclusion"] = None
    jobs[10].clear()
    _, metrics = collector.collect_gate_input(
        SHA, {"enterprise_ci": (10, 1)}, getter=getter
    )
    assert (
        metrics["independent_gates"]["domains"]["enterprise_ci"]["status"]
        == "PENDING"
    )
    assert metrics["independent_gates"]["domain_counts"]["FAIL"] == 0


@pytest.mark.parametrize(
    "raw",
    [
        "13", "13:", ":2", "a:2", "13:two", "0:1", "13:0", "-3:1",
        "1:2:3", None,
    ],
)
def test_invalid_run_selector_never_chooses_latest(raw):
    with pytest.raises(ValueError):
        collector.parse_selection(raw)


def test_duplicate_shared_run_cannot_satisfy_two_domains():
    getter, _runs, _jobs, _calls = build_getter()
    with pytest.raises(ValueError, match="same native run"):
        collector.collect_gate_input(
            SHA,
            {"enterprise_ci": (10, 1), "workflow_governance": (10, 1)},
            getter=getter,
        )


def test_unsupported_review_binding_rejected():
    with pytest.raises(ValueError, match="supported gate"):
        collector.collect_gate_input(
            SHA, {"independent_review": (10, 1)}, getter=lambda _: {}
        )


def test_collector_writes_scope_bound_artifacts(tmp_path, monkeypatch, capsys):
    getter, _runs, _jobs, _calls = build_getter()
    monkeypatch.setattr(collector, "github_get", lambda url, token=None: getter(url))
    source_path = tmp_path / "native" / "runs.json"
    metrics_path = tmp_path / "metrics" / "vector.json"
    assert collector.main([
        "--sha", SHA,
        "--enterprise-run", "10:1",
        "--governance-run", "11:1",
        "--out", str(source_path),
        "--metrics-out", str(metrics_path),
    ]) == 0
    source = json.loads(source_path.read_text(encoding="utf-8"))
    output = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert source["gate_bindings"]["enterprise_ci"] == {
        "run_id": 10, "run_attempt": 1
    }
    assert (
        output["independent_gates"]["domains"]["workflow_governance"]["status"]
        == "FAIL"
    )
    assert output["independent_gates"]["admission"] == "HOLD"
    assert "HOLD" in capsys.readouterr().out
