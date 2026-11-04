"""Behaviour tests for tools/everred_v3/sut_gui/server.py.

No port is bound and ``serve_forever`` never runs: the request handler is
built with ``__new__`` and driven through in-memory rfile/wfile buffers,
GitHub reads go through a fake ``fetch_github``/opener, ``subprocess.run`` is
faked, ``threading.Thread`` is replaced by an inert recorder and ``_work`` is
driven synchronously with ``tempfile`` pointed at ``tmp_path``.
"""

import hashlib
import io
import json
import pathlib
import sys
from types import SimpleNamespace

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("tools/everred_v3/sut_gui/server.py", name="abn_w6_sut_gui_server")

SHA = "a" * 40
CRED = "fixed-test-cred"
WRONG = "wrong-test-cred"
HDR = "X-SUT-" + "Token"
PORT = 8765
HOST = "127.0.0.1:8765"
ORIGIN = "http://127.0.0.1:8765"


class _Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _Inert:
    created = []

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.started = False
        _Inert.created.append(self)

    def start(self):
        self.started = True


# ---------------------------------------------------------------- helpers


def test_now_iso_is_utc():
    assert mod.now_iso().endswith("+00:00")


def test_git_revision_paths(monkeypatch, tmp_path):
    calls = []

    def ok(cmd, **kw):
        calls.append(cmd)
        return _Result(0, SHA + "\n")

    monkeypatch.setattr(mod.subprocess, "run", ok)
    assert mod.git_revision(tmp_path) == SHA
    assert calls[0][:2] == ["git", "-C"]
    monkeypatch.setattr(mod.subprocess, "run", lambda c, **k: _Result(1, SHA))
    assert mod.git_revision(tmp_path) is None
    monkeypatch.setattr(mod.subprocess, "run", lambda c, **k: _Result(0, "short"))
    assert mod.git_revision(tmp_path) is None

    def boom(cmd, **kw):
        raise OSError("no git")

    monkeypatch.setattr(mod.subprocess, "run", boom)
    assert mod.git_revision(tmp_path) is None

    def slow(cmd, **kw):
        raise mod.subprocess.TimeoutExpired(cmd, 3)

    monkeypatch.setattr(mod.subprocess, "run", slow)
    assert mod.git_revision(tmp_path) is None


def test_no_redirect_refuses():
    handler = mod._NoRedirect()
    with pytest.raises(OSError, match="redirect refused"):
        handler.redirect_request(None, None, 302, "Found", {}, "https://x")


class _Res:
    def __init__(self, status, body):
        self.status = status
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, n):
        return self.body[:n]


def _opener(monkeypatch, status, body, seen):
    class _Opener:
        def open(self, req, timeout):
            seen.append((req, timeout))
            return _Res(status, body)

    def build(*handlers):
        seen.append(handlers)
        return _Opener()

    monkeypatch.setattr(mod.request, "build_opener", build)


def test_fetch_github_success_with_and_without_auth(monkeypatch):
    seen = []
    _opener(monkeypatch, 200, b'{"ok": 1}', seen)
    assert mod.fetch_github("/x", CRED) == {"ok": 1}
    assert isinstance(seen[0][0], mod._NoRedirect)
    req, timeout = seen[1]
    assert req.full_url == "https://api.github.com/x"
    assert req.get_header("Authorization") == "Bearer " + CRED
    assert timeout == 7
    seen.clear()
    assert mod.fetch_github("/y", None) == {"ok": 1}
    assert seen[1][0].get_header("Authorization") is None


def test_fetch_github_rejects_status_and_oversize(monkeypatch):
    _opener(monkeypatch, 404, b"{}", [])
    with pytest.raises(OSError, match="HTTP 404"):
        mod.fetch_github("/x", None)
    _opener(monkeypatch, 200, b"".join([b"1"] * 1_500_001), [])
    with pytest.raises(OSError, match="too large"):
        mod.fetch_github("/x", None)


# ---------------------------------------------------------------- native CI


