"""Lane-B wave 9: everred_v3 runtime_probe host/debugger/Docker observations.

Every external effect (executables, sockets, platform, host files, temp dirs)
is replaced on the loaded module object, so nothing real is executed.
"""

import contextlib
import datetime as dt
import hashlib
import types
from pathlib import Path

import pytest

from ._l2_loader import load

fp = load("tools/everred_v3/src/four_planes.py")
rp = load("tools/everred_v3/src/runtime_probe.py", deps={"four_planes": fp})

A = "a" * 40
REPO = "GBOGEB/ABACUS"
OS_RELEASE = "/etc/os-release"
FIPS = "/proc/sys/crypto/fips_enabled"
BINARY = b"\x7fELF-probe"
TimeoutExpired = rp.subprocess.TimeoutExpired


def _src():
    return fp.Source(repository=REPO, source_sha=A, run_id=5, job_id=6)


def _which(monkeypatch, available):
    found = {name: "/usr/bin/" + name for name in available}
    monkeypatch.setattr(rp, "shutil", types.SimpleNamespace(which=found.get))


class _Completed:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _subprocess(monkeypatch, handler):
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return handler(argv, **kwargs)

    fake = types.SimpleNamespace(DEVNULL=-3, TimeoutExpired=TimeoutExpired, run=run)
    monkeypatch.setattr(rp, "subprocess", fake)
    return calls


def _platform(monkeypatch, system="Linux"):
    fake = types.SimpleNamespace(
        system=lambda: system, release=lambda: "6.1.0", machine=lambda: "x86_64"
    )
    monkeypatch.setattr(rp, "platform", fake)


def _host_files(monkeypatch, tmp_path, os_release=None, fips=None):
    mapping = {OS_RELEASE: tmp_path / "os-release", FIPS: tmp_path / "fips"}
    if os_release is not None:
        mapping[OS_RELEASE].write_text(os_release, encoding="utf-8")
    if fips is not None:
        mapping[FIPS].write_text(fips, encoding="utf-8")

    def fake_path(value):
        return mapping.get(value, Path(value))

    monkeypatch.setattr(rp, "Path", fake_path)


# --- timestamp ------------------------------------------------------------------------------------


def test_timestamp_is_utc_z():
    stamp = rp.timestamp()
    assert stamp.endswith("Z")
    parsed = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    assert parsed.utcoffset() == dt.timedelta(0)


# --- _call ----------------------------------------------------------------------------------------


def test_call_blocks_unlisted_executable(monkeypatch):
    calls = _subprocess(monkeypatch, lambda argv, **kw: _Completed())
    assert rp._call(["rm", "-rf", "/"]) == {
        "status": "BLOCKED",
        "exit_code": None,
        "stdout": None,
    }
    assert calls == []


def test_call_unavailable_executable(monkeypatch):
    _which(monkeypatch, [])
    assert rp._call(["/opt/bin/docker", "--version"]) == {
        "status": "UNAVAILABLE",
        "exit_code": None,
        "stdout": None,
    }


def test_call_executes_with_bounded_env(monkeypatch):
    _which(monkeypatch, ["gcc"])
    monkeypatch.setenv("PATH", "/usr/bin")
    calls = _subprocess(
        monkeypatch,
        lambda argv, **kw: _Completed(3, "out\x1b[31m red", "tok" + "en=abc"),
    )
    res = rp._call(["gcc", "--version"], timeout=4)
    assert res["status"] == "EXECUTED"
    assert res["exit_code"] == 3
    assert res["stdout"]["excerpt"] == "out red"
    assert res["stderr"]["excerpt"] == "[REDACTED]"
    argv, kwargs = calls[0]
    assert argv == ["/usr/bin/gcc", "--version"]
    assert kwargs["timeout"] == 4
    assert kwargs["env"] == {"PATH": "/usr/bin"}
    assert kwargs["check"] is False
    assert kwargs["stdin"] == -3
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True


