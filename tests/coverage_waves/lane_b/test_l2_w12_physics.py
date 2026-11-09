"""Lane-B wave 12: QPS phase-3 physics calculations (flow, heat, dP, T, scenarios).

The calculation modules read ``../engineering_baseline.json`` at import time.
That SSOT file is not committed, so the modules are loaded with a synthetic
baseline built from the committed physics_validation_report.md tables.
"""

import builtins
import contextlib
import io
import json
import math

import pytest

from ._l2_loader import load

CALC = "qplant/phase3_physics_validation/calculations/"

BASELINE = {
    "table_5_6_flows": {
        "wcs_hp_expected_flow": {"value": 304},
        "wcs_hp_design_flow": {"value": 350},
    },
    "compressor_specifications": {
        "count": 3,
        "per_unit_flow_gs": 112.54,
        "frequency_hz": 72,
        "motor_power_kW": 315,
        "vfd_range_pct": [50, 105],
    },
    "pressure_parameters": {"wcs_hp_outlet": {"nominal_barg": 14}},
    "heat_loads": {
        "static_heat_4K_W": 45,
        "dynamic_heat_4K_W": 120,
        "non_isothermal_transport_W": 80,
        "current_leads_W": 35,
        "thermal_shield_80K_W": 2500,
        "equivalent_delta_T_K": 2,
    },
    "temperature_parameters": {"operating_K": 4.5},
    "figure_6_scenarios": {
        "S1_nominal": {"description": "Nominal", "hp_flow_gs": 304},
        "S2_peak_demand": {"description": "Peak demand", "hp_flow_gs": 350},
        "S3_partial": {"description": "Partial load", "hp_flow_gs": 180},
        "S0_idle": {"description": "Idle, no flow key"},
    },
}

R_GAS = 8.314
M_HE = 4.002602e-3


@contextlib.contextmanager
def _baseline(payload):
    real_open = builtins.open

    def fake_open(path, *args, **kwargs):
        if str(path).endswith("engineering_baseline.json"):
            return io.StringIO(json.dumps(payload))
        return real_open(path, *args, **kwargs)

    builtins.open = fake_open
    try:
        yield
    finally:
        builtins.open = real_open


def _load(name, payload=None):
    with _baseline(BASELINE if payload is None else payload):
        return load(CALC + name + ".py")


flow = _load("flow_calculations")
heat = _load("heat_load_calculations")
ops = _load("operational_scenarios")
dp = _load("pressure_drop")
temps = _load("temperature_profiles")


@pytest.mark.parametrize(
    "name",
    [
        "flow_calculations",
        "heat_load_calculations",
        "operational_scenarios",
        "pressure_drop",
        "temperature_profiles",
    ],
)
def test_import_fails_without_committed_baseline(name):
    """production_defect: engineering_baseline.json (the SSOT these modules read
    at import time) is not committed next to calculations/, so every module
    raises FileNotFoundError on import; this test fails once fixed."""
    with pytest.raises(FileNotFoundError, match="engineering_baseline.json"):
        load(CALC + name + ".py", name="l2_w12_missing_" + name)


# --------------------------------------------------------------------- flow


def test_volumetric_flow_ideal_gas():
    res = flow.calc_volumetric_flow(350, 300, 14)
    expected = 0.35 * R_GAS * 300 / (14e5 * M_HE)
    assert res["m3_per_s"] == pytest.approx(expected, abs=1e-6)
    assert res["m3_per_s"] == pytest.approx(0.155786, abs=1e-6)
    assert res["m3_per_h"] == pytest.approx(expected * 3600, abs=0.01)
    assert res["L_per_s"] == pytest.approx(expected * 1000, abs=1e-3)


def test_volumetric_flow_scales_inverse_with_pressure():
    lo = flow.calc_volumetric_flow(100, 300, 7)["m3_per_s"]
    hi = flow.calc_volumetric_flow(100, 300, 14)["m3_per_s"]
    assert lo == pytest.approx(2 * hi, rel=1e-4)


def test_compressor_capacity_from_nm3h():
    res = flow.calc_compressor_capacity(3, 575)
    assert res == {"per_unit_gs": 26.13, "total_gs": 78.39, "units": 3}
    custom = flow.calc_compressor_capacity(2, 360, rho_stp=1.0)
    assert custom == {"per_unit_gs": 100.0, "total_gs": 200.0, "units": 2}


def test_vfd_affinity_laws():
    rated = flow.calc_vfd_operating_point(112.54, 112.54, 72, 315)
    assert (rated["frequency_hz"], rated["power_kw"], rated["freq_ratio"]) == (
        72.0,
        315.0,
        1.0,
    )
    half = flow.calc_vfd_operating_point(56.27, 112.54, 72, 315)
    assert half["frequency_hz"] == 36.0
    assert half["power_kw"] == pytest.approx(315 / 8, abs=0.05)
    assert half["freq_ratio"] == 0.5