def _run(rid, status="completed", conclusion="success", sha=SHA):
    return dict(
        id=rid,
        name="wf" + str(rid),
        status=status,
        conclusion=conclusion,
        head_sha=sha,
        html_url="https://github.com/r/" + str(rid),
        event="push",
    )


def _fake_fetch(routes):
    def fetch(path, token):
        value = routes[path]
        if isinstance(value, Exception):
            raise value
        return value

    return fetch


RUNS_PATH = "/repos/GBOGEB/ABACUS/actions/runs?head_sha=" + SHA + "&per_page=100"


def _jobs_path(rid):
    return "/repos/GBOGEB/ABACUS/actions/runs/" + str(rid) + "/jobs?per_page=100"


def test_native_ci_invalid_sha_returns_unknown():
    for sha in (None, "x", "A" * 40):
        out = mod._native_ci(None, sha)
        assert out["status"] == "UNKNOWN"
        assert out["total_count"] is None


def test_native_ci_rejects_missing_denominator_and_mixed_sha(monkeypatch):
    routes = {RUNS_PATH: {"total_count": "1", "workflow_runs": []}}
    monkeypatch.setattr(mod, "fetch_github", _fake_fetch(routes))
    with pytest.raises(ValueError, match="denominator"):
        mod._native_ci(None, SHA)
    routes[RUNS_PATH] = {"total_count": 1, "workflow_runs": [_run(1, sha="b" * 40)]}
    with pytest.raises(ValueError, match="mixes"):
        mod._native_ci(None, SHA)


def test_native_ci_complete_census_metrics(monkeypatch):
    runs = [
        _run(1),
        _run(2, conclusion="failure"),
        _run(3, status="queued", conclusion=None),
        _run(4, status="in_progress", conclusion=None),
        _run(5, conclusion="cancelled"),
    ]
    jobs = [
        dict(id=10, name="ok", conclusion="success"),
        dict(
            id=11,
            name="bad",
            conclusion="failure",
            html_url="https://github.com/j/11",
            steps=[
                dict(name="setup", number=1, conclusion="success"),
                dict(name="pytest", number=2, conclusion="failure"),
            ],
        ),
        dict(id=12, name="nostep", conclusion="timed_out", steps=None),
    ]
    routes = {
        RUNS_PATH: {"total_count": 5, "workflow_runs": runs},
        _jobs_path(2): {"total_count": 3, "jobs": jobs},
    }
    monkeypatch.setattr(mod, "fetch_github", _fake_fetch(routes))
    out = mod._native_ci(CRED, SHA)
    assert out["status"] == "OBSERVED"
    assert out["sample_complete"] is True
    assert out["metrics"] == dict(
        total_observed=5,
        terminal=3,
        success=1,
        failure=1,
        queued=1,
        in_progress=1,
        cancelled_or_other=1,
    )
    reds = out["first_reds"]
    assert [r["job_id"] for r in reds] == [11, 12]
    assert reds[0]["step"] == "pytest"
    assert reds[0]["step_number"] == 2
    assert reds[0]["url"] == "https://github.com/j/11"
    assert reds[1]["step"] is None
    assert reds[1]["url"] == "https://github.com/r/2"
    assert out["first_red_completeness"] == "COMPLETE"


def test_native_ci_partial_when_job_readback_fails(monkeypatch):
    runs = [_run(i, conclusion="failure") for i in (1, 2, 3, 4, 5)]
    routes = {
        RUNS_PATH: {"total_count": 9, "workflow_runs": runs},
        _jobs_path(1): {"total_count": 1, "jobs": "nope"},
        _jobs_path(2): {"total_count": 2, "jobs": []},
        _jobs_path(3): OSError("down"),
        _jobs_path(4): {"total_count": 0, "jobs": []},
    }
    monkeypatch.setattr(mod, "fetch_github", _fake_fetch(routes))
    out = mod._native_ci(None, SHA)
    assert out["sample_complete"] is False
    evidence = [r["evidence"] for r in out["first_reds"]]
    assert evidence == ["JOB_READBACK_UNAVAILABLE"] * 3
    assert [r["run_id"] for r in out["first_reds"]] == [1, 2, 3]
    assert out["first_red_completeness"] == "PARTIAL"


