"""W53/P05J quantitative execution bundle.

Produces four diagnostic receipts from the merged P05I baseline:
Q1 distributed Line-B pressure metrics;
Q2 same-boundary thermal-shield enthalpy residual;
Q3 time-stepped Line-S mass+energy transient;
Q4 PCA + Bradley-Terry decision metrics.

All outputs remain diagnostic unless separately source-accepted by the child authority.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from math import exp, pi
from pathlib import Path
from statistics import mean, median

import CoolProp
import numpy as np
from CoolProp.CoolProp import PropsSI

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "qps_quantitative" / "generated" / "P05J_QUANTITATIVE_RECEIPT.json"
FLUID = "Helium"


def friction_factor(reynolds: float, rel_roughness: float) -> float:
    if reynolds < 2300:
        return 64.0 / reynolds
    return 0.25 / (np.log10(rel_roughness / 3.7 + 5.74 / reynolds**0.9) ** 2)


def segment_dp_pa(length_m: float, diameter_m: float, roughness_m: float,
                  mass_flow_kg_s: float, density: float, viscosity: float,
                  k_local: float = 0.0) -> float:
    area = pi * diameter_m**2 / 4.0
    velocity = mass_flow_kg_s / (density * area)
    re = density * velocity * diameter_m / viscosity
    f = friction_factor(re, roughness_m / diameter_m)
    q = density * velocity**2 / 2.0
    return (f * length_m / diameter_m + k_local) * q


def q1_vlp() -> dict:
    n = 30
    length = 160.0
    d = 0.16276
    rough = 1e-5
    total_flow = 0.050
    boundary = 27.0
    local_limit = 31.0
    T = 4.0
    P = boundary * 100.0
    rho = PropsSI("D", "T", T, "P", P, FLUID)
    mu = PropsSI("V", "T", T, "P", P, FLUID)
    seg_len = length / n
    local_flow = total_flow / n

    cases = []
    for k_total in (0.0, 30.0, 50.0, 100.0):
        cumulative_dp_pa = 0.0
        rows = []
        for idx in range(1, n + 1):
            cumulative_flow = local_flow * idx
            seg_k = k_total / n
            dp = segment_dp_pa(seg_len, d, rough, cumulative_flow, rho, mu, seg_k)
            cumulative_dp_pa += dp
            p_local = boundary + cumulative_dp_pa / 100.0
            rows.append({
                "qcell_index_from_far_end": idx,
                "cumulative_flow_g_s": cumulative_flow * 1000.0,
                "segment_dp_mbar": dp / 100.0,
                "cumulative_dp_mbar": cumulative_dp_pa / 100.0,
                "predicted_pressure_mbar_abs": p_local,
                "margin_to_31_mbar": local_limit - p_local,
            })
        dps = [r["cumulative_dp_mbar"] for r in rows]
        margins = [r["margin_to_31_mbar"] for r in rows]
        cases.append({
            "K_total": k_total,
            "max_dp_mbar": max(dps),
            "median_dp_mbar": median(dps),
            "p95_dp_mbar": float(np.percentile(dps, 95)),
            "minimum_margin_mbar": min(margins),
            "controlling_qcell_index_from_far_end": rows[-1]["qcell_index_from_far_end"],
            "rows": rows,
        })
    return {
        "classification": "DIAGNOSTIC_SOURCE_BOUND_DIAMETER_BOUNDED_FLOW_DISTRIBUTION",
        "provider": f"CoolProp {CoolProp.__version__}",
        "density_kg_m3": rho,
        "viscosity_Pa_s": mu,
        "geometry": {"DN": "DN150", "ID_m": d, "length_m": length, "qcell_count": n},
        "total_flow_g_s": total_flow * 1000.0,
        "cases": cases,
    }


def q2_ts_residual() -> dict:
    # Contract/current design-flow boundary: D~14 bar/40 K -> E~13 bar/60 K,
    # mdot~77 g/s, Q_TS=8200 W. Normal-fluid state; appropriate for CoolProp.
    pin = 14.0e5
    tin = 40.0
    pout = 13.0e5
    tout = 60.0
    mdot = 0.077
    source_q = 8200.0
    hin = PropsSI("H", "T", tin, "P", pin, FLUID)
    hout = PropsSI("H", "T", tout, "P", pout, FLUID)
    predicted_q = mdot * (hout - hin)
    residual = predicted_q - source_q
    rel = residual / source_q * 100.0
    predicted_mdot = source_q / (hout - hin)
    mdot_residual = predicted_mdot - mdot
    return {
        "classification": "STRICT_CANDIDATE_NORMAL_FLUID_SAME_BOUNDARY",
        "provider": f"CoolProp {CoolProp.__version__}",
        "state": {"D": {"P_bara": 14.0, "T_K": 40.0}, "E": {"P_bara": 13.0, "T_K": 60.0}},
        "source_mass_flow_g_s": 77.0,
        "source_duty_W": source_q,
        "h_in_J_kg": hin,
        "h_out_J_kg": hout,
        "predicted_duty_W": predicted_q,
        "absolute_residual_W": residual,
        "relative_residual_percent": rel,
        "predicted_mass_flow_g_s_for_8200W": predicted_mdot * 1000.0,
        "mass_flow_residual_g_s": mdot_residual * 1000.0,
        "independent_low_temperature_reference_required": False,
        "child_acceptance_required": True,
    }


@dataclass
class LineSCase:
    name: str
    volume_m3: float
    m_in_g_s: float
    m_rec_g_s: float
    m_hp_g_s: float
    hp_start_s: float = 0.0
    duration_s: float = 600.0


def q3_line_s() -> dict:
    # Diagnostic well-mixed gas-volume transient. Source-bound replacement remains required.
    R = PropsSI("GAS_CONSTANT", FLUID) / PropsSI("MOLAR_MASS", FLUID)
    dt = 1.0
    p0 = 1.05e5
    t0 = 300.0
    cases = [
        LineSCase("balanced_100_100", 120.0, 100.0, 100.0, 0.0),
        LineSCase("pre_HP_112_100_delay180s", 120.0, 112.0, 100.0, 100.0, 180.0),
        LineSCase("peak_200_100_noHP", 120.0, 200.0, 100.0, 0.0),
        LineSCase("peak_200_100_HP100_delay60s", 120.0, 200.0, 100.0, 100.0, 60.0),
    ]
    out = []
    for case in cases:
        m = p0 * case.volume_m3 / (R * t0)
        cv = PropsSI("CVMASS", "T", t0, "P", p0, FLUID)
        u = m * cv * t0
        p = p0
        T = t0
        max_p = p
        max_t = T
        thresholds = {0.1: None, 0.5: None, 1.0: None}
        recovered = 0.0
        released = 0.0
        trace = []
        for step in range(int(case.duration_s / dt) + 1):
            time_s = step * dt
            hp = case.m_hp_g_s if time_s >= case.hp_start_s else 0.0
            mi = case.m_in_g_s / 1000.0
            mo = (case.m_rec_g_s + hp) / 1000.0
            hi = PropsSI("H", "T", 300.0, "P", max(p, 1e4), FLUID)
            ho = PropsSI("H", "T", T, "P", max(p, 1e4), FLUID)
            dm = (mi - mo) * dt
            u += (mi * hi - mo * ho) * dt
            m = max(m + dm, 1e-6)
            # fixed-point update of T using local Cv.
            for _ in range(4):
                cv = PropsSI("CVMASS", "T", max(T, 2.0), "P", max(p, 1e4), FLUID)
                T = max(u / (m * cv), 2.0)
                p = m * R * T / case.volume_m3
            released += mi * dt
            recovered += mo * dt
            max_p = max(max_p, p)
            max_t = max(max_t, T)
            dp_bar = (p - p0) / 1e5
            for thr in thresholds:
                if thresholds[thr] is None and dp_bar >= thr:
                    thresholds[thr] = time_s
            if step % 30 == 0:
                trace.append({"t_s": time_s, "P_bara": p / 1e5, "T_K": T, "mass_kg": m})
        out.append({
            "case": case.name,
            "input": asdict(case),
            "max_P_bara": max_p / 1e5,
            "max_T_K": max_t,
            "time_to_plus_0p1bar_s": thresholds[0.1],
            "time_to_plus_0p5bar_s": thresholds[0.5],
            "time_to_plus_1bar_s": thresholds[1.0],
            "released_kg": released,
            "recovered_kg": recovered,
            "net_inventory_change_kg": released - recovered,
            "trace_30s": trace,
        })
    return {
        "classification": "TIME_STEPPED_DIAGNOSTIC_SOURCE_SUBSTITUTION_PENDING",
        "provider": f"CoolProp {CoolProp.__version__}",
        "model": "well_mixed_constant_volume_mass_energy_balance",
        "cases": out,
        "source_bound_inputs_still_required": ["effective_volume", "release_profile", "recovery_capacity", "HP_start_delay", "thermal_mass"],
    }


def standardize(X: np.ndarray) -> np.ndarray:
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    return (X - mu) / sd


def pca(X: np.ndarray) -> tuple[list[float], np.ndarray]:
    Z = standardize(X)
    _, s, vt = np.linalg.svd(Z, full_matrices=False)
    var = s**2
    ratio = (var / var.sum()).tolist()
    return ratio, vt


def bt_scores(candidates: dict[str, dict[str, float]]) -> dict:
    # Deterministic pairwise Bradley-Terry-style ability fit from normalized observed criteria.
    names = list(candidates)
    criteria = list(next(iter(candidates.values())))
    M = np.array([[candidates[n][c] for c in criteria] for n in names], dtype=float)
    # higher is better for all criteria after construction
    mins = M.min(axis=0)
    spans = M.max(axis=0) - mins
    spans[spans == 0] = 1.0
    N = (M - mins) / spans
    utility = N.mean(axis=1)
    wins = np.zeros((len(names), len(names)))
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            p = 1.0 / (1.0 + exp(-(utility[i] - utility[j]) * 4.0))
            wins[i, j] = p
            wins[j, i] = 1.0 - p
    ability = utility - utility.mean()
    probs = np.exp(ability) / np.exp(ability).sum()
    ranking = sorted(
        [{"candidate": names[i], "ability": float(ability[i]), "share": float(probs[i]), "utility": float(utility[i])} for i in range(len(names))],
        key=lambda x: x["ability"], reverse=True,
    )
    return {"criteria": criteria, "ranking": ranking, "pairwise_win_probability": wins.tolist(), "names": names}


def q4_decision(q1: dict, q2: dict, q3: dict) -> dict:
    # Observation rows deliberately mix physical lanes to establish the first cross-lane quantitative basis.
    obs = []
    for c in q1["cases"]:
        obs.append([c["max_dp_mbar"], abs(c["minimum_margin_mbar"]), 0.0, 0.70, 0.75, 0.20])
    obs.append([0.0, 0.0, abs(q2["relative_residual_percent"]), 0.90, 0.95, 0.10])
    for c in q3["cases"]:
        rise = c["max_P_bara"] - 1.05
        obs.append([0.0, rise, 0.0, 0.55, 0.70, 0.35])
    X = np.array(obs, dtype=float)
    features = ["VLP_dp_mbar", "pressure_or_margin_risk", "thermo_residual_percent", "source_bound_fraction", "provenance_completeness", "manual_touch_fraction"]
    pca_status = "OK" if len(obs) >= 8 else "PCA_INSUFFICIENT_OBSERVATIONS"
    ratios, loadings = pca(X)

    candidates = {
        "J1_FLOW": {"uncertainty_reduction": 0.9, "DoV_gain": 0.8, "source_recoverability": 0.7, "cross_lane_reuse": 0.7, "low_effort": 0.7, "low_validation_risk": 0.8},
        "J1_KCV": {"uncertainty_reduction": 0.6, "DoV_gain": 0.7, "source_recoverability": 0.6, "cross_lane_reuse": 0.5, "low_effort": 0.6, "low_validation_risk": 0.8},
        "J2_TS_RESIDUAL": {"uncertainty_reduction": 0.8, "DoV_gain": 1.0, "source_recoverability": 0.9, "cross_lane_reuse": 0.9, "low_effort": 0.9, "low_validation_risk": 0.9},
        "J3_VOLUME_PROFILE": {"uncertainty_reduction": 0.9, "DoV_gain": 0.8, "source_recoverability": 0.5, "cross_lane_reuse": 0.8, "low_effort": 0.5, "low_validation_risk": 0.7},
        "HEPAK_REFERENCE": {"uncertainty_reduction": 1.0, "DoV_gain": 0.9, "source_recoverability": 0.4, "cross_lane_reuse": 1.0, "low_effort": 0.4, "low_validation_risk": 0.9},
        "LOCAL_WORKER_BUILDOUT": {"uncertainty_reduction": 0.3, "DoV_gain": 0.4, "source_recoverability": 1.0, "cross_lane_reuse": 0.8, "low_effort": 0.3, "low_validation_risk": 0.5},
    }
    bt = bt_scores(candidates)
    return {
        "observation_count": len(obs),
        "features": features,
        "pca_status": pca_status,
        "explained_variance_ratio": ratios,
        "loadings": {f"PC{i+1}": {features[j]: float(loadings[i, j]) for j in range(len(features))} for i in range(min(len(features), loadings.shape[0]))},
        "bradley_terry": bt,
        "pareto_guard": "retain >=3 orthogonal actions; >=4 if observability <60%",
    }


def main() -> int:
    if CoolProp.__version__ != "7.2.0":
        raise RuntimeError(f"CoolProp 7.2.0 required, got {CoolProp.__version__}")
    q1 = q1_vlp()
    q2 = q2_ts_residual()
    q3 = q3_line_s()
    q4 = q4_decision(q1, q2, q3)
    receipt = {
        "wave": "W53/P05J",
        "classification": "QUANTITATIVE_DIAGNOSTIC",
        "Q1_VLP": q1,
        "Q2_TS_RESIDUAL": q2,
        "Q3_LINE_S": q3,
        "Q4_PCA_BT": q4,
        "formal_credit_delta": 0,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