def test_call_env_path_defaults_to_empty(monkeypatch):
    _which(monkeypatch, ["cc"])
    monkeypatch.delenv("PATH", raising=False)
    calls = _subprocess(monkeypatch, lambda argv, **kw: _Completed())
    assert rp._call(["cc"])["status"] == "EXECUTED"
    assert calls[0][1]["env"] == {"PATH": ""}
    assert calls[0][1]["timeout"] == 8


@pytest.mark.parametrize(
    "exc,name",
    [(OSError("boom"), "OSError"), (TimeoutExpired("lldb", 1), "TimeoutExpired")],
)
def test_call_error_paths(monkeypatch, exc, name):
    _which(monkeypatch, ["lldb"])

    def boom(argv, **kw):
        raise exc

    _subprocess(monkeypatch, boom)
    assert rp._call(["lldb", "--version"]) == {
        "status": "ERROR",
        "exit_code": None,
        "error": name,
    }


# --- os_identity ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "system,release,family",
    [
        ("Darwin", None, "macOS"),
        ("Windows", None, "Windows"),
        ("Linux", 'ID="rhel"\nVERSION_ID="8.9"\n', "RHEL8"),
        ("Linux", "ID=redhat\nVERSION_ID=9.2\n", "RHEL9"),
        ("Linux", "ID=RHEL\nVERSION_ID=7.9\n", "OTHER"),
        ("Linux", "ID=ubuntu\nVERSION_ID=22.04\n", "Ubuntu"),
        ("Linux", "ID=debian\n", "Debian"),
        ("Linux", "ID=arch\n", "OTHER"),
        ("Linux", None, "OTHER"),
    ],
)
def test_os_identity_families(monkeypatch, tmp_path, system, release, family):
    _platform(monkeypatch, system)
    _host_files(monkeypatch, tmp_path, os_release=release)
    out = rp.os_identity()
    assert out["os_family"] == family
    assert out["kernel"] == "6.1.0"
    assert out["architecture"] == "x86_64"
    assert out["fips_mode"] is None
    assert out["evidence_status"] == "LOCAL_HOST_OBSERVED_NOT_REMOTE_RHEL_PROOF"


def test_os_identity_parses_release_and_fips(monkeypatch, tmp_path):
    _platform(monkeypatch, "Linux")
    release = (
        "# comment=ignored\n"
        "NO_EQUALS_LINE\n"
        'PRETTY_NAME="Red Hat Enterprise Linux 9.2 (Plow)"\n'
        "ID=rhel\n"
        "VERSION_ID=9.2\n"
        "URL=https://x/?a=b\n"
    )
    _host_files(monkeypatch, tmp_path, os_release=release, fips=" 1\n")
    out = rp.os_identity()
    assert out["os_family"] == "RHEL9"
    assert out["os_release"] == "Red Hat Enterprise Linux 9.2 (Plow)"
    assert out["fips_mode"] == 1


def test_os_identity_release_defaults_to_system(monkeypatch, tmp_path):
    _platform(monkeypatch, "Linux")
    _host_files(monkeypatch, tmp_path, os_release="ID=debian\n", fips="0")
    out = rp.os_identity()
    assert out["os_release"] == "Linux"
    assert out["fips_mode"] == 0


def test_os_identity_bad_fips_value(monkeypatch, tmp_path):
    _platform(monkeypatch, "Linux")
    _host_files(monkeypatch, tmp_path, fips="enabled")
    assert rp.os_identity()["fips_mode"] is None


def test_os_identity_fips_read_oserror(monkeypatch):
    _platform(monkeypatch, "Linux")

    class Unreadable:
        def __init__(self, value):
            self.value = value

        def is_file(self):
            return self.value == FIPS

        def read_text(self, *args, **kwargs):
            raise OSError("denied")

    monkeypatch.setattr(rp, "Path", Unreadable)
    out = rp.os_identity()
    assert out["fips_mode"] is None
    assert out["os_family"] == "OTHER"


