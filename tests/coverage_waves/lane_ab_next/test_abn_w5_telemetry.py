"""Behaviour tests for tools/everred_v3/acceptance/telemetry.py.

The ``acceptance`` directory is loaded as a privately named package so the
relative ``from .core import ...`` resolves without touching sys.path.
"""

import importlib
import importlib.util
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT

ACC_DIR = REPO_ROOT / "tools" / "everred_v3" / "acceptance"
PKG = "abn_w5_acceptance_telemetry_pkg"


def _load_package(name):
    spec = importlib.util.spec_from_file_location(
        name, ACC_DIR / "__init__.py", submodule_search_locations=[str(ACC_DIR)]
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    return package


_load_package(PKG)
telemetry = importlib.import_module(PKG + ".telemetry")
core = importlib.import_module(PKG + ".core")
Invalid = core.InvalidEvidence


def _pulse(clock, states, contract="c1", context="x1", dep="d1", **extra):
    projection = {
        "source_contract_sha256": contract,
        "source_contexts_sha256": context,
        "admission": "HOLD",
        "obligations": [dict(id=k, evidence_state=v) for k, v in states.items()],
    }
    doc = dict(pulse=clock, projection=projection, graph_hash="g", dependency_hash=dep)
    doc.update(extra)
    return doc


def test_analyze_three_pulses_counts_transitions_and_regressions():
    pulses = [
        _pulse(0, {"A": "MISSING", "B": "OBSERVED"}, evidence_class="LOCAL"),
        _pulse(1, {"A": "OBSERVED", "B": "OBSERVED"}),
        _pulse(2, {"A": "OBSERVED", "B": "STALE"}, context="x2", dep="d2"),
    ]
    result = telemetry.analyze(pulses)
    rows = result["pulses"]
    assert [r["pulse"] for r in rows] == [0, 1, 2]
    assert rows[0]["state_changes_from_previous"] is None
    assert rows[0]["descriptive_status_stability"] is None
    assert rows[0]["scope"] == "LOCAL"
    assert rows[1]["scope"] == "LOCAL_PROJECTION_ONLY"
    assert rows[1]["state_changes_from_previous"] == 1
    assert rows[1]["unchanged_from_previous"] == 1
    assert rows[1]["descriptive_status_stability"] == 0.5
    assert rows[2]["reverse_regressions"] == 1
    assert rows[2]["observed_fraction"] == 0.5
    assert rows[2]["source_context_hash"] == "x2"
    metrics = result["metrics"]
    assert metrics["pulses_measured"] == 3
    assert metrics["final_evidence_observed"] == 1
    assert metrics["net_observed_gain"] == 0
    assert metrics["reverse_regressions"] == 1
    assert metrics["dependency_edges_stable"] is False
    assert metrics["context_identity_stable"] is False
    assert metrics["formal_convergence"] is None
    transitions = {
        (t["from"], t["to"]): t["count"] for t in result["transition_counts"]
    }
    assert transitions == {
        ("MISSING", "OBSERVED"): 1,
        ("OBSERVED", "OBSERVED"): 2,
        ("OBSERVED", "STALE"): 1,
    }
    assert result["authority_transfer"] is False
    assert result["interpretation"].startswith("DESCRIPTIVE")


def test_analyze_stable_identity_flags():
    result = telemetry.analyze(
        [_pulse(0, {"A": "OBSERVED"}), _pulse(3, {"A": "OBSERVED"})]
    )
    assert result["metrics"]["dependency_edges_stable"] is True
    assert result["metrics"]["context_identity_stable"] is True
    assert result["pulses"][1]["descriptive_status_stability"] == 1.0


def test_analyze_empty_obligations_yields_null_fractions():
    result = telemetry.analyze([_pulse(0, {}), _pulse(1, {})])
    for row in result["pulses"]:
        assert row["observed_fraction"] is None
        assert row["obligations"] == 0
        assert row["state_changes_from_previous"] is None
    assert result["transition_counts"] == []


@pytest.mark.parametrize(
    "pulses,message",
    [
        ("nope", "at least two"),
        ([_pulse(0, {})], "at least two"),
        ([_pulse(1, {}), _pulse(0, {})], "nonmonotone"),
        ([_pulse(0, {}), _pulse(0, {})], "nonmonotone"),
        ([_pulse(-1, {}), _pulse(0, {})], "nonmonotone"),
        ([_pulse(True, {}), _pulse(2, {})], "nonmonotone"),
        ([_pulse(0, {}), _pulse(1, {}, contract="c2")], "incomparable"),
        ([_pulse(0, {"A": "MISSING"}), _pulse(1, {"B": "MISSING"})], "unpaired"),
    ],
)
def test_analyze_rejects_invalid_series(pulses, message):
    with pytest.raises(Invalid, match=message):
        telemetry.analyze(pulses)


def test_analyze_rejects_promotion_and_reused_ids():
    promoted = _pulse(1, {"A": "OBSERVED"})
    promoted["projection"]["admission"] = "ADMITTED"
    with pytest.raises(Invalid, match="unreviewed promotion"):
        telemetry.analyze([_pulse(0, {"A": "OBSERVED"}), promoted])
    reused = _pulse(1, {"A": "OBSERVED"})
    reused["projection"]["obligations"].append(dict(id="A", evidence_state="STALE"))
    with pytest.raises(Invalid, match="reused requirement ID"):
        telemetry.analyze([_pulse(0, {"A": "OBSERVED"}), reused])


def _prediction(**extra):
    doc = dict(
        schema="codepurple.acceptance.forecast.v1",
        target_clock=3,
        prediction_clock=2,
        predict_tests_min=10,
        predict_coverage_min_fraction=0.8,
        predict_unauthorized_admissions=0,
    )
    doc.update(extra)
    return doc


def _actual(**extra):
    doc = dict(pulse=3, tests_passed=12, coverage_fraction=0.75)
    doc["unauthorized_admissions"] = 0
    doc.update(extra)
    return doc


def test_score_forecast_reports_signed_errors():
    score = telemetry.score_pre_registered_forecast(_prediction(), _actual())
    assert score["schema"] == "codepurple.acceptance.forecast_score.v1"
    assert score["prediction_sha256"] == core.digest(_prediction())
    assert score["observed_pulse"] == 3
    assert score["tests_min_met"] is True
    assert score["coverage_target_met"] is False
    assert score["false_admission_guard_met"] is True
    assert score["test_signed_error_vs_minimum"] == 2
    assert score["coverage_signed_error_vs_target"] == -0.05
    assert score["forecast_is_statistical"] is False


def test_score_forecast_integer_coverage_and_admission_miss():
    actual = _actual(coverage_fraction=1, unauthorized_admissions=2, tests_passed=0)
    score = telemetry.score_pre_registered_forecast(_prediction(), actual)
    assert score["coverage_target_met"] is True
    assert score["false_admission_guard_met"] is False
    assert score["tests_min_met"] is False


@pytest.mark.parametrize(
    "prediction,actual,message",
    [
        (_prediction(schema="x"), _actual(), "invalid forecast pre-registration"),
        (_prediction(target_clock=4), _actual(), "target clock mismatch"),
        (_prediction(prediction_clock=3), _actual(), "must precede"),
        (_prediction(predict_tests_min=0), _actual(), "test denominator"),
        (_prediction(predict_tests_min=True), _actual(), "test denominator"),
        (_prediction(), _actual(tests_passed=-1), "test denominator"),
        (_prediction(), _actual(coverage_fraction=None), "coverage is missing"),
        (_prediction(), _actual(coverage_fraction=1.5), "coverage is missing"),
        (_prediction(), _actual(unauthorized_admissions=-1), "unverifiable"),
        (_prediction(), _actual(unauthorized_admissions="0"), "unverifiable"),
    ],
)
def test_score_forecast_rejects_invalid(prediction, actual, message):
    with pytest.raises(Invalid, match=message):
        telemetry.score_pre_registered_forecast(prediction, actual)
