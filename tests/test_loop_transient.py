"""Golden tests — SSOT Table 28 LOOP boil-off transient (NIST AISI 304)."""

from models.qps_line_s.loop_transient import simulate
from models.qps_line_s.ssot_tables import (
    k_aisi304_w_m_k,
    integrate_k_signed_w_per_m,
    static_heat_loads_w,
)


# --- NIST conductivity sanity ---

def test_nist_k_at_4k():
    k = k_aisi304_w_m_k(4.0)
    assert 0.1 < k < 1.0, f"k(4K)={k:.4f} W/mK out of expected range"


def test_nist_k_at_300k():
    k = k_aisi304_w_m_k(300.0)
    assert 10.0 < k < 20.0, f"k(300K)={k:.4f} W/mK out of expected range"


def test_nist_k_monotonically_increasing():
    temps = [4, 10, 50, 100, 200, 300]
    ks = [k_aisi304_w_m_k(t) for t in temps]
    assert ks == sorted(ks)


# --- conduction integral sign convention (matches SSOT negative a_cond) ---

def test_conduction_integral_hot_to_cold_is_negative():
    # INT(T_hot -> T_cold) with T_hot > T_cold is negative
    assert integrate_k_signed_w_per_m(50.0, 2.0) < 0


def test_conduction_integral_cold_to_hot_is_positive():
    assert integrate_k_signed_w_per_m(2.0, 50.0) > 0


def test_conduction_integral_antisymmetric():
    a = integrate_k_signed_w_per_m(50.0, 2.0)
    b = integrate_k_signed_w_per_m(2.0, 50.0)
    assert abs(a + b) < 1e-6


# --- SSOT Table 28 heat loads at nominal initial state ---

def test_q1_positive_at_nominal_ts():
    # Q1 (TS->Cold): heat flows cold-ward -> must be positive
    q = static_heat_loads_w("LINAC_30", t_cold_k=2.0, t_ts_k=50.0)
    assert q["q1_total_w"] > 0
    assert q["q1_cond_w"] > 0
    assert q["q1_rad_w"] > 0


def test_q2_positive_at_nominal_ts():
    # Q2 (Ambient->TS): ambient warms the TS -> must be positive
    q = static_heat_loads_w("LINAC_30", t_cold_k=2.0, t_ts_k=50.0)
    assert q["q2_total_w"] > 0


def test_q1_initial_magnitude():
    # Pin the SSOT-derived initial heat load against the computed value
    q = static_heat_loads_w("LINAC_30", t_cold_k=2.0, t_ts_k=50.0)
    assert 550 < q["q1_total_w"] < 750, (
        f"Q1(50K)={q['q1_total_w']:.0f} W outside expected 550-750 W range"
    )


def test_conduction_grows_with_ts_temperature():
    # As T_TS warms, the conduction integral (TS->cold) grows
    q50  = static_heat_loads_w("LINAC_30", 2.0, 50.0)
    q100 = static_heat_loads_w("LINAC_30", 2.0, 100.0)
    q200 = static_heat_loads_w("LINAC_30", 2.0, 200.0)
    assert q50["q1_cond_w"] < q100["q1_cond_w"] < q200["q1_cond_w"]


# --- full simulation golden bounds ---

def test_ssot_simulation_dryout_in_bracket():
    # SSOT result must fall between radiation-only (~4 h) and D2.1 baseline (~2 h)
    r = simulate("LINAC_30")
    assert 1.0 < r["dryout_h"] < 4.0, (
        f"dry-out {r['dryout_h']} h outside [1, 4] h bracket"
    )


def test_ssot_simulation_peak_flow_nontrivial():
    # The peak must exceed pure radiation-only (~50 g/s) — conduction is on
    r = simulate("LINAC_30")
    assert r["peak_g_s"] > 55


def test_ssot_simulation_linac24_vs_linac30():
    # LINAC_30 has larger a_cond and more mass; compare directionally
    r24 = simulate("LINAC_24")
    r30 = simulate("LINAC_30")
    # larger cold-path coefficients in LINAC_30 drive more Q1 -> higher peak
    assert r30["peak_g_s"] > r24["peak_g_s"]