# --- transient loopback probe ---------------------------------------------------------------------


class _FakeSocket:
    instances = []

    def __init__(self, family, kind):
        self.family = family
        self.kind = kind
        self.events = []
        self.accepted = None
        _FakeSocket.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.events.append("exit")
        return False

    def setsockopt(self, *args):
        self.events.append(("setsockopt", args))

    def bind(self, addr):
        self.events.append(("bind", addr))

    def getsockname(self):
        return ("127.0.0.1", 40404)

    def listen(self, backlog):
        self.events.append(("listen", backlog))

    def settimeout(self, value):
        self.events.append(("timeout", value))

    def connect(self, addr):
        self.events.append(("connect", addr))

    def accept(self):
        conn = types.SimpleNamespace(closed=False)

        def close():
            conn.closed = True

        conn.close = close
        self.accepted = conn
        return conn, ("127.0.0.1", 50000)


def _fake_socket(monkeypatch):
    _FakeSocket.instances = []
    fake = types.SimpleNamespace(
        AF_INET=2, SOCK_STREAM=1, SOL_SOCKET=65535, SO_REUSEADDR=4, socket=_FakeSocket
    )
    monkeypatch.setattr(rp, "socket", fake)


def test_transient_loopback_probe(monkeypatch):
    _fake_socket(monkeypatch)
    out = rp.transient_loopback_probe()
    assert out["port"] == 40404
    assert out["host"] == "127.0.0.1"
    assert out["state"] == "OBSERVED_CLOSED"
    assert out["probe_id"] == "loopback-self-test"
    assert out["tested_at"].endswith("Z")
    assert "not evidence" in out["note"]
    listener, peer = _FakeSocket.instances
    assert (listener.family, listener.kind) == (2, 1)
    assert ("bind", ("127.0.0.1", 0)) in listener.events
    assert ("setsockopt", (65535, 4, 1)) in listener.events
    assert ("listen", 1) in listener.events
    assert ("connect", ("127.0.0.1", 40404)) in peer.events
    assert listener.accepted.closed is True
    assert listener.events[-1] == "exit"
    assert peer.events[-1] == "exit"


# --- observe_host ---------------------------------------------------------------------------------


def test_observe_host_without_port_probe(monkeypatch, tmp_path):
    _platform(monkeypatch, "Darwin")
    _host_files(monkeypatch, tmp_path)
    monkeypatch.setenv("RUNNER_NAME", "runner-7")
    out = rp.observe_host(_src())
    assert out["plane"] == "runtime"
    assert out["domain"] == "host_container"
    assert out["trust"] == "LOCAL_OBSERVED"
    assert out["source_binding"] == _src().binding()
    data = out["data"]
    assert data["os_family"] == "macOS"
    assert data["runner_id"] == "runner-7"
    assert data["ports"] == []
    assert data["container_runtime"] == "none"
    assert data["container_id"] is None
    assert data["evidence_status"] == "LOCAL_HOST_OBSERVED_NOT_REMOTE_RHEL_PROOF"


def test_observe_host_with_port_probe(monkeypatch, tmp_path):
    _platform(monkeypatch, "Windows")
    _host_files(monkeypatch, tmp_path)
    _fake_socket(monkeypatch)
    monkeypatch.delenv("RUNNER_NAME", raising=False)
    out = rp.observe_host(_src(), port_probe=True)
    assert out["data"]["runner_id"] is None
    (port,) = out["data"]["ports"]
    assert port["port"] == 40404
    assert port["state"] == "OBSERVED_CLOSED"


# --- docker / lldb availability -------------------------------------------------------------------


def test_docker_unavailable(monkeypatch):
    _which(monkeypatch, [])
    assert rp.observe_docker_availability() == {
        "docker_cli": "UNAVAILABLE",
        "daemon": "UNKNOWN",
        "containers": None,
    }