# ---------------------------------------------------------------- live snapshot


def _live_routes():
    return {
        "/repos/GBOGEB/ABACUS/branches/main": {
            "commit": {"sha": SHA},
            "protected": True,
        },
        "/repos/GBOGEB/CODEX/branches/main": {"commit": {"sha": "b" * 40}},
        "/repos/GBOGEB/ABACUS/rulesets/24494381": {
            "id": 1,
            "enforcement": "active",
            "rules": [1, 2],
        },
        "/repos/GBOGEB/ABACUS/pulls/1956": {
            "state": "open",
            "draft": False,
            "merged": False,
            "head": {"sha": SHA},
            "html_url": "u",
            "title": "t",
            "user": {"login": "author"},
        },
        "/repos/GBOGEB/ABACUS/pulls/1951": {"state": "closed", "user": None},
        RUNS_PATH: {"total_count": 1, "workflow_runs": [_run(1)]},
        "/repos/GBOGEB/ABACUS/pulls/1956/reviews?per_page=100": [
            {"state": "APPROVED", "commit_id": SHA, "user": {"login": "rev"}},
        ],
    }


def test_live_snapshot_complete(monkeypatch):
    monkeypatch.setattr(mod, "fetch_github", _fake_fetch(_live_routes()))
    out = mod.live_snapshot(CRED)
    assert out["poll_policy"] == "AUTHENTICATED_90S"
    assert out["errors"] == []
    assert out["repositories"]["GBOGEB/ABACUS"]["sha"] == SHA
    assert out["repositories"]["GBOGEB/CODEX"]["protected"] is None
    assert out["ruleset"]["rule_count"] == 2
    assert out["prs"]["1956"]["author"] == "author"
    assert out["prs"]["1951"]["author"] is None
    assert out["ci"]["status"] == "OBSERVED"
    assert out["independent_review"] == "OBSERVED_NOT_ELIGIBILITY"
    assert out["collection"] == "COMPLETE"
    assert out["merge_authorized"] is False


def test_live_snapshot_self_review_and_non_list_rules(monkeypatch):
    routes = _live_routes()
    routes["/repos/GBOGEB/ABACUS/rulesets/24494381"]["rules"] = None
    reviews = [{"state": "APPROVED", "commit_id": SHA, "user": {"login": "author"}}]
    routes["/repos/GBOGEB/ABACUS/pulls/1956/reviews?per_page=100"] = reviews
    monkeypatch.setattr(mod, "fetch_github", _fake_fetch(routes))
    out = mod.live_snapshot(None)
    assert out["poll_policy"] == "PUBLIC_900S"
    assert out["ruleset"]["rule_count"] is None
    assert out["independent_review"] == "NOT_OBSERVED"


def test_live_snapshot_all_failures_are_partial(monkeypatch):
    routes = {key: OSError("down") for key in _live_routes()}
    routes["/repos/GBOGEB/ABACUS/pulls/1956"] = {"head": {"sha": SHA}}
    routes[RUNS_PATH] = {"total_count": None, "workflow_runs": []}
    routes["/repos/GBOGEB/ABACUS/pulls/1956/reviews?per_page=100"] = {"x": 1}
    monkeypatch.setattr(mod, "fetch_github", _fake_fetch(routes))
    out = mod.live_snapshot(None)
    assert out["repositories"]["GBOGEB/ABACUS"]["source"] == "UNKNOWN"
    assert out["ruleset"]["enforcement"] == "UNKNOWN"
    assert out["prs"]["1951"] == {"state": "UNKNOWN", "sha": None}
    assert out["ci"]["status"] == "UNKNOWN"
    assert out["ci"]["source_sha"] == SHA
    assert out["independent_review"] == "UNKNOWN"
    assert "Native CI: ValueError" in out["errors"]
    assert "Reviews: readback unavailable" in out["errors"]
    assert "GBOGEB/CODEX: OSError" in out["errors"]
    assert out["collection"] == "PARTIAL"


