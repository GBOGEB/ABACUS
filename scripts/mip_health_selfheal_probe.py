#!/usr/bin/env python3
"""Prove a fail-closed MIP health/self-heal loop on a transient fixture.

The probe reuses ABACUS's existing QuickFixer primitive but never targets the
source checkout. It measures one deterministic weak-type pattern before and
after repair, verifies the repaired fixture, and binds the sanitized result to
the exact repository SHA.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from DMAIC_V3.quick_error_fix import QuickFixer  # noqa: E402

BEFORE = "from typing import Any, Dict, List\n\nrecords: List[Dict] = []\n"
AFTER = (
    "from typing import Any, Dict, List\n\n"
    "records: List[Dict[str, Any]] = []\n"
)
WEAK_PATTERN = "List[Dict]"


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def compile_ok(source: str) -> bool:
    try:
        compile(source, "<mip-health-selfheal-fixture>", "exec")
    except SyntaxError:
        return False
    return True


def build_receipt() -> dict[str, Any]:
    exact_sha = git("rev-parse", "HEAD")
    checkout_before = git("status", "--porcelain")

    with tempfile.TemporaryDirectory(prefix="mip-health-selfheal-") as temp:
        fixture = Path(temp) / "fixture.py"
        fixture.write_text(BEFORE, encoding="utf-8")

        before_text = fixture.read_text(encoding="utf-8")
        before_metric = before_text.count(WEAK_PATTERN)
        before_compile = compile_ok(before_text)

        fixer = QuickFixer()
        fix_applied = fixer.fix_type_hints(fixture)

        after_text = fixture.read_text(encoding="utf-8")
        after_metric = after_text.count(WEAK_PATTERN)
        after_compile = compile_ok(after_text)

    checkout_after = git("status", "--porcelain")
    delta = after_metric - before_metric
    fix_records = fixer.fixes_applied

    checks = {
        "before_metric_observed": before_metric == 1,
        "before_fixture_compiles": before_compile,
        "repair_applied": fix_applied is True,
        "repair_recorded": len(fix_records) == 1,
        "repair_status_success": bool(fix_records)
        and fix_records[0].get("status") == "SUCCESS",
        "after_metric_closed": after_metric == 0,
        "after_fixture_compiles": after_compile,
        "after_fixture_exact": after_text == AFTER,
        "improvement_delta": delta == -1,
        "source_checkout_unchanged": checkout_before == checkout_after,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    verification = "PASS" if not failed else "FAIL"
    return_state = "IMPROVED" if verification == "PASS" else "REGRESSED"

    return {
        "schema_version": "0.1",
        "program": "MIP",
        "diagnostic": "repo_health_selfheal",
        "verification": verification,
        "exact_sha": exact_sha,
        "execution_context": "transient_controlled_fixture",
        "source_primitive": (
            "DMAIC_V3.quick_error_fix.QuickFixer.fix_type_hints"
        ),
        "repair_class": "test_gap",
        "before_metric": before_metric,
        "after_metric": after_metric,
        "delta": delta,
        "metric_direction": "lower_is_better",
        "return_state": return_state,
        "source_checkout_unchanged": checkout_before == checkout_after,
        "fixture_before_sha256": sha256_text(before_text),
        "fixture_after_sha256": sha256_text(after_text),
        "checks": checks,
        "failed_checks": failed,
        "raw_receipt_retention": "transient_runner_only",
        "promotion_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run transient MIP health/self-heal proof."
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    receipt = build_receipt()
    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if receipt["verification"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
