"""Local CODE PURPLE operator workbench: bounded commands, fresh clones and receipts.

No remote dispatch, arbitrary shell, credential use, source deletion, merge rights
or agent authority. This is explicitly NOT a container/OS sandbox; execute only
trusted local code after operator opt-in. Schedules live only while server runs.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SAFE_NAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_. -]{0,127}\Z")
BINARY_TYPES = frozenset({".pdf", ".docx", ".xlsx", ".pptx", ".html", ".htm"})
MAX_INPUT = 20 * 1024 * 1024
MAX_DELAY = 3600

# The name, scope and argv are controlled by code, never by browser input.
PROFILES = {
    "python-tests": ("Python", "Mission Control Lite unit tests", False),
    "pipeline-3p": ("Pipeline", "One bounded 3P pipeline in fresh clone", False),
    "binary-bridge": ("Binary bridge", "Read one inbox binary, retain original", True),
    "debug-compile": ("Debug", "Compile governed Python modules", False),
    "runner-tests": (
        "Runners",
        "Runner-wait and native identity contract tests",
        False,
    ),
    "task-census": ("Tasks", "Local Mission Control receipt census", False),
    "mcp-readiness": ("MCP", "Remote MCP invocation not authorized", False),
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def file_hash(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head(root: Path):
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and SHA40.fullmatch(value) else None


def _environment(tmp: str):
    # Do not pass GitHub/MCP/cloud credentials through to the child by default.
    allowed = ("PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "LANG")
    env = {k: os.environ[k] for k in allowed if k in os.environ}
    env.update(
        {
            "HOME": tmp,
            "TMP": tmp,
            "TEMP": tmp,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_LFS_SKIP_SMUDGE": "1",
            "NO_COLOR": "1",
        }
    )
    return env


class OperatorWorkbench:
    """Process-local, capacity-one task controller with append-only receipts."""

    def __init__(
        self,
        root: Path,
        inbox: Path,
        receipt_dir: Path,
        *,
        enabled=False,
        token=None,
        timeout_seconds=120,
    ):
        self.root = Path(root).resolve()
        self.inbox = Path(inbox).resolve()
        self.receipt_dir = Path(receipt_dir).resolve()
        self.enabled = bool(enabled)
        self.token = token if token is not None else secrets.token_urlsafe(32)
        self.timeout_seconds = timeout_seconds
        self.records = {}
        self.timers = {}
        self.active = None
        self.lock = threading.RLock()

    def available_inputs(self):
        if not self.inbox.is_dir():
            return []
        result = []
        for path in sorted(self.inbox.iterdir(), key=lambda item: item.name):
            if (
                not SAFE_NAME.fullmatch(path.name)
                or path.is_symlink()
                or not path.is_file()
                or path.suffix.lower() not in BINARY_TYPES
            ):
                continue
            size = path.stat().st_size
            if not 0 < size <= MAX_INPUT:
                continue
            result.append({"name": path.name, "bytes": size})
        return result[:100]

    def _input(self, name):
        if type(name) is not str or not SAFE_NAME.fullmatch(name):
            raise ValueError("Invalid local input identifier")
        candidate = self.inbox / name
        if candidate.is_symlink() or not candidate.is_file():
            raise ValueError("Input absent or symlink")
        if candidate.suffix.lower() not in BINARY_TYPES:
            raise ValueError("Unsupported binary input type")
        if not candidate.resolve().is_relative_to(self.inbox):
            raise ValueError("Input path escapes inbox")
        size = candidate.stat().st_size
        if not 0 < size <= MAX_INPUT:
            raise ValueError("Input is empty or exceeds 20 MiB")
        with candidate.open("rb") as stream:
            prefix = stream.read(8)
        if candidate.suffix.lower() in {
            ".docx",
            ".xlsx",
            ".pptx",
        } and not prefix.startswith(b"PK\x03\x04"):
            raise ValueError("Invalid OOXML ZIP signature")
        if candidate.suffix.lower() == ".pdf" and not prefix.startswith(b"%PDF-"):
            raise ValueError("Invalid PDF signature")
        return candidate

    def _steps(self, profile, filename, source_sha):
        out = "operator-output"
        commands = {
            "python-tests": [
                [
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "tests",
                    "-p",
                    "test_mission_control_lite.py",
                    "-q",
                ]
            ],
            "pipeline-3p": [
                [
                    "tools/generic_3p_pipeline.py",
                    "--root",
                    ".",
                    "--out-dir",
                    out + "/3p",
                    "--history",
                    out + "/3p/history.jsonl",
                    "--repeat",
                    "1",
                    "--source-sha",
                    source_sha,
                ]
            ],
            "debug-compile": [
                [
                    "-m",
                    "compileall",
                    "-q",
                    "mission_control_lite",
                    "tools/qps_binary_bridge.py",
                ]
            ],
            "runner-tests": [
                [
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "tests",
                    "-p",
                    "test_runner_wait.py",
                    "-q",
                ]
            ],
            "task-census": [
                [
                    "-m",
                    "mission_control_lite.cli",
                    "census",
                    "--db",
                    out + "/mcl.sqlite",
                ]
            ],
        }
        if profile == "binary-bridge":
            # Never construct an input-dependent command for unrelated profiles:
            # eager string concatenation with filename=None previously broke
            # every Python/test/runner GUI plan (W45 native first-red).
            if not isinstance(filename, str) or not filename:
                raise ValueError("Binary bridge requires a verified local input")
            return [
                [
                    "tools/qps_binary_bridge.py",
                    "operator-input/" + filename,
                    "--output",
                    out + "/bridge.json",
                    "--authority",
                    "LOCAL_USER_INPUT",
                    "--lifecycle-status",
                    "CANDIDATE",
                ]
            ]
        return commands[profile]

    def plan(self, profile, input_name=None):
        if profile not in PROFILES:
            raise ValueError("Unknown or unapproved task profile")
        if profile == "mcp-readiness":
            return {
                "schema": "codepurple.operator.plan.v1",
                "profile": profile,
                "executable": False,
                "status": "BLOCKED_AUTHENTICATED_MCP_ADAPTER",
                "message": "MCP remote tools need an external authenticated dispatcher; no token or write scope is delegated.",
            }
        if not (self.root / ".git").exists():
            raise ValueError("Trusted ABACUS git checkout not configured")
        source_sha = _git_head(self.root)
        if not source_sha:
            raise ValueError("Cannot resolve exact trusted checkout HEAD")
        binary = PROFILES[profile][2]
        if binary:
            selected = self._input(input_name)
            identity = {
                "name": selected.name,
                "bytes": selected.stat().st_size,
                "sha256": file_hash(selected),
            }
            filename = selected.name
        else:
            if input_name not in (None, ""):
                raise ValueError("Input only supported by binary-bridge")
            identity, filename = None, None
        steps = self._steps(profile, filename, source_sha)
        return {
            "schema": "codepurple.operator.plan.v1",
            "profile": profile,
            "category": PROFILES[profile][0],
            "source_sha": source_sha,
            "input": identity,
            "argv": [["python", *step] for step in steps],
            "executable": True,
            "status": "DRY_RUN_ONLY",
            "fresh_clone": True,
            "originals_disposition": "KEEP_AWAIT_USER_APPROVAL",
            "requires_consent": True,
            "merge_admission": "HOLD",
            "security_waiver": False,
            "authenticated_mcp_dispatch": False,
        }

    def catalog(self):
        return {
            "schema": "codepurple.operator.catalog.v1",
            "execution_enabled": self.enabled,
            "source_sha": _git_head(self.root),
            "source_root_configured": (self.root / ".git").exists(),
            "profiles": [
                {
                    "id": key,
                    "category": val[0],
                    "description": val[1],
                    "input_required": val[2],
                    "executable": key != "mcp-readiness",
                }
                for key, val in PROFILES.items()
            ],
            "inputs": self.available_inputs(),
            "active": self.active,
            "schedule": {
                "max_delay_seconds": MAX_DELAY,
                "persistent_after_restart": False,
            },
            "merge_admission": "HOLD",
            "security_waiver": False,
        }

    def _public(self, record):
        return json.loads(json.dumps(record, sort_keys=True))

    def list_runs(self):
        with self.lock:
            rows = list(self.records.values())[-100:]
            return [self._public(row) for row in reversed(rows)]

    def get_run(self, rid):
        with self.lock:
            row = self.records.get(rid)
            return self._public(row) if row is not None else None

    def artifact(self, rid, index):
        """Read back only a run-declared, hash-verified generated artifact."""
        row = self.get_run(rid)
        if (
            row is None
            or type(index) is not int
            or not 0 <= index < len(row["artifacts"])
        ):
            return None
        info = row["artifacts"][index]
        root = (self.receipt_dir / rid).resolve()
        path = (root / info["path"]).resolve()
        if (
            not path.is_relative_to(root)
            or path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != info["bytes"]
            or path.stat().st_size > 8 * 1024 * 1024
            or file_hash(path) != info["sha256"]
        ):
            return None
        return path.name, path.read_bytes()

    def submit(
        self,
        profile,
        input_name,
        source_sha,
        input_sha256,
        consent,
        delay_seconds,
        token,
    ):
        if not self.enabled:
            return 403, "Explicit --enable-operator is required"
        if not secrets.compare_digest(str(token), self.token):
            return 403, "Invalid per-process execution token"
        if consent is not True:
            return 403, "Explicit user consent required"
        if type(delay_seconds) is not int or not 0 <= delay_seconds <= MAX_DELAY:
            return 400, "Invalid bounded schedule delay"
        try:
            plan = self.plan(profile, input_name)
        except (TypeError, ValueError, OSError) as exc:
            return 400, str(exc)
        if plan.get("executable") is not True:
            return 403, "MCP not configured for authorized execution"
        if type(source_sha) is not str or source_sha != plan["source_sha"]:
            return 409, "Source SHA moved or was not explicitly selected"
        expected_input_hash = (plan["input"] or {}).get("sha256")
        if input_sha256 != expected_input_hash:
            return 409, "Binary input hash changed since dry-run approval"
        with self.lock:
            if self.active is not None or any(
                x["status"] == "SCHEDULED" for x in self.records.values()
            ):
                return 409, "One active or scheduled task allowed"
            rid = uuid4().hex[:16]
            record = {
                "id": rid,
                "profile": profile,
                "status": "SCHEDULED" if delay_seconds else "STARTING",
                "source_sha": source_sha,
                "input": plan["input"],
                "argv": plan["argv"],
                "started_at": None,
                "created_at": utc_now(),
                "finished_at": None,
                "delay_seconds": delay_seconds,
                "steps": [],
                "artifacts": [],
                "receipt_sha256": None,
                "merge_admission": "HOLD",
                "security_waiver": False,
                "originals_modified": False,
                "originals_disposition": "KEEP_AWAIT_USER_APPROVAL",
                "authority_transfer": False,
                "execution_scope": "LOCAL_TRUSTED_SOURCE_NOT_SANDBOXED",
            }
            self.records[rid] = record
            if delay_seconds:
                timer = threading.Timer(delay_seconds, self._work, args=(rid,))
                timer.daemon = True
                self.timers[rid] = timer
                timer.start()
            else:
                self.active = rid
                threading.Thread(target=self._work, args=(rid,), daemon=True).start()
            return 202, self._public(record)

    def cancel(self, rid, token):
        if not secrets.compare_digest(str(token), self.token):
            return 403, "Invalid token"
        with self.lock:
            row = self.records.get(rid)
            if row is None:
                return 404, "Unknown local task"
            if row["status"] != "SCHEDULED":
                return 409, "Only scheduled, unstarted tasks may be cancelled"
            timer = self.timers.pop(rid, None)
            if timer:
                timer.cancel()
            row["status"] = "CANCELLED"
            row["finished_at"] = utc_now()
            self._finalize(row)
            return 200, self._public(row)

    def _finalize(self, row):
        payload = json.dumps(
            {key: value for key, value in row.items() if key != "receipt_sha256"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        digest = hashlib.sha256(payload).hexdigest()
        folder = self.receipt_dir / row["id"]
        folder.mkdir(parents=True, exist_ok=True)
        # Publish the receipt identity only once the append-only file is complete.
        with (folder / "receipt.json").open("x", encoding="utf-8") as stream:
            stream.write(
                json.dumps({**row, "receipt_sha256": digest}, indent=2, sort_keys=True)
                + "\n"
            )
        row["receipt_sha256"] = digest

    def _work(self, rid):
        with self.lock:
            row = self.records[rid]
            self.timers.pop(rid, None)
            if row["status"] == "CANCELLED":
                return
            if self.active is not None and self.active != rid:
                row["status"] = "CAPACITY_HOLD"
                row["finished_at"] = utc_now()
                self._finalize(row)
                return
            self.active = rid
            row["status"] = "RUNNING"
            row["started_at"] = utc_now()
        try:
            if _git_head(self.root) != row["source_sha"]:
                raise ValueError("STALE_SOURCE: checkout HEAD changed since approval")
            with tempfile.TemporaryDirectory(prefix="code-purple-operator-") as tmp:
                clone = Path(tmp) / "repo"
                env = _environment(tmp)
                for cmd in (
                    [
                        "git",
                        "-c",
                        "core.hooksPath=" + os.devnull,
                        "clone",
                        "--quiet",
                        "--no-hardlinks",
                        "--no-checkout",
                        "--",
                        str(self.root),
                        str(clone),
                    ],
                    [
                        "git",
                        "-C",
                        str(clone),
                        "-c",
                        "core.hooksPath=" + os.devnull,
                        "checkout",
                        "--quiet",
                        "--detach",
                        row["source_sha"],
                    ],
                ):
                    result = subprocess.run(
                        cmd, env=env, text=True, capture_output=True, timeout=60
                    )
                    if result.returncode:
                        raise RuntimeError(
                            "Fresh git clone/checkout failed: " + result.stderr[-350:]
                        )
                if _git_head(clone) != row["source_sha"]:
                    raise ValueError("Fresh-clone checkout identity mismatch")
                work_out = clone / "operator-output"
                if work_out.is_symlink() or not work_out.resolve().is_relative_to(
                    clone.resolve()
                ):
                    raise ValueError("Output location escapes fresh clone")
                work_out.mkdir(exist_ok=True)
                if row["input"] is not None:
                    original = self._input(row["input"]["name"])
                    if (
                        file_hash(original) != row["input"]["sha256"]
                        or original.stat().st_size != row["input"]["bytes"]
                    ):
                        raise ValueError("Input changed after approval")
                    input_dir = clone / "operator-input"
                    if input_dir.is_symlink() or not input_dir.resolve().is_relative_to(
                        clone.resolve()
                    ):
                        raise ValueError("Input staging location escapes fresh clone")
                    input_dir.mkdir(exist_ok=True)
                    shutil.copyfile(original, input_dir / original.name)
                for step in row["argv"]:
                    args = [sys.executable, *step[1:]]
                    try:
                        # Spool output to files to cap process memory use.
                        with (
                            tempfile.TemporaryFile() as stdout_file,
                            tempfile.TemporaryFile() as stderr_file,
                        ):
                            out = subprocess.run(
                                args,
                                cwd=clone,
                                env=env,
                                stdout=stdout_file,
                                stderr=stderr_file,
                                timeout=self.timeout_seconds,
                            )
                            stdout_file.seek(max(0, stdout_file.tell() - 8000))
                            stderr_file.seek(max(0, stderr_file.tell() - 8000))
                            stdout_text = stdout_file.read().decode(
                                "utf-8", errors="replace"
                            )
                            stderr_text = stderr_file.read().decode(
                                "utf-8", errors="replace"
                            )
                        command = {
                            "argv": step,
                            "returncode": out.returncode,
                            "stdout": stdout_text,
                            "stderr": stderr_text,
                        }
                        row["steps"].append(command)
                        if out.returncode or "Ran 0 tests" in (
                            stdout_text + stderr_text
                        ):
                            row["status"] = "RED"
                            break
                    except subprocess.TimeoutExpired:
                        row["steps"].append(
                            {
                                "argv": step,
                                "returncode": None,
                                "stderr": "Timed out",
                                "stdout": "",
                            }
                        )
                        row["status"] = "TIMEOUT"
                        break
                output_files = [p for p in work_out.rglob("*") if p.is_file()]
                if len(output_files) > 64:
                    raise ValueError("Too many output artifacts")
                # Copy outputs only, never alter/delete the source or inbox file.
                for path in output_files:
                    if (
                        path.is_symlink()
                        or not path.resolve().is_relative_to(work_out.resolve())
                        or path.stat().st_size > 8 * 1024 * 1024
                    ):
                        raise ValueError("Unsafe or oversized generated output")
                    relative = path.relative_to(work_out)
                    stored = self.receipt_dir / rid / "artifacts" / relative
                    stored.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, stored)
                    row["artifacts"].append(
                        {
                            "path": "artifacts/" + relative.as_posix(),
                            "bytes": stored.stat().st_size,
                            "sha256": file_hash(stored),
                        }
                    )
                if row["status"] == "RUNNING":
                    row["status"] = "PASS_LOCAL_ONLY"
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            row["status"] = "STALE_SOURCE" if "STALE_SOURCE:" in str(exc) else "ERROR"
            row["steps"].append(
                {"argv": [], "returncode": None, "stdout": "", "stderr": str(exc)[:500]}
            )
        finally:
            with self.lock:
                row["finished_at"] = utc_now()
                try:
                    self._finalize(row)
                except OSError:
                    row["status"] = "RECEIPT_WRITE_FAILED"
                self.active = None