@pytest.mark.parametrize(
    "demand, capacity, margin, ok",
    [
        (304, 225.08, -25.96, False),
        (350, 225.08, -35.69, False),
        (200, 225.08, 12.54, True),
        (225.08, 225.08, 0.0, True),
    ],
)
def test_n_minus_1_capacity(demand, capacity, margin, ok):
    res = flow.calc_n_minus_1_capacity(3, 112.54, demand)
    assert res["n_minus_1_units"] == 2
    assert res["capacity_gs"] == capacity
    assert res["margin_pct"] == pytest.approx(margin, abs=0.01)
    assert res["can_meet_demand"] is ok


def test_flow_examples_and_self_test(capsys):
    flow.test()
    assert "All flow calculation tests passed" in capsys.readouterr().out
    res = flow.run_examples()
    assert set(res["equations"]) == {
        "mass_flow_continuity",
        "volumetric_flow",
        "compressor_capacity",
        "redundancy_n_plus_1",
        "vfd_flow_scaling",
        "power_scaling",
    }
    calcs = res["calculations"]
    assert len(calcs) == 5
    vfd = calcs[2]["result"]
    assert vfd["frequency_hz"] == pytest.approx(304 / 3 / 112.54 * 72, abs=0.05)
    assert vfd["power_kw"] == pytest.approx(315 * (304 / 3 / 112.54) ** 3, abs=0.05)
    assert "CANNOT meet 304 g/s" in calcs[3]["interpretation"]
    assert "SHORTFALL" in calcs[4]["interpretation"]
    assert "SSOT: 112.54 g/s" in calcs[1]["interpretation"]


# --------------------------------------------------------------------- heat


def test_total_heat_load_sums_components():
    res = heat.calc_total_heat_load()
    assert res["total_4K_W"] == 280
    assert res["total_with_margin_W"] == 322
    assert sum(res["components_W"].values()) == 280


def test_carnot_cop_at_4p5k():
    res = heat.calc_carnot_cop(4.5, 300)
    assert res["cop_carnot"] == pytest.approx(4.5 / 295.5, abs=1e-5)
    assert res["cop_real"] == pytest.approx(0.28 * 4.5 / 295.5, abs=1e-5)
    assert res["eta_carnot"] == 0.28


def test_carnot_cop_equal_temperatures_divides_by_zero():
    with pytest.raises(ZeroDivisionError):
        heat.calc_carnot_cop(300, 300)


def test_required_power_and_lhe_and_shield():
    pwr = heat.calc_required_power(280, 0.00426)
    assert pwr["W_comp_W"] == round(280 / 0.00426)
    assert pwr["W_comp_kW"] == pytest.approx(65.7, abs=0.05)
    lhe = heat.calc_lhe_consumption(280)
    assert lhe["boiloff_g_s"] == pytest.approx(13.514, abs=1e-3)
    assert lhe["boiloff_L_h"] == pytest.approx(280 / 20.72 / 124.96 * 3600, abs=0.01)
    assert lhe["boiloff_L_day"] == pytest.approx(lhe["boiloff_L_h"] * 24, abs=0.1)
    custom = heat.calc_lhe_consumption(100, h_vap_J_g=10)
    assert custom["boiloff_g_s"] == 10.0
    assert heat.calc_shield_equivalent(2500)["Q_4K_equivalent_W"] == 125.0


def test_heat_examples_and_self_test(capsys):
    heat.test()
    assert "All heat load tests passed" in capsys.readouterr().out
    res = heat.run_examples()
    names = [c["name"] for c in res["calculations"]]
    assert names[0] == "Total 4K Heat Load Summation"
    assert len(names) == 5
    assert res["calculations"][2]["result"]["W_comp_kW"] == pytest.approx(65.7, 0.1)
    assert "1046 kW" in res["calculations"][2]["interpretation"]
    assert "125.0 W at 4K" in res["calculations"][4]["interpretation"]


# ------------------------------------------------------------ pressure drop


def test_reynolds_and_laminar_friction():
    re = dp.calc_reynolds(1.2, 0.1, 0.01, 18e-6)
    assert re == pytest.approx(1.2 * 0.1 * 0.01 / 18e-6)
    assert dp.calc_friction_factor(re) == pytest.approx(64 / re)


def test_turbulent_friction_swamee_jain():
    f = dp.calc_friction_factor(1e5)
    expected = 0.25 / math.log10(0.00004 / 3.7 + 5.74 / 1e5**0.9) ** 2
    assert f == pytest.approx(expected)
    assert 0.017 < f < 0.019
    rough = dp.calc_friction_factor(1e5, epsilon_D=0.01)
    assert rough > f


def test_friction_boundary_at_2300_is_turbulent():
    assert dp.calc_friction_factor(2299.9) == pytest.approx(64 / 2299.9)
    assert dp.calc_friction_factor(2300) != pytest.approx(64 / 2300)


def test_pressure_drop_turbulent_line():
    res = dp.calc_pressure_drop(350, 0.15, 50, 2.19, 20.1e-6)
    area = math.pi * 0.15**2 / 4
    v = 0.35 / (2.19 * area)
    assert res["velocity_m_s"] == pytest.approx(v, abs=0.005)
    assert res["flow_regime"] == "turbulent"
    re = 2.19 * v * 0.15 / 20.1e-6
    f = dp.calc_friction_factor(re)
    assert res["dP_Pa"] == pytest.approx(f * 50 / 0.15 * 2.19 * v**2 / 2, abs=0.05)
    assert res["dP_mbar"] == pytest.approx(res["dP_Pa"] / 100, abs=0.005)


