#!/usr/bin/env python3
"""Truthful, non-mutating Phase-0 smoke runner for CI evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from DMAIC_V3.config import DMAICConfig, PathConfig
from DMAIC_V3.core.state import StateManager
from DMAIC_V3.phases.phase0_init import Phase0Init


ROOT = Path(__file__).resolve().parents[2]


def _head_sha(workspace: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(workspace), "rev-parse", "HEAD"],
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "WITHHELD"


def run_smoke(workspace: Path, scratch: Path) -> dict[str, Any]:
    workspace = workspace.resolve()
    scratch = scratch.resolve()
    paths = PathConfig(
        workspace_root=workspace,
        output_root=scratch / "output",
        state_dir=scratch / "state",
        knowledge_dir=scratch / "knowledge",
        reports_dir=scratch / "reports",
        iterations_dir=scratch / "iterations",
        logs_dir=scratch / "logs",
    )
    config = DMAICConfig(workspace_root=str(workspace), paths=paths)
    state = StateManager(paths.state_dir)
    phase = Phase0Init(config, state)

    steps: list[dict[str, Any]] = []

    environment = phase._check_environment()
    env_pass = bool(
        environment.get("workspace_exists")
        and environment.get("git_available")
        and all(environment.get("dependencies", {}).values())
    )
    steps.append(
        {
            "name": "phase0_environment",
            "status": "PASS" if env_pass else "FAIL",
            "evidence": environment,
        }
    )

    canonical = phase._setup_canonical_files()
    required = ("VERSION", "README")
    canonical_pass = all(
        bool(canonical.get(name, {}).get("exists"))
        for name in required
    )
    steps.append(
        {
            "name": "phase0_canonical_files",
            "status": "PASS" if canonical_pass else "FAIL",
            "required": list(required),
            "evidence": canonical,
        }
    )

    changes = phase._detect_changes()
    change_pass = bool(changes.get("git_available"))
    steps.append(
        {
            "name": "phase0_change_detection",
            "status": "PASS" if change_pass else "FAIL",
            "evidence": changes,
        }
    )

    status = "PASS" if all(step["status"] == "PASS" for step in steps) else "FAIL"
    return {
        "schema": "abacus-phase0-smoke/1.0.0",
        "status": status,
        "repo": "GBOGEB/ABACUS",
        "head_sha": _head_sha(workspace),
        "executed_steps": len(steps),
        "steps": steps,
        "scratch_root": str(scratch),
        "authority_transfer": False,
        "formal_credit_delta": 0,
        "engineering_credit_delta": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", required=True)
    parser.add_argument("--workspace", type=Path, default=ROOT)
    parser.add_argument("--scratch", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)

    if args.scratch is None:
        with tempfile.TemporaryDirectory(prefix="abacus-phase0-smoke-") as tmp:
            receipt = run_smoke(args.workspace, Path(tmp))
    else:
        args.scratch.mkdir(parents=True, exist_ok=True)
        receipt = run_smoke(args.workspace, args.scratch)

    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
