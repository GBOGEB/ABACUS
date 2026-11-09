"""Lane-B wave 10: MIP3 metrics and MIP2 method-effectiveness scorer."""

import copy
import hashlib
import json
import sys

import pytest

from ._l2_loader import load

m3 = load("tools/mip2/mip3_metrics.py")
me = load("tools/mip2/method_effectiveness.py", deps={"mip3_metrics": m3})

SHA_A = "a" * 40
H1, H2 = "1" * 64, "2" * 64
METHOD = "secrets"


def _corpus(cases=None):
    if cases is None:
        cases = [
            {"id": "p1", "family": METHOD, "kind": "positive"},
            {"id": "p2", "family": METHOD, "kind": "positive"},
            {"id": "n1", "family": METHOD, "kind": "negative"},
            {"id": "n2", "family": METHOD, "kind": "negative"},
            {"id": "other", "family": "lint", "kind": "positive"},
        ]
    return json.dumps(
        {"schema": "mip2.method-regression-corpus.v1", "cases": cases}
    ).encode()


ARTIFACT = b"native scanner output"


def _rows():
    return [
        {"case_id": "p1", "detected": True, "runtime_ms": 1, "fingerprints": [H1]},
        {"case_id": "p2", "detected": False, "runtime_ms": 2.5, "fingerprints": []},
        {"case_id": "n1", "detected": True, "runtime_ms": 0, "fingerprints": [H2]},
        {"case_id": "n2", "detected": False, "runtime_ms": 3, "fingerprints": []},
    ]


def _evidence(raw_corpus=None, raw_artifact=ARTIFACT, **overrides):
    raw_corpus = _corpus() if raw_corpus is None else raw_corpus
    e = {
        "schema": me.SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "source_sha": SHA_A,
        "method_id": METHOD,
        "tool_name": "gitleaks",
        "tool_version": "8.0.0",
        "config_sha256": "c" * 64,
        "corpus_sha256": hashlib.sha256(raw_corpus).hexdigest(),
        "artifact_sha256": hashlib.sha256(raw_artifact).hexdigest(),
        "run_id": 10,
        "run_attempt": 1,
        "job_id": 20,
        "observations": _rows(),
    }
    e.update(overrides)
    return e


# ---------------------------------------------------------------- mip3_metrics


def test_fingerprint_is_stable_24_hex():
    a = m3.fingerprint("r", "f", "rule", "loc", "sig")
    assert a == m3.fingerprint("r", "f", "rule", "loc", "sig")
    assert len(a) == 24 and int(a, 16) >= 0
    assert a != m3.fingerprint("r", "f", "rule", "loc", "sig2")


def test_metrics_values_and_none_denominators():
    full = m3.metrics(3, 1, 1, 5)
    assert full["precision"] == 0.75 and full["recall"] == 0.75
    assert full["specificity"] == 5 / 6
    empty = m3.metrics(0, 0, 0)
    assert empty["precision"] is None and empty["recall"] is None
    assert empty["specificity"] is None and empty["tn"] == 0


@pytest.mark.parametrize("args", [(-1, 0, 0), (1.0, 0, 0), (0, 0, 0, -2)])
def test_metrics_rejects_bad_counts(args):
    with pytest.raises(ValueError, match="nonnegative integers"):
        m3.metrics(*args)


@pytest.mark.parametrize("success,total", [(0, 0), (-1, 5), (6, 5)])
def test_wilson_invalid_returns_none(success, total):
    assert m3.wilson(success, total) is None


def test_wilson_bounds():
    lo, hi = m3.wilson(5, 10)
    assert 0 < lo < 0.5 < hi < 1
    assert m3.wilson(0, 10)[0] == pytest.approx(0, abs=1e-12)
    assert m3.wilson(10, 10)[1] == pytest.approx(1)


