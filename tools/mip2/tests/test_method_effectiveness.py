"""Source-bound method effectiveness: complete labels and strict non-promotion."""
import hashlib
import json
import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from method_effectiveness import comparable_delta, evaluate, main

CORPUS = (HERE / "method_regression_corpus.json").read_bytes()
FINGERPRINT = "f" * 64


def fixture():
    cases = [x["id"] for x in json.loads(CORPUS)["cases"] if x["family"] == "sast"]
    assert len(cases) == 2
    return {
        "schema": "mip2.method-observations.v1",
        "repository": "GBOGEB/ABACUS", "source_sha": "a" * 40,
        "method_id": "sast", "tool_name": "Bandit", "tool_version": "1.9.4",
        "config_sha256": "b" * 64, "corpus_sha256": hashlib.sha256(CORPUS).hexdigest(),
        "artifact_sha256": "c" * 64, "run_id": 123, "run_attempt": 1, "job_id": 456,
        "observations": [
            {"case_id": cases[0], "detected": True, "runtime_ms": 9.0,
             "fingerprints": [FINGERPRINT]},
            {"case_id": cases[1], "detected": False, "runtime_ms": 3.0,
             "fingerprints": []},
        ],
    }


def test_complete_scanner_confusion_is_corpus_only():
    result = evaluate(fixture(), CORPUS)
    assert result["state"] == "CORPUS_MEASURED_NOT_QUALIFIED"
    assert result["confusion"]["tp"] == 1 and result["confusion"]["tn"] == 1
    assert result["confusion"]["recall"] == 1.0
    assert result["runtime_ms"] == 12.0
    assert result["unique_fingerprints"] == 1
    assert result["root_closure_credited"] is False
    assert result["merge_authorized"] is False
    assert result["maturity_promotion"] == "NOT_ATTESTED"
    assert 0 < result["recall_wilson95"][0] < 1


def test_missing_case_is_unknown_not_false_negative():
    e = fixture()
    e["observations"].pop()
    result = evaluate(e, CORPUS)
    assert result["state"] == "INSUFFICIENT_EVIDENCE"
    assert result["confusion"] is None
    assert len(result["missing_cases"]) == 1


@pytest.mark.parametrize("field,bad,error", [
    ("source_sha", "abc", "SOURCE_SHA_INVALID"),
    ("config_sha256", "abc", "CONFIG_SHA256_INVALID"),
    ("corpus_sha256", "f" * 64, "CORPUS_BYTES_MISMATCH"),
    ("run_id", 0, "RUN_ID_INVALID"),
    ("run_attempt", False, "RUN_ATTEMPT_INVALID"),
    ("repository", "forged/owner", "REPOSITORY_NOT_IN_FEDERATION_SCOPE"),
])
def test_invalid_identity_rejected(field, bad, error):
    e = fixture()
    e[field] = bad
    with pytest.raises(ValueError, match=error):
        evaluate(e, CORPUS)


def test_duplicate_occurrence_is_rejected():
    e = fixture()
    e["observations"].append(dict(e["observations"][0]))
    with pytest.raises(ValueError, match="UNKNOWN_OR_DUPLICATE_CASE_ID"):
        evaluate(e, CORPUS)


def test_unknown_case_id_rejected():
    e = fixture()
    e["observations"][0]["case_id"] = "UNKNOWN"
    with pytest.raises(ValueError, match="UNKNOWN_OR_DUPLICATE_CASE_ID"):
        evaluate(e, CORPUS)


def test_invalid_runtimes_are_rejected():
    for bad in (True, -1, float("nan"), float("inf")):
        e = fixture()
        e["observations"][0]["runtime_ms"] = bad
        with pytest.raises(ValueError, match="RUNTIME_MS_INVALID"):
            evaluate(e, CORPUS)


def test_false_detection_cannot_claim_empty_fingerprint_set():
    e = fixture()
    e["observations"][1]["fingerprints"] = [FINGERPRINT]
    with pytest.raises(ValueError, match="FINDING_WITHOUT_DETECTION"):
        evaluate(e, CORPUS)


def test_fingerprint_duplicate_inside_case_rejected():
    e = fixture()
    e["observations"][0]["fingerprints"] = [FINGERPRINT, FINGERPRINT]
    with pytest.raises(ValueError, match="DUPLICATE_FINDING_IN_CASE"):
        evaluate(e, CORPUS)


def test_paired_method_improvement_never_credits_root_closure():
    before_e = fixture()
    before_e["observations"][0]["detected"] = False
    before_e["observations"][0]["fingerprints"] = []
    before = evaluate(before_e, CORPUS)
    after = evaluate(fixture(), CORPUS)
    delta = comparable_delta(before, after)
    assert delta["comparable"] is True
    assert delta["delta_recall_pp"] == 100
    assert delta["delta_precision_pp"] is None
    assert delta["merge_authorized"] is False


def test_changed_source_never_has_matched_delta():
    before = evaluate(fixture(), CORPUS)
    after = dict(before)
    after["source_sha"] = "b" * 40
    assert comparable_delta(before, after)["delta_recall_pp"] is None


def test_runtime_family_without_negative_controls_remains_unknown():
    e = fixture()
    e["method_id"] = "runtime"
    e["observations"] = [
        {"case_id": "RUNTIME_REPRODUCER", "detected": True,
         "runtime_ms": 2.0, "fingerprints": [FINGERPRINT]}]
    result = evaluate(e, CORPUS)
    assert result["state"] == "INSUFFICIENT_EVIDENCE"
    assert result["confusion"] is None


def test_cli_missing_receipt_fails_closed(tmp_path):
    out = tmp_path / "result.json"
    code = main(["--observations", str(tmp_path / "missing.json"), "--output", str(out)])
    assert code == 2
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["state"] == "INVALID"
    assert receipt["merge_authorized"] is False
