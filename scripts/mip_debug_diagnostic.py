#!/usr/bin/env python3
"""Executable debug/LDAB diagnostic for the MIP self-index, stdlib only.

Part of the canonical MIP kit hosted in GBOGEB/CODEX (``MIP/kit/KIT_MANIFEST.json``).
It is the default ``debug_diagnostic`` named by ``MIP/mip_surface.json``; a
repository may point that key at its own diagnostic or set it to ``null``.

The debug lane is GREEN only when this diagnostic runs on the exact checkout
SHA and every check passes. The emitter that runs it binds the receipt to
that SHA. Two checks, both in-process (no subprocess, no network):

* ``traceback_localizes``: a deliberate failure yields a traceback whose last
  frame names this file, the raising line and function, and the exception.
* ``validator_fails_closed``: the kit's receipt validator rejects a FAIL
  receipt with ``SystemExit`` naming the failed check.

The receipt holds no paths, remotes, or timestamps, so two runs on the same SHA
are identical.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import traceback
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
FAILING_RECEIPT = {
    "schema_version": "0.1",
    "program": "MIP",
    "verification": "FAIL",
    "repository": "diagnostic/negative-control",
    "head_sha": "0" * 40,
    "raw_receipt_retention": "transient_runner_only",
    "root_self_index": {"runs": 2, "normalized_equal": True},
}


def mip_debug_probe_target() -> None:
    raise LookupError("mip debug diagnostic")


TARGET_LINE = mip_debug_probe_target.__code__.co_firstlineno + 1


def traceback_localizes() -> bool:
    try:
        mip_debug_probe_target()
    except LookupError as exc:
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        rendered = "".join(traceback.format_exception(exc))
        return (
            Path(frame.filename).resolve() == Path(__file__).resolve()
            and frame.lineno == TARGET_LINE
            and frame.name == "mip_debug_probe_target"
            and "LookupError: mip debug diagnostic" in rendered
        )
    return False


def validator_fails_closed() -> bool:
    if not VALIDATOR.is_file():
        return False
    spec = importlib.util.spec_from_file_location("mip_debug_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        return False
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        module.validate_producer(dict(FAILING_RECEIPT), None)
    except SystemExit as exc:
        message = str(exc.code)
        return "receipt validation failed" in message and "verification" in message
    except Exception:  # noqa: BLE001 - any other error is a failed check
        return False
    return False


def build_receipt() -> dict:
    checks = {
        "traceback_localizes": traceback_localizes(),
        "validator_fails_closed": validator_fails_closed(),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "0.1",
        "program": "MIP",
        "diagnostic": DIAGNOSTIC_NAME,
        "verification": "FAIL" if failed else "PASS",
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
