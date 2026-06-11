import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from calc_leak_rate import (  # noqa: E402
    R_UNIVERSAL,
    SECONDS_PER_YEAR,
    dimensional_proof,
    leak_rate_to_mass_flow_g_year,
    mbar_l_s_to_pa_m3_s,
    normal_m3_per_day_to_kg_per_year,
)


def test_dimensional_chain():
    proof = dimensional_proof(1e-8, 300, 1)
    assert abs(proof["q_si_pa_m3_s"] - 1e-9) < 1e-15
    assert 0 < proof["n_dot_mol_s"] < 1e-9
    assert 0 < proof["m_dot_g_year"] < 1e-3


def test_temperature_pressure_scaling():
    base = leak_rate_to_mass_flow_g_year(1e-8, 300, 1)
    cold = leak_rate_to_mass_flow_g_year(1e-8, 4, 12)
    assert cold > base * 100


def test_reference_rtm048_nm3_day_to_kg_year():
    ref = normal_m3_per_day_to_kg_per_year(1.0)
    assert 60 <= ref <= 70


def test_baseline_scenario_total_range():
    import json

    scenarios = json.loads((ROOT / "data" / "scenarios.json").read_text(encoding="utf-8"))
    baseline = next(s for s in scenarios if s["id"] == "SCN-BASELINE-MIX")
    total_kg = 0.0
    for item in baseline["inventory"]:
        total_kg += (
            leak_rate_to_mass_flow_g_year(
                item["leak_rate_mbar_l_s"], item["temperature_k"], item["pressure_bar_abs"]
            )
            * item["count"]
            / 1000.0
        )
    assert 30 <= total_kg <= 100


def test_unit_conversion_constant():
    assert mbar_l_s_to_pa_m3_s(1.0) == 0.1
    # Equivalent form from ideal gas for quick consistency check
    g_year = leak_rate_to_mass_flow_g_year(1e-8, 300, 1)
    expected = (1e-8 * 0.1 * 4.002602 / (R_UNIVERSAL * 300)) * SECONDS_PER_YEAR
    assert abs(g_year - expected) < 1e-12
