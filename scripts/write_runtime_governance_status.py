#!/usr/bin/env python3
"""Generate run-bound W007 runtime-governance status evidence."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.validate_runtime_foundation import REPO_ROOT, validate_runtime_foundation
except ModuleNotFoundError:  # direct `python scripts/...` execution
    from validate_runtime_foundation import REPO_ROOT, validate_runtime_foundation


def build_status(repo_root: Path = REPO_ROOT) -> dict[str, object]:
    errors = validate_runtime_foundation(repo_root)
    return {
        "schema": "abacus-runtime-governance-status/1.0",
        "wave": "W007",
        "runtime_status": "validated" if not errors else "validation_failed",
        "validation_passed": not errors,
        "validation_errors": errors,
        "repository": os.getenv("GITHUB_REPOSITORY", "GBOGEB/ABACUS"),
        "head_sha": os.getenv("GITHUB_SHA", "UNBOUND_LOCAL"),
        "run_id": os.getenv("GITHUB_RUN_ID", "UNBOUND_LOCAL"),
        "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT", "UNBOUND_LOCAL"),
        "workflow": os.getenv("GITHUB_WORKFLOW", "LOCAL_VALIDATION"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority": "RUNTIME_EVIDENCE_ONLY_ZERO_ENGINEERING_AUTHORITY",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "reports" / "runtime_governance_status.json",
    )
    args = parser.parse_args()

    status = build_status()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0 if status["validation_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
