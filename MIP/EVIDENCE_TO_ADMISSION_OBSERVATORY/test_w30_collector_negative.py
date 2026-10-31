"""W30 adversarial remote-client, provenance, artifact and queue-gate tests.

All HTTP calls are mocked. No GitHub network, credential disclosure, merge,
Crew dispatch, or root-closure writes occur during this testflight.
"""

from __future__ import annotations

import io
import json
import pathlib
import urllib.error
import urllib.request
import zipfile

import census
import pytest
import render
from test_observatory import SHA_A, FakeClient


def canonical_zip(
    *, sha=SHA_A, branch=True, totals=True, ratchet="PASS", numeric=True, missing=None
):
    meta = {"meta": {"branch_coverage": branch}, "files": {}}
    if totals:
        meta["totals"] = {
            "num_statements": 8,
            "covered_lines": 7 if numeric else True,
            "num_branches": 2,
            "covered_branches": 1,
        }
    contents = {
        "canonical-contexts.json": json.dumps(meta),
        "canonical-test-evidence.json": json.dumps(
            {
                "exact_sha": sha,
                "ratchet_status": ratchet,
                "outcomes": {"pass": 3, "skip": 0, "fail": 0},
            }
        ),
        "canonical-junit.xml": "<testsuites/>",
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, body in contents.items():
            if name != missing:
                archive.writestr(name, body)
    return buffer.getvalue()


@pytest.mark.parametrize(
    "payload,allow_list,valid",
    [
        (b'{"ok":true}', False, True),
        (b"[1,2,3]", True, True),
        (b"[1,2,3]", False, False),
        (b'"not-a-dict"', False, False),
        (b"broken-json", False, False),
        (b"\xff", False, False),
    ],
)
def test_github_api_shape_and_decode_are_fail_closed(
    monkeypatch, payload, allow_list, valid
):
    observed = []

    def stub(request, timeout):
        observed.append((request.get_header("Authorization"), timeout))
        return io.BytesIO(payload)

    monkeypatch.setattr(urllib.request, "urlopen", stub)
    client = census.Client("synthetic-token", timeout=7)
    if valid:
        assert client.get("/repo/test", allow_list=allow_list) is not None
    else:
        with pytest.raises(census.CensusError, match="Invalid API JSON"):
            client.get("/repo/test", allow_list=allow_list)
    assert observed == [("Bearer synthetic-token", 7)]


@pytest.mark.parametrize(
    "fault", [urllib.error.URLError("offline"), TimeoutError("slow")]
)
def test_api_network_and_timeout_are_not_empty_success(monkeypatch, fault):
    def fail(request, timeout):
        raise fault

    monkeypatch.setattr(urllib.request, "urlopen", fail)
    with pytest.raises(census.CensusError, match="API unavailable"):
        census.Client().get("/repos/GBOGEB/ABACUS")


def test_artifact_download_never_falls_back_to_anonymous():
    with pytest.raises(census.CensusError, match="requires the runner token"):
        census.Client().artifact(123)


def test_artifact_redirect_drops_cross_host_authorization(monkeypatch):
    captured = []

    class Opener:
        def open(self, req, timeout):
            handlers = captured[0]
            request = urllib.request.Request(
                "https://api.github.com/redirect",
                headers={"Authorization": "Bearer synthetic"},
            )
            redirect = handlers.redirect_request(
                request,
                None,
                302,
                "moved",
                {},
                "https://objects.githubusercontent.com/receipt.zip",
            )
            assert redirect.get_header("Authorization") is None
            return io.BytesIO(b"ZIP-CONTENTS")

    def build(handler):
        captured.append(handler)
        return Opener()

    monkeypatch.setattr(urllib.request, "build_opener", build)
    assert census.Client("synthetic-token").artifact(7) == b"ZIP-CONTENTS"


def test_artifact_compressed_bound_is_enforced(monkeypatch):
    class Opener:
        def open(self, req, timeout):
            return io.BytesIO(b"x" * 14_000_001)

    monkeypatch.setattr(urllib.request, "build_opener", lambda handler: Opener())
    with pytest.raises(census.CensusError, match="exceeds 14 MB"):
        census.Client("synthetic-token").artifact(17)


@pytest.mark.parametrize(
    "bad",
    [
        "missing-junit",
        "missing-totals",
        "not-branch",
        "boolean-numerator",
        "ratchet-not-pass",
        "invalid-zip",
    ],
)
def test_native_b0_receipt_rejects_absent_or_false_proofs(bad):
    options = {
        "missing-junit": {"missing": "canonical-junit.xml"},
        "missing-totals": {"totals": False},
        "not-branch": {"branch": False},
        "boolean-numerator": {"numeric": False},
        "ratchet-not-pass": {"ratchet": "FAIL"},
    }
    raw = b"not a zip" if bad == "invalid-zip" else canonical_zip(**options[bad])
    with pytest.raises(census.CensusError):
        census.native_artifact_metrics(raw, SHA_A, None)


def test_valid_artifact_attaches_actual_outcome_counts():
    result = census.native_artifact_metrics(canonical_zip(), SHA_A, None)
    assert (result["covered_opportunities"], result["total_opportunities"]) == (8, 10)
    assert result["test_pass"] == 3
    assert result["test_fail"] == 0
    assert result["status"] == "MEASURED_ON_EXACT_MAIN_SHA"


class TimedClient(FakeClient):
    def __init__(self, queued=False):
        super().__init__()
        self.queued = queued

    def get(self, path, allow_list=False):
        if "/actions/runs/1811/jobs?" in path:
            jobs = [
                {
                    "id": 10,
                    "name": "B0 canonical producer",
                    "status": "completed",
                    "conclusion": "success",
                    "run_attempt": 1,
                    "created_at": "2026-10-18T10:00:00Z",
                    "started_at": "2026-10-18T10:00:30Z",
                    "completed_at": "2026-10-18T10:01:30Z",
                },
                {
                    "id": 11,
                    "name": "B0 static producer",
                    "status": "queued" if self.queued else "completed",
                    "conclusion": None if self.queued else "success",
                    "run_attempt": 1,
                    "created_at": "2026-10-18T10:00:00Z",
                    "started_at": (
                        "2026-10-18T10:00:00Z"
                        if self.queued
                        else "2026-10-18T10:00:49Z"
                    ),
                    "completed_at": None if self.queued else "2026-10-18T10:01:50Z",
                },
            ]
            return {"total_count": len(jobs), "jobs": jobs}
        return super().get(path, allow_list)


@pytest.mark.parametrize("queued,expected", [(False, 49), (True, None)])
def test_collector_b0_scale_clock_uses_terminal_jobs_only(queued, expected):
    base = json.loads(
        (pathlib.Path(census.__file__).parent / "evidence.json").read_text()
    )
    data = census.collect(TimedClient(queued=queued), base, artifact_download=False)
    receipt = data["workflows"]["b0"]["queue_telemetry"]
    assert receipt["queue_p95_seconds"] == expected
    assert data["workflows"]["b0"]["queue_p95_seconds"] == expected
    if queued:
        assert receipt["evidence_state"] == "QUEUED_OR_TIMESTAMP_INCOMPLETE"
        assert data["wave_metrics"]["scale_policy"]["read_only_parallel_lanes_max"] == 1
    else:
        assert receipt["evidence_state"] == "COMPLETE_TERMINAL_JOB_POPULATION"


@pytest.mark.parametrize(
    "bad",
    [
        {"schema": "wrong", "main": {"sha": SHA_A}},
        {"schema": render.SCHEMA, "main": {"sha": "short"}},
    ],
)
def test_renderer_rejects_invalid_source_objects(bad):
    with pytest.raises(ValueError):
        render.render(bad, "__EVIDENCE_JSON__")


@pytest.mark.parametrize("marker", ["missing", "__EVIDENCE_JSON____EVIDENCE_JSON__"])
def test_renderer_requires_single_nonexecutable_data_slot(marker):
    with pytest.raises(ValueError, match="Template marker"):
        render.render({"schema": render.SCHEMA, "main": {"sha": SHA_A}}, marker)


def test_cli_strict_head_returns_two_and_stores_unadmitted_json(monkeypatch, tmp_path):
    base = pathlib.Path(census.__file__).parent / "evidence.json"
    output = tmp_path / "nested" / "snapshot.json"
    monkeypatch.setattr(census, "Client", lambda token: FakeClient(change_head=True))
    assert (
        census.main(
            [
                "--baseline",
                str(base),
                "--out",
                str(output),
                "--strict-head",
                "--no-artifact-download",
            ]
        )
        == 2
    )
    obj = json.loads(output.read_text())
    assert obj["main"]["head_stable"] is False
    assert obj["governance"]["merge_admission"] == "HOLD"
    assert obj["coverage"]["measured"]["status"] == "STALE_OR_UNQUALIFIED_HEAD_MOVE"
