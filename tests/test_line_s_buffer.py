import math

from models.qps_line_s.line_s_buffer import (
    CP_HE,
    CV_HE,
    GAMMA,
    R_HE,
    boiloff_g_s,
    dpdt_bar_per_min,
    integrate,
    time_to_pressure_limit_min,
)


def test_constants_self_consistent():
    assert math.isclose(CP_HE - CV_HE, R_HE, rel_tol=1e-9)
    assert math.isclose(GAMMA, 5 / 3, rel_tol=1e-6)


def test_golden_dpdt_120m3_300k():
    assert math.isclose(dpdt_bar_per_min(12, 120, 300), 0.037390, abs_tol=1e-5)
    assert math.isclose(dpdt_bar_per_min(100, 120, 300), 0.311580, abs_tol=1e-5)


def test_volume_scaling_is_inverse():
    base = dpdt_bar_per_min(100, 120, 300)
    assert math.isclose(dpdt_bar_per_min(100, 9, 300), base * 120 / 9, rel_tol=1e-9)
    assert math.isclose(dpdt_bar_per_min(100, 30, 300), base * 120 / 30, rel_tol=1e-9)


def test_time_to_limit_inverse_of_rate():
    rate = dpdt_bar_per_min(12, 120, 300)
    assert math.isclose(time_to_pressure_limit_min(1.0, 12, 120, 300), 1.0 / rate, rel_tol=1e-9)
    assert time_to_pressure_limit_min(1.0, 0, 120, 300) is None


def test_no_silent_volume_default():
    for bad in (0.0, -1.0):
        try:
            dpdt_bar_per_min(100, bad, 300)
        except ValueError:
            continue
        raise AssertionError("expected ValueError for non-positive v_eff")


def test_boiloff_link():
    assert math.isclose(boiloff_g_s(8700, 20700), 420.3, abs_tol=0.5)


def test_energy_balance_is_gamma_times_ribbon():
    v, p0, t0, dur = 120.0, 1.05, 300.0, 600.0
    mdot = 12.0
    hist = integrate(
        p0_bar=p0,
        t0_k=t0,
        v_eff_m3=v,
        duration_s=dur,
        dt_s=1.0,
        mdot_in_g_s=lambda _t: mdot,
        t_in_k=lambda _t: t0,
        mdot_out_g_s=lambda _t: 0.0,
    )
    dp_energy = hist[-1].p_bar(v) - p0
    dp_ribbon = dpdt_bar_per_min(mdot, v, t0) * (dur / 60.0)
    assert math.isclose(dp_energy, GAMMA * dp_ribbon, rel_tol=1e-6)
    assert hist[-1].t_gas_k > t0
