#!/usr/bin/env python3
"""Local-only CODE PURPLE SUT GUI server. No generic command execution or GitHub writes."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import request, error
from urllib.parse import urlsplit
from uuid import uuid4

APP = Path(__file__).resolve().parent
WORKFLOWS = {
    "model-preflight": [["-m", "unittest", "discover", "-s", "tests", "-p", "test_model_readiness.py", "-q"]],
    "unit-tests": [["-m", "unittest", "discover", "-s", "tests", "-q"]],
    "ledger-verify": [["src/everred.py", "verify"]],
    "pipeline-testflight": [["src/everred.py", "verify"], ["-m", "unittest", "discover", "-s", "tests", "-q"], ["scripts/build_joined_census.py"], ["scripts/build_dashboard.py"]],
}
COPY_DIRS = ("src", "tests", "scripts", "data", "dashboard", "diagrams", "docs")
REPOS = ("GBOGEB/ABACUS", "GBOGEB/CODEX")
UA = "CODE-PURPLE-SUT-LOCAL/1.0"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def git_revision(path: Path):
    try:
        p = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=3)
        v = p.stdout.strip()
        return v if p.returncode == 0 and len(v) == 40 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise OSError("GitHub API redirect refused")


def fetch_github(path: str, token: str | None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": UA, "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = request.Request("https://api.github.com" + path, headers=headers)
    with request.build_opener(_NoRedirect()).open(req, timeout=7) as res:
        if res.status != 200:
            raise OSError("GitHub HTTP " + str(res.status))
        data = res.read(1_500_001)
        if len(data) > 1_500_000:
            raise OSError("GitHub response too large")
        return json.loads(data)


def live_snapshot(token: str | None = None):
    result = {"schema": "code-purple.live.v1", "collected_at": now_iso(), "source": "GITHUB_API_READ_ONLY", "repositories": {}, "prs": {}, "errors": []}
    for repo in REPOS:
        try:
            j = fetch_github(f"/repos/{repo}/branches/main", token)
            result["repositories"][repo] = {"sha": j["commit"]["sha"], "protected": j.get("protected"), "url": f"https://github.com/{repo}/tree/main", "source": "API"}
        except (OSError, error.URLError, ValueError, KeyError, TimeoutError) as ex:
            result["repositories"][repo] = {"sha": None, "protected": None, "source": "UNKNOWN"}
            result["errors"].append(f"{repo}: {type(ex).__name__}")
    try:
        j = fetch_github("/repos/GBOGEB/ABACUS/rulesets/24494381", token)
        result["ruleset"] = {"id": j.get("id"), "enforcement": j.get("enforcement"), "rule_count": len(j.get("rules", [])), "url": "https://github.com/GBOGEB/ABACUS/settings/rules/24494381"}
    except (OSError, error.URLError, ValueError, KeyError, TimeoutError) as ex:
        result["ruleset"] = {"rule_count": None, "enforcement": "UNKNOWN"}
        result["errors"].append(f"Ruleset: {type(ex).__name__}")
    for number in (1951, 1946):
        try:
            j = fetch_github(f"/repos/GBOGEB/ABACUS/pulls/{number}", token)
            result["prs"][str(number)] = {"state": j.get("state"), "draft": j.get("draft"), "merged": j.get("merged"), "sha": j.get("head", {}).get("sha"), "url": j.get("html_url"), "title": j.get("title")}
        except (OSError, error.URLError, ValueError, KeyError, TimeoutError) as ex:
            result["prs"][str(number)] = {"state": "UNKNOWN", "sha": None}
            result["errors"].append(f"PR #{number}: {type(ex).__name__}")
    return result


def clean_tree(source: Path, dest: Path):
    for name in COPY_DIRS:
        p = source / name
        if not p.is_dir() or p.is_symlink():
            continue
        # Executing source checkout is an explicit operator decision. Refuse symlinks.
        for item in p.rglob("*"):
            if item.is_symlink():
                raise ValueError(f"Symlink not allowed in SUT test copy: {item}")
        shutil.copytree(p, dest / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))


class RunManager:
    def __init__(self, root: Path, *, execution_enabled=False):
        self.root = root.resolve()
        self.execution_enabled = execution_enabled
        self.token = secrets.token_urlsafe(32)
        self.records = {}
        self.lock = threading.Lock()
        self.active = None

    def launch(self, profile, presented_token):
        if not self.execution_enabled:
            return (403, "Execution is disabled; restart with --enable-execution")
        if not secrets.compare_digest(str(presented_token), self.token):
            return (403, "Invalid local execution token")
        if profile not in WORKFLOWS:
            return (400, "Profile not allowlisted")
        if not (self.root / "src" / "everred.py").is_file():
            return (400, "Invalid EVERRED SUT source path")
        with self.lock:
            if self.active is not None:
                return (409, "Another SUT run is active")
            rid = uuid4().hex[:16]
            record = {"id": rid, "profile": profile, "status": "RUNNING", "started_at": now_iso(), "ended_at": None, "repository_sha": git_revision(self.root), "commands": [], "logs": [], "receipt_sha256": None, "scope": "LOCAL_ISOLATED_PREVIEW", "merge_authorized": False, "authority_transfer": False}
            self.records[rid] = record
            self.active = rid
        threading.Thread(target=self._work, args=(rid,), daemon=True).start()
        return (202, record.copy())

    def _work(self, rid):
        record = self.records[rid]
        try:
            with tempfile.TemporaryDirectory(prefix="code-purple-sut-") as tmp:
                dest = Path(tmp) / "sut"
                dest.mkdir()
                clean_tree(self.root, dest)
                for args in WORKFLOWS[record["profile"]]:
                    cmd = [sys.executable, *args]
                    item = {"command": ["python", *args], "started_at": now_iso(), "exit_code": None}
                    record["commands"].append(item)
                    env = {"PATH": os.environ.get("PATH", ""), "HOME": tmp, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1", "NO_COLOR": "1"}
                    try:
                        result = subprocess.run(cmd, cwd=dest, env=env, capture_output=True, text=True, timeout=180)
                        item["exit_code"] = result.returncode
                        record["logs"].append(("$ python " + " ".join(args) + "\n" + result.stdout + result.stderr)[-16000:])
                        no_tests = "unittest" in args and "Ran 0 tests" in (result.stdout + result.stderr)
                        if result.returncode or no_tests:
                            record["status"] = "RED"
                            if no_tests:
                                record["logs"].append("FAIL CLOSED: no tests executed")
                            break
                    except subprocess.TimeoutExpired:
                        item["exit_code"] = None
                        record["logs"].append("TIMEOUT: step exceeded 180 seconds")
                        record["status"] = "TIMEOUT"
                        break
                if record["status"] == "RUNNING":
                    record["status"] = "PASS_LOCAL_ONLY"
        except Exception as ex:
            record["status"] = "ERROR"
            record["logs"].append(f"SUT harness error: {type(ex).__name__}: {str(ex)[:500]}")
        finally:
            record["ended_at"] = now_iso()
            # Hash the receipt payload excluding its own hash.
            blob = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
            record["receipt_sha256"] = hashlib.sha256(blob).hexdigest()
            with self.lock:
                self.active = None


class Handler(BaseHTTPRequestHandler):
    manager: RunManager
    public_index = APP / "index.html"
    server_version = "CodePurpleSUT/1.0"

    def _send(self, code, body, content_type="application/json; charset=utf-8"):
        payload = json.dumps(body).encode() if not isinstance(body, bytes) else body
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ("/", "/index.html"):
            return self._send(200, self.public_index.read_bytes(), "text/html; charset=utf-8")
        if path == "/api/status":
            return self._send(200, {"schema": "code-purple.local-sut.v1", "execution_enabled": self.manager.execution_enabled, "profiles": list(WORKFLOWS), "sut_present": (self.manager.root / "src" / "everred.py").is_file(), "source_sha": git_revision(self.manager.root), "active_run": self.manager.active, "transport": "LOCALHOST_ONLY"})
        if path == "/api/live":
            return self._send(200, live_snapshot(os.environ.get("GITHUB_TOKEN")))
        if path == "/api/runs":
            return self._send(200, {"runs": list(self.manager.records.values())[-30:]})
        if path.startswith("/api/runs/"):
            rid = path[len("/api/runs/"):]
            record = self.manager.records.get(rid)
            return self._send(200, record) if record else self._send(404, {"error": "Unknown run"})
        self._send(404, {"error": "Unknown route"})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/run":
            return self._send(404, {"error": "Unknown route"})
        origin = self.headers.get("Origin")
        expected = f"http://127.0.0.1:{self.server.server_port}"
        if origin != expected:
            return self._send(403, {"error": "Same-origin browser request required"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self._send(415, {"error": "Expected JSON"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if not 0 < n <= 1024:
                raise ValueError("request size")
            data = json.loads(self.rfile.read(n))
            if not isinstance(data, dict) or set(data) != {"profile"}:
                raise ValueError("invalid payload")
            code, record = self.manager.launch(data["profile"], self.headers.get("X-SUT-Token", ""))
            return self._send(code, {"result": record} if code == 202 else {"error": record})
        except (ValueError, TypeError, json.JSONDecodeError):
            return self._send(400, {"error": "Invalid request"})

    def log_message(self, format, *args):
        print("[sut-gui]", format % args, file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="CODE PURPLE localhost SUT GUI")
    parser.add_argument("--sut-root", type=Path, default=APP.parent)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--enable-execution", action="store_true", help="Explicitly allow local trusted-source SUT test profiles")
    args = parser.parse_args()
    manager = RunManager(args.sut_root, execution_enabled=args.enable_execution)
    cls = type("SUTHandler", (Handler,), {"manager": manager})
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), cls)
    print(f"CODE PURPLE: http://127.0.0.1:{httpd.server_port}/", flush=True)
    print("SUT root:", manager.root, "| execution:", manager.execution_enabled, flush=True)
    if manager.execution_enabled:
        print("Execution token (enter in GUI; do not share):", manager.token, flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
