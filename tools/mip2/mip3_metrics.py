"""MIP3 statistical telemetry, root identity and method promotion guards."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter


def fingerprint(repo, family, rule, normalized_location, signature):
    parts = [repo, family, rule, normalized_location, signature]
    return hashlib.sha256(
        json.dumps(parts, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()[:24]


def metrics(tp, fp, fn, tn=0):
    if any(not isinstance(x, int) or x < 0 for x in (tp, fp, fn, tn)):
        raise ValueError("counts must be nonnegative integers")
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "specificity": tn / (tn + fp) if tn + fp else None,
    }


def wilson(success, total, z=1.959963984540054):
    if total <= 0 or success < 0 or success > total:
        return None
    p = success / total
    d = 1 + z * z / total
    mid = (p + z * z / (2 * total)) / d
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / d
    return [max(0, mid - half), min(1, mid + half)]


def summarize(observations):
    counts = Counter(x["family"] for x in observations)
    timings = [
        x["duration_s"]
        for x in observations
        if isinstance(x.get("duration_s"), (int, float)) and x["duration_s"] >= 0
    ]
    return {
        "n": len(observations),
        "pareto": sorted(counts.items(), key=lambda p: (-p[1], p[0])),
        "runtime_median_s": statistics.median(timings) if timings else None,
        "runtime_p95_s": (
            sorted(timings)[math.ceil(0.95 * len(timings)) - 1] if timings else None
        ),
        "pca_ready": False,
        "pca_reason": "Requires repeated independent, comparable labeled observations",
    }


def promotion(receipt, minimum_tests=4):
    j = receipt.get("junit", {})
    checks = [
        receipt.get("status") == "PASS",
        receipt.get("phase") == "postflight",
        bool(receipt.get("head_sha")),
        j.get("tests", 0) >= minimum_tests,
        all(j.get(k, -1) == 0 for k in ("failures", "errors", "skipped")),
        receipt.get("local_flight", {}).get("sha_matches") is True,
    ]
    return {
        "eligible_for_method_review": all(checks),
        "merge_admitted": False,
        "reasons": [
            name
            for name, ok in zip(
                (
                    "postflight_pass",
                    "postflight_phase",
                    "head_sha",
                    "minimum_tests",
                    "zero_failures_errors_skips",
                    "exact_sha_match",
                ),
                checks,
            )
            if not ok
        ],
    }