def test_cached_live_snapshot_reuses_within_window(monkeypatch):
    monkeypatch.setitem(mod.LIVE_CACHE, "time", 0.0)
    monkeypatch.setitem(mod.LIVE_CACHE, "result", None)
    clock = [1000.0]
    calls = []
    monkeypatch.setattr(mod.time, "monotonic", lambda: clock[0])

    def fake(token):
        calls.append(token)
        return {"n": len(calls)}

    monkeypatch.setattr(mod, "live_snapshot", fake)
    assert mod.cached_live_snapshot(CRED) == {"n": 1}
    clock[0] += 30
    assert mod.cached_live_snapshot(CRED) == {"n": 1}
    clock[0] += 31
    assert mod.cached_live_snapshot(CRED) == {"n": 2}
    clock[0] += 500
    assert mod.cached_live_snapshot(None) == {"n": 2}
    clock[0] += 101
    assert mod.cached_live_snapshot(None) == {"n": 3}
    assert calls == [CRED, CRED, None]


# ---------------------------------------------------------------- clean_tree


def _sut_tree(root):
    (root / "src").mkdir(parents=True)
    (root / "src" / "everred.py").write_bytes(b"print(1)\n")
    (root / "src" / "__pycache__").mkdir()
    (root / "src" / "__pycache__" / "x.pyc").write_bytes(b"0")
    (root / "tests").mkdir()
    (root / "tests" / "test_a.py").write_bytes(b"")
    (root / "docs").write_bytes(b"not a dir")
    return root


def test_clean_tree_copies_allowlisted_dirs(tmp_path):
    src = _sut_tree(tmp_path / "sut")
    dest = tmp_path / "dest"
    dest.mkdir()
    mod.clean_tree(src, dest)
    assert (dest / "src" / "everred.py").read_bytes() == b"print(1)\n"
    assert (dest / "tests" / "test_a.py").exists()
    assert not (dest / "src" / "__pycache__").exists()
    assert not (dest / "docs").exists()
    assert not (dest / "scripts").exists()


def test_clean_tree_refuses_symlinks(tmp_path, monkeypatch):
    src = _sut_tree(tmp_path / "sut")
    (src / "scripts").mkdir()
    (src / "scripts" / "link.txt").write_bytes(b"x")
    real = pathlib.Path.is_symlink

    def fake(self):
        return self.name in ("link.txt", "src") or real(self)

    monkeypatch.setattr(pathlib.Path, "is_symlink", fake)
    dest = tmp_path / "dest"
    dest.mkdir()
    with pytest.raises(ValueError, match="Symlink not allowed"):
        mod.clean_tree(src, dest)
    assert (dest / "tests" / "test_a.py").exists()
    assert not (dest / "src").exists()


# ---------------------------------------------------------------- RunManager


@pytest.fixture
def inert_threads(monkeypatch):
    _Inert.created = []
    monkeypatch.setattr(mod.threading, "Thread", _Inert)
    return _Inert.created


def _manager(root, enabled=True):
    mgr = mod.RunManager(root, execution_enabled=enabled)
    mgr.token = CRED
    return mgr


def test_launch_guards(tmp_path, inert_threads, monkeypatch):
    monkeypatch.setattr(mod, "git_revision", lambda p: SHA)
    assert _manager(tmp_path, enabled=False).launch("unit-tests", CRED)[0] == 403
    mgr = _manager(tmp_path)
    assert mgr.launch("unit-tests", WRONG) == (403, "Invalid local execution token")
    assert mgr.launch("rm-rf", CRED) == (400, "Profile not allowlisted")
    assert mgr.launch("unit-tests", CRED)[0] == 400
    _sut_tree(tmp_path)
    code, record = mgr.launch("unit-tests", CRED)
    assert code == 202
    assert record["status"] == "RUNNING"
    assert record["repository_sha"] == SHA
    assert record["merge_authorized"] is False
    assert mgr.active == record["id"]
    assert inert_threads[0].started is True
    assert inert_threads[0].kwargs["daemon"] is True
    assert mgr.launch("unit-tests", CRED) == (409, "Another SUT run is active")


