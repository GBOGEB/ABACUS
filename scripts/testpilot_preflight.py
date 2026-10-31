"""Local TestPilot preflight.

Purpose: catch deterministic defects before GitHub Actions without weakening
the authoritative CI gates.  Fast mode is suitable for pre-commit; full/gate
modes reproduce progressively stronger local checks.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import py_compile
import re
import subprocess
import sys
import time

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 compatibility
    import tomli as tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = ROOT / ".testpilot" / "last_receipt.json"
CONFIG_SUFFIXES = {".json", ".toml", ".yaml", ".yml"}
TEXT_SUFFIXES = {".py", ".json", ".toml", ".yaml", ".yml", ".md", ".txt", ".ini"}
CONFLICT_START_RE = re.compile(r"^<<<<<<< .+$", re.MULTILINE)
CONFLICT_MID_RE = re.compile(r"^=======$", re.MULTILINE)
CONFLICT_END_RE = re.compile(r"^>>>>>>> .+$", re.MULTILINE)


class GitProbeError(RuntimeError):
    """A Git census failure is never equivalent to an empty changed-file set."""



def run(cmd: list[str], *, cwd: Path = ROOT) -> dict:
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "command": cmd,
            "cwd": str(cwd.relative_to(ROOT)) if cwd != ROOT else ".",
            "returncode": None,
            "seconds": round(time.monotonic() - started, 3),
            "stdout_tail": "",
            "stderr_tail": type(exc).__name__,
            "status": "FAIL",
            "error_kind": type(exc).__name__,
        }
    return {
        "command": cmd,
        "cwd": str(cwd.relative_to(ROOT)) if cwd != ROOT else ".",
        "returncode": proc.returncode,
        "seconds": round(time.monotonic() - started, 3),
        "stdout_tail": proc.stdout[-5000:],
        "stderr_tail": proc.stderr[-5000:],
        "status": "PASS" if proc.returncode == 0 else "FAIL",
    }


def git_lines(*args: str) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
        )
    except OSError as exc:
        raise GitProbeError(f"git {args[0] if args else 'probe'} unavailable: {type(exc).__name__}") from exc
    if proc.returncode != 0:
        raise GitProbeError(f"git {args[0] if args else 'probe'} exited {proc.returncode}")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def changed_files() -> list[Path]:
    paths = []
    for args in (
        ("diff", "--cached", "--name-only", "--diff-filter=ACMR"),
        ("diff", "--name-only", "--diff-filter=ACMR"),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        paths.extend(git_lines(*args))
    unique = []
    seen = set()
    for raw in paths:
        if raw not in seen:
            seen.add(raw)
            p = ROOT / raw
            if p.is_file():
                unique.append(p)
    return unique


def parity_subject_files() -> list[Path]:
    """Files that implement/configure TestPilot itself.

    Parity must prove the local gate without turning inherited repository-wide
    lint debt into a blocker for adopting the gate.
    """
    raw_paths = [
        "scripts/testpilot_preflight.py",
        "scripts/testpilot.ps1",
        ".pre-commit-config.yaml",
        "requirements-dev.txt",
        "Makefile",
        "pytest.ini",
        "docs/ci/TESTPILOT_PREFLIGHT.md",
        ".github/workflows/testpilot-preflight.yml",
    ]
    return [ROOT / raw for raw in raw_paths if (ROOT / raw).is_file()]


def check_conflicts(files: list[Path]) -> dict:
    bad = []
    for p in files:
        if p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            if (
                CONFLICT_START_RE.search(text)
                and CONFLICT_MID_RE.search(text)
                and CONFLICT_END_RE.search(text)
            ):
                bad.append(str(p.relative_to(ROOT)))
        except OSError:
            bad.append(str(p.relative_to(ROOT)))
    return {
        "name": "merge_conflict_markers",
        "status": "PASS" if not bad else "FAIL",
        "files": bad,
    }


def check_python_compile(files: list[Path]) -> dict:
    bad = []
    checked = 0
    for p in files:
        if p.suffix.lower() != ".py":
            continue
        checked += 1
        try:
            py_compile.compile(str(p), doraise=True)
        except py_compile.PyCompileError as exc:  # compile error is the evidence
            bad.append({"file": str(p.relative_to(ROOT)), "error": str(exc)})
    return {
        "name": "python_compile",
        "status": "PASS" if not bad else "FAIL",
        "checked": checked,
        "failures": bad,
    }


def check_configs(files: list[Path]) -> dict:
    bad = []
    checked = 0
    for p in files:
        suffix = p.suffix.lower()
        if suffix not in CONFIG_SUFFIXES:
            continue
        checked += 1
        try:
            text = p.read_text(encoding="utf-8")
            if suffix == ".json":
                json.loads(text)
            elif suffix == ".toml":
                tomllib.loads(text)
            else:
                yaml.safe_load(text)
        except (json.JSONDecodeError, tomllib.TOMLDecodeError, yaml.YAMLError, OSError) as exc:
            bad.append({"file": str(p.relative_to(ROOT)), "error": str(exc)})
    return {
        "name": "config_parse",
        "status": "PASS" if not bad else "FAIL",
        "checked": checked,
        "failures": bad,
    }


def ruff_check(files: list[Path], *, fix: bool) -> dict:
    py_files = [str(p.relative_to(ROOT)) for p in files if p.suffix.lower() == ".py"]
    if not py_files:
        return {"name": "ruff", "status": "PASS", "checked": 0, "fix": fix}
    if importlib.util.find_spec("ruff") is None:
        return {
            "name": "ruff",
            "status": "FAIL" if fix else "SKIP",
            "checked": len(py_files),
            "fix": fix,
            "reason": "ruff unavailable; install requirements-dev.txt",
        }
    cmd = [sys.executable, "-m", "ruff", "check"]
    if fix:
        cmd.append("--fix")
    cmd.extend(py_files)
    result = run(cmd)
    result.update({"name": "ruff", "checked": len(py_files), "fix": fix})
    return result


def targeted_pytest() -> list[dict]:
    commands = [
        [
            sys.executable,
            "-m",
            "pytest",
            "DMAIC_V3/tests",
            "--collect-only",
            "-q",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            "DMAIC_V3/tests/test_super_bridge.py",
            "-q",
            "-m",
            "smoke or e2e",
            "--maxfail=1",
        ],
    ]
    return [dict(run(cmd), name=f"pytest_targeted_{i+1}") for i, cmd in enumerate(commands)]


def coverage_check(floor: float) -> dict:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests",
        "-q",
        "--cov=core",
        "--cov-report=term-missing",
        f"--cov-fail-under={floor:g}",
    ]
    result = run(cmd, cwd=ROOT / "DMAIC_V3")
    result.update({"name": "coverage_gate", "coverage_floor_pct": floor})
    return result


def source_sha() -> str | None:
    values = git_lines("rev-parse", "HEAD")
    return values[0] if len(values) == 1 and re.fullmatch(r"[0-9a-f]{40}", values[0]) else None



def receipt_outcome(checks: list[dict], mode: str, *, parity: bool = False) -> tuple[str, int]:
    """Unexecuted checks cannot be reported as complete, especially in gate mode."""
    if not checks:
        return "FAIL", 1
    if any(c.get("status") == "FAIL" for c in checks):
        return "FAIL", 1
    if any(c.get("status") == "SKIP" for c in checks):
        return ("FAIL", 1) if mode == "gate" or parity else ("PARTIAL", 0)
    if any(c.get("status") != "PASS" for c in checks):
        return ("FAIL", 1) if mode == "gate" or parity else ("PARTIAL", 0)
    return "PASS", 0



def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["fast", "full", "gate"], default="fast")
    ap.add_argument("--fix", action="store_true", help="apply only safe ruff fixes")
    ap.add_argument("--parity", action="store_true", help="validate TestPilot implementation/config only")
    ap.add_argument("--coverage-floor", type=float)
    ap.add_argument("--receipt", default=str(DEFAULT_RECEIPT))
    args = ap.parse_args()

    if args.coverage_floor is not None and (
        not math.isfinite(args.coverage_floor)
        or args.coverage_floor < 0
        or args.coverage_floor > 100
        or (args.mode == "gate" and args.coverage_floor < 75)
    ):
        ap.error("invalid coverage floor: gate mode requires at least 75%")

    git_checks: list[dict] = []
    try:
        files = parity_subject_files() if args.parity else changed_files()
    except GitProbeError as exc:
        files = []
        git_checks.append({"name": "git_changed_files", "status": "FAIL", "reason": str(exc)})
    try:
        verified_sha = source_sha()
    except GitProbeError as exc:
        verified_sha = None
        git_checks.append({"name": "git_source_sha", "status": "FAIL", "reason": str(exc)})
    if not isinstance(verified_sha, str) or re.fullmatch(r"[0-9a-f]{40}", verified_sha) is None:
        verified_sha = None
    if verified_sha is None and not any(c["name"] == "git_source_sha" for c in git_checks):
        git_checks.append({"name": "git_source_sha", "status": "FAIL",
                           "reason": "missing or malformed exact HEAD SHA"})
    checks: list[dict] = git_checks + [
        check_conflicts(files),
        check_python_compile(files),
        check_configs(files),
        ruff_check(files, fix=args.fix),
    ]
    checks.extend(targeted_pytest())

    if args.mode in {"full", "gate"}:
        default_floor = 25.0 if args.mode == "full" else 75.0
        floor = args.coverage_floor if args.coverage_floor is not None else default_floor
        checks.append(coverage_check(floor))

    failures = [c for c in checks if c.get("status") == "FAIL"]
    unverified = [c for c in checks if c.get("status") not in {"PASS", "FAIL"}]
    outcome, exit_code = receipt_outcome(checks, args.mode, parity=args.parity)
    receipt = {
        "schema": "abacus.testpilot.preflight.v1",
        "source_sha": verified_sha,
        "mode": args.mode,
        "fix_requested": args.fix,
        "coverage_policy": {
            "fast": "no coverage gate",
            "full": "regression floor defaults to 25%; override explicitly",
            "gate": "GitHub parity floor defaults to 75%; never auto-lowered",
        },
        "parity_scope": args.parity,
        "subject_files": [str(p.relative_to(ROOT)) for p in files],
        "checks": checks,
        "status": outcome,
        "failure_count": len(failures),
        "unverified_check_count": len(unverified),
    }
    receipt_path = Path(args.receipt)
    if not receipt_path.is_absolute():
        receipt_path = ROOT / receipt_path
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
