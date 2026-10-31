"""DMAIC/MIP pulse clocks, stability and forecast scoring without false inference."""
from __future__ import annotations

from collections import Counter

from .core import digest, require


def analyze(pulses):
    require(isinstance(pulses, list) and len(pulses) >= 2,
            "need at least two ordered pulse snapshots")
    clocks = [p.get("pulse") for p in pulses]
    require(all(type(n) is int and n >= 0 for n in clocks) and
            clocks == sorted(set(clocks)), "nonmonotone or repeated pulse clock")
    contracts = [p["projection"]["source_contract_sha256"] for p in pulses]
    require(len(set(contracts)) == 1, "incomparable acceptance contract revisions")
    rows = []
    transitions = Counter()
    previous = None
    for p in pulses:
        projection = p["projection"]
        require(projection.get("admission") == "HOLD", "unreviewed promotion in pulse")
        indexed = {o["id"]: o["evidence_state"] for o in projection["obligations"]}
        require(len(indexed) == len(projection["obligations"]), "reused requirement ID")
        if previous:
            require(set(indexed) == set(previous), "unpaired obligation denominator")
            delta = sum(indexed[k] != previous[k] for k in indexed)
            for k in sorted(indexed):
                transitions[(previous[k], indexed[k])] += 1
            unchanged = len(indexed) - delta
            status_stability = unchanged / len(indexed) if indexed else None
            regressions = sum(previous[k] == "OBSERVED" and indexed[k] != "OBSERVED"
                              for k in indexed)
        else:
            delta, unchanged, status_stability, regressions = None, None, None, 0
        observed = sum(v == "OBSERVED" for v in indexed.values())
        rows.append({
            "pulse": p["pulse"],
            "obligations": len(indexed),
            "observed_evidence": observed,
            "observed_fraction": observed / len(indexed) if indexed else None,
            "admitted": 0,
            "state_changes_from_previous": delta,
            "unchanged_from_previous": unchanged,
            "descriptive_status_stability": status_stability,
            "reverse_regressions": regressions,
            "scope": p.get("evidence_class", "LOCAL_PROJECTION_ONLY"),
            "graph_hash": p.get("graph_hash"),
            "dependency_hash": p.get("dependency_hash"),
            "source_context_hash": projection["source_contexts_sha256"],
        })
        previous = indexed
    deps = [r["dependency_hash"] for r in rows]
    contexts = [r["source_context_hash"] for r in rows]
    # No formal CI, PCA, convergence proof or independence from <=3 coupled pulses.
    return {
        "schema": "codepurple.acceptance.dmaic_mip.v1",
        "wave_clock": "ordered local pulse index",
        "pulses": rows,
        "transition_counts": [
            {"from": a, "to": b, "count": n}
            for (a, b), n in sorted(transitions.items())
        ],
        "metrics": {
            "pulses_measured": len(rows),
            "final_evidence_observed": rows[-1]["observed_evidence"],
            "net_observed_gain": rows[-1]["observed_evidence"] - rows[0]["observed_evidence"],
            "reverse_regressions": sum(r["reverse_regressions"] for r in rows),
            "dependency_edges_stable": all(d == deps[0] for d in deps),
            "context_identity_stable": all(x == contexts[0] for x in contexts),
            "independent_trial_denominator": None,
            "formal_convergence": None,
            "qualified_pca_result": None,
            "main_coverage_delta": None,
            "causal_roots_closed": None,
        },
        "interpretation": "DESCRIPTIVE_LOCAL_WAVES_NOT_INDEPENDENT_REMOTE_RUNS",
        "dmaic": {
            "define": "source-bound acceptance debts and immutable authorities",
            "measure": "matched obligation and exact-head provenance counts",
            "analyze": "transition matrix, dependency reach, reversals, staleness",
            "improve": "negative tests, repo-disjoint source-owner leases",
            "control": "deterministic SHA receipts and independent main recertification",
        },
        "mip": "Measure -> Improve -> Prove (local convention; not remote dispatch)",
        "authority_transfer": False,
    }


def score_pre_registered_forecast(prediction, actual):
    require(prediction.get("schema") == "codepurple.acceptance.forecast.v1",
            "invalid forecast pre-registration")
    require(prediction.get("target_clock") == actual.get("pulse"),
            "forecast target clock mismatch")
    require(prediction.get("prediction_clock") < actual["pulse"],
            "prediction must precede outcome")
    expected_tests = prediction.get("predict_tests_min")
    achieved_tests = actual.get("tests_passed")
    require(type(expected_tests) is int and expected_tests > 0 and
            type(achieved_tests) is int and achieved_tests >= 0,
            "invalid forecast test denominator")
    coverage = actual.get("coverage_fraction")
    require(type(coverage) in (float, int) and 0 <= coverage <= 1,
            "coverage is missing or malformed")
    admission = actual.get("unauthorized_admissions")
    require(type(admission) is int and admission >= 0,
            "unverifiable admission count")
    return {
        "schema": "codepurple.acceptance.forecast_score.v1",
        "prediction_sha256": digest(prediction),
        "observed_pulse": actual["pulse"],
        "tests_min_met": achieved_tests >= expected_tests,
        "coverage_target_met": coverage >= prediction["predict_coverage_min_fraction"],
        "false_admission_guard_met": admission == prediction["predict_unauthorized_admissions"],
        "test_signed_error_vs_minimum": achieved_tests - expected_tests,
        "coverage_signed_error_vs_target": round(
            coverage - prediction["predict_coverage_min_fraction"], 6),
        "forecast_is_statistical": False,
    }
