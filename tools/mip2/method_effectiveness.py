#!/usr/bin/env python3
"""Read-only MIP2 detection-effectiveness scorer. Never promotes maturity or closes roots."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Optional

from mip3_metrics import metrics, wilson

SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SCHEMA = "mip2.method-observations.v1"


def checked_identity(evidence: dict, raw_corpus: bytes, raw_artifact: Optional[bytes]) -> None:
    if not isinstance(evidence, dict) or evidence.get("schema") != SCHEMA:
        raise ValueError("OBSERVATION_SCHEMA_INVALID")
    required = ("repository", "source_sha", "method_id", "tool_name", "tool_version",
                "config_sha256", "corpus_sha256", "artifact_sha256", "run_id",
                "run_attempt", "job_id", "observations")
    if any(key not in evidence or evidence[key] is None for key in required):
        raise ValueError("OBSERVATION_IDENTITY_MISSING")
    if evidence["repository"] not in ("GBOGEB/ABACUS", "GBOGEB/CODEX",
                                      "GBOGEB/cryoplant-project"):
        raise ValueError("REPOSITORY_NOT_IN_FEDERATION_SCOPE")
    if not isinstance(evidence["source_sha"], str) or not SHA40.fullmatch(evidence["source_sha"]):
        raise ValueError("SOURCE_SHA_INVALID")
    for key in ("config_sha256", "corpus_sha256", "artifact_sha256"):
        value = evidence[key]
        if not isinstance(value, str) or not SHA256.fullmatch(value):
            raise ValueError(key.upper() + "_INVALID")
    if evidence["corpus_sha256"] != hashlib.sha256(raw_corpus).hexdigest():
        raise ValueError("CORPUS_BYTES_MISMATCH")
    if raw_artifact is None:
        raise ValueError("ARTIFACT_BYTES_MISSING")
    if evidence["artifact_sha256"] != hashlib.sha256(raw_artifact).hexdigest():
        raise ValueError("ARTIFACT_BYTES_MISMATCH")
    for key in ("run_id", "job_id", "run_attempt"):
        value = evidence[key]
        if type(value) is not int or value <= 0:
            raise ValueError(key.upper() + "_INVALID")
    for key in ("method_id", "tool_name", "tool_version"):
        value = evidence[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(key.upper() + "_INVALID")


def evaluate(evidence: dict, raw_corpus: bytes, raw_artifact: Optional[bytes] = None) -> dict:
    checked_identity(evidence, raw_corpus, raw_artifact)
    try:
        corpus = json.loads(raw_corpus)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("CORPUS_JSON_INVALID") from exc
    if not isinstance(corpus, dict) or corpus.get("schema") != "mip2.method-regression-corpus.v1":
        raise ValueError("CORPUS_SCHEMA_INVALID")
    cases = corpus.get("cases")
    if not isinstance(cases, list):
        raise ValueError("CORPUS_CASES_INVALID")
    expected = {}
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("CORPUS_CASE_INVALID")
        if case.get("family") != evidence["method_id"]:
            continue
        key = case.get("id")
        if not isinstance(key, str) or not key or key in expected:
            raise ValueError("CORPUS_CASE_ID_INVALID")
        if case.get("kind") not in ("positive", "negative"):
            raise ValueError("CORPUS_CASE_LABEL_INVALID")
        expected[key] = case["kind"]
    if not expected:
        raise ValueError("METHOD_NOT_PRESENT_IN_CORPUS")
    observations = evidence["observations"]
    if not isinstance(observations, list):
        raise ValueError("OBSERVATION_ROWS_INVALID")
    observed = {}
    total_runtime_ms = 0.0
    fingerprints = set()
    for row in observations:
        if not isinstance(row, dict):
            raise ValueError("OBSERVATION_ROW_INVALID")
        case_id = row.get("case_id")
        if case_id not in expected or case_id in observed:
            raise ValueError("UNKNOWN_OR_DUPLICATE_CASE_ID")
        detected = row.get("detected")
        runtime = row.get("runtime_ms")
        if type(detected) is not bool:
            raise ValueError("DETECTION_BOOLEAN_REQUIRED")
        if type(runtime) not in (int, float) or not 0 <= runtime < float("inf"):
            raise ValueError("RUNTIME_MS_INVALID")
        signatures = row.get("fingerprints")
        if not isinstance(signatures, list) or any(
            not isinstance(sig, str) or not SHA256.fullmatch(sig) for sig in signatures
        ):
            raise ValueError("FINGERPRINTS_INVALID")
        if not detected and signatures:
            raise ValueError("FINDING_WITHOUT_DETECTION")
        if len(signatures) != len(set(signatures)):
            raise ValueError("DUPLICATE_FINDING_IN_CASE")
        observed[case_id] = detected
        total_runtime_ms += runtime
        fingerprints.update(signatures)
    missing = sorted(set(expected) - set(observed))
    positives = sum(v == "positive" for v in expected.values())
    negatives = sum(v == "negative" for v in expected.values())
    result = {"schema": "mip2.method-effectiveness.v1", "repository": evidence["repository"],
              "source_sha": evidence["source_sha"], "method_id": evidence["method_id"],
              "tool_name": evidence["tool_name"], "tool_version": evidence["tool_version"],
              "run_id": evidence["run_id"], "run_attempt": evidence["run_attempt"],
              "job_id": evidence["job_id"], "artifact_sha256": evidence["artifact_sha256"],
              "corpus_sha256": evidence["corpus_sha256"],
              "expected_cases": len(expected), "observed_cases": len(observed),
              "positive_controls": positives, "negative_controls": negatives,
              "missing_cases": missing, "unique_fingerprints": len(fingerprints),
              "runtime_ms": round(total_runtime_ms, 3),
              "merge_authorized": False, "root_closure_credited": False,
              "maturity_promotion": "NOT_ATTESTED"}
    if missing or not positives or not negatives:
        result.update({"state": "INSUFFICIENT_EVIDENCE", "confusion": None,
                       "recall_wilson95": None})
        return result
    tp = sum(expected[k] == "positive" and v for k, v in observed.items())
    fn = sum(expected[k] == "positive" and not v for k, v in observed.items())
    fp = sum(expected[k] == "negative" and v for k, v in observed.items())
    tn = sum(expected[k] == "negative" and not v for k, v in observed.items())
    result.update({"state": "CORPUS_MEASURED_NOT_QUALIFIED",
                   "confusion": metrics(tp, fp, fn, tn),
                   "recall_wilson95": wilson(tp, tp + fn)})
    return result


def comparable_delta(before: dict, after: dict) -> dict:
    keys = ("repository", "source_sha", "method_id", "corpus_sha256",
            "expected_cases", "positive_controls", "negative_controls")
    comparable = (all(before.get(k) == after.get(k) for k in keys) and
                  before.get("state") == after.get("state") == "CORPUS_MEASURED_NOT_QUALIFIED")
    if not comparable:
        return {"comparable": False, "delta_recall_pp": None,
                "delta_precision_pp": None, "reason": "SOURCE_OR_CORPUS_MISMATCH"}
    a, b = before["confusion"], after["confusion"]
    return {"comparable": True,
            "delta_recall_pp": ((b["recall"] - a["recall"]) * 100
                                if b["recall"] is not None and a["recall"] is not None else None),
            "delta_precision_pp": ((b["precision"] - a["precision"]) * 100
                                   if b["precision"] is not None and a["precision"] is not None else None),
            "merge_authorized": False}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--observations", type=Path, required=True)
    p.add_argument("--artifact", type=Path, required=True,
                   help="actual native scanner artifact bytes; path is independently supplied")
    p.add_argument("--corpus", type=Path, default=Path(__file__).with_name("method_regression_corpus.json"))
    p.add_argument("--output", type=Path)
    args = p.parse_args(argv)
    try:
        value = evaluate(json.loads(args.observations.read_bytes()),
                         args.corpus.read_bytes(), args.artifact.read_bytes())
    except (OSError, UnicodeDecodeError, ValueError, TypeError) as exc:
        value = {"schema": "mip2.method-effectiveness.v1", "state": "INVALID",
                 "reason": str(exc), "merge_authorized": False, "root_closure_credited": False}
    output = json.dumps(value, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0 if value["state"] == "CORPUS_MEASURED_NOT_QUALIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
