"""Lane-B wave 10: everred_v3 native_ingest GitHub reader, artifact fetch, collect.

All HTTP is faked on the loaded module; no network, no real credentials.
"""

import hashlib
import io
import json
import sys
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
HTTPError = ni.urllib.error.HTTPError
A, B = "a" * 40, "b" * 40
REPO = "GBOGEB/ABACUS"
TS = "2026-10-01T00:00:00Z"
DIG = "d" * 64
FAKE_CRED = "fake-" + "tok" + "en-for-tests"
API = "https://api.github.com"


@pytest.fixture(autouse=True)
def _no_env_creds(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)


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
        "conclusion": "success",
        "name": "job",
        "completed_at": TS,
        "steps": [],
    }
    j.update(over)
    return j


class Transport:
    """Route -> JSON-able object (or raw bytes) fake for GitHubReadOnly."""

    def __init__(self, routes):
        self.routes = routes
        self.seen = []

    def __call__(self, req):
        self.seen.append(req)
        route = req.full_url[len(API) :]
        value = self.routes[route]
        return value if isinstance(value, (bytes, str)) else json.dumps(value).encode()


def _reader(routes):
    return ni.GitHubReadOnly(FAKE_CRED, transport=Transport(routes))


def _jobs_route(page):
    return f"/repos/{REPO}/actions/runs/7/jobs?per_page=100&page={page}"


RUN_ROUTE = f"/repos/{REPO}/actions/runs/7"
ARTS_ROUTE = f"/repos/{REPO}/actions/runs/7/artifacts?per_page=100"


# ------------------------------------------------------------- GitHubReadOnly


def test_init_token_sources(monkeypatch):
    with pytest.raises(Err, match="GITHUB_TOKEN required"):
        ni.GitHubReadOnly()
    monkeypatch.setenv("GH_TOKEN", FAKE_CRED)
    assert ni.GitHubReadOnly().token == FAKE_CRED
    monkeypatch.setenv("GITHUB_TOKEN", FAKE_CRED + "-2")
    assert ni.GitHubReadOnly().token == FAKE_CRED + "-2"
    assert ni.GitHubReadOnly(FAKE_CRED).api == API


def test_init_rejects_other_api():
    with pytest.raises(Err, match="only public GitHub API allowed"):
        ni.GitHubReadOnly(FAKE_CRED, api="https://ghe.example.com/api/v3")


def test_get_via_transport_sets_headers():
    t = Transport({"/repos/x/y": {"ok": 1}})
    r = ni.GitHubReadOnly(FAKE_CRED, transport=t)
    assert r.get("/repos/x/y") == {"ok": 1}
    req = t.seen[0]
    assert req.get_header("Authorization") == "Bearer " + FAKE_CRED
    assert req.get_header("X-github-api-version") == "2022-11-28"
    assert req.get_header("User-agent") == "ABACUS-EVERRED-V3"


@pytest.mark.parametrize("route", ["/users/x", "/repos/../x", "/repos/a\\b"])
def test_get_rejects_bad_route(route):
    with pytest.raises(Err, match="bad API path"):
        _reader({}).get(route)


@pytest.mark.parametrize(
    "payload,match",
    [
        ("text-not-bytes", "bad API response size"),
        (b"{not json", "invalid GitHub JSON"),
        (b"\xff\xfe\xfa", "invalid GitHub JSON"),
    ],
)
def test_get_rejects_bad_payload(payload, match):
    with pytest.raises(Err, match=match):
        _reader({"/repos/x/y": payload}).get("/repos/x/y")


def test_get_rejects_oversize(monkeypatch):
    monkeypatch.setattr(ni, "MAX_ARTIFACT", 3)
    with pytest.raises(Err, match="bad API response size"):
        _reader({"/repos/x/y": b"[1, 2]"}).get("/repos/x/y")


class FakeRes:
    def __init__(self, status, body):
        self.status = status
        self.body = body
        self.read_sizes = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, n):
        self.read_sizes.append(n)
        return self.body


