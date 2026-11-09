"""Lane A wave 11: bounded diagnostic sensitivity runner."""

import pytest

from models.qps_line_b import bounded_sensitivity as bs
from models.qps_line_b import vlp_solver

SMALL = bs.Bounds(
    distance_m=(50.0, 150.0),
    diameter_m=(0.1,),
    roughness_m=(1.0e-6,),
    k_local=(1.0,),
    mass_flow_kg_s=(0.02, 0.05),
)


def test_default_bounds_population_size_and_fields():
    rows = bs.diagnostic_population(density_kg_m3=5.0, viscosity_pa_s=1.0e-6)
    assert len(rows) == 243
    row = rows[0]
    assert row["classification"] == "DIAGNOSTIC_ONLY"
    assert set(row) >= {
        "distance_m",
        "delta_p_mbar",
        "predicted_local_pressure_mbar_abs",
        "pressure_margin_mbar",
    }


def test_population_values_follow_solver():
    rows = bs.diagnostic_population(
        density_kg_m3=5.0,
        viscosity_pa_s=1.0e-6,
        boundary_mbar_abs=20.0,
        required_max_mbar_abs=30.0,
        bounds=SMALL,
    )
    assert len(rows) == 4
    first = rows[0]
    seg = vlp_solver.Segment(50.0, 0.1, 1.0e-6, 1.0)
    dp = vlp_solver.pressure_drop_pa(seg, 0.02, 5.0, 1.0e-6)
    assert first["delta_p_mbar"] == pytest.approx(dp / 100.0)
    assert first["predicted_local_pressure_mbar_abs"] == pytest.approx(20 + dp / 100)
    assert first["pressure_margin_mbar"] == pytest.approx(10.0 - dp / 100.0)


def test_worst_case_picks_minimum_margin():
    rows = bs.diagnostic_population(
        density_kg_m3=5.0, viscosity_pa_s=1.0e-6, bounds=SMALL
    )
    worst = bs.worst_case(iter(rows))
    assert worst["distance_m"] == 150.0
    assert worst["mass_flow_kg_s"] == 0.05
    assert worst["pressure_margin_mbar"] == min(r["pressure_margin_mbar"] for r in rows)


def test_worst_case_empty_raises():
    with pytest.raises(ValueError, match="empty population"):
        bs.worst_case([])


def test_one_at_a_time_sensitivity_ranks_by_span():
    rows = bs.diagnostic_population(
        density_kg_m3=5.0, viscosity_pa_s=1.0e-6, bounds=SMALL
    )
    ranking = bs.one_at_a_time_sensitivity(iter(rows))
    top_two = {r["factor"] for r in ranking[:2]}
    assert top_two == {"mass_flow_kg_s", "distance_m"}
    spans = [r["margin_span_mbar"] for r in ranking]
    assert spans == sorted(spans, reverse=True)
    single = {r["factor"]: r["margin_span_mbar"] for r in ranking}
    assert single["diameter_m"] == 0.0
    assert single["k_local"] == 0.0
    assert single["distance_m"] > 0.0


def test_sensitivity_handcrafted_rows():
    base = dict(distance_m=1, diameter_m=1, roughness_m=1, k_local=1)
    rows = [
        dict(base, mass_flow_kg_s=1, pressure_margin_mbar=4.0),
        dict(base, mass_flow_kg_s=2, pressure_margin_mbar=1.0),
    ]
    ranking = bs.one_at_a_time_sensitivity(rows)
    assert ranking[0] == {"factor": "mass_flow_kg_s", "margin_span_mbar": 3.0}
