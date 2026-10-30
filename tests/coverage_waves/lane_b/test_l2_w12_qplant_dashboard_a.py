"""Lane-B wave 12: qplant handover dashboard physics and SSoT modules.

Covers config_loader, compressor_reliability, wcs_scenarios, calc_leak_rate,
liquid_he_loss, monte_carlo and risk_model. The SSoT config is a tmp YAML
injected through SSOT_CONFIG_PATH while the loader executes.
"""

import json
import math
import types

import numpy as np
import pytest

from ._l2_loader import REPO_ROOT, load

SRC = "qplant/handover_dashboard/src/"

SSOT_YAML = """\
version: "9.9.9"
note: scalar-at-top-level
tags: [alpha, beta]
financial:
  operating_hours_year: 7000.0
  electricity_cost_eur_kwh: 0.2
compressor_specifications:
  fsd575:
    motor_power_kW: 300
    package_power_kW: 350.0
    per_unit_flow_gs: 110.0
    capital_cost_eur: 210000
    annual_maint_eur: 16000
    mtbf_hours: 9000
    mttr_hours: 10
  hp_compressors:
    count: 4
pressure_parameters:
  wcs_hp_outlet:
    nominal_barg: 13
    max_barg: 16
    min_barg: 9
  hcc_inlet:
    nominal_mbar: 1040
  wcs_lcc_suction:
    nominal_mbar: 410
"""


@pytest.fixture(scope="module")
def ssot(tmp_path_factory):
    cfg_path = tmp_path_factory.mktemp("ssot") / "config.yaml"
    cfg_path.write_text(SSOT_YAML, encoding="utf-8")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("SSOT_CONFIG_PATH", str(cfg_path))
        mp.delenv("QPLANT_CONFIG_PATH", raising=False)
        cl = load(SRC + "config_loader.py")
    src_pkg = types.ModuleType("src")
    src_pkg.config_loader = cl
    deps = {"src": src_pkg, "src.config_loader": cl}
    cr = load(SRC + "compressor_reliability.py", deps=deps)
    wcs = load(SRC + "wcs_scenarios.py", deps=deps)
    return types.SimpleNamespace(path=cfg_path, cl=cl, cr=cr, wcs=wcs)


# --------------------------------------------------------------------------
# config_loader
# --------------------------------------------------------------------------


def test_runtime_env_path_selects_injected_config(ssot):
    assert ssot.cl.cfg.path == ssot.path
    assert ssot.cl.cfg.version == "9.9.9"
    assert repr(ssot.cl.cfg) == f"ConfigLoader(version='9.9.9', path={ssot.path})"


def test_default_path_falls_back_to_repo_config(monkeypatch):
    monkeypatch.delenv("SSOT_CONFIG_PATH", raising=False)
    monkeypatch.delenv("QPLANT_CONFIG_PATH", raising=False)
    cl = load(SRC + "config_loader.py", name="l2_w12_cfg_default")
    assert cl._DEFAULT_CONFIG == REPO_ROOT / "qplant" / "config.yaml"
    assert cl.cfg.path == cl._DEFAULT_CONFIG
    assert isinstance(cl.cfg.config, dict)


@pytest.mark.parametrize(
    "key, default, expected",
    [
        ("compressor_specifications.hp_compressors.count", None, 4),
        ("financial.electricity_cost_eur_kwh", None, 0.2),
        ("financial.missing", "dflt", "dflt"),
        ("note.deeper", "dflt", "dflt"),
        ("missing_top", None, None),
    ],
)
def test_get_dot_notation(ssot, key, default, expected):
    assert ssot.cl.cfg.get(key, default) == expected


def test_version_default_and_reload(tmp_path, ssot):
    p = tmp_path / "c.yaml"
    p.write_text("a: 1\n", encoding="utf-8")
    loader = ssot.cl.ConfigLoader(p)
    assert loader.version == "0.0.0"
    p.write_text("a: 2\nversion: '1.2'\n", encoding="utf-8")
    loader.reload()
    assert loader.get("a") == 2
    assert loader.version == "1.2"


def test_export_json_explicit_and_default(tmp_path, monkeypatch, ssot):
    loader = ssot.cl.ConfigLoader(ssot.path)
    out = loader.export_json(tmp_path / "x" / "cfg.json")
    assert json.loads(out.read_text(encoding="utf-8"))["version"] == "9.9.9"
    monkeypatch.setattr(ssot.cl, "_ROOT", tmp_path / "root")
    default = loader.export_json()
    assert default == tmp_path / "root" / "data" / "config.json"
    assert json.loads(default.read_text(encoding="utf-8"))["tags"] == ["alpha", "beta"]