class FakeOpener:
    """Pops one behaviour per open(): a FakeRes to return or an exception."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def open(self, req, timeout=None):
        self.calls.append((req, timeout))
        step = self.script.pop(0)
        if isinstance(step, BaseException):
            raise step
        return step


def _install_opener(monkeypatch, script):
    opener = FakeOpener(script)
    handlers = []

    def build_opener(*hs):
        handlers.append(hs)
        return opener

    monkeypatch.setattr(ni.urllib.request, "build_opener", build_opener)
    return opener, handlers


def test_get_without_transport_uses_no_redirect_opener(monkeypatch):
    res = FakeRes(200, b'{"a": 2}')
    opener, handlers = _install_opener(monkeypatch, [res])
    assert ni.GitHubReadOnly(FAKE_CRED).get("/repos/x/y") == {"a": 2}
    assert isinstance(handlers[0][0], ni._NoRedirect)
    assert opener.calls[0][1] == 20
    assert res.read_sizes == [ni.MAX_ARTIFACT + 1]


def test_get_without_transport_non_200(monkeypatch):
    _install_opener(monkeypatch, [FakeRes(204, b"{}")])
    with pytest.raises(Err, match="GitHub API not HTTP 200"):
        ni.GitHubReadOnly(FAKE_CRED).get("/repos/x/y")


def test_get_without_transport_http_error(monkeypatch):
    err = HTTPError(API + "/repos/x/y", 404, "nf", {}, io.BytesIO(b""))
    _install_opener(monkeypatch, [err])
    with pytest.raises(Err, match="GitHub API HTTP 404"):
        ni.GitHubReadOnly(FAKE_CRED).get("/repos/x/y")


def test_no_redirect_handler_returns_none():
    assert ni._NoRedirect().redirect_request(None, None, 302, "m", {}, "u") is None


# --------------------------------------------------------------- run_and_jobs


def test_run_and_jobs_paginates():
    routes = {
        RUN_ROUTE: _run(),
        _jobs_route(1): {"total_count": 2, "jobs": [_job(11)]},
        _jobs_route(2): {"total_count": 2, "jobs": [_job(12, head_sha=None)]},
    }
    run, jobs = _reader(routes).run_and_jobs(REPO, 7, A)
    assert run["id"] == 7
    assert [j["id"] for j in jobs] == [11, 12]


def test_run_and_jobs_zero_jobs():
    routes = {RUN_ROUTE: _run(), _jobs_route(1): {"total_count": 0, "jobs": []}}
    assert _reader(routes).run_and_jobs(REPO, 7, A)[1] == []


@pytest.mark.parametrize(
    "run,pages,match",
    [
        ([], {}, "run ID mismatch"),
        (_run(id=8), {}, "run ID mismatch"),
        (_run(head_sha=B), {}, "GitHub run SHA mismatch"),
        (_run(repository={}), {}, "GitHub run repository mismatch"),
        (_run(), {1: []}, "missing jobs list"),
        (_run(), {1: {"jobs": {}}}, "missing jobs list"),
        (_run(), {1: {"jobs": []}}, "missing jobs denominator"),
        (_run(), {1: {"jobs": [], "total_count": -1}}, "missing jobs denominator"),
        (_run(), {1: {"jobs": [], "total_count": 3}}, "jobs pagination incomplete"),
        (
            _run(),
            {1: {"jobs": [_job(11), _job(11)], "total_count": 2}},
            "jobs incomplete or duplicated",
        ),
        (
            _run(),
            {1: {"jobs": [_job(11), _job(12)], "total_count": 1}},
            "jobs incomplete or duplicated",
        ),
        (_run(), {1: {"jobs": [_job(run_id=9)], "total_count": 1}}, "job run ID"),
        (_run(), {1: {"jobs": [_job(jid="11")], "total_count": 1}}, "bad job ID"),
        (_run(), {1: {"jobs": [_job(jid=-1)], "total_count": 1}}, "bad job ID"),
        (_run(), {1: {"jobs": [_job(head_sha=B)], "total_count": 1}}, "job source"),
    ],
)
def test_run_and_jobs_rejects(run, pages, match):
    routes = {RUN_ROUTE: run}
    routes.update({_jobs_route(p): v for p, v in pages.items()})
    with pytest.raises(Err, match=match):
        _reader(routes).run_and_jobs(REPO, 7, A)


def test_run_and_jobs_rejects_bad_scope():
    with pytest.raises(Err, match="invalid repository"):
        _reader({}).run_and_jobs("nope", 7, A)


def test_run_and_jobs_page_cap():
    routes = {RUN_ROUTE: _run()}
    for p in range(1, 22):
        routes[_jobs_route(p)] = {"total_count": 100, "jobs": [_job(p)]}
    with pytest.raises(Err, match="jobs API truncated"):
        _reader(routes).run_and_jobs(REPO, 7, A)


# ------------------------------------------------------------------ artifacts


def test_artifacts_ok_and_rejects():
    arts = [{"id": 1}, {"id": 2}]
    r = _reader({ARTS_ROUTE: {"total_count": 2, "artifacts": arts}})
    assert r.artifacts(REPO, 7) == arts
    r = _reader({ARTS_ROUTE: {"total_count": 3, "artifacts": arts}})
    with pytest.raises(Err, match="artifact list truncated"):
        r.artifacts(REPO, 7)
    r = _reader({ARTS_ROUTE: {"total_count": 0}})
    with pytest.raises(Err, match="invalid artifacts"):
        r.artifacts(REPO, 7)
    with pytest.raises(Err, match="invalid run ID"):
        r.artifacts(REPO, 0)


# ----------------------------------------------------------- _zip_from_github


def _zip_bytes(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return buf.getvalue()


ZIP = _zip_bytes({"report.json": b"{}"})
ZIP_DIGEST = "sha256:" + hashlib.sha256(ZIP).hexdigest()


def _redirect(location, code=302):
    return HTTPError(API, code, "redirect", {"Location": location}, io.BytesIO(b""))


@pytest.mark.parametrize(
    "dest",
    [
        "https://pipelines.actions.githubusercontent.com/x?sig=1",
        "https://store.blob.core.windows.net/x",
        "https://objects.githubusercontent.com:443/x",
    ],
)
def test_zip_from_github_ok(monkeypatch, dest):
    opener, handlers = _install_opener(
        monkeypatch, [_redirect(dest, 307), FakeRes(200, ZIP)]
    )
    reader = ni.GitHubReadOnly(FAKE_CRED)
    out = ni._zip_from_github(reader, REPO, {"id": 5, "digest": ZIP_DIGEST})
    assert out == {"report.json": b"{}"}
    first, second = opener.calls
    assert first[0].full_url == API + f"/repos/{REPO}/actions/artifacts/5/zip"
    assert first[0].get_header("Authorization") == "Bearer " + FAKE_CRED
    # the bearer credential must not be forwarded to the storage host
    assert second[0].full_url == dest
    assert second[0].get_header("Authorization") is None
    assert second[1] == 30
    assert all(isinstance(h[0], ni._NoRedirect) for h in handlers)


@pytest.mark.parametrize(
    "dest",
    [
        "http://objects.githubusercontent.com/x",
        "https://evil.example.com/x",
        "https://user@objects.githubusercontent.com/x",
        "https://u:pw@objects.githubusercontent.com/x",
        "https://objects.githubusercontent.com:8443/x",
        "https://objects.githubusercontent.com/x#frag",
        "",
    ],
)
def test_zip_from_github_rejects_storage_host(monkeypatch, dest):
    _install_opener(monkeypatch, [_redirect(dest)])
    reader = ni.GitHubReadOnly(FAKE_CRED)
    with pytest.raises(Err, match="unrecognized artifact storage host"):
        ni._zip_from_github(reader, REPO, {"id": 5, "digest": ZIP_DIGEST})


def test_zip_from_github_missing_location_header(monkeypatch):
    err = HTTPError(API, 302, "redirect", {}, io.BytesIO(b""))
    _install_opener(monkeypatch, [err])
    with pytest.raises(Err, match="unrecognized artifact storage host"):
        ni._zip_from_github(ni.GitHubReadOnly(FAKE_CRED), REPO, {"id": 5})


def test_zip_from_github_requires_redirect(monkeypatch):
    _install_opener(monkeypatch, [FakeRes(200, ZIP)])
    with pytest.raises(Err, match="expected explicit GitHub artifact storage"):
        ni._zip_from_github(ni.GitHubReadOnly(FAKE_CRED), REPO, {"id": 5})


def test_zip_from_github_unexpected_status(monkeypatch):
    _install_opener(monkeypatch, [HTTPError(API, 404, "nf", {}, io.BytesIO(b""))])
    with pytest.raises(Err, match="unexpected artifact response"):
        ni._zip_from_github(ni.GitHubReadOnly(FAKE_CRED), REPO, {"id": 5})


@pytest.mark.parametrize("aid", [None, 0, "5", True])
def test_zip_from_github_bad_id(aid):
    with pytest.raises(Err, match="invalid artifact ID"):
        ni._zip_from_github(ni.GitHubReadOnly(FAKE_CRED), REPO, {"id": aid})


@pytest.mark.parametrize(
    "digest,match",
    [
        (None, "artifact digest missing"),
        ("md5:" + "0" * 32, "artifact digest missing"),
        ("sha256:" + "0" * 64, "artifact SHA-256 mismatch"),
    ],
)
def test_zip_from_github_digest_checks(monkeypatch, digest, match):
    good = "https://objects.githubusercontent.com/x"
    _install_opener(monkeypatch, [_redirect(good), FakeRes(200, ZIP)])
    with pytest.raises(Err, match=match):
        ni._zip_from_github(
            ni.GitHubReadOnly(FAKE_CRED), REPO, {"id": 5, "digest": digest}
        )


def test_zip_from_github_size_limit(monkeypatch):
    good = "https://objects.githubusercontent.com/x"
    _install_opener(monkeypatch, [_redirect(good), FakeRes(200, ZIP)])
    monkeypatch.setattr(ni, "MAX_ARTIFACT", 10)
    with pytest.raises(Err, match="artifact exceeds size limit"):
        ni._zip_from_github(
            ni.GitHubReadOnly(FAKE_CRED), REPO, {"id": 5, "digest": ZIP_DIGEST}
        )


# ---------------------------------------------------------------- collect_native

BANDIT = json.dumps(
    {
        "results": [
            {"filename": "a.py", "test_id": "B101", "code": "x", "issue_text": "t"}
        ]
    }
).encode()
COVERAGE = (
    b'<coverage><classes><class filename="a.py"><lines>'
    b'<line number="1" hits="1"/><line number="2" hits="0"/>'
    b"</lines></class></classes></coverage>"
)
JUNIT = b'<testsuite><testcase name="t"><failure message="m"/></testcase></testsuite>'
RUNTIME = json.dumps(
    {
        "schema": "abacus.everred.runtime.v1",
        "repository": REPO,
        "source_sha": A,
        "run_id": 7,
        "job_id": 11,
        "backend": "UBI9",
        "exit_code": 0,
        "runner_id": "r",
        "command_digest": DIG,
        "os_release": "9",
        "uname_release": "5",
    }
).encode()
MEMBERS = {
    "bandit.json": BANDIT,
    "coverage.xml": COVERAGE,
    "junit.xml": JUNIT,
    "runtime.json": RUNTIME,
}


def _art(aid=100, **over):
    a = {
        "id": aid,
        "name": f"art-{aid}",
        "expired": False,
        "digest": "sha256:" + "e" * 64,
        "created_at": "2026-10-01T00:10:00Z",
        "workflow_run": {"id": 7, "head_sha": A},
    }
    a.update(over)
    return a


def _collect_reader(arts):
    return _reader(
        {
            RUN_ROUTE: _run(),
            _jobs_route(1): {"total_count": 1, "jobs": [_job(11)]},
            ARTS_ROUTE: {"total_count": len(arts), "artifacts": arts},
        }
    )


@pytest.fixture
def fake_zip(monkeypatch):
    calls = []

    def fake(reader, repo, artifact):
        calls.append((repo, artifact["id"]))
        return dict(MEMBERS)

    monkeypatch.setattr(ni, "_zip_from_github", fake)
    # collect_native re-imports everred lazily for final validation
    monkeypatch.setitem(sys.modules, "everred", ev)
    return calls


def _plan(kind, member, **extra):
    p = {"artifact_id": 100, "job_id": 11, "kind": kind, "member": member}
    p.update(extra)
    return p


BANDIT_PLAN = _plan(
    "bandit",
    "bandit.json",
    config_digest=DIG,
    scanner_version="1.7",
    rule_profile="default",
)
COVERAGE_PLAN = _plan(
    "coverage",
    "coverage.xml",
    config_id="cfg",
    selection="all",
    exclusions="none",
    tool_version="7.6",
)


def test_collect_native_no_plan_skips_artifacts(fake_zip):
    reader = _collect_reader([])
    out = ni.collect_native(REPO, A, 7, [], reader=reader)
    assert [e["kind"] for e in out] == ["note", "verification"]
    assert all(e["provenance"] == "observed" for e in out)
    assert ARTS_ROUTE not in [r.full_url[len(API) :] for r in reader.transport.seen]
    assert fake_zip == []


def test_collect_native_all_kinds(fake_zip):
    plans = [
        BANDIT_PLAN,
        COVERAGE_PLAN,
        _plan("junit", "junit.xml"),
        _plan("runtime", "runtime.json"),
    ]
    out = ni.collect_native(REPO, A, 7, plans, reader=_collect_reader([_art()]))
    kinds = [e["kind"] for e in out]
    assert kinds == [
        "note",
        "verification",
        "security_census",
        "coverage",
        "occurrence",
        "runtime",
    ]
    assert fake_zip == [(REPO, 100)] * 4
    # run/job events keep their own scope; artifact events gain a receipt
    assert "artifact_receipt" not in out[0]["evidence"]
    assert "artifact_receipt" not in out[1]["evidence"]
    for e, member in zip(out[2:], MEMBERS):
        receipt = e["evidence"]["artifact_receipt"]
        assert receipt["id"] == 100
        assert receipt["upload_job_binding"] == "DECLARED_NOT_ATTESTED"
        assert receipt["name"] == "art-100"
        assert e["occurred_at"] == "2026-10-01T00:10:00Z"
    assert out[3]["evidence"]["covered"] == 1
    assert out[5]["evidence"]["reported_complete"] is True
    last = hashlib.sha256(RUNTIME).hexdigest()
    assert out[5]["evidence"]["artifact_receipt"]["members_sha256"] == last


def test_collect_native_receipt_overwritten_by_later_member(fake_zip):
    """production_defect: collect_native stamps artifact_receipt on every event whose
    source_binding equals the current scope, so when two plans share a job and
    artifact the earlier event's members_sha256 is overwritten with the later
    member's hash (bandit event claims the coverage.xml digest); this test fails
    once fixed."""
    plans = [BANDIT_PLAN, COVERAGE_PLAN]
    out = ni.collect_native(REPO, A, 7, plans, reader=_collect_reader([_art()]))
    bandit_receipt = out[2]["evidence"]["artifact_receipt"]
    assert out[2]["kind"] == "security_census"
    assert bandit_receipt["members_sha256"] == hashlib.sha256(COVERAGE).hexdigest()
    assert bandit_receipt["members_sha256"] != hashlib.sha256(BANDIT).hexdigest()


@pytest.mark.parametrize(
    "arts,plan,match",
    [
        ([_art()], "nope", "bad artifact plan"),
        ([_art()], _plan("junit", "junit.xml", artifact_id=101), "not bound to run"),
        ([_art()], _plan("junit", "junit.xml", artifact_id="100"), "not bound to run"),
        ([_art(expired=True)], _plan("junit", "junit.xml"), "artifact expired"),
        ([_art(expired=None)], _plan("junit", "junit.xml"), "artifact expired"),
        (
            [_art(workflow_run={"id": 8, "head_sha": A})],
            _plan("junit", "junit.xml"),
            "exact-run/source binding",
        ),
        (
            [{k: v for k, v in _art().items() if k != "workflow_run"}],
            _plan("junit", "junit.xml"),
            "exact-run/source binding",
        ),
        ([_art()], _plan("junit", "junit.xml", job_id=99), "job binding not in run"),
        ([_art()], _plan("junit", "missing.xml"), "declared artifact member missing"),
        ([_art()], _plan("sbom", "junit.xml"), "unsupported artifact kind"),
    ],
)
def test_collect_native_rejects(fake_zip, arts, plan, match):
    with pytest.raises(Err, match=match):
        ni.collect_native(REPO, A, 7, [plan], reader=_collect_reader(arts))


def test_collect_native_revalidates_events(fake_zip, monkeypatch):
    seen = []
    stub = types.SimpleNamespace(validate_event=seen.append)
    monkeypatch.setitem(sys.modules, "everred", stub)
    out = ni.collect_native(REPO, A, 7, [], reader=_collect_reader([]))
    assert seen == out