def _prime(mgr, profile):
    rid = "r" * 16
    mgr.records[rid] = {
        "id": rid,
        "profile": profile,
        "status": "RUNNING",
        "commands": [],
        "logs": [],
        "receipt_sha256": None,
    }
    mgr.active = rid
    return rid


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    tmpdir = tmp_path / "tmp"
    tmpdir.mkdir()
    monkeypatch.setattr(mod.tempfile, "tempdir", str(tmpdir))
    root = _sut_tree(tmp_path / "sut")
    return _manager(root)


def _receipt_ok(record):
    body = {k: v for k, v in record.items() if k != "receipt_sha256"}
    body["receipt_sha256"] = None
    blob = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode()).hexdigest() == record["receipt_sha256"]


def test_work_pipeline_passes(sandbox, monkeypatch):
    seen = []

    def run(cmd, **kw):
        seen.append((cmd, kw))
        return _Result(0, "Ran 3 tests\nOK", "")

    monkeypatch.setattr(mod.subprocess, "run", run)
    rid = _prime(sandbox, "pipeline-testflight")
    sandbox._work(rid)
    record = sandbox.records[rid]
    assert record["status"] == "PASS_LOCAL_ONLY"
    assert len(record["commands"]) == 4
    assert all(c["exit_code"] == 0 for c in record["commands"])
    assert record["commands"][0]["command"][0] == "python"
    assert seen[0][0][0] == sys.executable
    assert seen[0][1]["env"]["NO_COLOR"] == "1"
    assert sandbox.active is None
    assert record["ended_at"]
    assert _receipt_ok(record)


def test_work_red_on_nonzero_exit(sandbox, monkeypatch):
    monkeypatch.setattr(mod.subprocess, "run", lambda c, **k: _Result(2, "", "boom"))
    rid = _prime(sandbox, "pipeline-testflight")
    sandbox._work(rid)
    record = sandbox.records[rid]
    assert record["status"] == "RED"
    assert len(record["commands"]) == 1
    assert "boom" in record["logs"][0]


def test_work_red_when_no_tests_ran(sandbox, monkeypatch):
    monkeypatch.setattr(
        mod.subprocess, "run", lambda c, **k: _Result(0, "", "Ran 0 tests")
    )
    rid = _prime(sandbox, "unit-tests")
    sandbox._work(rid)
    record = sandbox.records[rid]
    assert record["status"] == "RED"
    assert record["logs"][-1] == "FAIL CLOSED: no tests executed"


def test_work_timeout(sandbox, monkeypatch):
    def slow(cmd, **kw):
        raise mod.subprocess.TimeoutExpired(cmd, 180)

    monkeypatch.setattr(mod.subprocess, "run", slow)
    rid = _prime(sandbox, "ledger-verify")
    sandbox._work(rid)
    record = sandbox.records[rid]
    assert record["status"] == "TIMEOUT"
    assert record["commands"][0]["exit_code"] is None
    assert "TIMEOUT" in record["logs"][0]


def test_work_harness_error(sandbox, monkeypatch):
    def broken(source, dest):
        raise ValueError("bad tree")

    monkeypatch.setattr(mod, "clean_tree", broken)
    rid = _prime(sandbox, "unit-tests")
    sandbox._work(rid)
    record = sandbox.records[rid]
    assert record["status"] == "ERROR"
    assert record["logs"] == ["SUT harness error: ValueError: bad tree"]
    assert sandbox.active is None


# ---------------------------------------------------------------- Handler


class _Op:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.token = CRED
        self.calls = []

    def catalog(self):
        return {"profiles": ["p"]}

    def list_runs(self):
        return [{"id": "x"}]

    def artifact(self, rid, index):
        self.calls.append(("artifact", rid, index))
        return (None, b"BIN") if index == 0 else None

    def get_run(self, rid):
        return {"id": rid} if rid == "known" else None

    def plan(self, profile, input_name):
        if profile == "bad":
            raise ValueError("unknown profile")
        return {"profile": profile, "input_name": input_name}

    def cancel(self, rid, token):
        self.calls.append(("cancel", rid, token == self.token))
        return (200, {"cancelled": rid})

    def submit(self, *args):
        self.calls.append(("submit",) + args)
        return (409, "busy")


