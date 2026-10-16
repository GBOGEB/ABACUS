"""Fail-closed, evidence-only qualification. Does not execute scanners or authorize merges."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "method_qualification_registry.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST64 = re.compile(r"^[0-9a-f]{64}$")

REQUIRED = (
    "repository",
    "source_sha",
    "method_id",
    "tool_version",
    "config_digest",
    "corpus_digest",
    "run_id",
    "job_id",
    "attempt",
    "tp",
    "fp",
    "fn",
    "tn",
    "runtime_seconds",
    "repair_receipt",
    "negative_controls_pass",
    "federation_receipts",
    "adaptive_receipt",
)


def _nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def _registered_methods():
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {row["id"] for row in data.get("methods", []) if _nonempty_string(row.get("id"))}


def _valid_identity(e):
    return (
        _nonempty_string(e["repository"])
        and isinstance(e["source_sha"], str)
        and bool(SHA40.fullmatch(e["source_sha"]))
        and _nonempty_string(e["method_id"])
        and e["method_id"] in _registered_methods()
        and _nonempty_string(e["tool_version"])
        and isinstance(e["config_digest"], str)
        and bool(DIGEST64.fullmatch(e["config_digest"]))
        and isinstance(e["corpus_digest"], str)
        and bool(DIGEST64.fullmatch(e["corpus_digest"]))
        and all(type(e[key]) is int and e[key] > 0 for key in ("run_id", "job_id", "attempt"))
    )


def _valid_federation_receipt(receipt, method_id):
    if not isinstance(receipt, dict):
        return False
    return (
        _nonempty_string(receipt.get("receipt_id"))
        and _nonempty_string(receipt.get("repository"))
        and isinstance(receipt.get("source_sha"), str)
        and bool(SHA40.fullmatch(receipt["source_sha"]))
        and receipt.get("method_id") == method_id
        and receipt.get("applicable") is True
        and receipt.get("independent") is True
    )


def _valid_adaptive_receipt(receipt, source_sha, method_id):
    if not isinstance(receipt, dict):
        return False
    baseline = receipt.get("baseline_receipt")
    candidate = receipt.get("candidate_receipt")
    return (
        receipt.get("source_sha") == source_sha
        and receipt.get("method_id") == method_id
        and _nonempty_string(baseline)
        and _nonempty_string(candidate)
        and baseline != candidate
        and _nonempty_string(receipt.get("metric"))
        and isinstance(receipt.get("delta"), (int, float))
        and receipt.get("improved") is True
    )


def qualify(e):
    missing = [key for key in REQUIRED if key not in e or e[key] is None]
    if missing:
        return {
            "state": "UNKNOWN",
            "level": "M0",
            "missing": missing,
            "merge_authorized": False,
        }

    if not _valid_identity(e):
        return {
            "state": "INVALID",
            "level": "M0",
            "reason": "invalid evidence identity",
            "merge_authorized": False,
        }

    if any(type(e[key]) is not int or e[key] < 0 for key in ("tp", "fp", "fn", "tn")):
        return {"state": "INVALID", "level": "M0", "merge_authorized": False}

    if not isinstance(e["runtime_seconds"], (int, float)) or e["runtime_seconds"] < 0:
        return {"state": "INVALID", "level": "M0", "merge_authorized": False}

    if type(e["negative_controls_pass"]) is not bool:
        return {
            "state": "INVALID",
            "level": "M0",
            "reason": "negative_controls_pass must be boolean",
            "merge_authorized": False,
        }

    if not isinstance(e["federation_receipts"], list):
        return {
            "state": "INVALID",
            "level": "M0",
            "reason": "federation_receipts must be a list",
            "merge_authorized": False,
        }

    tp, fp, fn, tn = (e[key] for key in ("tp", "fp", "fn", "tn"))
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None

    level = "M1"
    if tp + fn and fp + tn:
        level = "M2"
        if _nonempty_string(e["repair_receipt"]):
            level = "M3"
            if e["negative_controls_pass"] is True and fn == 0:
                level = "M4"
                valid_receipts = [
                    receipt
                    for receipt in e["federation_receipts"]
                    if _valid_federation_receipt(receipt, e["method_id"])
                ]
                repositories = {receipt["repository"] for receipt in valid_receipts}
                receipt_ids = {receipt["receipt_id"] for receipt in valid_receipts}
                if len(repositories) >= 2 and len(receipt_ids) >= 2:
                    level = "M5"
                    if _valid_adaptive_receipt(
                        e["adaptive_receipt"], e["source_sha"], e["method_id"]
                    ):
                        level = "M6"

    return {
        "state": "MEASURED",
        "level": level,
        "precision": precision,
        "recall": recall,
        "runtime_seconds": e["runtime_seconds"],
        "merge_authorized": False,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            qualify(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))),
            sort_keys=True,
        )
    )
