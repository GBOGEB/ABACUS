"""QPS Line S — LOOP boil-off transient (SSOT Tables 27/28/29 + NIST 304).

CONDUCTION_AL_CONSTANT is CLOSED. The Table 28 a_cond [m] values are the
SSOT empirical lumped coefficients used directly in:

    Q_cond = a_cond * INT_{T_from}^{T_to} lambda_SS(T) dT

where lambda_SS comes from the NIST AISI 304 / UNS S30400 log-polynomial fit
(1–300 K). Conduction is temperature-dependent at every time step — it grows
as T_TS warms, which is the correct physical driver of the accelerating boil-off.

Physics (cooling stopped; cold mass isothermal at 2 K while liquid remains):

    dH_TS/dt  = (Q2 - Q1)          [W = J/s]
    dm_LHe/dt = -Q1 / h_fg(2K)     [kg/s]
    mdot_relief = Q1 / h_fg         [kg/s] -> converted to g/s for output

    Q1 (Table 28, TS → Cold Mass):
        Q1_cond = a1_cond * INT_{T_TS}^{T_cold} lambda(T) dT
        Q1_rad  = a1_rad  * (T_TS^4 - T_cold^4)

    Q2 (Table 28, Ambient → TS Mass):
        Q2_cond = a2_cond * INT_{T_amb}^{T_TS} lambda(T) dT
        Q2_rad  = a2_rad  * (T_amb^4 - T_TS^4)

Run:  python -m models.qps_line_s.loop_transient
"""

from __future__ import annotations

from models.qps_line_s.ssot_tables import (
    SSOT_TABLE_27_MASS_KG,
    inverse_ts_enthalpy_k,
    specific_enthalpy_j_per_kg,
    static_heat_loads_w,
)

T_AMB   = 300.0   # K, ambient (fixed)
T_COLD  = 2.0     # K, cold-mass temperature while liquid present
M_LHE_KG   = 391.5   # LHe inventory: 2700 L * 0.145 kg/L  (D2.1 §5.6.5)
H_FG_2K    = 23300.0  # J/kg, latent heat of He-4 at 2 K


def simulate(
    config: str = "LINAC_30",
    t0_ts_k: float = 50.0,
    dt_s: float = 1.0,
    max_h: float = 12.0,
) -> dict:
    """Euler integration of the two-lump energy balance using SSOT Table 28.

    Returns dry-out time, peak and average relief flow, and a sparse series.
    """
    masses = SSOT_TABLE_27_MASS_KG[config]  # type: ignore[index]
    m_ts = masses.ts_mass_kg

    t_ts  = t0_ts_k
    h_ts  = specific_enthalpy_j_per_kg("ts", t_ts)   # J/kg (specific)
    m_lhe = M_LHE_KG
    t_s   = 0.0
    series: list[tuple[float, float, float, float]] = []
    peak   = 0.0
    boiled = 0.0

    n_steps = int(max_h * 3600 / dt_s)
    for _ in range(n_steps):
        q = static_heat_loads_w(config, T_COLD, t_ts, T_AMB)
        q1 = q["q1_total_w"]
        q2 = q["q2_total_w"]

        mdot_g_s = 1000.0 * q1 / H_FG_2K
        peak = max(peak, mdot_g_s)

        h_ts  += (q2 - q1) * dt_s / m_ts   # specific enthalpy advance [J/kg]
        t_ts   = inverse_ts_enthalpy_k(h_ts)
        dm     = q1 * dt_s / H_FG_2K
        m_lhe -= dm
        boiled += dm
        t_s   += dt_s

        if t_s % 600 < dt_s:
            series.append((
                round(t_s / 3600, 3),
                round(mdot_g_s, 1),
                round(t_ts, 1),
                round(max(m_lhe, 0.0), 1),
            ))
        if m_lhe <= 0:
            break

    avg = 1000.0 * boiled / t_s if t_s else 0.0
    return {
        "config": config,
        "dryout_h":     round(t_s / 3600, 2),
        "peak_g_s":     round(peak, 1),
        "avg_g_s":      round(avg, 1),
        "ts_at_dryout_k": round(t_ts, 1),
        "series":       series,
    }


def render(config: str = "LINAC_30") -> str:
    r = simulate(config)
    q_nom = static_heat_loads_w(config, T_COLD, 50.0, T_AMB)
    lines = [
        f"LOOP boil-off transient ({config}, SSOT Tables 27/28/29 + NIST AISI 304).",
        "CONDUCTION_AL_CONSTANT closed — a_cond [m] from Table 28 used directly.",
        f"Relief flow mdot(t) = Q1(T_TS) / h_fg(2K); conduction grows as T_TS warms.",
        "",
        f"  dry-out:  {r['dryout_h']} h",
        f"  peak:     {r['peak_g_s']} g/s",
        f"  average:  {r['avg_g_s']} g/s",
        f"  T_TS at dry-out: {r['ts_at_dryout_k']} K",
        "",
        f"Q1 at T_TS=50 K (initial): "
        f"cond={q_nom['q1_cond_w']:.0f} W  rad={q_nom['q1_rad_w']:.0f} W  "
        f"total={q_nom['q1_total_w']:.0f} W",
        f"Q2 at T_TS=50 K (initial): "
        f"cond={q_nom['q2_cond_w']:.0f} W  rad={q_nom['q2_rad_w']:.0f} W  "
        f"total={q_nom['q2_total_w']:.0f} W",
        "",
        "D2.1 targets: avg >120 g/s, peak >150 g/s, 200 g/s spike.",
        "Bracket vs D2.1: ~3.9 h (radiation-only), ~2.0 h (D2.1 baseline).",
        "Remaining open: RECOVERY_POWER_DURING_LOOP (diesel backup credit).",
    ]
    return "\n".join(lines)


def main() -> None:
    print(render())


if __name__ == "__main__":
    main()