def _handler(path, manager, operator=None, headers=None, body=b""):
    cls = type("H", (mod.Handler,), {"manager": manager, "operator": operator})
    h = cls.__new__(cls)
    h.path = path
    h.headers = headers or {}
    h.rfile = io.BytesIO(body)
    h.wfile = io.BytesIO()
    h.server = SimpleNamespace(server_port=PORT)
    h.request_version = "HTTP/1.1"
    h.requestline = "X " + path + " HTTP/1.1"
    h.command = "X"
    return h


def _response(h):
    head, _, payload = h.wfile.getvalue().partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    code = int(lines[0].split()[1])
    hdrs = dict(line.split(": ", 1) for line in lines[1:])
    return code, hdrs, payload


def _get(path, manager, operator=None, headers=None):
    h = _handler(path, manager, operator, headers)
    h.do_GET()
    code, hdrs, payload = _response(h)
    return code, hdrs, payload


def _json(payload):
    return json.loads(payload.decode())


@pytest.fixture
def mgr(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "git_revision", lambda p: SHA)
    return _manager(_sut_tree(tmp_path / "sut"))


def test_get_public_routes(mgr, tmp_path, monkeypatch, capsys):
    page = tmp_path / "index.html"
    page.write_bytes(b"<html>hi</html>")
    monkeypatch.setattr(mod.Handler, "public_index", page)
    code, hdrs, payload = _get("/?q=1", mgr)
    assert code == 200
    assert payload == b"<html>hi</html>"
    assert hdrs["Content-Type"].startswith("text/html")
    assert hdrs["X-Frame-Options"] == "DENY"
    assert hdrs["Content-Length"] == str(len(payload))
    assert _get("/index.html", mgr)[0] == 200

    code, _, payload = _get("/api/status", mgr)
    status = _json(payload)
    assert code == 200
    assert status["sut_present"] is True
    assert status["source_sha"] == SHA
    assert status["profiles"] == list(mod.WORKFLOWS)
    assert status["transport"] == "LOCALHOST_ONLY"

    tokens = []
    monkeypatch.setenv("GITHUB_TOKEN", CRED)
    monkeypatch.setattr(
        mod, "cached_live_snapshot", lambda t: tokens.append(t) or {"ok": 1}
    )
    assert _json(_get("/api/live", mgr)[2]) == {"ok": 1}
    assert tokens == [CRED]

    mgr.records = {str(i): {"id": str(i)} for i in range(35)}
    runs = _json(_get("/api/runs", mgr)[2])["runs"]
    assert len(runs) == 30
    assert runs[0]["id"] == "5"
    assert _json(_get("/api/runs/7", mgr)[2]) == {"id": "7"}
    assert _get("/api/runs/nope", mgr)[0] == 404
    assert _get("/elsewhere", mgr)[0] == 404
    assert "[sut-gui]" in capsys.readouterr().err


def test_get_operator_routes(mgr, tmp_path, monkeypatch):
    loop = {"Host": HOST}
    assert _get("/operator", mgr, headers={"Host": "evil:1"})[0] == 403
    assert _get("/api/operator/catalog", mgr)[0] == 403
    page = tmp_path / "operator.html"
    page.write_bytes(b"<op/>")
    monkeypatch.setattr(mod.Handler, "operator_page", page)
    assert _get("/operator", mgr, headers=loop)[2] == b"<op/>"
    assert _get("/api/operator/catalog", mgr, None, loop)[0] == 503
    op = _Op()
    assert _json(_get("/api/operator/catalog", mgr, op, loop)[2]) == {"profiles": ["p"]}
    assert _json(_get("/api/operator/runs", mgr, op, loop)[2]) == {
        "runs": [{"id": "x"}]
    }
    assert _json(_get("/api/operator/runs/known", mgr, op, loop)[2]) == {"id": "known"}
    assert _get("/api/operator/runs/other", mgr, op, loop)[0] == 404
    assert _get("/api/operator/other", mgr, op, loop)[0] == 404


