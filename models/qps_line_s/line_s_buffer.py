"""QPS Line S pressure-buffer model - Wave 0 spine.

Scope (MDA only): the reduced control-volume needed to answer RTM-261/292.
NOT a SIMCRYOGENICS reproduction.

Design rules enforced here:
  * No hardcoded V_eff or T baseline. Both are REQUIRED inputs. The old
    V_EFF = 120.0 default is removed on purpose: 120 m3 was carried over from
    an unrelated storage-vessel question and may be wrong for a DN150 line.
  * Mass balance alone is non-conservative for early charging. Injecting gas
    into a rigid control volume carries flow work, so the fixed-T closed form
    under-predicts pressure rise. The energy-balance integrator is the
    defensible model; the closed form is kept only as a labelled sanity ribbon.

Helium, ideal-gas default (Z approximately 1.00-1.02 at <=16 bar and >=80 K).
CoolProp may be added later behind a flag; not imported here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

R_HE = 2077.2
CV_HE = 1.5 * R_HE
CP_HE = 2.5 * R_HE
GAMMA = CP_HE / CV_HE
PA_PER_BAR = 1.0e5


def dpdt_bar_per_min(mdot_net_g_s: float, v_eff_m3: float, t_gas_k: float) -> float:
    """Isothermal ideal-gas sanity ribbon only.

    dP/dt = mdot_net * R * T / V.
    This holds temperature fixed and therefore under-predicts the early
    energy-balance charging rise. It remains useful as a reproducible check.
    """
    if v_eff_m3 <= 0:
        raise ValueError("v_eff_m3 must be > 0")
    mdot_kg_s = mdot_net_g_s / 1000.0
    dp_pa_s = mdot_kg_s * R_HE * t_gas_k / v_eff_m3
    return dp_pa_s * 60.0 / PA_PER_BAR


def time_to_pressure_limit_min(
    delta_p_bar: float, mdot_net_g_s: float, v_eff_m3: float, t_gas_k: float
) -> float | None:
    """Allowed transient time = available margin / pressure-rise rate."""
    rate = dpdt_bar_per_min(mdot_net_g_s, v_eff_m3, t_gas_k)
    if rate <= 0:
        return None
    return delta_p_bar / rate


def boiloff_g_s(qdot_w: float, dh_release_j_kg: float) -> float:
    """Relief mass flow from bath heat load: mdot = Qdot / dh_release.

    dh_release is a registered calibrated quantity, not the shield-coolant
    sensible heat cp*dT term.
    """
    if dh_release_j_kg <= 0:
        raise ValueError("dh_release_j_kg must be > 0")
    return 1000.0 * qdot_w / dh_release_j_kg


@dataclass(frozen=True)
class State:
    t_s: float
    m_kg: float
    u_j: float

    @property
    def t_gas_k(self) -> float:
        return self.u_j / (self.m_kg * CV_HE)

    def p_bar(self, v_eff_m3: float) -> float:
        return self.m_kg * R_HE * self.t_gas_k / v_eff_m3 / PA_PER_BAR


def initial_state(p0_bar: float, t0_k: float, v_eff_m3: float) -> State:
    m0 = p0_bar * PA_PER_BAR * v_eff_m3 / (R_HE * t0_k)
    return State(0.0, m0, m0 * CV_HE * t0_k)


def integrate(
    *,
    p0_bar: float,
    t0_k: float,
    v_eff_m3: float,
    duration_s: float,
    dt_s: float = 1.0,
    mdot_in_g_s: Callable[[float], float],
    t_in_k: Callable[[float], float],
    mdot_out_g_s: Callable[[float], float],
    qdot_wall_w: Callable[[float], float] = lambda _t: 0.0,
) -> list[State]:
    """Rigid control-volume first-law energy balance.

    dm/dt = mdot_in - mdot_out
    dU/dt = mdot_in*cp*T_in - mdot_out*cp*T_cv + Qdot_wall

    All flows are callables of time so the D2.1 LOOP profiles can be dropped in.
    Required keyword arguments only: there is no implicit baseline volume.
    """
    if v_eff_m3 <= 0:
        raise ValueError("v_eff_m3 must be > 0")

    def deriv(t: float, m: float, u: float) -> tuple[float, float]:
        t_cv = u / (m * CV_HE)
        min_kg = mdot_in_g_s(t) / 1000.0
        mout_kg = mdot_out_g_s(t) / 1000.0
        dm = min_kg - mout_kg
        du = min_kg * CP_HE * t_in_k(t) - mout_kg * CP_HE * t_cv + qdot_wall_w(t)
        return dm, du

    s = initial_state(p0_bar, t0_k, v_eff_m3)
    out = [s]
    t, m, u = 0.0, s.m_kg, s.u_j
    n = int(round(duration_s / dt_s))
    for _ in range(n):
        k1m, k1u = deriv(t, m, u)
        k2m, k2u = deriv(t + dt_s / 2, m + dt_s / 2 * k1m, u + dt_s / 2 * k1u)
        k3m, k3u = deriv(t + dt_s / 2, m + dt_s / 2 * k2m, u + dt_s / 2 * k2u)
        k4m, k4u = deriv(t + dt_s, m + dt_s * k3m, u + dt_s * k3u)
        m += dt_s / 6 * (k1m + 2 * k2m + 2 * k3m + k4m)
        u += dt_s / 6 * (k1u + 2 * k2u + 2 * k3u + k4u)
        t += dt_s
        out.append(State(t, m, u))
    return out


if __name__ == "__main__":
    for v in (9.0, 30.0, 120.0):
        print(
            f"V_eff={v:6.1f} m3  "
            f"dP/dt(12 g/s)={dpdt_bar_per_min(12, v, 300):.4f}  "
            f"dP/dt(100 g/s)={dpdt_bar_per_min(100, v, 300):.4f} bar/min"
        )