@pytest.mark.parametrize("code,status", [(0, "OBSERVED"), (1, "ERROR")])
def test_docker_version_probe(monkeypatch, code, status):
    _which(monkeypatch, ["docker"])
    calls = _subprocess(
        monkeypatch, lambda argv, **kw: _Completed(code, "Docker version 27", "")
    )
    out = rp.observe_docker_availability()
    assert out["docker_cli"] == status
    assert out["daemon"] == "UNKNOWN"
    assert out["containers"] is None
    assert out["version_probe"]["exit_code"] == code
    assert calls[0][0] == ["/usr/bin/docker", "--version"]
    assert calls[0][1]["timeout"] == 5


def test_docker_version_probe_error(monkeypatch):
    _which(monkeypatch, ["docker"])

    def boom(argv, **kw):
        raise OSError("gone")

    _subprocess(monkeypatch, boom)
    out = rp.observe_docker_availability()
    assert out["docker_cli"] == "ERROR"
    assert out["version_probe"]["status"] == "ERROR"


def test_lldb_unavailable(monkeypatch):
    _which(monkeypatch, [])
    assert rp.observe_lldb_availability() == {
        "lldb_cli": "UNAVAILABLE",
        "real_step_count": None,
        "session_status": "UNKNOWN",
    }


@pytest.mark.parametrize("code,status", [(0, "OBSERVED"), (2, "ERROR")])
def test_lldb_version_probe(monkeypatch, code, status):
    _which(monkeypatch, ["lldb"])
    calls = _subprocess(monkeypatch, lambda argv, **kw: _Completed(code, "lldb-17"))
    out = rp.observe_lldb_availability()
    assert out["lldb_cli"] == status
    assert out["real_step_count"] is None
    assert out["session_status"] == "NOT_EXECUTED"
    assert out["version_probe"]["stdout"]["excerpt"] == "lldb-17"
    assert calls[0][1]["timeout"] == 8


# --- probe_debug_target ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "available",
    [[], ["lldb"], ["cc"], ["gcc"], ["clang"]],
)
def test_probe_debug_target_unavailable(monkeypatch, available):
    _which(monkeypatch, available)
    calls = _subprocess(monkeypatch, lambda argv, **kw: _Completed())
    assert rp.probe_debug_target(_src()) == (
        {},
        {"status": "UNAVAILABLE", "real_step_count": None},
    )
    assert calls == []


def _tempdir(monkeypatch, tmp_path):
    @contextlib.contextmanager
    def temporary_directory(prefix=""):
        assert prefix == "everred-lldb-"
        yield str(tmp_path)

    monkeypatch.setattr(
        rp, "tempfile", types.SimpleNamespace(TemporaryDirectory=temporary_directory)
    )


def _toolchain(compile_rc=0, lldb=None, compile_err=""):
    """Fake compiler writes the output binary; the lldb call returns ``lldb``."""

    def handler(argv, **kwargs):
        if argv[0].endswith("/lldb"):
            if isinstance(lldb, Exception):
                raise lldb
            return lldb
        if compile_rc == 0:
            Path(argv[-1]).write_bytes(BINARY)
        return _Completed(compile_rc, "", compile_err)

    return handler