def test_get_operator_artifacts(mgr):
    op = _Op()
    good = dict(Host=HOST)
    good[HDR] = CRED
    bad = dict(Host=HOST)
    bad[HDR] = WRONG
    rid = "0123456789abcdef"
    base = "/api/operator/artifacts/"
    assert _get(base + rid + "/0", mgr, op, bad)[0] == 403
    assert _get(base + rid + "/0", mgr, _Op(enabled=False), good)[0] == 403
    for tail in (rid, rid + "/0/1", "XYZ/0", rid + "/a"):
        assert _get(base + tail, mgr, op, good)[0] == 404
    code, hdrs, payload = _get(base + rid + "/0", mgr, op, good)
    assert (code, payload) == (200, b"BIN")
    assert hdrs["Content-Type"] == "application/octet-stream"
    code, _, payload = _get(base + rid + "/3", mgr, op, good)
    assert code == 404
    assert _json(payload)["error"] == "Missing or altered artifact"
    assert op.calls == [("artifact", rid, 0), ("artifact", rid, 3)]


def _post(path, manager, operator=None, data=None, raw=None, **over):
    body = raw if raw is not None else json.dumps(data).encode()
    headers = {
        "Host": HOST,
        "Origin": ORIGIN,
        "Content-Type": "application/json; charset=utf-8",
        "Content-Length": str(len(body)),
    }
    for key, value in over.items():
        headers[key.replace("_", "-")] = value
    h = _handler(path, manager, operator, headers, body)
    h.do_POST()
    code, _, payload = _response(h)
    return code, _json(payload)


def test_post_request_guards(mgr):
    assert _post("/api/nope", mgr, data={})[0] == 404
    assert _post("/api/operator/plan", mgr, data={}, Host="x")[0] == 403
    assert _post("/api/run", mgr, data={}, Origin="http://evil")[0] == 403
    assert _post("/api/run", mgr, data={}, Content_Type="text/plain")[0] == 415
    assert _post("/api/run", mgr, raw=b"", Content_Length="0")[0] == 400
    big = json.dumps({"profile": "".join(["x"] * 1100)}).encode()
    assert _post("/api/run", mgr, raw=big)[0] == 400
    assert _post("/api/run", mgr, raw=b"{bad")[0] == 400
    assert _post("/api/run", mgr, data=[1])[0] == 400
    assert _post("/api/run", mgr, data={"profile": "x", "extra": 1}) == (
        400,
        {"error": "Invalid request"},
    )


def test_post_run_launches(mgr, inert_threads):
    over = {HDR.replace("-", "_"): CRED}
    code, body = _post("/api/run", mgr, data={"profile": "unit-tests"}, **over)
    assert code == 202
    assert body["result"]["status"] == "RUNNING"
    code, body = _post("/api/run", mgr, data={"profile": "unit-tests"})
    assert code == 403
    assert body == {"error": "Invalid local execution token"}


def test_post_operator_routes(mgr):
    assert _post("/api/operator/plan", mgr, data={"profile": "p"})[0] == 503
    op = _Op()
    plan = _post("/api/operator/plan", mgr, op, data={"profile": "p"})
    assert plan == (200, {"result": {"profile": "p", "input_name": None}})
    data = {"profile": "p", "input_name": "f.pdf"}
    assert (
        _post("/api/operator/plan", mgr, op, data=data)[1]["result"]["input_name"]
        == "f.pdf"
    )
    assert _post("/api/operator/plan", mgr, op, data={"profile": "bad"}) == (
        400,
        {"error": "unknown profile"},
    )
    assert _post("/api/operator/plan", mgr, op, data={"x": 1})[0] == 400
    over = {HDR.replace("-", "_"): CRED}
    cancel = _post("/api/operator/cancel", mgr, op, data={"id": "r1"}, **over)
    assert cancel == (200, {"result": {"cancelled": "r1"}})
    assert _post("/api/operator/cancel", mgr, op, data={})[0] == 400
    submit = dict(
        profile="p",
        input_name="f",
        source_sha=SHA,
        input_sha256="0" * 64,
        consent=True,
        after_seconds=0,
    )
    assert _post("/api/operator/run", mgr, op, data=submit, **over) == (
        409,
        {"error": "busy"},
    )
    assert op.calls[-1] == ("submit", "p", "f", SHA, "0" * 64, True, 0, CRED)
    assert _post("/api/operator/run", mgr, op, data={"profile": "p"})[0] == 400


