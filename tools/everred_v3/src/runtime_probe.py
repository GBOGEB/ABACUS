"""Read-only, bounded host/debugger/Docker observations; no live proof invention."""

from __future__ import annotations

import datetime as dt
import hashlib
import os
import platform
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path

from four_planes import Source, clean_log, diagnostic_receipt, runtime_receipt


def timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _call(args: list[str], timeout: int = 8) -> dict:
    """Bounded fixed executable argv, never shell or user-injected commands."""
    allow = {"lldb", "docker", "podman", "cc", "clang", "gcc"}
    if Path(args[0]).name not in allow:
        return {"status": "BLOCKED", "exit_code": None, "stdout": None}
    executable = shutil.which(args[0])
    if not executable:
        return {"status": "UNAVAILABLE", "exit_code": None, "stdout": None}
    try:
        res = subprocess.run(
            [executable, *args[1:]],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env={"PATH": os.getenv("PATH", "")},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "ERROR", "exit_code": None, "error": type(exc).__name__}
    return {
        "status": "EXECUTED",
        "exit_code": res.returncode,
        "stdout": clean_log(res.stdout),
        "stderr": clean_log(res.stderr),
    }


def os_identity() -> dict:
    raw = {}
    p = Path("/etc/os-release")
    if p.is_file():
        for line in p.read_text(encoding="utf-8")[:8192].splitlines():
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                raw[key] = value.strip().strip('"')
    system = platform.system()
    version = raw.get("VERSION_ID", "")
    dist = raw.get("ID", "").lower()
    if system == "Darwin":
        family = "macOS"
    elif system == "Windows":
        family = "Windows"
    elif dist in ("rhel", "redhat") and version.startswith(("8", "9")):
        family = "RHEL" + version[0]
    elif dist == "ubuntu":
        family = "Ubuntu"
    elif dist == "debian":
        family = "Debian"
    else:
        family = "OTHER"
    fips = Path("/proc/sys/crypto/fips_enabled")
    try:
        fips_mode = int(fips.read_text().strip()) if fips.is_file() else None
    except (ValueError, OSError):
        fips_mode = None
    return {
        "os_family": family,
        "os_release": raw.get("PRETTY_NAME", system),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "fips_mode": fips_mode,
        "evidence_status": "LOCAL_HOST_OBSERVED_NOT_REMOTE_RHEL_PROOF",
    }


def transient_loopback_probe() -> dict:
    """Real network probe closed before returning, never an active-listener claim."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        listener.listen(1)
        listener.settimeout(2)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer:
            peer.settimeout(2)
            peer.connect(("127.0.0.1", port))
            conn, _ = listener.accept()
            conn.close()
    return {
        "port": port,
        "host": "127.0.0.1",
        "state": "OBSERVED_CLOSED",
        "tested_at": timestamp(),
        "probe_id": "loopback-self-test",
        "note": "ephemeral socket closed; not evidence of a running service",
    }


def observe_host(source: Source, *, port_probe: bool = False) -> dict:
    data = os_identity()
    data.update(
        {
            "container_runtime": "none",
            "container_id": None,
            "image_digest": None,
            "runner_id": os.getenv("RUNNER_NAME"),
            "ports": [transient_loopback_probe()] if port_probe else [],
            "container_health": None,
            "exit_code": None,
            "logs": [],
        }
    )
    return runtime_receipt(source, data, trust="LOCAL_OBSERVED")


def observe_docker_availability() -> dict:
    """Installed Docker CLI is not Docker daemon or container proof."""
    binary = shutil.which("docker")
    if not binary:
        return {"docker_cli": "UNAVAILABLE", "daemon": "UNKNOWN", "containers": None}
    res = _call(["docker", "--version"], timeout=5)
    return {
        "docker_cli": "OBSERVED" if res.get("exit_code") == 0 else "ERROR",
        "daemon": "UNKNOWN",
        "containers": None,
        "version_probe": res,
    }


def observe_lldb_availability() -> dict:
    binary = shutil.which("lldb")
    if not binary:
        return {
            "lldb_cli": "UNAVAILABLE",
            "real_step_count": None,
            "session_status": "UNKNOWN",
        }
    res = _call(["lldb", "--version"], timeout=8)
    return {
        "lldb_cli": "OBSERVED" if res.get("exit_code") == 0 else "ERROR",
        "real_step_count": None,
        "session_status": "NOT_EXECUTED",
        "version_probe": res,
    }


def probe_debug_target(source: Source) -> tuple[dict, dict]:
    """Compile and step a disposable C target; failure remains a FAILED probe.

    This runs only after explicit invocation by the operator or native job;
    no customer process, remote debugger or sensitive source is touched.
    """
    cc = shutil.which("cc") or shutil.which("clang") or shutil.which("gcc")
    if not cc or not shutil.which("lldb"):
        return {}, {"status": "UNAVAILABLE", "real_step_count": None}
    code = '#include <stdio.h>\nint square(int x) { return x * x; }\nint main(void) { printf("%d\\n", square(3)); return 0; }\n'
    with tempfile.TemporaryDirectory(prefix="everred-lldb-") as tmp:
        src = Path(tmp) / "probe.c"
        dest = Path(tmp) / "probe-bin"
        src.write_text(code, encoding="utf-8")
        compiled = subprocess.run(
            [cc, "-g", "-O0", str(src), "-o", str(dest)],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if compiled.returncode != 0:
            return {}, {
                "status": "COMPILATION_FAILED",
                "real_step_count": 0,
                "compile_log": clean_log(compiled.stderr),
            }
        result = _call(
            [
                "lldb",
                "--batch",
                "-o",
                "breakpoint set --name square",
                "-o",
                "run",
                "-o",
                "thread step-over",
                "-o",
                "thread backtrace",
                "--",
                str(dest),
            ],
            timeout=30,
        )
        joined = (
            (result.get("stdout") or {}).get("excerpt", "")
            + "\n"
            + (result.get("stderr") or {}).get("excerpt", "")
        )
        hit = (
            result.get("exit_code") == 0
            and "stop reason = breakpoint" in joined.lower()
        )
        # A debugger command echoed in a log is not, alone, execution proof.
        real_steps = (
            1
            if hit
            and ("stop reason = step" in joined.lower() or "frame #" in joined.lower())
            else 0
        )
        dbg = {
            "tool": "LLDB",
            "session_id": "local-" + hashlib.sha256(joined.encode()).hexdigest()[:16],
            "binary_build_id": hashlib.sha256(dest.read_bytes()).hexdigest(),
            "verified_step_count": real_steps,
            "breakpoints": ["square"],
            "frames": [],
            "runner_id": os.getenv("RUNNER_NAME"),
            "started_at": timestamp(),
            "ended_at": timestamp(),
        }
        receipt = diagnostic_receipt(source, dbg, trust="LOCAL_OBSERVED")
        return receipt, {
            "status": (
                "LOCAL_PROBE_OBSERVED" if real_steps else "PROBE_FAILED_OR_RESTRICTED"
            ),
            "real_step_count": real_steps,
            "result": result,
        }