def test_summarize_with_and_without_timings():
    obs = [
        {"family": "b", "duration_s": 2},
        {"family": "a", "duration_s": 1.0},
        {"family": "b", "duration_s": -1},
        {"family": "a", "duration_s": "x"},
        {"family": "c"},
    ]
    s = m3.summarize(obs)
    assert s["n"] == 5
    assert s["pareto"] == [("a", 2), ("b", 2), ("c", 1)]
    assert s["runtime_median_s"] == 1.5 and s["runtime_p95_s"] == 2
    assert s["pca_ready"] is False
    none = m3.summarize([{"family": "x"}])
    assert none["runtime_median_s"] is None and none["runtime_p95_s"] is None


def _receipt():
    return {
        "status": "PASS",
        "phase": "postflight",
        "head_sha": SHA_A,
        "junit": {"tests": 4, "failures": 0, "errors": 0, "skipped": 0},
        "local_flight": {"sha_matches": True},
    }


def test_promotion_eligible():
    out = m3.promotion(_receipt())
    assert out == {
        "eligible_for_method_review": True,
        "merge_admitted": False,
        "reasons": [],
    }


def test_promotion_all_reasons_on_empty_receipt():
    out = m3.promotion({})
    assert out["eligible_for_method_review"] is False
    assert out["reasons"] == [
        "postflight_pass",
        "postflight_phase",
        "head_sha",
        "minimum_tests",
        "zero_failures_errors_skips",
        "exact_sha_match",
    ]


def test_promotion_minimum_tests_threshold():
    out = m3.promotion(_receipt(), minimum_tests=5)
    assert out["reasons"] == ["minimum_tests"]


# ---------------------------------------------------------- checked_identity


def test_evaluate_measures_confusion():
    out = me.evaluate(_evidence(), _corpus(), ARTIFACT)
    assert out["state"] == "CORPUS_MEASURED_NOT_QUALIFIED"
    assert out["expected_cases"] == 4 and out["observed_cases"] == 4
    assert out["positive_controls"] == 2 and out["negative_controls"] == 2
    assert out["unique_fingerprints"] == 2 and out["runtime_ms"] == 6.5
    c = out["confusion"]
    assert (c["tp"], c["fp"], c["fn"], c["tn"]) == (1, 1, 1, 1)
    assert out["recall_wilson95"] == m3.wilson(1, 2)
    assert out["merge_authorized"] is False


@pytest.mark.parametrize(
    "mutate,match",
    [
        (lambda e: e.update(schema="x"), "OBSERVATION_SCHEMA_INVALID"),
        (lambda e: e.pop("run_id"), "OBSERVATION_IDENTITY_MISSING"),
        (lambda e: e.update(job_id=None), "OBSERVATION_IDENTITY_MISSING"),
        (lambda e: e.update(repository="x/y"), "REPOSITORY_NOT_IN_FEDERATION"),
        (lambda e: e.update(source_sha=5), "SOURCE_SHA_INVALID"),
        (lambda e: e.update(source_sha="A" * 40), "SOURCE_SHA_INVALID"),
        (lambda e: e.update(config_sha256=1), "CONFIG_SHA256_INVALID"),
        (lambda e: e.update(artifact_sha256="z"), "ARTIFACT_SHA256_INVALID"),
        (lambda e: e.update(corpus_sha256="d" * 64), "CORPUS_BYTES_MISMATCH"),
        (lambda e: e.update(artifact_sha256="d" * 64), "ARTIFACT_BYTES_MISMATCH"),
        (lambda e: e.update(run_id=True), "RUN_ID_INVALID"),
        (lambda e: e.update(job_id=0), "JOB_ID_INVALID"),
        (lambda e: e.update(method_id=3), "METHOD_ID_INVALID"),
        (lambda e: e.update(tool_version="  "), "TOOL_VERSION_INVALID"),
    ],
)
def test_checked_identity_rejections(mutate, match):
    e = _evidence()
    mutate(e)
    with pytest.raises(ValueError, match=match):
        me.checked_identity(e, _corpus(), ARTIFACT)


