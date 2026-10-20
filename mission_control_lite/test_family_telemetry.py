"""Fail-closed, native-log census of deliberately named test families.

Counts execution *intent* only. Synthetic cases are not field FPR/FNR,
causal-root closure, authenticated artifact ingestion or merge admission.
"""
from __future__ import annotations

import hashlib
import re

SCHEMA = "mcl.test.family.v1"
FAMILIES = ("positive", "negative", "reverse", "force_trip")
SHA = re.compile(r"^[0-9a-f]{40}$")
SUMMARY = re.compile(r"(?m)^Ran ([0-9]+) tests? in [0-9]+(?:\.[0-9]+)?s$")
CASE = re.compile(
    r"(?m)^(test_[a-z][a-z0-9_]*) "
    r"\(([A-Za-z_]\w*(?:\.[A-Za-z_]\w*){2,})\) \.\.\. ok$"
)
CASE_LINE = re.compile(r"(?m)^test_\w+ \([^\n]*\) \.\.\. .+$")


def audit_native_family_log(log: str, source_sha: str, run_id: int, *, min_per_family: int = 4) -> dict:
    """Verify one passing verbose-unittest census; never infer performance accuracy."""
    if not isinstance(source_sha, str) or not SHA.fullmatch(source_sha):
        raise ValueError("noncanonical exact source SHA")
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("invalid native run ID")
    if type(min_per_family) is not int or min_per_family <= 0:
        raise ValueError("invalid family minimum")
    if not isinstance(log, str) or not log or len(log) > 2_000_000:
        raise ValueError("missing or oversized native test log")
    counts = SUMMARY.findall(log)
    if len(counts) != 1 or len(re.findall(r"(?m)^OK$", log)) != 1:
        raise ValueError("missing unique passing unittest summary")
    if re.search(r"(?m)^(FAILED|ERROR|Traceback \(most recent call last\))", log):
        raise ValueError("failed native unittest status")
    declared = int(counts[0])
    if not declared:
        raise ValueError("empty test population")
    rows = CASE.findall(log)
    if len(rows) != declared or len(CASE_LINE.findall(log)) != declared:
        raise ValueError("case identity or status count differs from native summary")
    identities = []
    per_family = {name: 0 for name in FAMILIES}
    for method, qualified in rows:
        if not qualified.endswith("." + method):
            raise ValueError("case method/qualified identity mismatch")
        family = next((name for name in FAMILIES if method.startswith("test_" + name + "_")), None)
        if family is None:
            raise ValueError("unclassified test family: " + method)
        identities.append(qualified)
        per_family[family] += 1
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate native test case identity")
    below = [name for name, count in per_family.items() if count < min_per_family]
    if below:
        raise ValueError("required test family underrepresented: " + ", ".join(below))
    unique = sorted(identities)
    return {
        "schema": SCHEMA,
        "source_sha": source_sha,
        "run_id": run_id,
        "case_identity_sha256": hashlib.sha256("\n".join(unique).encode("utf-8")).hexdigest(),
        "native_case_executions": declared,
        "unique_case_ids": len(unique),
        "duplicate_case_executions": 0,
        "planned_families": list(FAMILIES),
        "families_represented": len(FAMILIES),
        "family_presence_percent": 100.0,
        "case_counts_by_family": per_family,
        "minimum_per_family": min_per_family,
        "classification_basis": "verbose_unittest_case_method_prefix",
        "evidence_class": "NATIVE_EXECUTED_CASE_INTENT_ONLY",
        "field_false_positive_rate": None,
        "field_false_negative_rate": None,
        "fault_injection_detection_rate": None,
        "verified_root_closures": 0,
        "merge_admission": "HOLD",
    }
