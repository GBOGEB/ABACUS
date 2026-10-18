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
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))
from operator_workbench import OperatorWorkbench

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


def _native_ci(token, sha):
    """Conservative exact-head GitHub Actions census (one page, fail closed)."""
    result = {
        "schema": "code-purple.native-ci.v2", "source_sha": sha, "repository": "GBOGEB/ABACUS",
        "status": "UNKNOWN", "total_count": None, "sample_complete": False,
        "runs": [], "first_reds": [], "first_red_completeness": "UNKNOWN",
        "metrics": {"total_observed": None, "terminal": None, "success": None,
                    "failure": None, "queued": None, "in_progress": None,
                    "cancelled_or_other": None},
    }
    if not isinstance(sha, str) or len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha):
        return result
    data = fetch_github(f"/repos/GBOGEB/ABACUS/actions/runs?head_sha={sha}&per_page=100", token)
    total, rows = data.get("total_count"), data.get("workflow_runs")
    if type(total) is not int or not isinstance(rows, list):
        raise ValueError("Native workflow collection lacks denominator")
    if any(not isinstance(row, dict) or row.get("head_sha") != sha for row in rows):
        raise ValueError("Workflow census mixes source SHA identities")
    result["status"] = "OBSERVED"
    result["total_count"] = total
    result["sample_complete"] = len(rows) == total and total <= 100
    for row in rows:
        result["runs"].append({
            "id": row.get("id"), "name": row.get("name"), "status": row.get("status"),
            "conclusion": row.get("conclusion"), "head_sha": row.get("head_sha"),
            "created_at": row.get("created_at"), "updated_at": row.get("updated_at"),
            "url": row.get("html_url"), "event": row.get("event"),
        })
    terminal = [row for row in result["runs"] if row["status"] == "completed"]
    result["metrics"] = {
        "total_observed": len(result["runs"]), "terminal": len(terminal),
        "success": sum(row["conclusion"] == "success" for row in terminal),
        "failure": sum(row["conclusion"] in ("failure", "timed_out", "action_required") for row in terminal),
        "queued": sum(row["status"] in ("queued", "pending", "waiting", "requested") for row in result["runs"]),
        "in_progress": sum(row["status"] == "in_progress" for row in result["runs"]),
        "cancelled_or_other": sum(row["conclusion"] not in ("success", "failure", "timed_out", "action_required") for row in terminal),
    }
    failed = [row for row in terminal if row["conclusion"] in ("failure", "timed_out", "action_required")]
    inspected = 0
    for row in failed[:4]:
        try:
            detail = fetch_github(f"/repos/GBOGEB/ABACUS/actions/runs/{row['id']}/jobs?per_page=100", token)
            jobs = detail.get("jobs")
            if not isinstance(jobs, list) or type(detail.get("total_count")) is not int:
                raise ValueError("Job census denominator unavailable")
            if len(jobs) != detail["total_count"]:
                raise ValueError("Job census incomplete")
            inspected += 1
            for job in jobs:
                if job.get("conclusion") not in ("failure", "timed_out", "action_required"):
                    continue
                steps = job.get("steps") or []
                first = next((step for step in steps if step.get("conclusion") in ("failure", "timed_out", "action_required")), None)
                result["first_reds"].append({
                    "workflow": row["name"], "run_id": row["id"],
                    "job_id": job.get("id"), "job": job.get("name"),
                    "step": first.get("name") if first else None,
                    "step_number": first.get("number") if first else None,
                    "sha": sha, "url": job.get("html_url") or row["url"],
                    "classification": "UNCLASSIFIED", "root_id": None,
                    "evidence": "NATIVE_JOB_STEP_METADATA",
                })
        except (OSError, error.URLError, ValueError, KeyError, TypeError, TimeoutError):
            result["first_reds"].append({
                "workflow": row["name"], "run_id": row["id"], "job_id": None,
                "job": None, "step": None, "sha": sha, "url": row["url"],
                "classification": "UNKNOWN", "root_id": None,
                "evidence": "JOB_READBACK_UNAVAILABLE",
            })
    result["first_red_completeness"] = (
        "COMPLETE" if result["sample_complete"] and inspected == len(failed) else "PARTIAL"
    )
    return result