def test_export_markdown_renders_nested_tables(tmp_path, monkeypatch, ssot):
    loader = ssot.cl.ConfigLoader(ssot.path)
    explicit = loader.export_markdown(tmp_path / "md" / "cfg.md")
    text = explicit.read_text(encoding="utf-8")
    assert text.startswith("# QPLANT Configuration — v9.9.9")
    assert "## Compressor Specifications" in text
    assert "### Fsd575" in text
    assert "| motor_power_kW | 300 |" in text
    assert "**tags**: alpha, beta" in text
    assert "scalar-at-top-level" not in text
    monkeypatch.setattr(ssot.cl, "_ROOT", tmp_path / "root")
    assert loader.export_markdown() == tmp_path / "root" / "data" / "config.md"


def test_dict_to_md_caps_heading_depth(ssot):
    loader = ssot.cl.ConfigLoader(ssot.path)
    lines = []
    loader._dict_to_md({"a": {"b": {"c": 1}}}, lines, depth=5)
    assert lines[0] == "###### A"
    assert lines[2] == "###### B"
    assert "| c | 1 |" in lines


# --------------------------------------------------------------------------
# compressor_reliability
# --------------------------------------------------------------------------


def test_compressor_constants_come_from_ssot(ssot):
    cr = ssot.cr
    assert cr.OPERATING_HOURS_YEAR == 7000.0
    assert cr.ELECTRICITY_COST_EUR_KWH == 0.2
    assert cr.FSD575_PACKAGE_KW == 350.0
    assert cr.HP_COUNT == 4
    assert cr.CONFIGS["N1_FSD575_VFD"].total_units == 4
    assert cr.CONFIGS["N3_baseline"].mtbf_hours == 9000


def test_single_unit_math(ssot):
    cr = ssot.cr
    assert cr.failure_rate(1000.0) == pytest.approx(1e-3)
    assert cr.single_availability(90.0, 10.0) == pytest.approx(0.9)
    assert cr.single_reliability(1000.0, 1000.0) == pytest.approx(math.exp(-1))


def test_k_of_m_system(ssot):
    cr = ssot.cr
    assert cr.system_availability_k_of_m(0.9, 3, 2) == pytest.approx(0.972)
    r = cr.single_reliability(500.0, 1000.0)
    expected = 3 * r**2 * (1 - r) + r**3
    assert cr.system_reliability_k_of_m(500.0, 1000.0, 3, 2) == pytest.approx(expected)


def test_mtbf_and_downtime(ssot):
    cr = ssot.cr
    assert cr.system_mtbf_approx(1.0) == float("inf")
    assert cr.system_mtbf_approx(0.5, 8.0) == pytest.approx(8.0)
    assert cr.downtime_hours_year(0.99) == pytest.approx(87.6)


def test_vfd_and_fixed_power(ssot):
    cr = ssot.cr
    assert cr.vfd_power_at_load(100.0, 0.5, 1.0) == pytest.approx(12.5)
    assert cr.fixed_speed_power_at_load(100.0, 0.5) == pytest.approx(70.0)


def test_annual_energy_savings(ssot):
    info = ssot.cr.annual_energy_savings_vfd(100.0, 0.5, 1000.0, 0.1, 1.0)
    assert info == {
        "power_fixed_kw": 70.0,
        "power_vfd_kw": 12.5,
        "energy_fixed_kwh_yr": 70000.0,
        "energy_vfd_kwh_yr": 12500.0,
        "energy_savings_kwh_yr": 57500.0,
        "cost_savings_eur_yr": 5750.0,
        "savings_pct": 82.1,
    }


def test_annual_energy_savings_zero_power_has_zero_pct(ssot):
    info = ssot.cr.annual_energy_savings_vfd(0.0, 0.5)
    assert info["savings_pct"] == 0
    assert info["energy_fixed_kwh_yr"] == 0


def test_comparison_table_rows(ssot):
    df = ssot.cr.build_comparison_table()
    assert list(df["config_key"]) == ["N3_baseline", "N1_FSD575_VFD", "N1_HSD_twin"]
    vfd = df.set_index("config_key").loc["N1_FSD575_VFD"]
    assert vfd["redundancy"] == "2-of-4"
    assert bool(vfd["has_vfd"]) is True
    base = df.set_index("config_key").loc["N3_baseline"]
    assert base["total_capex_eur"] == 3 * 210000
    assert base["annual_energy_eur"] == round(2 * 350.0 * 7000.0 * 0.2, 0)


