"""QPS Line S LOOP / recovery lumped mass-energy balance.

This is Tier-B evidence for ASSUM-ENERGY-MODEL. It does not resolve or accept
any gate automatically. Confirm inventory, compressor timing, pressure limits,
and recovery-power basis before using results externally.
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from CoolProp.CoolProp import PropsSI
except ImportError:  # pragma: no cover - tests use importorskip before simulation
    PropsSI = None

FLUID = "Helium"
BAR = 1e5
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "qps_line_s_recovery" / "generated"


@dataclass
class Config:
    m_liq0_kg: float = 400.0       # RFI: liquid helium inventory anchor
    m_metal_kg: float = 10000.0    # RFI: 2 K-stage effective metal mass
    p_suction_bar: float = 1.05    # RFI: WCS compressor suction basis
    comp_cap_kgs: float = 0.112    # RFI: WCS capacity, 112 g/s
    comp_start_s: float = 120.0    # RFI: compressor start delay
    balloon_vol_m3: float = 80.0   # RFI: interim warm buffer volume
    balloon_fill_bar: float = 1.0
    balloon_T_K: float = 300.0
    p_open_bar: float = 1.5        # RFI: control-valve / relief-opening basis
    p_psv_bar: float = 1.7         # RFI: PSV cap basis
    ramp_s: float = 300.0          # RFI: boil-off rise time to peak
    dt_s: float = 1.0
    t_max_s: float = 7200.0


def require_coolprop() -> None:
    if PropsSI is None:
        raise RuntimeError("missing dependency: pip install CoolProp")


def sat_pressure(T: float) -> float:
    require_coolprop()
    return PropsSI("P", "T", T, "Q", 0, FLUID)


def sat_temp(P: float) -> float:
    require_coolprop()
    return PropsSI("T", "P", P, "Q", 0, FLUID)


def latent_heat(T: float) -> float:
    require_coolprop()
    return PropsSI("H", "T", T, "Q", 1, FLUID) - PropsSI("H", "T", T, "Q", 0, FLUID)


def liquid_cp(T: float) -> float:
    require_coolprop()
    return PropsSI("C", "T", T, "Q", 0, FLUID)


def metal_cp(T: float) -> float:
    """Placeholder low-temperature metal heat capacity.

    Replace with an H(T) spline when the NIST material table is wired in.
    """
    return max(0.05, 0.0016 * T)


def balloon_capacity(cfg: Config) -> float:
    require_coolprop()
    rho = PropsSI("D", "P", cfg.balloon_fill_bar * BAR, "T", cfg.balloon_T_K, FLUID)
    return rho * cfg.balloon_vol_m3


def boiloff(t: float, peak_kgs: float, cfg: Config) -> float:
    return peak_kgs * min(1.0, t / cfg.ramp_s) if cfg.ramp_s > 0 else peak_kgs


def simulate(peak_kgs: float, cfg: Config | None = None, blocked_in: bool = False) -> dict[str, Any]:
    require_coolprop()
    cfg = Config() if cfg is None else cfg
    comp_cap = 0.0 if blocked_in else cfg.comp_cap_kgs
    bal_cap = 0.0 if blocked_in else balloon_capacity(cfg)
    p_suction = cfg.p_suction_bar * BAR

    T = sat_temp(p_suction)
    P = p_suction
    m_liq = cfg.m_liq0_kg
    m_bal = 0.0
    m_recovered = 0.0
    m_vented = 0.0
    t = 0.0
    t_relief = None
    p_peak = P

    while t < cfg.t_max_s and m_liq > 0.0:
        gen = boiloff(t, peak_kgs, cfg)
        comp = comp_cap if (t >= cfg.comp_start_s and P >= p_suction) else 0.0
        net = gen - comp
        m_liq -= gen * cfg.dt_s
        m_recovered += comp * cfg.dt_s

        if P >= cfg.p_open_bar * BAR:
            m_vented += max(0.0, net) * cfg.dt_s
            P = min(P, cfg.p_psv_bar * BAR)
            if t_relief is None:
                t_relief = t
        elif net <= 0.0:
            m_bal = max(0.0, m_bal + net * cfg.dt_s)
            P = p_suction
            T = sat_temp(P)
        else:
            to_bal = min(net * cfg.dt_s, bal_cap - m_bal)
            m_bal += to_bal
            retained = net * cfg.dt_s - to_bal
            if retained > 0.0:
                Ceff = m_liq * liquid_cp(T) + cfg.m_metal_kg * metal_cp(T)
                T += retained * latent_heat(T) / Ceff
                P = sat_pressure(T)

        p_peak = max(p_peak, P)
        t += cfg.dt_s

    return {
        "peak_g_s": round(peak_kgs * 1000, 1),
        "mode": "blocked_in" if blocked_in else "recovery",
        "verdict": "RELIEF" if t_relief is not None else "RECOVERED",
        "t_relief_min": round(t_relief / 60, 2) if t_relief is not None else None,
        "p_peak_bar": round(p_peak / BAR, 3),
        "kg_recovered": round(m_recovered, 1),
        "kg_vented": round(m_vented, 1),
    }


def default_rows(cfg: Config | None = None) -> list[dict[str, Any]]:
    cfg = Config() if cfg is None else cfg
    rows = [simulate(peak, cfg) for peak in (0.05, 0.10, 0.20)]
    rows.append(simulate(0.20, cfg, blocked_in=True))
    return rows


def write_outputs(rows: list[dict[str, Any]], out_dir: Path = OUT) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    cols = ["peak_g_s", "mode", "verdict", "t_relief_min", "p_peak_bar", "kg_recovered", "kg_vented"]
    with (out_dir / "recovery_matrix.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# QPS Line S - recovery matrix",
        "",
        "Generated by `models/qps_line_s/recovery_model.py`.",
        "Values are Tier-B evidence only and do not resolve gates automatically.",
        "",
        "| " + " | ".join(cols) + " |",
        "|" + "|".join(["---"] * len(cols)) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row[col]) for col in cols) + " |")
    (out_dir / "recovery_matrix.md").write_text("\n".join(lines) + "\n")


def print_table(rows: list[dict[str, Any]]) -> None:
    cols = ["peak_g_s", "mode", "verdict", "t_relief_min", "p_peak_bar", "kg_recovered", "kg_vented"]
    print("\t".join(cols))
    for row in rows:
        print("\t".join(str(row[col]) for col in cols))


def main() -> int:
    try:
        rows = default_rows(Config())
    except RuntimeError as exc:
        sys.exit(str(exc))
    write_outputs(rows)
    print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
