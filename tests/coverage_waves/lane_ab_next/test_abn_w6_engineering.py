"""Behaviour tests for qplant/handover_dashboard/src/calculations/engineering.py."""

import math

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load(
    "qplant/handover_dashboard/src/calculations/engineering.py",
    name="abn_w6_qplant_engineering",
)


def test_mbar_l_s_to_pa_m3_s():
    assert mod.mbar_l_s_to_pa_m3_s(1.0) == pytest.approx(0.1)
    assert mod.mbar_l_s_to_pa_m3_s(0.0) == 0.0


def test_leak_rate_to_mass_flow_reference_value():
    # 1e-8 mbar.L/s -> 1e-9 Pa.m3/s; ideal gas at 300 K; x1e3 g/kg x1e3 alignment.
    expected = 1e-9 * 4.003e-3 / (8.314462618 * 300.0) * 1e6
    assert mod.leak_rate_to_mass_flow_g_s(1e-8, 300.0) == pytest.approx(expected)


def test_leak_rate_scales_with_pressure_and_inverse_temperature():
    base = mod.leak_rate_to_mass_flow_g_s(1e-5, 300.0, 1.0)
    assert mod.leak_rate_to_mass_flow_g_s(1e-5, 300.0, 5.0) == pytest.approx(5 * base)
    assert mod.leak_rate_to_mass_flow_g_s(1e-5, 30.0, 1.0) == pytest.approx(10 * base)


def test_helium_density_ideal_gas():
    rho = mod.helium_density_kg_m3(300.0, 1.0)
    assert rho == pytest.approx(1e5 * 4.003e-3 / (8.314462618 * 300.0))
    assert mod.helium_density_kg_m3(300.0, 2.0) == pytest.approx(2 * rho)


def test_helium_viscosity_reference_and_monotonic():
    assert mod.helium_dynamic_viscosity_pa_s(273.15) == pytest.approx(1.96e-5)
    cold = mod.helium_dynamic_viscosity_pa_s(4.0)
    warm = mod.helium_dynamic_viscosity_pa_s(300.0)
    assert cold < warm


def test_sonic_flow_choked_branch():
    out = mod.sonic_flow_indicators(1e-5, 300.0, p_up_bar=5.0, p_down_bar=1.0)
    crit = (2 / 2.66) ** (1.66 / 0.66)
    assert out["critical_pressure_ratio"] == pytest.approx(crit)
    assert out["actual_pressure_ratio"] == pytest.approx(0.2)
    assert out["is_choked"] == 1.0
    assert out["mach_est"] == 1.0
    assert out["reynolds"] > 0
    assert out["nusselt"] >= 0.023 * 0.67**0.4
    assert set(out) == {
        "density_kg_m3",
        "velocity_m_s",
        "critical_pressure_ratio",
        "actual_pressure_ratio",
        "mach_est",
        "reynolds",
        "nusselt",
        "is_choked",
    }


def test_sonic_flow_subsonic_branch():
    out = mod.sonic_flow_indicators(1e-5, 300.0, p_up_bar=1.2, p_down_bar=1.0)
    assert out["is_choked"] == 0.0
    ratio = 1.0 / 1.2
    g = 1.66
    expected = math.sqrt((2 / (g - 1)) * ((1 / ratio) ** ((g - 1) / g) - 1))
    assert out["mach_est"] == pytest.approx(expected)
    assert 0 < out["mach_est"] < 1


def test_sonic_flow_equal_pressure_gives_zero_mach():
    out = mod.sonic_flow_indicators(1e-9, 20.0, p_up_bar=1.0, p_down_bar=1.0)
    assert out["mach_est"] == pytest.approx(0.0)
    assert out["is_choked"] == 0.0


def test_build_conversion_table_shape_and_consistency():
    df = mod.build_conversion_table()
    n = len(mod.LEAK_CLASSES) * len(mod.TEMPERATURES_K) * len(mod.PRESSURES_BAR)
    assert len(df) == n
    row = df.iloc[0]
    assert row["mass_flow_g_day"] == pytest.approx(row["mass_flow_g_s"] * 86400)
    assert row["mass_flow_g_year"] == pytest.approx(
        row["mass_flow_g_s"] * 365.25 * 86400
    )
    assert set(df["is_choked"].unique()) <= {0.0, 1.0}


def test_build_valve_spec_table():
    df = mod.build_valve_spec_table()
    assert len(df) == 3
    assert "Swagelok SS-42GSE" in list(df["valve_type"])


def test_build_inventory_table_totals():
    df = mod.build_inventory_table()
    assert len(df) == 4
    for _, r in df.iterrows():
        assert r["mass_loss_g_year_total"] == pytest.approx(
            r["mass_loss_g_year_each"] * r["count"]
        )
    warm = df[df["temperature_K"] == 300]["mass_loss_g_year_each"].iloc[0]
    cold = df[df["leak_class"] == 1e-9]["mass_loss_g_year_each"].iloc[0]
    assert warm > cold


def test_build_reliability_table_returns_pair():
    df, spares = mod.build_reliability_table()
    assert len(df) == 8
    first = df.iloc[0]
    assert first["valve_type"] == "Meca Inox"
    assert first["mdt_h"] == pytest.approx(14.0)
    assert first["availability"] == pytest.approx(8000 / (8000 + 14.0 / 8.0))
    assert list(spares["count"]) == [210, 200]
    mean_mtbf = (8.0 + 5.0 + 3.5 + 2.5) / 4
    assert spares.iloc[0]["weighted_mtbf_years"] == pytest.approx(mean_mtbf)
    expected = math.ceil(210 / mean_mtbf * 1.5 + 2)
    assert spares.iloc[0]["recommended_spares_per_year"] == expected


def test_build_cost_table_tco():
    df = mod.build_cost_table(helium_eur_per_kg=20.0, lifetime_years=10)
    assert list(df["class"]) == [
        "Leak-tight",
        "High-integrity",
        "Industrial",
        "Seat leakage",
    ]
    for _, r in df.iterrows():
        assert r["tco_per_valve_eur"] == pytest.approx(
            r["valve_capex_eur"] + r["helium_cost_over_life_eur"]
        )
        assert r["helium_cost_over_life_eur"] == pytest.approx(
            r["helium_loss_kg_over_life"] * 20.0
        )
    default = mod.build_cost_table()
    assert default.iloc[3]["helium_loss_kg_over_life"] == pytest.approx(
        4 * df.iloc[3]["helium_loss_kg_over_life"]
    )


def test_build_traceability_matrix():
    df = mod.build_traceability_matrix()
    assert len(df) == 21
    assert df.iloc[0]["requirement_id"] == "RTM-047"
    assert df.iloc[-1]["requirement_id"] == "RTM-067"
    assert df.iloc[5]["requirement_summary"] == df.iloc[0]["requirement_summary"]
    assert df.iloc[4]["verification_method"] == "Version metadata check"
