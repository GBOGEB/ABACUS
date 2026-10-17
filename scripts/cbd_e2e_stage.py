"""CBD TestPilot end-to-end stage receipts and isolated local clone replay.

Independent of repository-wide security/merge admission. A runner replay cannot
prove that a developer's earlier local Git hook actually executed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

SHA = re.compile(r"[a-f0-9]{40}")
TEST_SUMMARY = re.compile(r"(?<!\d)(\d+)\s+passed\b")
OWNED = ("scripts/cbd_e2e_stage.py", "tests/test_cbd_e2e_stage.py")
PARENT_TESTS = (
    "tests/test_cbd_native_job_projection.py",
    "tests/test_cbd_workflow_failure_waves.py",
)
STAGES = ("pre-commit", "pre-push", "checkout", "replay", "compare")
MAX_SECONDS = 240


def now_utc():
    """Return an offset-aware wall clock; durations use monotonic separately."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def command(args, cwd, *, timeout=MAX_SECONDS):
    """Record exit/duration/digests; never publish raw output or secrets."""
    start = time.monotonic_ns()
    try:
        done = subprocess.run(
            list(args), cwd=str(cwd), capture_output=True, timeout=timeout,
            check=False,
        )
        rc, stdout, stderr = done.returncode, done.stdout, done.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        rc = None
        stdout, stderr = exc.stdout or b"", exc.stderr or b""
        timed_out = True
    except OSError as exc:
        rc, stdout, stderr, timed_out = None, b"", repr(type(exc)).encode(), False
    return {
        "argv": [str(x) for x in args],
        "returncode": rc,
        "timed_out": timed_out,
        "duration_ms": round((time.monotonic_ns() - start) / 1_000_000, 2),
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_sha256": sha256_bytes(stderr),
        "output": (stdout + b"\n" + stderr).decode("utf-8", "replace"),
        "status": "PASS" if rc == 0 and not timed_out else "FAIL",
    }