def test_checked_identity_non_dict_and_missing_artifact():
    with pytest.raises(ValueError, match="OBSERVATION_SCHEMA_INVALID"):
        me.checked_identity([], b"", ARTIFACT)
    with pytest.raises(ValueError, match="ARTIFACT_BYTES_MISSING"):
        me.checked_identity(_evidence(), _corpus(), None)


# ------------------------------------------------------------------ evaluate


def _eval_with_corpus(raw):
    return me.evaluate(_evidence(raw_corpus=raw), raw, ARTIFACT)


@pytest.mark.parametrize(
    "raw,match",
    [
        (b"{bad", "CORPUS_JSON_INVALID"),
        (b"\xff\xfe\x00", "CORPUS_JSON_INVALID"),
        (b"[]", "CORPUS_SCHEMA_INVALID"),
        (json.dumps({"schema": "x"}).encode(), "CORPUS_SCHEMA_INVALID"),
        (
            json.dumps({"schema": "mip2.method-regression-corpus.v1"}).encode(),
            "CORPUS_CASES_INVALID",
        ),
        (_corpus([1]), "CORPUS_CASE_INVALID"),
        (_corpus([{"family": METHOD, "id": ""}]), "CORPUS_CASE_ID_INVALID"),
        (
            _corpus(
                [
                    {"family": METHOD, "id": "a", "kind": "positive"},
                    {"family": METHOD, "id": "a", "kind": "positive"},
                ]
            ),
            "CORPUS_CASE_ID_INVALID",
        ),
        (_corpus([{"family": METHOD, "id": "a", "kind": "x"}]), "LABEL_INVALID"),
        (_corpus([{"family": "lint", "id": "a"}]), "METHOD_NOT_PRESENT"),
    ],
)
def test_evaluate_corpus_rejections(raw, match):
    with pytest.raises(ValueError, match=match):
        _eval_with_corpus(raw)


def _with_rows(rows):
    return me.evaluate(_evidence(observations=rows), _corpus(), ARTIFACT)


def _row(**overrides):
    r = {"case_id": "p1", "detected": True, "runtime_ms": 1, "fingerprints": [H1]}
    r.update(overrides)
    return r


@pytest.mark.parametrize(
    "rows,match",
    [
        ({}, "OBSERVATION_ROWS_INVALID"),
        ([1], "OBSERVATION_ROW_INVALID"),
        ([_row(case_id="zzz")], "UNKNOWN_OR_DUPLICATE"),
        ([_row(), _row()], "UNKNOWN_OR_DUPLICATE"),
        ([_row(detected=1)], "DETECTION_BOOLEAN_REQUIRED"),
        ([_row(runtime_ms="1")], "RUNTIME_MS_INVALID"),
        ([_row(runtime_ms=-1)], "RUNTIME_MS_INVALID"),
        ([_row(runtime_ms=float("inf"))], "RUNTIME_MS_INVALID"),
        ([_row(fingerprints="x")], "FINGERPRINTS_INVALID"),
        ([_row(fingerprints=[1])], "FINGERPRINTS_INVALID"),
        ([_row(fingerprints=["g" * 64])], "FINGERPRINTS_INVALID"),
        ([_row(detected=False)], "FINDING_WITHOUT_DETECTION"),
        ([_row(fingerprints=[H1, H1])], "DUPLICATE_FINDING_IN_CASE"),
    ],
)
def test_evaluate_row_rejections(rows, match):
    with pytest.raises(ValueError, match=match):
        _with_rows(rows)


def test_evaluate_missing_cases_is_insufficient():
    out = _with_rows(_rows()[:3])
    assert out["state"] == "INSUFFICIENT_EVIDENCE"
    assert out["missing_cases"] == ["n2"]
    assert out["confusion"] is None and out["recall_wilson95"] is None


