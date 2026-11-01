"""Lane A wave 13: models.qps_line_s.ssot_tables numerics."""

import math

import pytest

from models.qps_line_s import ssot_tables as st


def test_conductivity_range_and_value():
    assert st.k_aisi304_w_m_k(300.0) > st.k_aisi304_w_m_k(4.0) > 0
    with pytest.raises(ValueError, match="valid 1"):
        st.k_aisi304_w_m_k(0.5)
    with pytest.raises(ValueError):
        st.k_aisi304_w_m_k(301.0)


def test_integral_zero_sign_and_odd_n():
    assert st.integrate_k_signed_w_per_m(50.0, 50.0) == 0.0
    up = st.integrate_k_signed_w_per_m(4.0, 80.0, n=63)
    down = st.integrate_k_signed_w_per_m(80.0, 4.0, n=64)
    assert up > 0
    assert down == pytest.approx(-up, rel=1e-9)


def test_static_heat_loads_are_positive_and_consistent():
    loads = st.static_heat_loads_w("LINAC_24", 4.0, 50.0)
    assert loads["q1_total_w"] == pytest.approx(loads["q1_cond_w"] + loads["q1_rad_w"])
    assert loads["q2_total_w"] == pytest.approx(loads["q2_cond_w"] + loads["q2_rad_w"])
    assert loads["q1_cond_w"] > 0
    assert loads["q2_cond_w"] > 0
    bigger = st.static_heat_loads_w("LINAC_30", 4.0, 50.0, t_ambient_k=300.0)
    assert bigger["q1_total_w"] > loads["q1_total_w"]


def test_specific_enthalpy_exact_interp_and_range():
    assert st.specific_enthalpy_j_per_kg("cold", 4.0) == 2.2
    assert st.specific_enthalpy_j_per_kg("ts", 4.0) == 0.4
    assert st.specific_enthalpy_j_per_kg("cold", 5.0) == pytest.approx(3.55)
    assert st.specific_enthalpy_j_per_kg("cold", 1.0) == 0.0
    with pytest.raises(ValueError, match="Table 29"):
        st.specific_enthalpy_j_per_kg("ts", 0.5)


def test_inverse_ts_enthalpy_branches():
    assert st.inverse_ts_enthalpy_k(-1.0) == 1.0
    assert st.inverse_ts_enthalpy_k(1e9) == 300.0
    assert st.inverse_ts_enthalpy_k(0.65) == pytest.approx(5.0)
    h = st.specific_enthalpy_j_per_kg("ts", 123.0)
    assert st.inverse_ts_enthalpy_k(h) == pytest.approx(123.0)
    # NaN fails every comparison and falls through to the final return.
    assert st.inverse_ts_enthalpy_k(math.nan) == 300.0


def test_table_constants():
    assert st.SSOT_TABLE_27_MASS_KG["LINAC_30"].cold_mass_kg == 12356.0
    assert st.SSOT_TABLE_28_A_VALUES["LINAC_24"].q1_cond_a_m < 0