def live_snapshot(token: str | None = None):
    """Read-only GitHub evidence. No local/remote run is inferred successful."""
    result = {"schema": "code-purple.live.v2", "collected_at": now_iso(),
              "source": "GITHUB_API_READ_ONLY", "poll_policy": "AUTHENTICATED_90S" if token else "PUBLIC_900S", "repositories": {}, "prs": {},
              "errors": [], "ci": None, "independent_review": "UNKNOWN"}
    for repo in REPOS:
        try:
            j = fetch_github(f"/repos/{repo}/branches/main", token)
            result["repositories"][repo] = {
                "sha": j["commit"]["sha"], "protected": j.get("protected"),
                "url": f"https://github.com/{repo}/tree/main", "source": "API"}
        except (OSError, error.URLError, ValueError, KeyError, TimeoutError) as ex:
            result["repositories"][repo] = {"sha": None, "protected": None, "source": "UNKNOWN"}
            result["errors"].append(f"{repo}: {type(ex).__name__}")
    try:
        j = fetch_github("/repos/GBOGEB/ABACUS/rulesets/24494381", token)
        rules = j.get("rules")
        result["ruleset"] = {"id": j.get("id"), "enforcement": j.get("enforcement"),
                             "rule_count": len(rules) if isinstance(rules, list) else None,
                             "url": "https://github.com/GBOGEB/ABACUS/settings/rules/24494381"}
    except (OSError, error.URLError, ValueError, KeyError, TimeoutError) as ex:
        result["ruleset"] = {"rule_count": None, "enforcement": "UNKNOWN"}
        result["errors"].append(f"Ruleset: {type(ex).__name__}")
    for number in (1956, 1951):
        try:
            j = fetch_github(f"/repos/GBOGEB/ABACUS/pulls/{number}", token)
            result["prs"][str(number)] = {
                "state": j.get("state"), "draft": j.get("draft"),
                "merged": j.get("merged"), "sha": j.get("head", {}).get("sha"),
                "url": j.get("html_url"), "title": j.get("title"),
                "author": (j.get("user") or {}).get("login")}
        except (OSError, error.URLError, ValueError, KeyError, TimeoutError) as ex:
            result["prs"][str(number)] = {"state": "UNKNOWN", "sha": None}
            result["errors"].append(f"PR #{number}: {type(ex).__name__}")
    primary = result["prs"].get("1956", {})
    try:
        result["ci"] = _native_ci(token, primary.get("sha"))
    except (OSError, error.URLError, ValueError, KeyError, TimeoutError) as ex:
        result["errors"].append(f"Native CI: {type(ex).__name__}")
        result["ci"] = {"status": "UNKNOWN", "source_sha": primary.get("sha"),
                        "runs": [], "metrics": None, "first_reds": [],
                        "total_count": None, "sample_complete": False,
                        "first_red_completeness": "UNKNOWN"}
    try:
        reviews = fetch_github("/repos/GBOGEB/ABACUS/pulls/1956/reviews?per_page=100", token)
        if not isinstance(reviews, list):
            raise ValueError("Reviews not a list")
        exact = [x for x in reviews if x.get("state") == "APPROVED"
                 and x.get("commit_id") == primary.get("sha")
                 and (x.get("user") or {}).get("login") != primary.get("author")]
        # Review existence is not eligibility or a policy acceptance.
        result["independent_review"] = "OBSERVED_NOT_ELIGIBILITY" if exact else "NOT_OBSERVED"
    except (OSError, error.URLError, ValueError, KeyError, TimeoutError):
        result["independent_review"] = "UNKNOWN"
        result["errors"].append("Reviews: readback unavailable")
    result["collection"] = "COMPLETE" if not result["errors"] and result["ci"]["sample_complete"] and result["ci"]["first_red_completeness"] == "COMPLETE" else "PARTIAL"
    result["merge_authorized"] = False
    result["authority_transfer"] = False
    result["security_waiver"] = False
    return result


LIVE_CACHE = {"time": 0.0, "result": None}
LIVE_CACHE_LOCK = threading.Lock()


