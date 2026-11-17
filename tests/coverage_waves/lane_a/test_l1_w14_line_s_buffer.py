"""Lane A wave 14: models.qps_line_s.line_s_buffer closed form and integrator."""

import runpy

import pytest

from models.qps_line_s import line_s_buffer as lb
from tests.coverage_waves.lane_a._load import REPO


def _const(value):
    def fn(_t):
        return value

    return fn


def test_gas_constants():
    assert lb.GAMMA == pytest.approx(5.0 / 3.0)
    assert lb.CP_HE - lb.CV_HE == pytest.approx(lb.R_HE)


def test_dpdt_and_validation():
    rate = lb.dpdt_bar_per_min(1000.0, lb.R_HE, 1.0)
    assert rate == pytest.approx(60.0 / lb.PA_PER_BAR)
    with pytest.raises(ValueError, match="v_eff_m3"):
        lb.dpdt_bar_per_min(1.0, 0.0, 300.0)


def test_time_to_limit_positive_and_none():
    rate = lb.dpdt_bar_per_min(12.0, 30.0, 300.0)
    assert lb.time_to_pressure_limit_min(1.0, 12.0, 30.0, 300.0) == pytest.approx(
        1.0 / rate
    )
    assert lb.time_to_pressure_limit_min(1.0, 0.0, 30.0, 300.0) is None
    assert lb.time_to_pressure_limit_min(1.0, -5.0, 30.0, 300.0) is None


def test_boiloff():
    assert lb.boiloff_g_s(23.3, 23300.0) == pytest.approx(1.0)
    with pytest.raises(ValueError, match="dh_release"):
        lb.boiloff_g_s(1.0, 0.0)


def test_initial_state_roundtrip():
    s = lb.initial_state(1.3, 300.0, 30.0)
    assert s.t_s == 0.0
    assert s.t_gas_k == pytest.approx(300.0)
    assert s.p_bar(30.0) == pytest.approx(1.3)


def test_integrate_no_flow_is_steady():
    out = lb.integrate(
        p0_bar=1.2,
        t0_k=80.0,
        v_eff_m3=10.0,
        duration_s=5.0,
        mdot_in_g_s=_const(0.0),
        t_in_k=_const(300.0),
        mdot_out_g_s=_const(0.0),
    )
    assert len(out) == 6
    assert out[-1].t_s == pytest.approx(5.0)
    assert out[-1].p_bar(10.0) == pytest.approx(1.2)


def test_integrate_charging_beats_isothermal_ribbon():
    v, t0, dur = 10.0, 300.0, 60.0
    out = lb.integrate(
        p0_bar=1.0,
        t0_k=t0,
        v_eff_m3=v,
        duration_s=dur,
        dt_s=2.0,
        mdot_in_g_s=_const(10.0),
        t_in_k=_const(t0),
        mdot_out_g_s=_const(0.0),
    )
    rise = out[-1].p_bar(v) - out[0].p_bar(v)
    iso = lb.dpdt_bar_per_min(10.0, v, t0) * dur / 60.0
    assert rise == pytest.approx(iso * lb.GAMMA, rel=1e-6)
    assert out[-1].t_gas_k > t0


def test_integrate_wall_heat_and_outflow():
    out = lb.integrate(
        p0_bar=2.0,
        t0_k=100.0,
        v_eff_m3=5.0,
        duration_s=10.0,
        mdot_in_g_s=_const(0.0),
        t_in_k=_const(100.0),
        mdot_out_g_s=_const(1.0),
        qdot_wall_w=_const(500.0),
    )
    assert out[-1].m_kg < out[0].m_kg
    with pytest.raises(ValueError, match="v_eff_m3"):
        lb.integrate(
            p0_bar=1.0,
            t0_k=100.0,
            v_eff_m3=-1.0,
            duration_s=1.0,
            mdot_in_g_s=_const(0.0),
            t_in_k=_const(0.0),
            mdot_out_g_s=_const(0.0),
        )


def test_script_entry_prints_table(capsys):
    runpy.run_path(
        str(REPO / "models" / "qps_line_s" / "line_s_buffer.py"), run_name="__main__"
    )
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 3
    assert out[0].startswith("V_eff=   9.0 m3")
