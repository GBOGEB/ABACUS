"""
Liquid Helium Inventory Loss Calculator — v3.1.0

Converts gas-phase leak rates (mbar·L/s) into liquid helium inventory
depletion metrics: mass flow, liquid volume loss, cost, and time-to-depletion.

Physics:
  Gas leak from liquid space → liquid boils to replace lost gas.
  Mass conservation: ṁ_leak,gas = ṁ_boiloff,liquid (steady state)
  ṁ_gas = (Q [Pa·m³/s] × M [kg/mol]) / (R [J/mol·K] × T [K])
  V̇_liq = ṁ_gas / ρ_liq

Reference: NIST REFPROP He-4, ideal gas law with compressibility correction.
"""

from __future__ import annotations
import math
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd

# ── Physical constants ──────────────────────────────────────────────
R_UNIVERSAL = 8.314462618  # J/(mol·K)
MOLAR_MASS_HE = 0.004003   # kg/mol (He-4)
SECONDS_PER_YEAR = 365.25 * 24 * 3600  # 31,557,600 s
SECONDS_PER_DAY = 86400

# ── Liquid He reference properties (saturated, 1 atm, 4.222 K) ─────
RHO_LIQ_DEFAULT = 124.96     # kg/m³
H_VAP_DEFAULT = 20.9e3       # J/kg  (20.9 kJ/kg)
T_NBP = 4.222                # K  normal boiling point
HE_PRICE_EUR_PER_KG = 120.0  # €/kg (2024 market estimate, varies)


@dataclass(frozen=True)
class LiquidHeState:
    """Operating condition for liquid He inventory loss calculation."""
    leak_rate_mbar_l_s: float        # volumetric throughput leak rate
    temperature_K: float = 4.222     # gas temperature at leak point
    pressure_bar_abs: float = 1.0    # pressure at leak point
    compressibility_Z: float = 1.0   # Z factor (≈1 for low-P gas)
    rho_liquid_kg_m3: float = RHO_LIQ_DEFAULT
    h_vap_J_kg: float = H_VAP_DEFAULT
    label: str = ""


def mbar_l_s_to_pa_m3_s(q: float) -> float:
    """Convert mbar·L/s → Pa·m³/s.  1 mbar = 100 Pa, 1 L = 1e-3 m³.
    => 1 mbar·L/s = 100 × 1e-3 = 0.1 Pa·m³/s."""
    return q * 0.1


def gas_mass_flow_kg_s(q_mbar_l_s: float, T_K: float, P_bar: float,
                        Z: float = 1.0) -> float:
    """
    Convert volumetric leak rate to mass flow.
    
    ṁ = Q_throughput [Pa·m³/s] × M / (R × T)
    
    Note: Q_throughput in mbar·L/s is already a PV throughput 
    (pressure × volume / time), so it encodes the amount of gas.
    At the measurement reference condition (usually ~room T, ~1 bar),
    Q = P_ref × V̇_ref.  For a fixed Q, the actual mass flow is:
    ṁ = Q [Pa·m³/s] × M / (R × T_ref)
    
    For leaks specified at the *operating* temperature T:
    ṁ = Q [Pa·m³/s] × M / (Z × R × T)
    """
    Q_pa_m3_s = mbar_l_s_to_pa_m3_s(q_mbar_l_s)
    return (Q_pa_m3_s * MOLAR_MASS_HE) / (Z * R_UNIVERSAL * T_K)


def liquid_volume_loss_L_s(mass_flow_kg_s: float,
                            rho_liq: float = RHO_LIQ_DEFAULT) -> float:
    """Liquid volume loss rate in litres/s."""
    # 1 m³ = 1000 L
    return (mass_flow_kg_s / rho_liq) * 1000.0


def compute_liquid_loss(state: LiquidHeState) -> dict:
    """
    Full liquid He loss calculation from a single leak point.
    
    Returns dict with all derived quantities.
    """
    q = state.leak_rate_mbar_l_s
    T = state.temperature_K
    P = state.pressure_bar_abs
    Z = state.compressibility_Z
    rho = state.rho_liquid_kg_m3
    h_vap = state.h_vap_J_kg

    # Mass flow
    m_dot_kg_s = gas_mass_flow_kg_s(q, T, P, Z)
    m_dot_g_s = m_dot_kg_s * 1000.0
    m_dot_g_year = m_dot_g_s * SECONDS_PER_YEAR
    m_dot_kg_year = m_dot_g_year / 1000.0

    # Liquid volume loss
    v_dot_L_s = liquid_volume_loss_L_s(m_dot_kg_s, rho)
    v_dot_L_day = v_dot_L_s * SECONDS_PER_DAY
    v_dot_L_year = v_dot_L_s * SECONDS_PER_YEAR

    # Energy (boil-off power)
    Q_boiloff_W = m_dot_kg_s * h_vap  # Watts

    # Cost
    cost_eur_year = m_dot_kg_year * HE_PRICE_EUR_PER_KG
    cost_eur_day = cost_eur_year / 365.25

    return {
        "leak_rate_mbar_l_s": q,
        "temperature_K": T,
        "pressure_bar": P,
        "Z": Z,
        "label": state.label,
        # Mass flow
        "mass_flow_kg_s": m_dot_kg_s,
        "mass_flow_g_s": m_dot_g_s,
        "mass_flow_g_year": m_dot_g_year,
        "mass_flow_kg_year": m_dot_kg_year,
        # Liquid volume
        "liquid_loss_L_s": v_dot_L_s,
        "liquid_loss_L_day": v_dot_L_day,
        "liquid_loss_L_year": v_dot_L_year,
        # Energy
        "boiloff_power_W": Q_boiloff_W,
        # Cost
        "cost_eur_day": cost_eur_day,
        "cost_eur_year": cost_eur_year,
    }