def cached_live_snapshot(token: str | None = None):
    # Conservatively cache read-only GETs for 60 seconds. The original
    # collected_at remains unchanged, preventing a false freshness reset.
    with LIVE_CACHE_LOCK:
        if LIVE_CACHE["result"] is not None and time.monotonic() - LIVE_CACHE["time"] < (60 if token else 600):
            return LIVE_CACHE["result"]
        result = live_snapshot(token)
        LIVE_CACHE["time"] = time.monotonic()
        LIVE_CACHE["result"] = result
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
    operator = None
    public_index = APP / "index.html"
    operator_page = APP / "operator.html"
    server_version = "CodePurpleSUT/2.1"

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
        if path.startswith("/api/operator") or path == "/operator":
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
                return self._send(403, {"error": "Loopback Host required"})
            if path == "/operator":
                return self._send(200, self.operator_page.read_bytes(), "text/html; charset=utf-8")
            if self.operator is None:
                return self._send(503, {"error": "Operator root not configured"})
            if path == "/api/operator/catalog":
                return self._send(200, self.operator.catalog())
            if path == "/api/operator/runs":
                return self._send(200, {"runs": self.operator.list_runs()})
            if path.startswith("/api/operator/runs/"):
                rid = path.rsplit("/", 1)[-1]
                row = self.operator.get_run(rid)
                return self._send(200, row) if row is not None else self._send(404, {"error": "Unknown operator run"})
            return self._send(404, {"error": "Unknown operator route"})
        if path in ("/", "/index.html"):
            return self._send(200, self.public_index.read_bytes(), "text/html; charset=utf-8")
        if path == "/api/status":
            return self._send(200, {"schema": "code-purple.local-sut.v1", "execution_enabled": self.manager.execution_enabled, "profiles": list(WORKFLOWS), "sut_present": (self.manager.root / "src" / "everred.py").is_file(), "source_sha": git_revision(self.manager.root), "active_run": self.manager.active, "transport": "LOCALHOST_ONLY"})
        if path == "/api/live":
            return self._send(200, cached_live_snapshot(os.environ.get("GITHUB_TOKEN")))
        if path == "/api/runs":
            return self._send(200, {"runs": list(self.manager.records.values())[-30:]})
        if path.startswith("/api/runs/"):
            rid = path[len("/api/runs/"):]
            record = self.manager.records.get(rid)
            return self._send(200, record) if record else self._send(404, {"error": "Unknown run"})
        self._send(404, {"error": "Unknown route"})

    def do_POST(self):
        route = urlsplit(self.path).path
        if route not in {"/api/run", "/api/operator/plan",
                         "/api/operator/run", "/api/operator/cancel"}:
            return self._send(404, {"error": "Unknown route"})
        expected = f"http://127.0.0.1:{self.server.server_port}"
        if route.startswith("/api/operator") and self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
            return self._send(403, {"error": "Loopback Host required"})
        if self.headers.get("Origin") != expected:
            return self._send(403, {"error": "Same-origin browser request required"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self._send(415, {"error": "Expected JSON"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if not 0 < n <= (1024 if route == "/api/run" else 2048):
                raise ValueError("request size")
            data = json.loads(self.rfile.read(n))
            if not isinstance(data, dict):
                raise ValueError("invalid payload")
            if route == "/api/run":
                if set(data) != {"profile"}:
                    raise ValueError("invalid SUT payload")
                code, record = self.manager.launch(data["profile"], self.headers.get("X-SUT-Token", ""))
            else:
                if self.operator is None:
                    return self._send(503, {"error": "Operator root not configured"})
                if route == "/api/operator/plan":
                    if set(data) not in ({"profile"}, {"profile", "input_name"}):
                        raise ValueError("invalid plan payload")
                    try:
                        record = self.operator.plan(data["profile"], data.get("input_name"))
                        return self._send(200, {"result": record})
                    except (ValueError, OSError) as exc:
                        return self._send(400, {"error": str(exc)})
                if route == "/api/operator/cancel":
                    if set(data) != {"id"}:
                        raise ValueError("invalid cancel payload")
                    code, record = self.operator.cancel(data["id"], self.headers.get("X-SUT-Token", ""))
                else:
                    if set(data) != {"profile", "input_name", "source_sha", "input_sha256", "consent", "after_seconds"}:
                        raise ValueError("invalid execute payload")
                    code, record = self.operator.submit(
                        data["profile"], data["input_name"], data["source_sha"],
                        data["input_sha256"], data["consent"], data["after_seconds"],
                        self.headers.get("X-SUT-Token", ""),
                    )
            return self._send(code, {"result": record} if code in (200, 202) else {"error": record})
        except (ValueError, TypeError, json.JSONDecodeError):
            return self._send(400, {"error": "Invalid request"})

    def log_message(self, format, *args):
        print("[sut-gui]", format % args, file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="CODE PURPLE localhost SUT GUI")
    parser.add_argument("--sut-root", type=Path, default=APP.parent)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--enable-execution", action="store_true", help="Explicitly allow local trusted-source SUT test profiles")
    parser.add_argument("--abacus-root", type=Path, help="Trusted local ABACUS Git checkout for operator profiles")
    parser.add_argument("--operator-inbox", type=Path, help="Original files for derived binary analysis")
    parser.add_argument("--operator-receipts", type=Path, help="Append-only local operator receipts")
    parser.add_argument("--enable-operator", action="store_true", help="Explicitly allow bounded local operator tasks")
    args = parser.parse_args()
    if args.enable_operator and args.abacus_root is None:
        parser.error("--enable-operator requires --abacus-root")
    manager = RunManager(args.sut_root, execution_enabled=args.enable_execution)
    operator = None
    if args.abacus_root is not None:
        operator = OperatorWorkbench(
            args.abacus_root,
            args.operator_inbox or (Path.cwd() / "operator-inbox"),
            args.operator_receipts or (Path.cwd() / "operator-receipts"),
            enabled=args.enable_operator, token=manager.token,
        )
    cls = type("SUTHandler", (Handler,), {"manager": manager, "operator": operator})
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), cls)
    print(f"CODE PURPLE: http://127.0.0.1:{httpd.server_port}/", flush=True)
    print("SUT root:", manager.root, "| execution:", manager.execution_enabled, flush=True)
    if manager.execution_enabled or (operator is not None and operator.enabled):
        print("Execution token (enter in GUI; do not share):", manager.token, flush=True)
    if operator is not None:
        print("Operator: http://127.0.0.1:%d/operator" % httpd.server_port,
              "| enabled:", operator.enabled, flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