def test_log_message_goes_to_stderr(mgr, capsys):
    h = _handler("/", mgr)
    h.log_message("%s-%d", "hit", 7)
    assert capsys.readouterr().err.strip() == "[sut-gui] hit-7"


# ---------------------------------------------------------------- main


class _FakeServer:
    instances = []

    def __init__(self, addr, cls):
        self.addr = addr
        self.cls = cls
        self.server_port = addr[1]
        self.served = False
        _FakeServer.instances.append(self)

    def serve_forever(self):
        self.served = True


class _FakeWorkbench:
    def __init__(self, root, inbox, receipts, enabled, token):
        self.root = root
        self.inbox = inbox
        self.receipts = receipts
        self.enabled = enabled
        self.token = token


@pytest.fixture
def fake_server(monkeypatch, tmp_path):
    _FakeServer.instances = []
    monkeypatch.setattr(mod, "ThreadingHTTPServer", _FakeServer)
    monkeypatch.setattr(mod, "OperatorWorkbench", _FakeWorkbench)
    monkeypatch.chdir(tmp_path)
    return _FakeServer.instances


def test_main_default_no_execution(fake_server, monkeypatch, tmp_path, capsys):
    argv = ["server.py", "--sut-root", str(tmp_path), "--port", "9001"]
    monkeypatch.setattr(sys, "argv", argv)
    mod.main()
    out = capsys.readouterr().out
    srv = fake_server[0]
    assert srv.addr == ("127.0.0.1", 9001)
    assert srv.served is True
    assert srv.cls.operator is None
    assert srv.cls.manager.execution_enabled is False
    assert "http://127.0.0.1:9001/" in out
    assert "Execution token" not in out
    assert "Operator:" not in out


def test_main_with_operator_and_execution(fake_server, monkeypatch, tmp_path, capsys):
    argv = ["server.py", "--sut-root", str(tmp_path), "--enable-execution"]
    argv += ["--abacus-root", str(tmp_path), "--enable-operator"]
    monkeypatch.setattr(sys, "argv", argv)
    mod.main()
    out = capsys.readouterr().out
    srv = fake_server[0]
    op = srv.cls.operator
    assert op.enabled is True
    assert op.token == srv.cls.manager.token
    assert op.inbox == tmp_path / "operator-inbox"
    assert "Execution token (enter in GUI; do not share):" in out
    assert "Operator: http://127.0.0.1:8765/operator | enabled: True" in out


def test_main_operator_disabled_custom_dirs(fake_server, monkeypatch, tmp_path, capsys):
    inbox = tmp_path / "in"
    argv = ["server.py", "--abacus-root", str(tmp_path), "--operator-inbox", str(inbox)]
    argv += ["--operator-receipts", str(tmp_path / "rc")]
    monkeypatch.setattr(sys, "argv", argv)
    mod.main()
    out = capsys.readouterr().out
    op = fake_server[0].cls.operator
    assert op.inbox == inbox
    assert op.receipts == tmp_path / "rc"
    assert "Execution token" not in out
    assert "enabled: False" in out


def test_main_rejects_operator_without_root(fake_server, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["server.py", "--enable-operator"])
    with pytest.raises(SystemExit) as info:
        mod.main()
    assert info.value.code == 2
    assert "--enable-operator requires --abacus-root" in capsys.readouterr().err
    assert fake_server == []