def build_leak_rate_liquid_loss_table(
    leak_rates: list[float] | None = None,
    temperature_K: float = 4.222,
    pressure_bar: float = 1.0,
    rho_liq: float = RHO_LIQ_DEFAULT,
) -> pd.DataFrame:
    """
    Build a table of liquid He losses for standard leak rate values.
    """
    if leak_rates is None:
        leak_rates = [1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2]

    rows = []
    for q in leak_rates:
        state = LiquidHeState(
            leak_rate_mbar_l_s=q,
            temperature_K=temperature_K,
            pressure_bar_abs=pressure_bar,
            rho_liquid_kg_m3=rho_liq,
            label=f"{q:.0e}",
        )
        result = compute_liquid_loss(state)
        rows.append(result)

    return pd.DataFrame(rows)


def inventory_depletion_timeseries(
    initial_volume_L: float = 5000.0,
    leak_rates: list[float] | None = None,
    duration_days: int = 365,
    temperature_K: float = 4.222,
    pressure_bar: float = 1.0,
    min_level_fraction: float = 0.20,
) -> pd.DataFrame:
    """
    Time-series of liquid He inventory level for multiple leak rate scenarios.
    
    Returns DataFrame with columns: day, and one column per leak rate 
    showing remaining liquid volume (L).
    """
    if leak_rates is None:
        leak_rates = [1e-9, 1e-8, 1e-5, 1e-4]

    days = list(range(0, duration_days + 1))
    data = {"day": days}

    for q in leak_rates:
        state = LiquidHeState(
            leak_rate_mbar_l_s=q,
            temperature_K=temperature_K,
            pressure_bar_abs=pressure_bar,
        )
        result = compute_liquid_loss(state)
        loss_L_day = result["liquid_loss_L_day"]

        col_name = f"Q={q:.0e}"
        levels = []
        for d in days:
            remaining = max(0.0, initial_volume_L - loss_L_day * d)
            levels.append(remaining)
        data[col_name] = levels

    df = pd.DataFrame(data)
    df.attrs["initial_volume_L"] = initial_volume_L
    df.attrs["min_level_L"] = initial_volume_L * min_level_fraction
    return df


def time_to_threshold(
    initial_volume_L: float,
    leak_rate_mbar_l_s: float,
    threshold_fraction: float = 0.20,
    temperature_K: float = 4.222,
    pressure_bar: float = 1.0,
) -> float:
    """
    Calculate days until liquid inventory drops to threshold level.
    Returns float('inf') if loss rate is effectively zero.
    """
    state = LiquidHeState(
        leak_rate_mbar_l_s=leak_rate_mbar_l_s,
        temperature_K=temperature_K,
        pressure_bar_abs=pressure_bar,
    )
    result = compute_liquid_loss(state)
    loss_L_day = result["liquid_loss_L_day"]
    if loss_L_day <= 0:
        return float("inf")
    
    depletable = initial_volume_L * (1.0 - threshold_fraction)
    return depletable / loss_L_day


# ── Convenience: example calculation from task spec ─────────────────
def example_calculation():
    """
    Reproduce the example from the task specification.
    Leak: 1×10⁻⁵ mbar·L/s at 4K, 1 bar
    Expected: ~37.9 g/year, ~0.303 L/year
    """
    state = LiquidHeState(
        leak_rate_mbar_l_s=1e-5,
        temperature_K=4.0,
        pressure_bar_abs=1.0,
        label="RTM-048 system max example"
    )
    result = compute_liquid_loss(state)
    print(f"Leak rate: {result['leak_rate_mbar_l_s']:.0e} mbar·L/s")
    print(f"Mass flow: {result['mass_flow_g_year']:.2f} g/year")
    print(f"Liquid loss: {result['liquid_loss_L_year']:.4f} L/year")
    print(f"Cost: €{result['cost_eur_year']:.2f}/year")
    return result


if __name__ == "__main__":
    print("=== Liquid He Loss Example ===")
    example_calculation()
    print()
    print("=== Standard Leak Rate Table ===")
    df = build_leak_rate_liquid_loss_table()
    print(df[["leak_rate_mbar_l_s", "mass_flow_g_year", "liquid_loss_L_year", "cost_eur_year"]].to_string(index=False))