def test_pressure_drop_laminar_line():
    # Re = 4 m_dot / (pi D mu) = 1000 for 39.27 g/s, D=50 mm, mu=1e-3 Pa s
    res = dp.calc_pressure_drop(39.27, 0.05, 1, 1.0, 1e-3)
    assert res["flow_regime"] == "laminar"
    assert res["Re"] == 1000
    assert res["friction_factor"] == pytest.approx(0.064, abs=1e-5)


def test_pressure_drop_examples_and_self_test(capsys):
    dp.test()
    assert "Pressure drop tests passed" in capsys.readouterr().out
    res = dp.run_examples()
    first, second = res["calculations"]
    assert first["result"]["dP_mbar"] < 50 and "OK" in first["interpretation"]
    assert second["result"]["dP_mbar"] < 26 and "OK" in second["interpretation"]
    assert set(res["equations"]) == {"darcy_weisbach", "reynolds", "colebrook"}


# -------------------------------------------------------------- temperature


def test_temperature_rise():
    res = temps.calc_temp_rise(80, 350, 5210)
    assert res["dT_K"] == pytest.approx(80 / (0.35 * 5210), abs=1e-4)
    assert res["dT_K"] == pytest.approx(0.0439, abs=1e-4)
    assert temps.calc_temp_rise(5193, 1000)["dT_K"] == 1.0


def test_temperature_rise_zero_flow_divides_by_zero():
    with pytest.raises(ZeroDivisionError):
        temps.calc_temp_rise(10, 0)


def test_cooldown_time_is_symmetric_in_direction():
    down = temps.calc_cooldown_time(50000, 400, 300, 4.5, 50000)
    assert down["Q_total_MJ"] == pytest.approx(5910.0, abs=0.1)
    assert down["time_h"] == pytest.approx(5.91e9 / 50000 / 3600, abs=0.05)
    assert down["time_days"] == pytest.approx(5.91e9 / 50000 / 86400, abs=0.005)
    assert down["T_range"] == "300→4.5 K"
    up = temps.calc_cooldown_time(50000, 400, 4.5, 300, 50000)
    assert up["Q_total_MJ"] == down["Q_total_MJ"]


def test_temperature_examples_and_self_test(capsys):
    temps.test()
    assert "Temperature profile tests passed" in capsys.readouterr().out
    res = temps.run_examples()
    rise, cool = res["calculations"]
    assert "consistent" in rise["interpretation"]
    assert rise["result"]["dT_K"] == pytest.approx(0.0439, abs=1e-4)
    assert cool["result"]["time_h"] == pytest.approx(32.8, abs=0.05)


# ---------------------------------------------------------------- scenarios


def test_model_nominal_scenario():
    res = ops.model_scenario("S1", BASELINE["figure_6_scenarios"]["S1_nominal"])
    ratio = 304 / 3 / 112.54
    assert res["units_active"] == 3
    assert res["per_unit_flow_gs"] == pytest.approx(101.33, abs=0.005)
    assert res["frequency_hz"] == pytest.approx(ratio * 72, abs=0.05)
    assert res["frequency_hz"] == 64.8
    assert res["total_power_kW"] == pytest.approx(3 * 315 * ratio**3, abs=0.05)
    assert res["capacity_margin_pct"] == pytest.approx(11.1, abs=0.05)
    assert res["within_vfd_range"] is True
    assert res["feasible"] is True


def test_model_peak_scenario_exceeds_rated_capacity():
    res = ops.model_scenario("S2", BASELINE["figure_6_scenarios"]["S2_peak_demand"])
    assert res["units_active"] == 3
    assert res["frequency_hz"] == 74.6
    assert res["feasible"] is False
    assert res["capacity_margin_pct"] == pytest.approx(-3.5, abs=0.05)
    assert res["within_vfd_range"] is True


def test_model_partial_and_zero_flow():
    part = ops.model_scenario("S3", BASELINE["figure_6_scenarios"]["S3_partial"])
    assert part["units_active"] == 2
    assert part["frequency_hz"] == 57.6
    idle = ops.model_scenario("S0", BASELINE["figure_6_scenarios"]["S0_idle"])
    assert idle["demand_gs"] == 0
    assert idle["units_active"] == 1
    assert idle["capacity_margin_pct"] == float("inf")
    assert idle["within_vfd_range"] is False
    assert idle["feasible"] is True


def test_run_all_scenarios_and_self_test(capsys):
    ops.test()
    assert "Operational scenario tests passed" in capsys.readouterr().out
    res = ops.run_all_scenarios()
    assert [r["scenario_id"] for r in res] == [
        "S1_nominal",
        "S2_peak_demand",
        "S3_partial",
        "S0_idle",
    ]
    assert [r["feasible"] for r in res] == [True, False, True, True]
