"""W53/P05C bounded diagnostic sensitivity runner.

This runner is intentionally non-promoting. It exercises the merged VLP solver over
bounded geometry/flow assumptions and ranks pressure-margin sensitivity. Exact
engineering acceptance still requires source-bound geometry and validated low-T
properties.
"""
from dataclasses import dataclass
from itertools import product
from typing import Iterable

from .vlp_solver import Segment, pressure_drop_pa, qcell_pressure_mbar, pressure_margin_mbar


@dataclass(frozen=True)
class Bounds:
    distance_m: tuple[float, ...] = (70.0, 115.0, 160.0)
    diameter_m: tuple[float, ...] = (0.08, 0.10, 0.12)
    roughness_m: tuple[float, ...] = (1.0e-6, 5.0e-6, 1.0e-5)
    k_local: tuple[float, ...] = (1.0, 3.0, 6.0)
    mass_flow_kg_s: tuple[float, ...] = (0.020, 0.035, 0.050)


def diagnostic_population(
    *,
    density_kg_m3: float,
    viscosity_pa_s: float,
    boundary_mbar_abs: float = 27.0,
    required_max_mbar_abs: float = 31.0,
    bounds: Bounds = Bounds(),
) -> list[dict]:
    rows: list[dict] = []
    for distance_m, diameter_m, roughness_m, k_local, mass_flow_kg_s in product(
        bounds.distance_m,
        bounds.diameter_m,
        bounds.roughness_m,
        bounds.k_local,
        bounds.mass_flow_kg_s,
    ):
        segment = Segment(distance_m, diameter_m, roughness_m, k_local)
        dp_pa = pressure_drop_pa(segment, mass_flow_kg_s, density_kg_m3, viscosity_pa_s)
        local_p = qcell_pressure_mbar(boundary_mbar_abs, dp_pa)
        margin = pressure_margin_mbar(required_max_mbar_abs, local_p)
        rows.append({
            "distance_m": distance_m,
            "diameter_m": diameter_m,
            "roughness_m": roughness_m,
            "k_local": k_local,
            "mass_flow_kg_s": mass_flow_kg_s,
            "delta_p_mbar": dp_pa / 100.0,
            "predicted_local_pressure_mbar_abs": local_p,
            "pressure_margin_mbar": margin,
            "classification": "DIAGNOSTIC_ONLY",
        })
    return rows


def worst_case(rows: Iterable[dict]) -> dict:
    rows = list(rows)
    if not rows:
        raise ValueError("empty population")
    return min(rows, key=lambda row: row["pressure_margin_mbar"])


def one_at_a_time_sensitivity(rows: Iterable[dict]) -> list[dict]:
    rows = list(rows)
    factors = ["distance_m", "diameter_m", "roughness_m", "k_local", "mass_flow_kg_s"]
    ranked = []
    for factor in factors:
        grouped = {}
        for row in rows:
            grouped.setdefault(row[factor], []).append(row["pressure_margin_mbar"])
        means = [sum(v) / len(v) for v in grouped.values()]
        ranked.append({"factor": factor, "margin_span_mbar": max(means) - min(means)})
    return sorted(ranked, key=lambda item: item["margin_span_mbar"], reverse=True)