def git_value(repo, *args):
    try:
        result = subprocess.run(
            ["git", *args], cwd=str(repo), capture_output=True,
            text=True, check=False, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def fingerprint(repo):
    """Bind HEAD, tree, staged/worktree diffs, not a guessed source SHA."""
    sha = git_value(repo, "rev-parse", "HEAD")
    tree = git_value(repo, "rev-parse", "HEAD^{tree}")
    staged = git_value(repo, "diff", "--cached", "--binary", "--no-ext-diff")
    unstaged = git_value(repo, "diff", "--binary", "--no-ext-diff")
    return {
        "head_sha": sha if sha and SHA.fullmatch(sha) else None,
        "head_tree_sha": tree if tree and SHA.fullmatch(tree) else None,
        "staged_diff_sha256": sha256_bytes(staged.encode()) if staged is not None else None,
        "unstaged_diff_sha256": sha256_bytes(unstaged.encode()) if unstaged is not None else None,
        "tracked_changes_present": (
            bool(staged or unstaged) if staged is not None and unstaged is not None else None
        ),
    }


def project_check(result, name):
    """Retain only safe command fingerprints and verified test denominators."""
    output = result.pop("output")
    result["name"] = name
    if name == "pytest":
        parsed = TEST_SUMMARY.search(output)
        result["tests_passed"] = int(parsed.group(1)) if parsed else None
        if result["status"] == "PASS" and result["tests_passed"] is None:
            result["status"] = "UNKNOWN"
    return result


def tools_for_stage(repo, stage):
    py = [name for name in OWNED if (repo / name).is_file()]
    tests = [name for name in OWNED + PARENT_TESTS
             if name.startswith("tests/") and (repo / name).is_file()]
    owned_tests = [name for name in OWNED if name.startswith("tests/") and
                   (repo / name).is_file()]
    if len(py) != len(OWNED) or not owned_tests:
        return None
    suite = owned_tests if stage == "pre-commit" else tests
    checks = [
        ("compile", [sys.executable, "-m", "compileall", "-q", *py]),
        ("black", [sys.executable, "-m", "black", "--check", *py]),
        ("isort", [sys.executable, "-m", "isort", "--check-only", *py]),
        ("pytest", [sys.executable, "-m", "pytest", "-q", *suite, "--disable-warnings"]),
    ]
    return checks


def run_stage(repo, stage, expected_sha=None):
    """Execute real subprocess checks; no SKIP is treated as success."""
    started = now_utc()
    clock = time.monotonic_ns()
    source = fingerprint(repo)
    checks = []
    required = tools_for_stage(repo, stage)
    if required:
        for name, argv in required:
            checks.append(project_check(command(argv, repo), name))
    has_tests = any(
        c["name"] == "pytest" and type(c.get("tests_passed")) is int
        and c["tests_passed"] > 0 for c in checks
    )
    exact = (
        expected_sha is None
        or (isinstance(expected_sha, str)
            and SHA.fullmatch(expected_sha) is not None
            and source["head_sha"] == expected_sha)
    )
    clean = stage not in ("checkout", "pre-push") or source["tracked_changes_present"] is False
    passed = (
        required is not None and len(checks) == len(required)
        and all(c["status"] == "PASS" for c in checks)
        and has_tests and exact and clean and source["head_sha"] is not None
    )
    return {
        "schema": "abacus.cbd.e2e.stage.v1",
        "stage": stage,
        "repo": "GBOGEB/ABACUS",
        "source": source,
        "expected_sha": expected_sha,
        "clock": {
            "started_utc": started,
            "ended_utc": now_utc(),
            "elapsed_process_ms": round((time.monotonic_ns() - clock) / 1_000_000, 2),
            "cross_host_clock_offset_ms": None,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": sys.platform,
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "github_event": os.environ.get("GITHUB_EVENT_NAME"),
        },
        "checks": checks,
        "tests_executed": next((c.get("tests_passed") for c in checks
                                if c["name"] == "pytest"), None),
        "source_exact": exact,
        "clean_tracked": clean,
        "local_developer_hook_verified": None,
        "repository_wide_security_admission": None,
        "merge_admission": "HOLD",
        "status": "PASS" if passed else "FAIL",
    }


def compare(before, after):
    """Exact-source and test-count parity; wall-clock/runtime not conflated."""
    def valid(r):
        return (
            isinstance(r, dict)
            and r.get("schema") == "abacus.cbd.e2e.stage.v1"
            and r.get("status") == "PASS"
            and isinstance(r.get("source"), dict)
        )
    if not valid(before) or not valid(after):
        status, reasons = "HOLD", ["missing or failed source-bound stage"]
    else:
        reasons = []
        for key in ("head_sha", "head_tree_sha"):
            if before["source"].get(key) != after["source"].get(key):
                reasons.append("source mismatch: " + key)
        if (before.get("tests_executed") is None or
                after.get("tests_executed") is None or
                before["tests_executed"] != after["tests_executed"]):
            reasons.append("test denominator mismatch")
        for name in ("black", "isort", "pytest"):
            b = next((c for c in before["checks"] if c["name"] == name), None)
            a = next((c for c in after["checks"] if c["name"] == name), None)
            if not b or not a or b["status"] != "PASS" or a["status"] != "PASS":
                reasons.append("unverified check: " + name)
        status = "PASS" if not reasons else "HOLD"
    return {
        "schema": "abacus.cbd.e2e.diff.v1",
        "before_stage": before.get("stage") if isinstance(before, dict) else None,
        "after_stage": after.get("stage") if isinstance(after, dict) else None,
        "status": status,
        "differences": reasons,
        "before_process_ms": before.get("clock", {}).get("elapsed_process_ms") if isinstance(before, dict) else None,
        "after_process_ms": after.get("clock", {}).get("elapsed_process_ms") if isinstance(after, dict) else None,
        "cross_host_elapsed_delta_ms": None,
        "developer_pre_push_vs_ci": None,
        "independent_security_admission": None,
        "merge_admission": "HOLD",
    }


def replay(repo, expected):
    """Fetch an exact HEAD into an isolated local Git clone (no network needed)."""
    started = time.monotonic_ns()
    with tempfile.TemporaryDirectory(prefix="cbd-fresh-clone-") as temp:
        target = Path(temp) / "fresh"
        init = command(["git", "init", "-q", str(target)], repo)
        fetch = command(
            ["git", "-C", str(target), "fetch", "--no-tags", "--depth", "1",
             str(repo), str(expected)], repo, timeout=90,
        ) if init["status"] == "PASS" else None
        checkout = command(
            ["git", "-C", str(target), "checkout", "-q", "--detach", "FETCH_HEAD"],
            repo,
        ) if fetch and fetch["status"] == "PASS" else None
        if checkout and checkout["status"] == "PASS":
            result = run_stage(target, "checkout", expected)
        else:
            result = {
                "schema": "abacus.cbd.e2e.stage.v1",
                "stage": "checkout",
                "status": "FAIL",
                "source": {},
                "checks": [],
                "tests_executed": None,
            }
    result["stage"] = "replay"
    result["clone_mechanism"] = "git init + local git fetch exact sha + detached checkout"
    result["clone_steps"] = [
        {"name": name, "status": data["status"], "returncode": data["returncode"]}
        for name, data in (("init", init), ("fetch", fetch), ("checkout", checkout))
        if data is not None
    ]
    result["replay_elapsed_process_ms"] = round(
        (time.monotonic_ns() - started) / 1_000_000, 2
    )
    result["remote_github_fresh_clone_proven"] = False
    return result


def write_receipt(path, data):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n",
                      encoding="utf-8")
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--expected-sha")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--before", type=Path)
    parser.add_argument("--after", type=Path)
    parser.add_argument("--receipt", type=Path, default=Path(".testpilot/e2e/receipt.json"))
    args = parser.parse_args()
    repo = args.repo.resolve()
    if args.stage == "compare":
        if not args.before or not args.after:
            parser.error("compare needs --before and --after")
        data = compare(json.loads(args.before.read_text()),
                       json.loads(args.after.read_text()))
    elif args.stage == "replay":
        if not args.expected_sha or SHA.fullmatch(args.expected_sha) is None:
            parser.error("replay needs exact 40-character --expected-sha")
        data = replay(repo, args.expected_sha)
    else:
        data = run_stage(repo, args.stage, args.expected_sha)
    target = args.receipt if args.receipt.is_absolute() else repo / args.receipt
    write_receipt(target, data)
    print(json.dumps({
        "stage": args.stage, "status": data["status"],
        "receipt": str(target), "sha": data.get("source", {}).get("head_sha"),
        "tests_executed": data.get("tests_executed"),
    }, sort_keys=True))
    return 0 if data["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
