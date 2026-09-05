"""W53-P05N: held-out validation of LKT nominal 2K-OP HP power.

The target row (326 g/s, 814 kW) is excluded from model fitting. The predictor is
fit only to the other source-bound LKT operating-mode HP flow/power rows. This is
an internal cross-mode validation, not an independent OEM performance guarantee.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

DATA = Path(__file__).parent / "energy_exergy/rev1_7/data/operating_utility_scenarios_24_30_rev1_7.csv"
TARGET_FLOW = 326.0
TARGET_POWER = 814.0
TOLERANCE_PERCENT = 1.0


def load_rows() -> list[dict]:
    with DATA.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fit_predict(rows: list[dict], degree: int) -> dict:
    training = [r for r in rows if not (float(r["hp_flow_g_s"]) == TARGET_FLOW and float(r["hp_kwe"]) == TARGET_POWER)]
    x = np.array([float(r["hp_flow_g_s"]) for r in training], dtype=float)
    y = np.array([float(r["hp_kwe"]) for r in training], dtype=float)
    coeff = np.polyfit(x, y, degree)
    pred = float(np.polyval(coeff, TARGET_FLOW))
    fitted = np.polyval(coeff, x)
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot
    residual = pred - TARGET_POWER
    residual_pct = 100.0 * residual / TARGET_POWER
    return {
        "degree": degree,
        "training_points": len(training),
        "coefficients": [float(v) for v in coeff],
        "training_r2": r2,
        "predicted_target_kW": pred,
        "residual_kW": residual,
        "residual_percent": residual_pct,
        "within_1pct_engineering_tolerance": abs(residual_pct) <= TOLERANCE_PERCENT,
    }


def report() -> dict:
    rows = load_rows()
    linear = fit_predict(rows, 1)
    quadratic = fit_predict(rows, 2)
    cubic = fit_predict(rows, 3)
    return {
        "schema": "qps-w53-p05n-hp-heldout-validation/v1",
        "target": {
            "scenario": "30-QCELL / 30 QM design, 2K-OP",
            "flow_g_s": TARGET_FLOW,
            "reported_HP_power_kW": TARGET_POWER,
            "excluded_from_fit": True,
        },
        "training_authority": "OTHER_LKT_SOURCE_BOUND_OPERATING_MODE_ROWS_FROM_REV1_7_SSOT",
        "models": {"linear": linear, "quadratic": quadratic, "cubic_sensitivity": cubic},
        "primary_model": "linear",
        "primary_reason": "lowest_complexity_cross_mode_predictor; avoids overfitting eight training rows",
        "strict_interpretation": {
            "numeric_result": "CANDIDATE_PASS" if linear["within_1pct_engineering_tolerance"] else "FAIL_NUMERIC",
            "score_before": "1/5",
            "score_after": "1/5",
            "promotion_blocker": "CHILD_AUTHORITY_MUST_ACCEPT_CROSS_MODE_HELDOUT_PREDICTION_AS_SUFFICIENTLY_INDEPENDENT_FOR_R4",
            "important_guard": "same_bidder_mode_family_is_independent_of_target_row_but_not_independent_of_bidder_model_family",
        },
        "external_envelope_context": {
            "installed_units": 4,
            "nominal_equal_share_g_s_per_unit": 81.5,
            "derived_equivalent_frequency_Hz": 52.4,
            "max_reference": "112 g/s per unit at 72 Hz; do not linearly scale power for acceptance",
        },
    }


if __name__ == "__main__":
    print(json.dumps(report(), indent=2, sort_keys=True))
