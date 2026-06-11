"""
HP Compressor Redundancy & Reliability Analysis — v4.0.0

CRITICAL CORRECTION (v4.0.0):
  - HP compressor count reduced from 4 to 3 (Kaeser FSD 575 SFC)
  - Design flow achievable with 3 units: 337.62 g/s max (3 × 112.54)
  - Expected operational flow: 304 g/s
  - Motor power corrected to 315 kW per vendor sheet (was 400 kW generic)
  - Package power: 348.54 kW (water-cooled)

Models N-of-M parallel compressor configurations for helium HP supply:
  - N=3 baseline (2-out-of-3)
  - N+1 FSD575 VFD (2-of-3 active, N=3 total with VFD)
  - N+1 HSD Twin Combi (1-out-of-2)

All parameters loaded from data/config.yaml (SSoT).

Reference: MIL-HDBK-217, IEEE 493, IEC 61078.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional

import pandas as pd

# ── Load from SSoT ──────────────────────────────────────────────────
from src.config_loader import cfg

# ── Constants (from SSoT where applicable) ──────────────────────────
HOURS_PER_YEAR = 8760.0
OPERATING_HOURS_YEAR = cfg.get('financial.operating_hours_year', 8000.0)
ELECTRICITY_COST_EUR_KWH = cfg.get('financial.electricity_cost_eur_kwh', 0.15)

# FSD575 specs from SSoT
_FSD575 = cfg.get('compressor_specifications.fsd575', {})
_HP = cfg.get('compressor_specifications.hp_compressors', {})
FSD575_MOTOR_KW = _FSD575.get('motor_power_kW', 315)
FSD575_PACKAGE_KW = _FSD575.get('package_power_kW', 348.54)
FSD575_PER_UNIT_FLOW_GS = _FSD575.get('per_unit_flow_gs', 112.54)
FSD575_CAPITAL_EUR = _FSD575.get('capital_cost_eur', 200000)
FSD575_MAINT_EUR = _FSD575.get('annual_maint_eur', 15000)
FSD575_MTBF = _FSD575.get('mtbf_hours', 8760)
FSD575_MTTR = _FSD575.get('mttr_hours', 8)
HP_COUNT = _HP.get('count', 3)


@dataclass
class CompressorConfig:
    """Definition of a compressor configuration."""
    name: str
    total_units: int           # M — total installed
    required_units: int        # k — minimum for full operation
    capacity_per_unit_pct: float  # % of total system capacity per unit
    mtbf_hours: float = 8760.0    # per-unit MTBF
    mttr_hours: float = 8.0       # per-unit MTTR
    power_kw: float = 348.54      # per-unit package power (corrected)
    has_vfd: bool = False
    vfd_turndown_min: float = 0.30  # minimum speed fraction
    capital_cost_eur: float = 200000.0  # per unit (corrected)
    annual_maint_eur: float = 15000.0   # per unit
    compressor_type: str = "oil-flooded screw"
    efficiency_pct: float = 72.5


# ── Pre-defined configurations (CORRECTED for v4.0.0) ───────────────

CONFIGS = {
    "N3_baseline": CompressorConfig(
        name="N=3 Baseline (2-of-3)",
        total_units=3,
        required_units=2,
        capacity_per_unit_pct=50.0,
        mtbf_hours=FSD575_MTBF,
        mttr_hours=FSD575_MTTR,
        power_kw=FSD575_PACKAGE_KW,
        has_vfd=False,
        capital_cost_eur=FSD575_CAPITAL_EUR,
        annual_maint_eur=FSD575_MAINT_EUR,
        compressor_type="oil-flooded screw (fixed speed)",
        efficiency_pct=72.5,
    ),
    "N1_FSD575_VFD": CompressorConfig(
        name="N+1 FSD575 VFD (2-of-3)",
        total_units=HP_COUNT,       # 3 units (CORRECTED from 4)
        required_units=2,
        capacity_per_unit_pct=50.0,
        mtbf_hours=FSD575_MTBF,
        mttr_hours=FSD575_MTTR,
        power_kw=FSD575_PACKAGE_KW,
        has_vfd=True,
        vfd_turndown_min=0.30,
        capital_cost_eur=FSD575_CAPITAL_EUR,
        annual_maint_eur=FSD575_MAINT_EUR,
        compressor_type="oil-flooded screw + VFD",
        efficiency_pct=72.5,
    ),
    "N1_HSD_twin": CompressorConfig(
        name="N+1 HSD Twin Combi (1-of-2)",
        total_units=2,
        required_units=1,
        capacity_per_unit_pct=100.0,
        mtbf_hours=8760,
        mttr_hours=8,
        power_kw=575,
        has_vfd=False,
        capital_cost_eur=350000,
        annual_maint_eur=10000,
        compressor_type="oil-free centrifugal twin-head",
        efficiency_pct=82.5,
    ),
}


# ── Single-unit calculations ───────────────────────────────────────

def failure_rate(mtbf: float) -> float:
    """Failure rate λ = 1/MTBF [failures/hour]."""
    return 1.0 / mtbf


def single_availability(mtbf: float, mttr: float) -> float:
    """Steady-state availability A = MTBF / (MTBF + MTTR)."""
    return mtbf / (mtbf + mttr)


def single_reliability(t_hours: float, mtbf: float) -> float:
    """Reliability at time t: R(t) = e^(-λt)."""
    lam = failure_rate(mtbf)
    return math.exp(-lam * t_hours)


# ── k-out-of-M system calculations ────────────────────────────────

def _comb(n: int, k: int) -> int:
    """Binomial coefficient C(n, k)."""
    return math.comb(n, k)


def system_availability_k_of_m(A: float, M: int, k: int) -> float:
    """
    Availability of a k-out-of-M parallel system.
    System works if ≥ k of M units are operational.

    A_sys = Σ_{i=k}^{M} C(M,i) × A^i × (1-A)^(M-i)
    """
    q = 1.0 - A  # unavailability
    a_sys = 0.0
    for i in range(k, M + 1):
        a_sys += _comb(M, i) * (A ** i) * (q ** (M - i))
    return a_sys


def system_reliability_k_of_m(t_hours: float, mtbf: float,
                                M: int, k: int) -> float:
    """
    Reliability of a k-out-of-M system at time t.
    R_sys(t) = Σ_{i=k}^{M} C(M,i) × R(t)^i × (1-R(t))^(M-i)
    """
    R = single_reliability(t_hours, mtbf)
    F = 1.0 - R
    r_sys = 0.0
    for i in range(k, M + 1):
        r_sys += _comb(M, i) * (R ** i) * (F ** (M - i))
    return r_sys


def system_mtbf_approx(A_sys: float, mttr_sys: float = 8.0) -> float:
    """
    Approximate system MTBF from system availability.
    A_sys = MTBF_sys / (MTBF_sys + MTTR_sys)
    => MTBF_sys = A_sys × MTTR_sys / (1 - A_sys)
    """
    if A_sys >= 1.0:
        return float("inf")
    return A_sys * mttr_sys / (1.0 - A_sys)


def downtime_hours_year(A_sys: float) -> float:
    """Annual downtime in hours from system availability."""
    return HOURS_PER_YEAR * (1.0 - A_sys)


# ── VFD Energy Savings ─────────────────────────────────────────────

def vfd_power_at_load(full_load_kw: float, load_fraction: float,
                       vfd_efficiency: float = 0.97) -> float:
    """
    Power consumption with VFD at partial load.
    Affinity law for compressors: P ∝ Speed³
    With VFD: speed ∝ load → P = P_full × (load)³ / η_VFD
    """
    return full_load_kw * (load_fraction ** 3) / vfd_efficiency


def fixed_speed_power_at_load(full_load_kw: float,
                                load_fraction: float) -> float:
    """
    Fixed-speed compressor with unloading.
    Simplified: draws ~70% power at 50% load (typical screw with slide valve).
    Linear interpolation: P = P_full × (0.4 + 0.6 × load_fraction)
    """
    return full_load_kw * (0.4 + 0.6 * load_fraction)


def annual_energy_savings_vfd(
    full_load_kw: float = FSD575_PACKAGE_KW,
    avg_load_fraction: float = 0.70,
    operating_hours: float = OPERATING_HOURS_YEAR,
    electricity_cost: float = ELECTRICITY_COST_EUR_KWH,
    vfd_efficiency: float = 0.97,
) -> dict:
    """Calculate annual energy savings from VFD vs fixed-speed."""
    P_fixed = fixed_speed_power_at_load(full_load_kw, avg_load_fraction)
    P_vfd = vfd_power_at_load(full_load_kw, avg_load_fraction, vfd_efficiency)

    E_fixed = P_fixed * operating_hours  # kWh/yr
    E_vfd = P_vfd * operating_hours
    delta_E = E_fixed - E_vfd
    savings_eur = delta_E * electricity_cost
    savings_pct = (delta_E / E_fixed) * 100 if E_fixed > 0 else 0

    return {
        "power_fixed_kw": round(P_fixed, 1),
        "power_vfd_kw": round(P_vfd, 1),
        "energy_fixed_kwh_yr": round(E_fixed, 0),
        "energy_vfd_kwh_yr": round(E_vfd, 0),
        "energy_savings_kwh_yr": round(delta_E, 0),
        "cost_savings_eur_yr": round(savings_eur, 0),
        "savings_pct": round(savings_pct, 1),
    }


# ── Comprehensive comparison ──────────────────────────────────────

def build_comparison_table() -> pd.DataFrame:
    """Build full comparison table for all predefined configurations."""
    rows = []
    for key, c in CONFIGS.items():
        A_single = single_availability(c.mtbf_hours, c.mttr_hours)
        A_sys = system_availability_k_of_m(A_single, c.total_units,
                                            c.required_units)
        dt = downtime_hours_year(A_sys)
        mtbf_sys = system_mtbf_approx(A_sys, c.mttr_hours)

        total_capex = c.capital_cost_eur * c.total_units
        total_maint = c.annual_maint_eur * c.total_units

        # Energy cost (running units × power × operating hours)
        running = c.required_units
        if c.has_vfd:
            avg_load = 0.70
            P_per = vfd_power_at_load(c.power_kw, avg_load)
        else:
            P_per = c.power_kw
        annual_energy_cost = running * P_per * OPERATING_HOURS_YEAR * ELECTRICITY_COST_EUR_KWH

        rows.append({
            "config_key": key,
            "name": c.name,
            "units": f"{c.total_units}×{c.capacity_per_unit_pct:.0f}%",
            "redundancy": f"{c.required_units}-of-{c.total_units}",
            "type": c.compressor_type,
            "A_single_pct": round(A_single * 100, 4),
            "A_system_pct": round(A_sys * 100, 6),
            "A_system_nines": -math.log10(1 - A_sys) if A_sys < 1 else float("inf"),
            "downtime_h_yr": round(dt, 4),
            "MTBF_system_hours": round(mtbf_sys, 0),
            "MTBF_system_years": round(mtbf_sys / HOURS_PER_YEAR, 1),
            "total_capex_eur": total_capex,
            "annual_maint_eur": total_maint,
            "annual_energy_eur": round(annual_energy_cost, 0),
            "total_annual_opex_eur": round(total_maint + annual_energy_cost, 0),
            "has_vfd": c.has_vfd,
            "efficiency_pct": c.efficiency_pct,
        })

    return pd.DataFrame(rows)


def build_reliability_curves(
    t_max_hours: float = 8760.0,
    n_points: int = 200,
) -> pd.DataFrame:
    """Build R(t) curves for all configurations."""
    import numpy as np
    times = np.linspace(0, t_max_hours, n_points)
    data = {"hours": times}

    for key, c in CONFIGS.items():
        R_vals = [
            system_reliability_k_of_m(t, c.mtbf_hours,
                                       c.total_units, c.required_units)
            for t in times
        ]
        data[c.name] = R_vals

    return pd.DataFrame(data)


def build_vfd_savings_table(
    full_load_kw: float = FSD575_PACKAGE_KW,
    loads: list[float] | None = None,
) -> pd.DataFrame:
    """Build table comparing fixed-speed vs VFD at various load points."""
    if loads is None:
        loads = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]

    rows = []
    for load in loads:
        info = annual_energy_savings_vfd(full_load_kw, load)
        info["load_pct"] = round(load * 100, 0)
        rows.append(info)

    return pd.DataFrame(rows)


# ── Quick report ───────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"=== HP Compressor Redundancy Comparison (v{cfg.version}) ===\n")
    print(f"HP Compressor Count: {HP_COUNT} (from SSoT)")
    print(f"FSD575 Package Power: {FSD575_PACKAGE_KW} kW\n")
    df = build_comparison_table()
    display_cols = ["name", "redundancy", "A_system_pct", "downtime_h_yr",
                    "MTBF_system_years", "total_capex_eur", "total_annual_opex_eur"]
    print(df[display_cols].to_string(index=False))

    print(f"\n=== VFD Energy Savings ({FSD575_PACKAGE_KW} kW unit) ===\n")
    vfd_df = build_vfd_savings_table()
    print(vfd_df[["load_pct", "power_fixed_kw", "power_vfd_kw",
                   "cost_savings_eur_yr", "savings_pct"]].to_string(index=False))
