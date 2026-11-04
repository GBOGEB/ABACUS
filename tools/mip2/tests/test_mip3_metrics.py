"""MIP3 positive/negative method telemetry and promotion controls."""

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mip3_metrics import fingerprint, metrics, promotion, summarize, wilson


def test_labeled_detection():
    x = metrics(3, 1, 2, 4)
    assert x["precision"] == 0.75
    assert x["recall"] == 0.6
    assert metrics(0, 0, 0)["precision"] is None


def test_invalid_detection_counts_fail_closed():
    with pytest.raises(ValueError):
        metrics(-1, 0, 0)


def test_wilson_and_unknown():
    assert wilson(4, 4)[0] < 1
    assert wilson(0, 0) is None


def test_fingerprint_stability_and_distinct_roots():
    a = fingerprint("ABACUS", "sast", "B602", "src/x.py", "shell")
    assert a == fingerprint("ABACUS", "sast", "B602", "src/x.py", "shell")
    assert a != fingerprint("CODEX", "sast", "B602", "src/x.py", "shell")


def test_pareto_does_not_claim_pca():
    s = summarize(
        [
            {"family": "sast", "duration_s": 2},
            {"family": "sast", "duration_s": 4},
            {"family": "format", "duration_s": 1},
        ]
    )
    assert s["pareto"][0] == ("sast", 2)
    assert s["runtime_median_s"] == 2
    assert s["pca_ready"] is False


def test_false_green_rejected():
    good = {
        "status": "PASS",
        "phase": "postflight",
        "head_sha": "abc",
        "junit": {"tests": 4, "failures": 0, "errors": 0, "skipped": 0},
        "local_flight": {"sha_matches": True},
    }
    assert promotion(good)["eligible_for_method_review"]
    for change in (
        {"status": "HOLD"},
        {"head_sha": None},
        {"junit": {"tests": 4, "failures": 1, "errors": 0, "skipped": 0}},
        {"local_flight": {"sha_matches": False}},
    ):
        bad = dict(good, **change)
        assert not promotion(bad)["eligible_for_method_review"]
    assert promotion(good)["merge_admitted"] is False