def test_evaluate_without_negatives_is_insufficient():
    raw = _corpus([{"family": METHOD, "id": "p1", "kind": "positive"}])
    e = _evidence(raw_corpus=raw, observations=[_row()])
    out = me.evaluate(e, raw, ARTIFACT)
    assert out["state"] == "INSUFFICIENT_EVIDENCE" and out["missing_cases"] == []
    assert out["negative_controls"] == 0


# ---------------------------------------------------------- comparable_delta


def _measured():
    return me.evaluate(_evidence(), _corpus(), ARTIFACT)


def test_comparable_delta_measures_change():
    before = _measured()
    after = copy.deepcopy(before)
    after["confusion"] = m3.metrics(2, 0, 0, 2)
    out = me.comparable_delta(before, after)
    assert out["comparable"] is True and out["merge_authorized"] is False
    assert out["delta_recall_pp"] == pytest.approx(50.0)
    assert out["delta_precision_pp"] == pytest.approx(50.0)


def test_comparable_delta_none_metrics():
    before = _measured()
    after = copy.deepcopy(before)
    after["confusion"] = m3.metrics(0, 0, 0, 2)
    out = me.comparable_delta(before, after)
    assert out["delta_recall_pp"] is None and out["delta_precision_pp"] is None
    out = me.comparable_delta(after, before)
    assert out["delta_recall_pp"] is None and out["delta_precision_pp"] is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(source_sha="b" * 40),
        lambda d: d.update(state="INSUFFICIENT_EVIDENCE"),
    ],
)
def test_comparable_delta_mismatch(mutate):
    before = _measured()
    after = copy.deepcopy(before)
    mutate(after)
    out = me.comparable_delta(before, after)
    assert out == {
        "comparable": False,
        "delta_recall_pp": None,
        "delta_precision_pp": None,
        "reason": "SOURCE_OR_CORPUS_MISMATCH",
    }


# ---------------------------------------------------------------------- main


def _files(tmp_path, evidence=None, corpus=None, artifact=ARTIFACT):
    corpus = _corpus() if corpus is None else corpus
    evidence = _evidence(raw_corpus=corpus) if evidence is None else evidence
    obs = tmp_path / "obs.json"
    obs.write_text(json.dumps(evidence), encoding="utf-8")
    cp = tmp_path / "corpus.json"
    cp.write_bytes(corpus)
    art = tmp_path / "artifact.bin"
    art.write_bytes(artifact)
    return [
        "--observations",
        str(obs),
        "--artifact",
        str(art),
        "--corpus",
        str(cp),
    ]


def test_main_writes_output_file(tmp_path):
    out = tmp_path / "out.json"
    rc = me.main(_files(tmp_path) + ["--output", str(out)])
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["state"] == "CORPUS_MEASURED_NOT_QUALIFIED"


def test_main_prints_insufficient(tmp_path, capsys):
    evidence = _evidence(observations=_rows()[:1])
    rc = me.main(_files(tmp_path, evidence=evidence))
    assert rc == 2
    assert json.loads(capsys.readouterr().out)["state"] == "INSUFFICIENT_EVIDENCE"


def test_main_invalid_on_missing_artifact(tmp_path, capsys):
    args = _files(tmp_path)
    args[3] = str(tmp_path / "absent.bin")
    rc = me.main(args)
    out = json.loads(capsys.readouterr().out)
    assert rc == 2 and out["state"] == "INVALID"
    assert out["root_closure_credited"] is False


def test_main_invalid_on_bad_identity_via_argv(tmp_path, monkeypatch, capsys):
    evidence = _evidence(repository="evil/repo")
    monkeypatch.setattr(sys, "argv", ["me"] + _files(tmp_path, evidence=evidence))
    assert me.main() == 2
    out = json.loads(capsys.readouterr().out)
    assert out["reason"] == "REPOSITORY_NOT_IN_FEDERATION_SCOPE"