def test_comparison_table_perfect_availability(ssot, monkeypatch):
    cr = ssot.cr
    perfect = cr.CompressorConfig(
        name="Perfect", total_units=1, required_units=1, capacity_per_unit_pct=100.0
    )
    perfect.mttr_hours = 0.0
    monkeypatch.setattr(cr, "CONFIGS", {"perfect": perfect})
    row = cr.build_comparison_table().iloc[0]
    assert row["A_system_nines"] == float("inf")
    assert row["MTBF_system_hours"] == float("inf")
    assert row["downtime_h_yr"] == 0.0


def test_reliability_curves_shape(ssot):
    df = ssot.cr.build_reliability_curves(t_max_hours=100.0, n_points=5)
    assert list(df["hours"]) == [0.0, 25.0, 50.0, 75.0, 100.0]
    assert df.shape == (5, 4)
    assert df.iloc[0, 1] == pytest.approx(1.0)


def test_vfd_savings_table_default_and_custom(ssot):
    df = ssot.cr.build_vfd_savings_table()
    assert list(df["load_pct"]) == [30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    custom = ssot.cr.build_vfd_savings_table(100.0, loads=[0.5])
    assert custom.iloc[0]["power_fixed_kw"] == 70.0


# --------------------------------------------------------------------------
# wcs_scenarios
# --------------------------------------------------------------------------


def test_wcs_constants_from_ssot(ssot):
    wcs = ssot.wcs
    assert (wcs.HP_OUTLET_BARG, wcs.HP_MAX_BARG, wcs.HP_MIN_BARG) == (13, 16, 9)
    assert (wcs.HCC_INLET_MBAR, wcs.VLP_NOMINAL_MBAR) == (1040, 410)
    assert wcs.INTERLOCKS[0]["setpoint"] == "< 12.5 barg"
    assert wcs.SCENARIOS[1].hp_header_barg == pytest.approx(12.8)


def test_leak_budget_table(ssot):
    df = ssot.wcs.build_leak_budget_table()
    assert list(df["circuit"]) == [
        "Main Hp Supply",
        "Sidestreams",
        "Contingency",
        "TOTAL",
    ]
    assert df["budget_mbar_l_s"].iloc[:3].sum() == pytest.approx(1e-5)
    assert df.iloc[-1]["fraction_pct"] == 100


def test_interlock_and_scenario_tables(ssot):
    assert len(ssot.wcs.build_interlock_table()) == 6
    df = ssot.wcs.build_scenario_table()
    assert list(df["sidestreams"]) == ["Open", "Closed", "Closed", "Closed"]
    assert list(df["status"]) == ["NOMINAL", "WARNING", "ALARM", "TRIP"]


# --------------------------------------------------------------------------
# calc_leak_rate
# --------------------------------------------------------------------------

clr = load(SRC + "calc_leak_rate.py")


def test_leak_rate_unit_chain():
    assert clr.mbar_l_s_to_pa_m3_s(1.0) == pytest.approx(0.1)
    mol = clr.leak_rate_to_molar_flow_mol_s(1.0, 300.0, 2.0, 1.0)
    assert mol == pytest.approx(0.2 / (clr.R_UNIVERSAL * 300.0))
    g_s = clr.leak_rate_to_mass_flow_g_s(1.0, 300.0)
    assert g_s == pytest.approx(mol / 2 * clr.MOLAR_MASS_HE_G_PER_MOL)
    assert clr.leak_rate_to_mass_flow_g_year(1.0, 300.0) == pytest.approx(
        g_s * clr.SECONDS_PER_YEAR
    )


def test_normal_m3_and_density():
    assert clr.normal_m3_per_day_to_kg_per_year(1.0) == pytest.approx(0.1785 * 365.25)
    rho = clr.helium_density_kg_m3(300.0, 1.0)
    assert rho == pytest.approx(1e5 * 4.002602e-3 / (clr.R_UNIVERSAL * 300.0))


def test_choked_ratio():
    assert clr.choked_flow_critical_ratio(1.4) == pytest.approx(0.528, abs=1e-3)


@pytest.mark.parametrize("up, choked", [(10.0, 1.0), (1.2, 0.0)])
def test_sonic_flow_indicators(up, choked):
    ind = clr.sonic_flow_indicators(1e-6, 300.0, up)
    assert ind["is_choked"] == choked
    assert ind["actual_pressure_ratio"] == pytest.approx(1.0 / up)
    assert ind["mach_est"] == pytest.approx(
        ind["velocity_m_s"] / ind["speed_of_sound_m_s"]
    )


def test_conversion_grid_and_proof():
    df = clr.build_conversion_grid([1e-8, 1e-5], [4.0, 300.0], [1.0])
    assert len(df) == 4
    assert {"mass_flow_g_day", "is_choked", "density_kg_m3"} <= set(df.columns)
    proof = clr.dimensional_proof(1e-8, 300.0, 1.0)
    assert proof["m_dot_g_year"] == pytest.approx(
        clr.leak_rate_to_mass_flow_g_year(1e-8, 300.0)
    )
    assert proof["q_si_pa_m3_s"] == pytest.approx(1e-9)


# --------------------------------------------------------------------------
# liquid_he_loss
# --------------------------------------------------------------------------

lhl = load(SRC + "liquid_he_loss.py")


def test_compute_liquid_loss_example_values():
    """The example docstring claims ~37.9 g/year; the ideal-gas code yields 3.80."""
    res = lhl.compute_liquid_loss(lhl.LiquidHeState(1e-5, 4.0, 1.0, label="x"))
    assert res["mass_flow_g_year"] == pytest.approx(3.798, rel=1e-3)
    assert res["liquid_loss_L_year"] == pytest.approx(0.0304, rel=1e-2)
    assert res["label"] == "x"
    assert res["cost_eur_day"] == pytest.approx(res["cost_eur_year"] / 365.25)
    assert res["boiloff_power_W"] == pytest.approx(res["mass_flow_kg_s"] * 20.9e3)


def test_liquid_volume_and_mass_helpers():
    assert lhl.mbar_l_s_to_pa_m3_s(2.0) == pytest.approx(0.2)
    assert lhl.liquid_volume_loss_L_s(124.96) == pytest.approx(1000.0)
    assert lhl.gas_mass_flow_kg_s(1.0, 4.0, 1.0, Z=2.0) == pytest.approx(
        0.1 * 0.004003 / (2.0 * lhl.R_UNIVERSAL * 4.0)
    )


def test_leak_rate_table_default_and_custom():
    df = lhl.build_leak_rate_liquid_loss_table()
    assert list(df["label"]) == [
        "1e-09",
        "1e-08",
        "1e-07",
        "1e-06",
        "1e-05",
        "1e-04",
        "1e-03",
        "1e-02",
    ]
    assert len(lhl.build_leak_rate_liquid_loss_table([1e-3])) == 1


def test_depletion_timeseries_floor_and_attrs():
    df = lhl.inventory_depletion_timeseries(initial_volume_L=1.0, duration_days=3)
    assert list(df.columns) == ["day", "Q=1e-09", "Q=1e-08", "Q=1e-05", "Q=1e-04"]
    assert df.attrs == {"initial_volume_L": 1.0, "min_level_L": 0.2}
    big = lhl.inventory_depletion_timeseries(
        initial_volume_L=0.001, leak_rates=[10.0], duration_days=2
    )
    assert list(big["Q=1e+01"]) == [0.001, 0.0, 0.0]


def test_time_to_threshold():
    days = lhl.time_to_threshold(100.0, 1e-3)
    loss = lhl.compute_liquid_loss(lhl.LiquidHeState(1e-3))["liquid_loss_L_day"]
    assert days == pytest.approx(80.0 / loss)
    assert lhl.time_to_threshold(100.0, 0.0) == float("inf")


def test_example_calculation_prints(capsys):
    res = lhl.example_calculation()
    out = capsys.readouterr().out
    assert "Mass flow: 3.80 g/year" in out
    assert res["label"] == "RTM-048 system max example"


# --------------------------------------------------------------------------
# monte_carlo
# --------------------------------------------------------------------------

mc = load(SRC + "monte_carlo.py")


def _fleet():
    return [mc.ValveFleet("seg", 10, 1e-5, 4.0, 12.0, 60000, 4, 1000, 100)]


def test_he_mass_loss():
    expected = 1e-6 * 12.0 / (8.314462618 * 4.0) * 4.002602e-3 * 365.25 * 86400 * 10
    assert mc._he_mass_loss_kg_year(1e-5, 4.0, 12.0, 10) == pytest.approx(expected)


@pytest.mark.parametrize("prob, expected", [(0.0, False), (1.0, True)])
def test_run_monte_carlo_geo_toggle(monkeypatch, prob, expected):
    monkeypatch.setattr(mc, "RNG", np.random.default_rng(7))
    cfg = mc.ScenarioConfig("t", "d", _fleet(), geopolitical_disruption_prob=prob)
    df = mc.run_monte_carlo(cfg, n_runs=20)
    assert len(df) == 20
    assert list(df["run"]) == list(range(20))
    assert bool(df["geopolitical_event"].all()) is expected
    low, high = (117.0, 300.0) if not expected else (117.0 * 2.5, 300.0 * 2.5)
    assert df["he_price_eur_kg"].between(low, high).all()
    assert (df["beam_availability_pct"] <= 100).all()


def test_run_monte_carlo_is_deterministic_under_seed(monkeypatch):
    cfg = mc.ScenarioConfig("t", "d", _fleet())
    monkeypatch.setattr(mc, "RNG", np.random.default_rng(11))
    a = mc.run_monte_carlo(cfg, n_runs=5)
    monkeypatch.setattr(mc, "RNG", np.random.default_rng(11))
    b = mc.run_monte_carlo(cfg, n_runs=5)
    assert a.equals(b)


def test_statistics_and_tornado(monkeypatch):
    monkeypatch.setattr(mc, "RNG", np.random.default_rng(3))
    cfg = mc.ScenarioConfig("t", "d", _fleet(), geopolitical_disruption_prob=0.5)
    df = mc.run_monte_carlo(cfg, n_runs=60)
    stats = mc.compute_statistics(df)
    assert stats["n_runs"] == 60
    assert 0 < stats["geo_event_pct"] < 100
    tc = stats["total_cost_eur"]
    assert tc["min"] <= tc["p10"] <= tc["p50"] <= tc["p90"] <= tc["max"]
    tornado = mc.sensitivity_tornado(df, cfg)
    assert len(tornado) == 5
    assert list(tornado["range"]) == sorted(tornado["range"])
    geo = tornado.set_index("variable").loc["Geopolitical Disruption"]
    assert geo["high"] == df[df["geopolitical_event"]]["total_cost_eur"].median()


def test_tornado_without_geo_events_uses_base(monkeypatch):
    monkeypatch.setattr(mc, "RNG", np.random.default_rng(5))
    cfg = mc.ScenarioConfig("t", "d", _fleet())
    df = mc.run_monte_carlo(cfg, n_runs=30)
    geo = mc.sensitivity_tornado(df, cfg).set_index("variable")
    row = geo.loc["Geopolitical Disruption"]
    assert row["high"] == row["base"] == df["total_cost_eur"].median()


def test_baseline_fleet_and_scenarios():
    fleet = mc.build_baseline_fleet()
    assert sum(seg.count for seg in fleet) == 410
    assert set(mc.SCENARIOS) == {
        "baseline",
        "geopolitical",
        "supply_chain",
        "accelerated_failure",
    }
    assert mc.SCENARIOS["geopolitical"].geopolitical_disruption_prob == 0.30


def test_run_all_scenarios(monkeypatch):
    monkeypatch.setattr(mc, "RNG", np.random.default_rng(9))
    real = mc.run_monte_carlo
    calls = []

    def small(config, n_runs=mc.N_SIMULATIONS):
        calls.append((config.name, n_runs))
        return real(config, n_runs=25)

    monkeypatch.setattr(mc, "run_monte_carlo", small)
    out = mc.run_all_scenarios()
    assert list(out) == list(mc.SCENARIOS)
    assert calls[0] == ("Baseline", 10_000)
    for key, res in out.items():
        assert res["config"] is mc.SCENARIOS[key]
        assert res["stats"]["n_runs"] == 25
        assert len(res["tornado"]) == 5


# --------------------------------------------------------------------------
# risk_model
# --------------------------------------------------------------------------

rm = load(SRC + "risk_model.py")


def test_risk_matrix_data():
    rows = rm.risk_matrix_data()
    assert len(rows) == 10
    assert rows[0]["id"] == "RISK-001"
    assert all(r["risk_score"] == r["likelihood"] * r["impact"] for r in rows)


def test_beam_impact_analysis():
    res = rm.beam_impact_analysis()
    assert list(res) == [
        "OPS-BASELINE",
        "OPS-EXTENDED-REPAIR",
        "OPS-CASCADE",
        "OPS-LOOP",
    ]
    base = res["OPS-BASELINE"]
    assert base["lost_beam_hours"] == 36
    assert base["lost_experiments"] == 18.0
    assert base["financial_impact_eur"] == 540000
