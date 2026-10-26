"""Lane 2 coverage: W10 read-only GitHub refresh evidence integrity.

``refresh_w10_spine.py`` acquires a SOURCE-BOUND snapshot through read-only
GitHub REST GETs and only reports coverage when a SHA-bound native B0 artifact
is downloaded and byte-verified.  These tests drive it against a scripted fake
GitHub served through ``urllib.request.urlopen`` (patched at the module's import
site) so no network is touched; every output goes to ``tmp_path``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import sys
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT
    / "MIP"
    / "G3CS_CONVERGENCE_V2"
    / "observatory"
    / "w10"
    / "refresh_w10_spine.py"
)
MODULE_NAME = "_lane2_refresh_w10_spine"


def _load():
    if MODULE_NAME in sys.modules:
        return sys.modules[MODULE_NAME]
    spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


refresh = _load()
EvidenceError = refresh.EvidenceError

SHA = "2b68462d6578fd435a6f22e750b4d4e7855c2195"
OTHER_SHA = "9e0200190555736c74295ee74881e3c003e8a35c"
B0_NAME = "MIP B0 Test Admission and Coverage Evidence"


def _run(
    i,
    conclusion="success",
    *,
    attempt=1,
    sha=SHA,
    event="push",
    status="completed",
    name="CI",
):
    return {
        "id": i,
        "run_attempt": attempt,
        "head_sha": sha,
        "event": event,
        "status": status,
        "conclusion": conclusion,
        "name": name,
    }


def _zip(contexts=None, evidence=None, members=("ctx", "ev"), raw=None):
    buf = io.BytesIO()
    with ZipFile(buf, "w") as z:
        if "ctx" in members:
            z.writestr(
                "canonical-contexts.json",
                (
                    raw
                    if raw is not None
                    else json.dumps(
                        contexts
                        or {
                            "totals": {
                                "covered_lines": 4,
                                "num_statements": 7,
                                "covered_branches": 1,
                                "num_branches": 4,
                            }
                        }
                    )
                ),
            )
        if "ev" in members:
            z.writestr(
                "canonical-test-evidence.json",
                json.dumps(
                    evidence or {"exact_sha": SHA, "outcomes": {"pass": 3, "skip": 1}}
                ),
            )
    data = buf.getvalue()
    return data, "sha256:" + hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------
# primitive validators
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value", [None, 123, "A" * 40, SHA[:39], SHA + "0", "g" * 40, " " + SHA[1:]]
)
def test_check_sha_rejects_non_exact(value):
    with pytest.raises(EvidenceError, match="40-character"):
        refresh.check_sha(value)


def test_check_sha_accepts_exact():
    assert refresh.check_sha(SHA) == SHA


@pytest.mark.parametrize("pair", [(None, 1), (1, None), (True, 1), (1.0, 2), (0, -1)])
def test_count_pair_null_or_negative_never_zero(pair):
    with pytest.raises(EvidenceError, match="never null-as-zero"):
        refresh.count_pair(*pair)


def test_count_pair_sums():
    assert refresh.count_pair(0, 0) == 0
    assert refresh.count_pair(105, 373) == 478


# --------------------------------------------------------------------------
# complete_ci_runs
# --------------------------------------------------------------------------


@pytest.mark.parametrize("runs", [None, [], {}, "x"])
def test_ci_runs_empty_population_rejected(runs):
    with pytest.raises(EvidenceError, match="Empty or missing"):
        refresh.complete_ci_runs(runs, SHA)


def test_ci_runs_requires_valid_sha():
    with pytest.raises(EvidenceError):
        refresh.complete_ci_runs([_run(1)], "HEAD")


@pytest.mark.parametrize(
    "bad",
    [
        _run(1, sha=OTHER_SHA),
        _run(1, event="pull_request"),
        dict(_run(1), head_sha=None),
    ],
)
def test_ci_runs_stale_or_mixed_population_rejected(bad):
    with pytest.raises(EvidenceError, match="Mixed source SHA"):
        refresh.complete_ci_runs([_run(2), bad], SHA)


@pytest.mark.parametrize(
    "run",
    [
        _run(0),
        _run(-3),
        _run("7"),
        _run(True),
        _run(5, attempt=0),
        _run(5, attempt=None),
    ],
)
def test_ci_runs_identity_must_be_positive_int(run):
    with pytest.raises(EvidenceError, match="positive integer"):
        refresh.complete_ci_runs([run], SHA)


def test_ci_runs_retry_attempts_are_distinct_but_duplicates_rejected():
    out = refresh.complete_ci_runs(
        [_run(7, attempt=2), _run(7, "failure", attempt=1)], SHA
    )
    assert out["run_attempts"] == [[7, 1], [7, 2]]
    assert (out["success"], out["failure"], out["total"]) == (1, 1, 2)
    with pytest.raises(EvidenceError, match="duplicated"):
        refresh.complete_ci_runs([_run(7), _run(8), _run(7, "failure")], SHA)


def test_ci_runs_full_outcome_taxonomy():
    others = [
        "timed_out",
        "skipped",
        "neutral",
        "action_required",
        "stale",
        "startup_failure",
    ]
    runs = [_run(1), _run(2, "failure"), _run(3, "cancelled")] + [
        _run(10 + i, c) for i, c in enumerate(others)
    ]
    out = refresh.complete_ci_runs(runs, SHA)
    assert out == {
        "sha": SHA,
        "event": "push",
        "success": 1,
        "failure": 1,
        "cancelled": 1,
        "other": 6,
        "total": 9,
        "run_attempts": [[i, 1] for i in (1, 2, 3, 10, 11, 12, 13, 14, 15)],
    }
    assert (
        out["success"] + out["failure"] + out["cancelled"] + out["other"]
        == out["total"]
    )


@pytest.mark.parametrize("conclusion", [None, "", "SUCCESS", "unknown"])
def test_ci_runs_unclassified_outcome_rejected(conclusion):
    with pytest.raises(EvidenceError, match="Unclassified"):
        refresh.complete_ci_runs([_run(1), _run(2, conclusion)], SHA)


# --------------------------------------------------------------------------
# parse_canonical_zip
# --------------------------------------------------------------------------


def test_parse_zip_round_trip_values():
    data, digest = _zip()
    out = refresh.parse_canonical_zip(data, SHA, 42, 123, digest)
    assert out["archive_sha256"] == digest.split(":", 1)[1]
    assert (out["covered"], out["eligible"], out["uncovered"]) == (5, 11, 6)
    assert out["coverage_percent"] == round(100 * 5 / 11, 6)
    assert (out["statements_covered"], out["branches_eligible"]) == (4, 4)
    assert (out["native_run_id"], out["artifact_id"], out["source_sha"]) == (
        123,
        42,
        SHA,
    )
    assert out["native_zip_digest_verified"] is True
    assert (out["test_passed"], out["test_skipped"]) == (3, 1)
    # determinism
    assert refresh.parse_canonical_zip(data, SHA, 42, 123, digest) == out


def test_parse_zip_evidence_without_outcomes_reports_none():
    data, digest = _zip(evidence={"exact_sha": SHA})
    out = refresh.parse_canonical_zip(data, SHA, 1, 1, digest)
    assert out["test_passed"] is None and out["test_skipped"] is None


@pytest.mark.parametrize(
    "ids", [(0, 1), (1, 0), ("1", 1), (1, True), (None, 5), (-1, 5)]
)
def test_parse_zip_identities_required(ids):
    data, digest = _zip()
    with pytest.raises(EvidenceError, match="positive native"):
        refresh.parse_canonical_zip(data, SHA, ids[0], ids[1], digest)


@pytest.mark.parametrize(
    "digest", [None, "", "sha256:XYZ", "md5:" + "0" * 64, "sha256:" + "A" * 64]
)
def test_parse_zip_unadvertised_digest_rejected(digest):
    data, _ = _zip()
    with pytest.raises(EvidenceError, match="did not advertise"):
        refresh.parse_canonical_zip(data, SHA, 1, 1, digest)


def test_parse_zip_tampered_bytes_rejected():
    data, digest = _zip()
    with pytest.raises(EvidenceError, match="differs"):
        refresh.parse_canonical_zip(data + b"\x00", SHA, 1, 1, digest)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"members": ("ev",)},
        {"members": ("ctx",)},
        {"raw": "{not json"},
    ],
)
def test_parse_zip_missing_or_malformed_members(kwargs):
    data, digest = _zip(**kwargs)
    with pytest.raises(EvidenceError, match="lacks complete"):
        refresh.parse_canonical_zip(data, SHA, 1, 1, digest)


def test_parse_zip_not_a_zip_with_matching_digest():
    data = b"definitely not a zip"
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    with pytest.raises(EvidenceError, match="lacks complete"):
        refresh.parse_canonical_zip(data, SHA, 1, 1, digest)


def test_parse_zip_stale_sha_receipt_rejected():
    data, digest = _zip(evidence={"exact_sha": OTHER_SHA, "outcomes": {"pass": 1}})
    with pytest.raises(EvidenceError, match="another source SHA"):
        refresh.parse_canonical_zip(data, SHA, 1, 1, digest)


@pytest.mark.parametrize(
    "totals, phrase",
    [
        (None, "Missing coverage context totals"),
        ([1, 2], "Missing coverage context totals"),
        (
            {"covered_lines": 1, "num_statements": 2, "covered_branches": 0},
            "num_branches",
        ),
        (
            {
                "covered_lines": -1,
                "num_statements": 2,
                "covered_branches": 0,
                "num_branches": 0,
            },
            "covered_lines",
        ),
        (
            {
                "covered_lines": 1.0,
                "num_statements": 2,
                "covered_branches": 0,
                "num_branches": 0,
            },
            "covered_lines",
        ),
        (
            {
                "covered_lines": 0,
                "num_statements": 0,
                "covered_branches": 0,
                "num_branches": 0,
            },
            "Inconsistent",
        ),
        (
            {
                "covered_lines": 3,
                "num_statements": 2,
                "covered_branches": 0,
                "num_branches": 0,
            },
            "Inconsistent",
        ),
        (
            {
                "covered_lines": 1,
                "num_statements": 2,
                "covered_branches": 5,
                "num_branches": 4,
            },
            "Inconsistent",
        ),
    ],
)
def test_parse_zip_forged_coverage_counters(totals, phrase):
    ctx = {"totals": totals} if totals is not None else {"other": 1}
    data, digest = _zip(contexts=ctx)
    with pytest.raises(EvidenceError, match=phrase):
        refresh.parse_canonical_zip(data, SHA, 1, 1, digest)


# --------------------------------------------------------------------------
# Fake GitHub served through urlopen
# --------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, body: bytes, status: int = 200):
        self.body = body
        self.status = status

    def read(self, n=-1):
        return self.body if n < 0 else self.body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeGitHub:
    """Routes API paths to canned JSON/bytes; records every request."""

    def __init__(self):
        self.routes = {}
        self.requests = []

    def add(self, path, payload, status=200):
        body = (
            payload
            if isinstance(payload, (bytes, Exception))
            else json.dumps(payload).encode()
        )
        self.routes[path] = (body, status)

    def urlopen(self, req, timeout=None):
        assert timeout == 60
        assert req.get_method() == "GET"
        self.requests.append(req)
        full = req.full_url
        assert full.startswith(refresh.BASE + "/")
        path = full[len(refresh.BASE) :]
        if path not in self.routes:
            raise urllib.error.URLError("no route " + path)
        body, status = self.routes[path]
        if isinstance(body, Exception):
            raise body
        return FakeResponse(body, status)


@pytest.fixture
def gh(monkeypatch):
    fake = FakeGitHub()
    monkeypatch.setattr(refresh.urllib.request, "urlopen", fake.urlopen)
    return fake


def _search_path(repo, mode):
    return "/search/issues?" + urllib.parse.urlencode(
        {"q": f"repo:{repo} is:issue is:{mode}", "per_page": "1"}
    )


def _runs_path(repo, sha, page):
    return f"/repos/{repo}/actions/runs?" + urllib.parse.urlencode(
        {"event": "push", "head_sha": sha, "per_page": 100, "page": page}
    )


def _artifacts_path(repo, run_id, page):
    return f"/repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100&page={page}"


# --------------------------------------------------------------------------
# GitHubReadOnly.get
# --------------------------------------------------------------------------


def test_get_rejects_absolute_url_without_request(gh):
    client = refresh.GitHubReadOnly(None)
    with pytest.raises(EvidenceError, match="relative paths"):
        client.get("https://evil.example/x")
    assert gh.requests == []


def test_get_json_receipts_headers_and_token(gh):
    gh.add("/x?secret=1", {"a": 1})
    client = refresh.GitHubReadOnly("tok123")
    assert client.get("/x?secret=1") == {"a": 1}
    req = gh.requests[0]
    assert req.get_header("Authorization") == "Bearer tok123"
    assert req.get_header("X-github-api-version") == "2022-11-28"
    body = json.dumps({"a": 1}).encode()
    assert client.receipts == [
        {
            "url": refresh.BASE + "/x",
            "status": 200,
            "content_sha256": hashlib.sha256(body).hexdigest(),
        }
    ]


def test_get_without_token_sends_no_authorization(gh):
    gh.add("/y", b"raw-bytes")
    client = refresh.GitHubReadOnly(None)
    assert client.get("/y", binary=True) == b"raw-bytes"
    assert gh.requests[0].get_header("Authorization") is None


def test_get_non_200_and_invalid_json_rejected_without_receipt_on_status(gh):
    gh.add("/s", {"a": 1}, status=204)
    gh.add("/j", b"<html>")
    client = refresh.GitHubReadOnly(None)
    with pytest.raises(EvidenceError, match="non-200"):
        client.get("/s")
    assert client.receipts == []
    with pytest.raises(EvidenceError, match="Invalid GitHub JSON"):
        client.get("/j")
    # receipt for the body that was fetched is still recorded
    assert len(client.receipts) == 1


def test_get_http_and_url_errors_are_evidence_errors(gh):
    gh.add("/h?q=secret", urllib.error.HTTPError("u", 503, "down", {}, None))
    client = refresh.GitHubReadOnly(None)
    with pytest.raises(
        EvidenceError, match=r"GitHub GET failed for /h: HTTPError"
    ) as exc:
        client.get("/h?q=secret")
    assert "secret" not in str(exc.value)
    with pytest.raises(EvidenceError, match="URLError"):
        client.get("/unrouted")


def test_get_oversized_response_rejected(gh, monkeypatch):
    gh.add("/big", b"x")

    class Huge(FakeResponse):
        def read(self, n=-1):
            assert n == 40_000_000
            return b"0" * n

    monkeypatch.setattr(
        refresh.urllib.request, "urlopen", lambda req, timeout=None: Huge(b"")
    )
    with pytest.raises(EvidenceError, match="40MB"):
        refresh.GitHubReadOnly(None).get("/big")


# --------------------------------------------------------------------------
# counts / ref / runs / canonical
# --------------------------------------------------------------------------


def test_counts_success_and_incomplete_and_unknown(gh):
    repo = "GBOGEB/ABACUS"
    gh.add(_search_path(repo, "open"), {"incomplete_results": False, "total_count": 38})
    gh.add(
        _search_path(repo, "closed"), {"incomplete_results": False, "total_count": 267}
    )
    client = refresh.GitHubReadOnly(None)
    assert client.counts(repo) == {"repo": repo, "issue_open": 38, "issue_closed": 267}

    gh.add(
        _search_path(repo, "closed"), {"incomplete_results": None, "total_count": 267}
    )
    with pytest.raises(EvidenceError, match="incomplete"):
        client.counts(repo)
    gh.add(
        _search_path(repo, "closed"), {"incomplete_results": False, "total_count": None}
    )
    with pytest.raises(EvidenceError, match="Issue count unknown"):
        client.counts(repo)
    gh.add(
        _search_path(repo, "closed"), {"incomplete_results": False, "total_count": -4}
    )
    with pytest.raises(EvidenceError, match="Issue count unknown"):
        client.counts(repo)


def test_ref_requires_exact_sha(gh):
    gh.add("/repos/R/x/git/ref/heads/main", {"object": {"sha": SHA}})
    gh.add("/repos/R/y/git/ref/heads/main", {"object": {"sha": "abc"}})
    gh.add("/repos/R/z/git/ref/heads/main", {})
    client = refresh.GitHubReadOnly(None)
    assert client.ref("R/x") == SHA
    for repo in ("R/y", "R/z"):
        with pytest.raises(EvidenceError, match="40-character"):
            client.ref(repo)


def test_runs_pagination_reconciled(gh):
    repo = "R/a"
    page1 = [_run(i) for i in range(1, 101)]
    gh.add(_runs_path(repo, SHA, 1), {"total_count": 102, "workflow_runs": page1})
    gh.add(
        _runs_path(repo, SHA, 2),
        {"total_count": 102, "workflow_runs": [_run(101), _run(102)]},
    )
    runs = refresh.GitHubReadOnly(None).runs(repo, SHA)
    assert [r["id"] for r in runs] == list(range(1, 103))


@pytest.mark.parametrize(
    "pages, phrase",
    [
        ([{"workflow_runs": []}], "denominator"),
        ([{"total_count": "3", "workflow_runs": []}], "denominator"),
        ([{"total_count": 3, "workflow_runs": None}], "Workflow run list absent"),
        (
            [
                {"total_count": 3, "workflow_runs": [_run(1)]},
                {"total_count": 4, "workflow_runs": [_run(2)]},
            ],
            "changed",
        ),
        (
            [
                {"total_count": 3, "workflow_runs": [_run(1)]},
                {"total_count": 3, "workflow_runs": []},
            ],
            "ended before",
        ),
        ([{"total_count": 1, "workflow_runs": [_run(1), _run(2)]}], "Unreconciled"),
    ],
)
def test_runs_pagination_forgeries_rejected(gh, pages, phrase):
    for i, payload in enumerate(pages, start=1):
        gh.add(_runs_path("R/a", SHA, i), payload)
    with pytest.raises(EvidenceError, match=phrase):
        refresh.GitHubReadOnly(None).runs("R/a", SHA)


def test_runs_zero_total_returns_empty(gh):
    gh.add(_runs_path("R/a", SHA, 1), {"total_count": 0, "workflow_runs": []})
    assert refresh.GitHubReadOnly(None).runs("R/a", SHA) == []


def test_runs_page_cap_refuses_truncation(gh):
    for page in range(1, 41):
        gh.add(
            _runs_path("R/a", SHA, page),
            {"total_count": 10_000, "workflow_runs": [_run(page)]},
        )
    client = refresh.GitHubReadOnly(None)
    with pytest.raises(EvidenceError, match="Unreconciled"):
        client.runs("R/a", SHA)
    assert len(gh.requests) == 40


def test_canonical_none_without_successful_b0(gh):
    client = refresh.GitHubReadOnly(None)
    runs = [
        _run(1, name="CI"),
        _run(2, "failure", name=B0_NAME),
        _run(3, None, status="in_progress", name=B0_NAME),
    ]
    assert client.canonical("R/a", SHA, runs) is None
    assert gh.requests == []


def test_canonical_selects_latest_b0_with_matching_unexpired_artifact(gh):
    data, digest = _zip()
    runs = [_run(5, name=B0_NAME), _run(9, name=B0_NAME)]
    # newest run 9: artifact only for another SHA, and an expired one -> skipped
    gh.add(
        _artifacts_path("R/a", 9, 1),
        {
            "artifacts": [
                {
                    "name": "b0-canonical-" + OTHER_SHA,
                    "expired": False,
                    "id": 1,
                    "digest": digest,
                },
                {
                    "name": "b0-canonical-" + SHA,
                    "expired": True,
                    "id": 2,
                    "digest": digest,
                },
                {
                    "name": "b0-canonical-" + SHA,
                    "expired": None,
                    "id": 3,
                    "digest": digest,
                },
            ]
        },
    )
    filler = [{"name": f"other-{i}", "expired": False} for i in range(100)]
    gh.add(_artifacts_path("R/a", 5, 1), {"artifacts": filler})
    gh.add(
        _artifacts_path("R/a", 5, 2),
        {
            "artifacts": [
                {
                    "name": "b0-canonical-" + SHA,
                    "expired": False,
                    "id": 77,
                    "digest": digest,
                }
            ]
        },
    )
    gh.add("/repos/R/a/actions/artifacts/77/zip", data)
    out = refresh.GitHubReadOnly(None).canonical("R/a", SHA, runs)
    assert (out["artifact_id"], out["native_run_id"]) == (77, 5)
    assert out["covered"] == 5


def test_canonical_artifact_list_unavailable(gh):
    gh.add(_artifacts_path("R/a", 4, 1), {"message": "Not Found"})
    with pytest.raises(EvidenceError, match="Artifact list unavailable"):
        refresh.GitHubReadOnly(None).canonical("R/a", SHA, [_run(4, name=B0_NAME)])


def test_canonical_no_artifact_anywhere_is_none(gh):
    filler = [{"name": f"n{i}", "expired": False} for i in range(100)]
    for page in range(1, 7):
        gh.add(_artifacts_path("R/a", 4, page), {"artifacts": filler})
    assert (
        refresh.GitHubReadOnly(None).canonical("R/a", SHA, [_run(4, name=B0_NAME)])
        is None
    )
    assert len(gh.requests) == 6


def test_canonical_tampered_archive_fails_closed(gh):
    data, digest = _zip()
    gh.add(
        _artifacts_path("R/a", 4, 1),
        {
            "artifacts": [
                {
                    "name": "b0-canonical-" + SHA,
                    "expired": False,
                    "id": 8,
                    "digest": digest,
                }
            ]
        },
    )
    gh.add("/repos/R/a/actions/artifacts/8/zip", data[:-1] + b"!")
    with pytest.raises(EvidenceError, match="differs"):
        refresh.GitHubReadOnly(None).canonical("R/a", SHA, [_run(4, name=B0_NAME)])


# --------------------------------------------------------------------------
# collect / main
# --------------------------------------------------------------------------


def _wire_world(gh, *, runs, artifact=True, counts=None):
    counts = counts or {r: (i + 1, 10 * (i + 1)) for i, r in enumerate(refresh.REPOS)}
    gh.add("/repos/GBOGEB/ABACUS/git/ref/heads/main", {"object": {"sha": SHA}})
    for repo, (o, c) in counts.items():
        gh.add(
            _search_path(repo, "open"), {"incomplete_results": False, "total_count": o}
        )
        gh.add(
            _search_path(repo, "closed"),
            {"incomplete_results": False, "total_count": c},
        )
    gh.add(
        _runs_path("GBOGEB/ABACUS", SHA, 1),
        {"total_count": len(runs), "workflow_runs": runs},
    )
    if artifact:
        data, digest = _zip()
        b0 = [r for r in runs if r.get("name") == B0_NAME]
        for r in b0:
            gh.add(
                _artifacts_path("GBOGEB/ABACUS", r["id"], 1),
                {
                    "artifacts": [
                        {
                            "name": "b0-canonical-" + SHA,
                            "expired": False,
                            "id": 500 + r["id"],
                            "digest": digest,
                        }
                    ]
                },
            )
            gh.add(f"/repos/GBOGEB/ABACUS/actions/artifacts/{500 + r['id']}/zip", data)


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 21, 8, 30, 15, 987654, tzinfo=timezone.utc)


def test_collect_complete_snapshot(gh, monkeypatch):
    monkeypatch.setattr(refresh, "datetime", FixedDatetime)
    runs = [_run(1), _run(2, "failure"), _run(3, name=B0_NAME)]
    _wire_world(gh, runs=runs)
    snap = refresh.collect(refresh.GitHubReadOnly(None))
    assert snap["schema"] == "codepurple.spine.w10.snapshot.v1"
    assert snap["as_of_utc"] == "2026-10-21T08:30:15Z"
    assert snap["abacus_main_sha"] == SHA
    assert [r["repo"] for r in snap["repos"]] == list(refresh.REPOS)
    assert snap["main_ci"]["total"] == 3 and snap["main_ci"]["success"] == 2
    assert snap["coverage"]["artifact_id"] == 503
    assert snap["coverage_absent_reason"] is None
    assert snap["governance"]["merge_admission"] == "HOLD"
    assert snap["governance"]["authority_transfer"] is False
    assert snap["scope_complete_federation"] is False
    assert snap["accepted_rex"] is None
    # every GET produced a receipt: ref + 6 searches + runs + artifacts + zip
    assert len(snap["source_receipts"]) == 10


def test_collect_nonterminal_ci_becomes_unknown_not_partial(gh, monkeypatch):
    monkeypatch.setattr(refresh, "datetime", FixedDatetime)
    runs = [_run(1), _run(2, None, status="in_progress")]
    _wire_world(gh, runs=runs, artifact=False)
    snap = refresh.collect(refresh.GitHubReadOnly(None))
    ci = snap["main_ci"]
    assert all(
        ci[k] is None for k in ("success", "failure", "cancelled", "other", "total")
    )
    assert ci["run_attempts"] == []
    assert "nonterminal" in ci["incomplete_reason"]
    assert snap["coverage"] is None
    assert "missing" in snap["coverage_absent_reason"]


def test_collect_empty_run_population_unknown(gh, monkeypatch):
    monkeypatch.setattr(refresh, "datetime", FixedDatetime)
    _wire_world(gh, runs=[], artifact=False)
    snap = refresh.collect(refresh.GitHubReadOnly(None))
    assert snap["main_ci"]["total"] is None
    assert "Empty" in snap["main_ci"]["incomplete_reason"]
    assert snap["coverage"] is None


def _main(monkeypatch, out, token_env=None):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    if token_env:
        monkeypatch.setenv(*token_env)
    monkeypatch.setattr(sys, "argv", ["refresh_w10_spine.py", "--out", str(out)])
    refresh.main()


def test_main_writes_deterministic_snapshot(gh, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(refresh, "datetime", FixedDatetime)
    _wire_world(gh, runs=[_run(1), _run(3, name=B0_NAME)])
    out = tmp_path / "nested" / "dir" / "W10_NEXT_SNAPSHOT.json"
    _main(monkeypatch, out, ("GH_TOKEN", "ghtok"))
    first = out.read_bytes()
    printed = capsys.readouterr().out
    assert f"main={SHA}" in printed
    assert (
        "native CI complete=True" in printed
        and "native coverage proven=True" in printed
    )
    assert all(r.get_header("Authorization") == "Bearer ghtok" for r in gh.requests)
    # write_text uses platform newlines; compare with normalised newlines.
    text = first.decode("utf-8").replace("\r\n", "\n")
    assert "ghtok" not in text
    snap = json.loads(text)
    assert text.endswith("}\n")
    assert text == json.dumps(snap, sort_keys=True, indent=2) + "\n"

    # Repeated refresh against unchanged source is byte-identical (idempotent).
    _main(monkeypatch, out, ("GITHUB_TOKEN", "other"))
    assert out.read_bytes() == first
    assert gh.requests[-1].get_header("Authorization") == "Bearer other"


def test_main_reports_unproven_coverage(gh, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(refresh, "datetime", FixedDatetime)
    _wire_world(gh, runs=[_run(1, None, status="queued")], artifact=False)
    out = tmp_path / "snap.json"
    _main(monkeypatch, out)
    printed = capsys.readouterr().out
    assert "native CI complete=False" in printed
    assert "native coverage proven=False" in printed
    assert gh.requests[0].get_header("Authorization") is None
    assert json.loads(out.read_text(encoding="utf-8"))["coverage"] is None


def test_main_network_failure_writes_nothing(gh, monkeypatch, tmp_path):
    out = tmp_path / "snap.json"
    with pytest.raises(EvidenceError, match="GitHub GET failed"):
        _main(monkeypatch, out)
    assert not out.exists()


def test_main_requires_out(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["refresh_w10_spine.py"])
    with pytest.raises(SystemExit) as exc:
        refresh.main()
    assert exc.value.code == 2
