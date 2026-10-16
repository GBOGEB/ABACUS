"""Fail-closed, evidence-only method qualification; never grants admission.

Levels calculated here are *candidates*. Native artifacts, independent receipts,
and causal-root closure require verification outside this untrusted input.
"""

import json
import math
import re
import sys
from pathlib import Path

REQUIRED = (
    "repository", "source_sha", "method_id", "tool_version", "config_digest",
    "corpus_digest", "run_id", "job_id", "attempt", "tp", "fp", "fn", "tn",
    "runtime_seconds", "repair_receipt", "negative_controls_pass",
    "federation_receipts", "adaptive_receipt",
)
OPTIONAL_EVIDENCE = {"repair_receipt", "adaptive_receipt"}
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def _rejected(state, missing=None):
    result = {
        "state": state,
        "level": "M0",
        "native_verified": False,
        "root_closed": False,
        "merge_authorized": False,
    }
    if missing:
        result["missing"] = missing
    return result


def qualify(e):
    """Classify syntactically valid, untrusted method evidence as provisional."""
    if not isinstance(e, dict):
        return _rejected("INVALID")
    missing = [
        key
        for key in REQUIRED
        if key not in e or (key not in OPTIONAL_EVIDENCE and e[key] is None)
    ]
    if missing:
        return _rejected("UNKNOWN", missing)
    if any(
        not isinstance(e[key], str) or not e[key].strip()
        for key in ("repository", "method_id", "tool_version")
    ):
        return _rejected("INVALID")
    if not isinstance(e["source_sha"], str) or not HEX40.fullmatch(e["source_sha"]):
        return _rejected("INVALID")
    if any(
        not isinstance(e[key], str) or not HEX64.fullmatch(e[key])
        for key in ("config_digest", "corpus_digest")
    ):
        return _rejected("INVALID")
    if any(type(e[key]) is not int or e[key] < 1 for key in ("run_id", "job_id", "attempt")):
        return _rejected("INVALID")
    if any(type(e[key]) is not int or e[key] < 0 for key in ("tp", "fp", "fn", "tn")):
        return _rejected("INVALID")
    duration = e["runtime_seconds"]
    if type(duration) not in (int, float) or not math.isfinite(duration) or duration < 0:
        return _rejected("INVALID")
    if type(e["negative_controls_pass"]) is not bool:
        return _rejected("INVALID")
    if any(
        e[key] is not None and (not isinstance(e[key], str) or not e[key].strip())
        for key in OPTIONAL_EVIDENCE
    ):
        return _rejected("INVALID")
    federation = e["federation_receipts"]
    if (
        not isinstance(federation, list)
        or any(not isinstance(item, str) or not item.strip() for item in federation)
        or len(federation) != len(set(federation))
    ):
        return _rejected("INVALID")

    tp, fp, fn, tn = (e[key] for key in ("tp", "fp", "fn", "tn"))
    if tp + fp + fn + tn == 0:
        return _rejected("UNKNOWN")
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    level = "M1"
    if tp + fn and fp + tn:
        level = "M2"
        if e["repair_receipt"]:
            level = "M3"
            if e["negative_controls_pass"] and fn == 0:
                level = "M4"
                if len(federation) >= 2:
                    level = "M5"
                    if e["adaptive_receipt"]:
                        level = "M6"

    return {
        "state": "MEASURED",
        "level": level,
        "qualification_status": "PROVISIONAL_NOT_NATIVE_VERIFIED",
        "precision": precision,
        "recall": recall,
        "runtime_seconds": duration,
        "native_verified": False,
        "root_closed": False,
        "merge_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(qualify(json.loads(Path(sys.argv[1]).read_text())), sort_keys=True))