@pytest.mark.parametrize("compiler", ["cc", "clang", "gcc"])
def test_probe_debug_target_compile_failure(monkeypatch, tmp_path, compiler):
    _which(monkeypatch, [compiler, "lldb"])
    _tempdir(monkeypatch, tmp_path)
    calls = _subprocess(
        monkeypatch, _toolchain(compile_rc=1, compile_err="probe.c:1: error")
    )
    receipt, status = rp.probe_debug_target(_src())
    assert receipt == {}
    assert status["status"] == "COMPILATION_FAILED"
    assert status["real_step_count"] == 0
    assert status["compile_log"]["excerpt"] == "probe.c:1: error"
    (call,) = calls
    argv, kwargs = call
    src = tmp_path / "probe.c"
    dest = tmp_path / "probe-bin"
    assert argv == ["/usr/bin/" + compiler, "-g", "-O0", str(src), "-o", str(dest)]
    assert kwargs["timeout"] == 20
    assert "int square(int x)" in src.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "stdout,stderr,steps,status",
    [
        (
            "Process 1 stopped\n* thread #1, stop reason = breakpoint 1.1\n",
            "stop reason = step over",
            1,
            "LOCAL_PROBE_OBSERVED",
        ),
        (
            "Stop Reason = Breakpoint 1.1\n  frame #0: probe-bin square",
            "",
            1,
            "LOCAL_PROBE_OBSERVED",
        ),
        ("stop reason = breakpoint 1.1\n", "", 0, "PROBE_FAILED_OR_RESTRICTED"),
        ("(lldb) run\n", "frame #0", 0, "PROBE_FAILED_OR_RESTRICTED"),
    ],
)
def test_probe_debug_target_lldb_outcomes(
    monkeypatch, tmp_path, stdout, stderr, steps, status
):
    _which(monkeypatch, ["cc", "lldb"])
    _tempdir(monkeypatch, tmp_path)
    monkeypatch.setenv("RUNNER_NAME", "runner-9")
    calls = _subprocess(monkeypatch, _toolchain(lldb=_Completed(0, stdout, stderr)))
    receipt, out = rp.probe_debug_target(_src())
    assert out["status"] == status
    assert out["real_step_count"] == steps
    assert out["result"]["status"] == "EXECUTED"
    assert receipt["plane"] == "diagnostic"
    assert receipt["domain"] == "debugger"
    assert receipt["trust"] == "LOCAL_OBSERVED"
    data = receipt["data"]
    assert data["tool"] == "LLDB"
    assert data["reported_steps"] == steps
    assert data["observed_step_evidence"] is bool(steps)
    assert data["breakpoints"] == ["square"]
    assert data["frames"] == []
    assert data["runner_id"] == "runner-9"
    joined = stdout + "\n" + stderr
    session = "local-" + hashlib.sha256(joined.encode()).hexdigest()[:16]
    assert data["session_id"] == session
    assert data["binary_build_id"] == hashlib.sha256(BINARY).hexdigest()
    assert data["started_at"].endswith("Z")
    lldb_argv, lldb_kwargs = calls[1]
    assert lldb_argv[0] == "/usr/bin/lldb"
    assert lldb_argv[1] == "--batch"
    assert lldb_argv[-2:] == ["--", str(tmp_path / "probe-bin")]
    assert "breakpoint set --name square" in lldb_argv
    assert lldb_kwargs["timeout"] == 30


def test_probe_debug_target_nonzero_lldb_exit(monkeypatch, tmp_path):
    _which(monkeypatch, ["gcc", "lldb"])
    _tempdir(monkeypatch, tmp_path)
    _subprocess(
        monkeypatch,
        _toolchain(lldb=_Completed(1, "stop reason = breakpoint\nframe #0", "")),
    )
    receipt, out = rp.probe_debug_target(_src())
    assert out["status"] == "PROBE_FAILED_OR_RESTRICTED"
    assert out["real_step_count"] == 0
    assert out["result"]["exit_code"] == 1
    assert receipt["data"]["reported_steps"] == 0


def test_probe_debug_target_lldb_error_has_no_logs(monkeypatch, tmp_path):
    _which(monkeypatch, ["cc", "lldb"])
    _tempdir(monkeypatch, tmp_path)
    _subprocess(monkeypatch, _toolchain(lldb=TimeoutExpired("lldb", 30)))
    receipt, out = rp.probe_debug_target(_src())
    assert out["result"] == {
        "status": "ERROR",
        "exit_code": None,
        "error": "TimeoutExpired",
    }
    assert out["status"] == "PROBE_FAILED_OR_RESTRICTED"
    assert out["real_step_count"] == 0
    assert receipt["data"]["session_id"] == (
        "local-" + hashlib.sha256(b"\n").hexdigest()[:16]
    )
