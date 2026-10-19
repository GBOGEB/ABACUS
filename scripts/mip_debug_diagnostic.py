#!/usr/bin/env python3
"""Executable debug/LDAB diagnostic for the MIP self-index, stdlib only.

Part of the canonical MIP kit hosted in GBOGEB/CODEX (``MIP/kit/KIT_MANIFEST.json``).
It is the default ``debug_diagnostic`` named by ``MIP/mip_surface.json``; a
repository may point that key at its own diagnostic or set it to ``null``.

The debug lane is GREEN only when this diagnostic runs on the exact checkout
SHA and every check passes. Two checks:

* ``traceback_localizes``: a deliberate failure in a child interpreter yields
  a traceback naming the failing file, line, function and exception type.
* ``validator_fails_closed``: the kit's receipt validator rejects a FAIL
  receipt with a non-zero exit that names the failed check.

The receipt holds no paths, remotes, or timestamps, so two runs on the same SHA
are identical.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = (
    ROOT
    / ".codex"
    / "skills"
    / "mip-repo-self-index"
    / "scripts"
    / "validate_receipt.py"
)
DIAGNOSTIC_NAME = "mip-debug-diagnostic"
FAILING_SOURCE = (
    "def mip_debug_probe_target():\n"
    "    raise LookupError('mip debug diagnostic')\n"
    "\n"
    "mip_debug_probe_target()\n"
)


def run_git(args: list[str]) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), *args],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def traceback_localizes(tmp: Path) -> bool:
    script = tmp / "mip_debug_failing_target.py"
    script.write_text(FAILING_SOURCE, encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp,
        text=True,
        capture_output=True,
        check=False,
    )
    stderr = completed.stderr
    return (
        completed.returncode != 0
        and script.name in stderr
        and "line 2" in stderr
        and "mip_debug_probe_target" in stderr
        and "LookupError: mip debug diagnostic" in stderr
    )


def validator_fails_closed(tmp: Path) -> bool:
    if not VALIDATOR.is_file():
        return False
    receipt = tmp / "failing-producer.json"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "program": "MIP",
                "verification": "FAIL",
                "repository": "diagnostic/negative-control",
                "head_sha": "0" * 40,
                "raw_receipt_retention": "transient_runner_only",
                "root_self_index": {"runs": 2, "normalized_equal": True},
            }
        ),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR), str(receipt)],
        cwd=tmp,
        text=True,
        capture_output=True,
        check=False,
    )
    output = completed.stdout + completed.stderr
    return (
        completed.returncode != 0
        and "receipt validation failed" in output
        and "verification" in output
    )


def build_receipt() -> dict:
    with tempfile.TemporaryDirectory(prefix="mip-debug-diagnostic-") as temp:
        tmp = Path(temp)
        checks = {
            "traceback_localizes": traceback_localizes(tmp),
            "validator_fails_closed": validator_fails_closed(tmp),
        }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "0.1",
        "program": "MIP",
        "diagnostic": DIAGNOSTIC_NAME,
        "verification": "FAIL" if failed else "PASS",
        "exact_sha": run_git(["rev-parse", "HEAD"]),
        "checks": checks,
        "failed_checks": failed,
        "raw_receipt_retention": "transient_runner_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the MIP debug/LDAB diagnostic.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    receipt = build_receipt()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["verification"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
