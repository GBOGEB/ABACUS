"""Behaviour tests for tools/everred_v3/sut_gui/operator_workbench.py.

The workbench is a process-local task controller, not a server. No socket is
bound: git and child-process calls go through a fake ``subprocess.run``,
``threading.Thread``/``Timer`` are replaced with inert recorders, and
``tempfile`` is pointed at ``tmp_path``. ``_work`` is driven synchronously.
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load(
    "tools/everred_v3/sut_gui/operator_workbench.py", name="abn_operator_workbench"
)

SHA = "a" * 40
OTHER_SHA = "b" * 40
CRED = "fixed-test-cred"
WRONG = "wrong-test-cred"
PDF = b"%" + b"PDF-1.7 test body"
OOXML = b"PK\x03\x04 fake zip"


class _Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _Inert:
    """Stand-in for Thread/Timer: records construction, never runs."""

    created = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.started = False
        self.cancelled = False
        self.daemon = False
        _Inert.created.append(self)

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True


@pytest.fixture
def inert_threads(monkeypatch):
    _Inert.created = []
    monkeypatch.setattr(mod.threading, "Thread", _Inert)
    monkeypatch.setattr(mod.threading, "Timer", _Inert)
    return _Inert


@pytest.fixture
def env(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    receipts = tmp_path / "receipts"
    monkeypatch.setattr(mod.tempfile, "tempdir", str(tmp_path / "tmp"))
    (tmp_path / "tmp").mkdir()
    return root, inbox, receipts


def _bench(env, enabled=True, timeout_seconds=5):
    root, inbox, receipts = env
    return mod.OperatorWorkbench(
        root,
        inbox,
        receipts,
        enabled=enabled,
        token=CRED,
        timeout_seconds=timeout_seconds,
    )


def _head(monkeypatch, value=SHA):
    monkeypatch.setattr(mod, "_git_head", lambda root: value)


# --- module helpers ---------------------------------------------------------


def test_utc_now_is_timezone_aware_iso():
    value = mod.utc_now()
    assert value.endswith("+00:00")
    assert "T" in value


def test_file_hash_matches_sha256(tmp_path):
    path = tmp_path / "blob.bin"
    path.write_bytes(b"abc" * 1000)
    assert mod.file_hash(path) == hashlib.sha256(b"abc" * 1000).hexdigest()


def test_git_head_returns_valid_sha(monkeypatch, tmp_path):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        return _Result(0, SHA + "\n")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    assert mod._git_head(tmp_path) == SHA
    assert seen["cmd"][-2:] == ["rev-parse", "HEAD"]


@pytest.mark.parametrize(
    "result",
    [_Result(1, SHA), _Result(0, "not-a-sha"), _Result(0, SHA.upper())],
)
def test_git_head_rejects_failure_or_bad_output(monkeypatch, tmp_path, result):
    monkeypatch.setattr(mod.subprocess, "run", lambda cmd, **kw: result)
    assert mod._git_head(tmp_path) is None


@pytest.mark.parametrize("kind", ["oserror", "timeout"])
def test_git_head_swallows_launch_errors(monkeypatch, tmp_path, kind):
    def fake_run(cmd, **kwargs):
        if kind == "oserror":
            raise OSError("no git")
        raise mod.subprocess.TimeoutExpired(cmd, 5)

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    assert mod._git_head(tmp_path) is None


def test_environment_filters_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("GITHUB_TOKEN", "should-not-leak")
    monkeypatch.delenv("LANG", raising=False)
    env = mod._environment(str(tmp_path))
    assert env["PATH"] == "/usr/bin"
    assert "GITHUB_TOKEN" not in env
    assert "LANG" not in env
    assert env["HOME"] == env["TMP"] == env["TEMP"] == str(tmp_path)
    assert env["GIT_CONFIG_NOSYSTEM"] == "1"


def test_default_token_is_generated(env):
    root, inbox, receipts = env
    bench = mod.OperatorWorkbench(root, inbox, receipts)
    assert bench.enabled is False
    assert isinstance(bench.token, str) and len(bench.token) >= 32


# --- inputs -----------------------------------------------------------------


def test_available_inputs_missing_inbox(env, tmp_path):
    root, _, receipts = env
    bench = mod.OperatorWorkbench(root, tmp_path / "absent", receipts, token=CRED)
    assert bench.available_inputs() == []


def test_available_inputs_filters(env):
    _, inbox, _ = env
    (inbox / "good.pdf").write_bytes(PDF)
    (inbox / "b.docx").write_bytes(OOXML)
    (inbox / ".hidden.pdf").write_bytes(PDF)
    (inbox / "notes.txt").write_bytes(b"x")
    (inbox / "empty.pdf").write_bytes(b"")
    (inbox / "folder.pdf").mkdir()
    bench = _bench(env)
    assert bench.available_inputs() == [
        {"name": "b.docx", "bytes": len(OOXML)},
        {"name": "good.pdf", "bytes": len(PDF)},
    ]


@pytest.mark.parametrize("name", [None, 5, "../x.pdf", ".x.pdf", ""])
def test_input_rejects_bad_identifiers(env, name):
    with pytest.raises(ValueError, match="Invalid local input identifier"):
        _bench(env)._input(name)


def test_input_validation_errors(env):
    _, inbox, _ = env
    bench = _bench(env)
    with pytest.raises(ValueError, match="absent"):
        bench._input("missing.pdf")
    (inbox / "a.txt").write_bytes(b"x")
    with pytest.raises(ValueError, match="Unsupported"):
        bench._input("a.txt")
    (inbox / "empty.pdf").write_bytes(b"")
    with pytest.raises(ValueError, match="empty or exceeds"):
        bench._input("empty.pdf")
    (inbox / "bad.xlsx").write_bytes(b"not a zip")
    with pytest.raises(ValueError, match="OOXML"):
        bench._input("bad.xlsx")
    (inbox / "bad.pdf").write_bytes(b"GIF89a")
    with pytest.raises(ValueError, match="PDF signature"):
        bench._input("bad.pdf")


def test_input_accepts_valid_files(env):
    _, inbox, _ = env
    (inbox / "ok.pdf").write_bytes(PDF)
    (inbox / "page.HTML").write_bytes(b"<html></html>")
    bench = _bench(env)
    assert bench._input("ok.pdf").name == "ok.pdf"
    assert bench._input("page.HTML").name == "page.HTML"


# --- planning ---------------------------------------------------------------


def test_plan_unknown_profile(env):
    with pytest.raises(ValueError, match="Unknown"):
        _bench(env).plan("rm-rf")


def test_plan_mcp_is_blocked(env):
    plan = _bench(env).plan("mcp-readiness")
    assert plan["executable"] is False
    assert plan["status"] == "BLOCKED_AUTHENTICATED_MCP_ADAPTER"


def test_plan_requires_git_checkout(env, tmp_path):
    _, inbox, receipts = env
    bench = mod.OperatorWorkbench(tmp_path / "nogit", inbox, receipts, token=CRED)
    with pytest.raises(ValueError, match="checkout not configured"):
        bench.plan("python-tests")


def test_plan_requires_resolvable_head(env, monkeypatch):
    _head(monkeypatch, None)
    with pytest.raises(ValueError, match="Cannot resolve"):
        _bench(env).plan("python-tests")


@pytest.mark.parametrize(
    "profile,needle",
    [
        ("python-tests", "test_mission_control_lite.py"),
        ("pipeline-3p", "tools/generic_3p_pipeline.py"),
        ("debug-compile", "compileall"),
        ("runner-tests", "test_runner_wait.py"),
        ("task-census", "census"),
    ],
)
def test_plan_non_binary_profiles(env, monkeypatch, profile, needle):
    _head(monkeypatch)
    plan = _bench(env).plan(profile, "")
    assert plan["status"] == "DRY_RUN_ONLY"
    assert plan["source_sha"] == SHA
    assert plan["input"] is None
    assert plan["argv"][0][0] == "python"
    assert needle in plan["argv"][0]
    assert plan["merge_admission"] == "HOLD"


def test_plan_pipeline_embeds_source_sha(env, monkeypatch):
    _head(monkeypatch)
    argv = _bench(env).plan("pipeline-3p")["argv"][0]
    assert argv[argv.index("--source-sha") + 1] == SHA


def test_plan_rejects_input_for_non_binary(env, monkeypatch):
    _head(monkeypatch)
    with pytest.raises(ValueError, match="only supported by binary-bridge"):
        _bench(env).plan("python-tests", "x.pdf")


def test_plan_binary_bridge(env, monkeypatch):
    _, inbox, _ = env
    (inbox / "in.pdf").write_bytes(PDF)
    _head(monkeypatch)
    plan = _bench(env).plan("binary-bridge", "in.pdf")
    assert plan["input"] == {
        "name": "in.pdf",
        "bytes": len(PDF),
        "sha256": hashlib.sha256(PDF).hexdigest(),
    }
    assert "operator-input/in.pdf" in plan["argv"][0]


def test_steps_binary_bridge_requires_filename(env):
    with pytest.raises(ValueError, match="verified local input"):
        _bench(env)._steps("binary-bridge", None, SHA)


def test_catalog(env, monkeypatch):
    _, inbox, _ = env
    (inbox / "a.pdf").write_bytes(PDF)
    _head(monkeypatch)
    cat = _bench(env).catalog()
    assert cat["execution_enabled"] is True
    assert cat["source_sha"] == SHA
    assert cat["source_root_configured"] is True
    ids = {p["id"]: p for p in cat["profiles"]}
    assert ids["mcp-readiness"]["executable"] is False
    assert ids["binary-bridge"]["input_required"] is True
    assert cat["inputs"] == [{"name": "a.pdf", "bytes": len(PDF)}]
    assert cat["schedule"]["max_delay_seconds"] == mod.MAX_DELAY


# --- submit / cancel --------------------------------------------------------


def _submit(bench, **overrides):
    args = dict(
        profile="python-tests",
        input_name=None,
        source_sha=SHA,
        input_sha256=None,
        consent=True,
        delay_seconds=0,
        token=CRED,
    )
    args.update(overrides)
    return bench.submit(**args)


def test_submit_guard_rails(env, monkeypatch, inert_threads):
    _head(monkeypatch)
    assert _submit(_bench(env, enabled=False))[0] == 403
    bench = _bench(env)
    assert _submit(bench, token=WRONG) == (403, "Invalid per-process execution token")
    assert _submit(bench, consent="yes")[0] == 403
    assert _submit(bench, delay_seconds=-1)[0] == 400
    assert _submit(bench, delay_seconds=1.5)[0] == 400
    assert _submit(bench, delay_seconds=mod.MAX_DELAY + 1)[0] == 400
    code, msg = _submit(bench, profile="nope")
    assert (code, msg) == (400, "Unknown or unapproved task profile")
    assert _submit(bench, profile="mcp-readiness")[0] == 403
    assert _submit(bench, source_sha=OTHER_SHA)[0] == 409
    assert _submit(bench, input_sha256="f" * 64)[0] == 409
    assert bench.records == {}
    assert inert_threads.created == []


def test_submit_immediate_starts_thread(env, monkeypatch, inert_threads):
    _head(monkeypatch)
    bench = _bench(env)
    code, record = _submit(bench)
    assert code == 202
    assert record["status"] == "STARTING"
    assert bench.active == record["id"]
    (thread,) = inert_threads.created
    assert thread.started and thread.kwargs["daemon"] is True
    assert thread.kwargs["args"] == (record["id"],)
    # capacity-one: a second submission is refused
    assert _submit(bench) == (409, "One active or scheduled task allowed")
    assert bench.list_runs()[0]["id"] == record["id"]
    assert bench.get_run(record["id"])["profile"] == "python-tests"
    assert bench.get_run("missing") is None


def test_submit_scheduled_then_cancel(env, monkeypatch, inert_threads):
    _head(monkeypatch)
    bench = _bench(env)
    code, record = _submit(bench, delay_seconds=30)
    assert code == 202 and record["status"] == "SCHEDULED"
    (timer,) = inert_threads.created
    assert timer.args[0] == 30 and timer.started and timer.daemon
    assert bench.active is None
    assert _submit(bench)[0] == 409

    rid = record["id"]
    assert bench.cancel(rid, "bad") == (403, "Invalid token")
    assert bench.cancel("nope", CRED) == (404, "Unknown local task")
    code, row = bench.cancel(rid, CRED)
    assert code == 200
    assert row["status"] == "CANCELLED"
    assert timer.cancelled
    receipt = json.loads((bench.receipt_dir / rid / "receipt.json").read_text("utf-8"))
    assert receipt["receipt_sha256"] == row["receipt_sha256"]
    assert bench.cancel(rid, CRED)[0] == 409


def test_cancel_scheduled_without_timer(env):
    bench = _bench(env)
    bench.records["r1"] = {"id": "r1", "status": "SCHEDULED", "finished_at": None}
    code, row = bench.cancel("r1", CRED)
    assert code == 200 and row["status"] == "CANCELLED"


# --- _work ------------------------------------------------------------------


def _record(bench, rid="run1", argv=None, input_identity=None, status="STARTING"):
    row = {
        "id": rid,
        "profile": "python-tests",
        "status": status,
        "source_sha": SHA,
        "input": input_identity,
        "argv": argv if argv is not None else [["python", "-m", "x"]],
        "started_at": None,
        "finished_at": None,
        "steps": [],
        "artifacts": [],
        "receipt_sha256": None,
    }
    bench.records[rid] = row
    return row


class _FakeRunner:
    """Fake subprocess.run covering git clone/checkout and child steps."""

    def __init__(
        self,
        clone_rc=0,
        step_rc=0,
        step_stdout=b"OK\n",
        outputs=None,
        timeout=False,
    ):
        self.clone_rc = clone_rc
        self.step_rc = step_rc
        self.step_stdout = step_stdout
        self.outputs = outputs if outputs is not None else {"r.json": b"{}"}
        self.timeout = timeout
        self.calls = []

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        if cmd[0] == "git":
            if "clone" in cmd:
                Path(cmd[-1]).mkdir(parents=True)
                return _Result(self.clone_rc, "", "fatal: clone broke")
            return _Result(0)
        assert cmd[0] == sys.executable
        if self.timeout:
            raise mod.subprocess.TimeoutExpired(cmd, 5)
        clone = Path(kwargs["cwd"])
        for rel, data in self.outputs.items():
            target = clone / "operator-output" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        kwargs["stdout"].write(self.step_stdout)
        kwargs["stderr"].write(b"warn\n")
        return _Result(self.step_rc)


def _receipt(bench, rid="run1"):
    path = bench.receipt_dir / rid / "receipt.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_work_happy_path_collects_artifacts(env, monkeypatch):
    _head(monkeypatch)
    runner = _FakeRunner(outputs={"r.json": b"{}", "sub/n.txt": b"hello"})
    monkeypatch.setattr(mod.subprocess, "run", runner)
    bench = _bench(env)
    row = _record(bench)
    bench.active = "run1"
    bench._work("run1")
    assert row["status"] == "PASS_LOCAL_ONLY"
    assert bench.active is None
    assert row["steps"][0]["stdout"] == "OK\n"
    assert row["steps"][0]["stderr"] == "warn\n"
    paths = sorted(a["path"] for a in row["artifacts"])
    assert paths == ["artifacts/r.json", "artifacts/sub/n.txt"]
    assert _receipt(bench)["status"] == "PASS_LOCAL_ONLY"
    idx = [a["path"] for a in row["artifacts"]].index("artifacts/sub/n.txt")
    assert bench.artifact("run1", idx) == ("n.txt", b"hello")


def test_artifact_rejections(env, monkeypatch):
    _head(monkeypatch)
    monkeypatch.setattr(mod.subprocess, "run", _FakeRunner())
    bench = _bench(env)
    _record(bench)
    bench._work("run1")
    assert bench.artifact("missing", 0) is None
    assert bench.artifact("run1", 5) is None
    assert bench.artifact("run1", "0") is None
    stored = bench.receipt_dir / "run1" / "artifacts" / "r.json"
    stored.write_bytes(b"[]")
    assert bench.artifact("run1", 0) is None
    stored.unlink()
    assert bench.artifact("run1", 0) is None


def test_work_red_on_nonzero_return(env, monkeypatch):
    _head(monkeypatch)
    monkeypatch.setattr(mod.subprocess, "run", _FakeRunner(step_rc=1))
    bench = _bench(env)
    row = _record(bench, argv=[["python", "a"], ["python", "b"]])
    bench._work("run1")
    assert row["status"] == "RED"
    assert len(row["steps"]) == 1


def test_work_red_when_zero_tests_ran(env, monkeypatch):
    _head(monkeypatch)
    runner = _FakeRunner(step_stdout=b"Ran 0 tests in 0.000s\n")
    monkeypatch.setattr(mod.subprocess, "run", runner)
    bench = _bench(env)
    row = _record(bench)
    bench._work("run1")
    assert row["status"] == "RED"


def test_work_timeout(env, monkeypatch):
    _head(monkeypatch)
    monkeypatch.setattr(mod.subprocess, "run", _FakeRunner(timeout=True))
    bench = _bench(env)
    row = _record(bench)
    bench._work("run1")
    assert row["status"] == "TIMEOUT"
    assert row["steps"][-1]["stderr"] == "Timed out"


def test_work_stale_source(env, monkeypatch):
    _head(monkeypatch, OTHER_SHA)
    bench = _bench(env)
    row = _record(bench)
    bench._work("run1")
    assert row["status"] == "STALE_SOURCE"
    assert "STALE_SOURCE" in row["steps"][-1]["stderr"]


def test_work_clone_failure(env, monkeypatch):
    _head(monkeypatch)
    monkeypatch.setattr(mod.subprocess, "run", _FakeRunner(clone_rc=128))
    bench = _bench(env)
    row = _record(bench)
    bench._work("run1")
    assert row["status"] == "ERROR"
    assert "clone broke" in row["steps"][-1]["stderr"]


def test_work_clone_identity_mismatch(env, monkeypatch):
    root = env[0].resolve()
    monkeypatch.setattr(
        mod, "_git_head", lambda path: SHA if Path(path) == root else OTHER_SHA
    )
    monkeypatch.setattr(mod.subprocess, "run", _FakeRunner())
    bench = _bench(env)
    row = _record(bench)
    bench._work("run1")
    assert row["status"] == "ERROR"
    assert "identity mismatch" in row["steps"][-1]["stderr"]


def test_work_too_many_outputs(env, monkeypatch):
    _head(monkeypatch)
    outputs = {"f{}.txt".format(i): b"x" for i in range(65)}
    monkeypatch.setattr(mod.subprocess, "run", _FakeRunner(outputs=outputs))
    bench = _bench(env)
    row = _record(bench)
    bench._work("run1")
    assert row["status"] == "ERROR"
    assert "Too many" in row["steps"][-1]["stderr"]


def test_work_with_binary_input(env, monkeypatch):
    _, inbox, _ = env
    (inbox / "in.pdf").write_bytes(PDF)
    _head(monkeypatch)
    staged = {}
    runner = _FakeRunner()

    def capture(cmd, **kwargs):
        if cmd[0] == sys.executable:
            copy = Path(kwargs["cwd"]) / "operator-input" / "in.pdf"
            staged["bytes"] = copy.read_bytes()
        return runner(cmd, **kwargs)

    monkeypatch.setattr(mod.subprocess, "run", capture)
    bench = _bench(env)
    identity = {
        "name": "in.pdf",
        "bytes": len(PDF),
        "sha256": hashlib.sha256(PDF).hexdigest(),
    }
    row = _record(bench, input_identity=identity)
    bench._work("run1")
    assert row["status"] == "PASS_LOCAL_ONLY"
    assert staged["bytes"] == PDF
    assert (inbox / "in.pdf").read_bytes() == PDF


def test_work_input_changed_after_approval(env, monkeypatch):
    _, inbox, _ = env
    (inbox / "in.pdf").write_bytes(PDF)
    _head(monkeypatch)
    monkeypatch.setattr(mod.subprocess, "run", _FakeRunner())
    bench = _bench(env)
    identity = {"name": "in.pdf", "bytes": len(PDF), "sha256": "0" * 64}
    row = _record(bench, input_identity=identity)
    bench._work("run1")
    assert row["status"] == "ERROR"
    assert "changed after approval" in row["steps"][-1]["stderr"]


def test_work_skips_cancelled(env):
    bench = _bench(env)
    row = _record(bench, status="CANCELLED")
    bench.timers["run1"] = object()
    bench._work("run1")
    assert row["status"] == "CANCELLED"
    assert "run1" not in bench.timers
    assert not (bench.receipt_dir / "run1").exists()


def test_work_capacity_hold(env):
    bench = _bench(env)
    row = _record(bench, status="SCHEDULED")
    bench.active = "other"
    bench._work("run1")
    assert row["status"] == "CAPACITY_HOLD"
    assert bench.active == "other"
    assert _receipt(bench)["status"] == "CAPACITY_HOLD"


def test_work_receipt_write_failure(env, monkeypatch):
    _head(monkeypatch)
    monkeypatch.setattr(mod.subprocess, "run", _FakeRunner())
    bench = _bench(env)
    row = _record(bench)
    folder = bench.receipt_dir / "run1"
    folder.mkdir(parents=True)
    (folder / "receipt.json").write_bytes(b"pre-existing")
    bench.active = "run1"
    bench._work("run1")
    assert row["status"] == "RECEIPT_WRITE_FAILED"
    assert bench.active is None
    assert (folder / "receipt.json").read_bytes() == b"pre-existing"
