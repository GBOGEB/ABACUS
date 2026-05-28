from __future__ import annotations

import math

from src.calc_leak_rate import leak_rate_to_mass_flow_g_year
from src.compressor_reliability import (
    CONFIGS,
    FSD575_PACKAGE_KW,
    HP_COUNT,
    annual_energy_savings_vfd,
    fixed_speed_power_at_load,
    system_availability_k_of_m,
    vfd_power_at_load,
)
from src.config_loader import cfg
from src.liquid_he_loss import LiquidHeState, compute_liquid_loss


def test_leak_rate_to_mass():
    g_year_4k = leak_rate_to_mass_flow_g_year(1e-5, 4, 1)
    g_year_300k = leak_rate_to_mass_flow_g_year(1e-5, 300, 1)

    assert g_year_4k > g_year_300k
    assert g_year_4k > 0
    assert g_year_300k > 0


def test_liquid_boiloff():
    state = LiquidHeState(leak_rate_mbar_l_s=1e-5, temperature_K=4.222)
    result = compute_liquid_loss(state)

    assert result["mass_flow_g_year"] > 0
    assert result["liquid_loss_L_year"] > 0
    assert result["cost_eur_year"] > 0


def test_compressor_availability():
    A = 8760 / (8760 + 8)

    a_2_of_3 = system_availability_k_of_m(A, 3, 2)
    a_2_of_4 = system_availability_k_of_m(A, 4, 2)
    a_1_of_2 = system_availability_k_of_m(A, 2, 1)

    assert 0 < a_2_of_3 <= 1
    assert 0 < a_2_of_4 <= 1
    assert 0 < a_1_of_2 <= 1
    assert a_2_of_4 >= a_2_of_3


def test_vfd_savings():
    p_fixed_70 = fixed_speed_power_at_load(FSD575_PACKAGE_KW, 0.7)
    p_vfd_70 = vfd_power_at_load(FSD575_PACKAGE_KW, 0.7)
    summary = annual_energy_savings_vfd(full_load_kw=FSD575_PACKAGE_KW, avg_load_fraction=0.7)

    assert p_vfd_70 < p_fixed_70
    assert summary["cost_savings_eur_yr"] > 0
    assert summary["savings_pct"] > 0


def test_vfd_full_load_near_fixed_speed():
    p_fixed = fixed_speed_power_at_load(FSD575_PACKAGE_KW, 1.0)
    p_vfd = vfd_power_at_load(FSD575_PACKAGE_KW, 1.0)
    assert math.isclose(p_fixed, FSD575_PACKAGE_KW, rel_tol=1e-9)
    assert p_vfd > p_fixed


def test_ssot_hp_count_and_config_map():
    assert cfg.get("compressor_specifications.hp_compressors.count") == 3
    assert HP_COUNT == 3
    assert CONFIGS["N1_FSD575_VFD"].total_units == 3
