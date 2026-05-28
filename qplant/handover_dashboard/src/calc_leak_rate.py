"""Core leak-rate physics engine (no empirical alignment factors).

This module converts helium leak-rate specifications from mbar·L/s to
mass-flow units using first principles from ideal-gas throughput.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt
from typing import Iterable

import pandas as pd

# Physical constants
R_UNIVERSAL = 8.314462618  # J/(mol·K) == Pa·m³/(mol·K)
MOLAR_MASS_HE_G_PER_MOL = 4.002602  # g/mol
MOLAR_MASS_HE_KG_PER_MOL = MOLAR_MASS_HE_G_PER_MOL / 1000.0
SECONDS_PER_DAY = 86_400
SECONDS_PER_YEAR = 365.25 * SECONDS_PER_DAY
HE_GAMMA = 1.66
STANDARD_HE_DENSITY_KG_PER_NM3 = 0.1785  # at 0 °C and 1 atm (normal conditions)


@dataclass(frozen=True)
class LeakState:
    leak_rate_mbar_l_s: float
    temperature_k: float
    pressure_bar_abs: float


# ----------------------------
# Unit conversion primitives
# ----------------------------

def mbar_l_s_to_pa_m3_s(leak_rate_mbar_l_s: float) -> float:
    """Convert mbar·L/s -> Pa·m³/s.

    1 mbar = 100 Pa
    1 L = 1e-3 m³
    => 1 mbar·L/s = 0.1 Pa·m³/s
    """
    return leak_rate_mbar_l_s * 0.1


def leak_rate_to_molar_flow_mol_s(
    leak_rate_mbar_l_s: float,
    temperature_k: float,
    pressure_bar_abs: float = 1.0,
    reference_pressure_bar: float = 1.0,
) -> float:
    """Convert leak-rate throughput to molar flow.

    The leak-rate class is interpreted as throughput at reference pressure
    (default 1 bar differential). A linear pressure ratio scaling is applied
    for comparative operating-point sensitivity.
    """
    q_pa_m3_s = mbar_l_s_to_pa_m3_s(leak_rate_mbar_l_s)
    pressure_ratio = pressure_bar_abs / reference_pressure_bar
    return (q_pa_m3_s * pressure_ratio) / (R_UNIVERSAL * temperature_k)


def leak_rate_to_mass_flow_g_s(
    leak_rate_mbar_l_s: float,
    temperature_k: float,
    pressure_bar_abs: float = 1.0,
    reference_pressure_bar: float = 1.0,
) -> float:
    mol_s = leak_rate_to_molar_flow_mol_s(
        leak_rate_mbar_l_s=leak_rate_mbar_l_s,
        temperature_k=temperature_k,
        pressure_bar_abs=pressure_bar_abs,
        reference_pressure_bar=reference_pressure_bar,
    )
    return mol_s * MOLAR_MASS_HE_G_PER_MOL


def leak_rate_to_mass_flow_g_year(
    leak_rate_mbar_l_s: float,
    temperature_k: float,
    pressure_bar_abs: float = 1.0,
    reference_pressure_bar: float = 1.0,
) -> float:
    return (
        leak_rate_to_mass_flow_g_s(
            leak_rate_mbar_l_s,
            temperature_k,
            pressure_bar_abs,
            reference_pressure_bar,
        )
        * SECONDS_PER_YEAR
    )


def normal_m3_per_day_to_kg_per_year(normal_m3_per_day: float) -> float:
    """Convert normal m³/day helium flow to kg/year for RTM checks."""
    return normal_m3_per_day * STANDARD_HE_DENSITY_KG_PER_NM3 * 365.25


# ----------------------------
# Thermodynamic/context helpers
# ----------------------------

def helium_density_kg_m3(temperature_k: float, pressure_bar_abs: float) -> float:
    p_pa = pressure_bar_abs * 1e5
    return p_pa * MOLAR_MASS_HE_KG_PER_MOL / (R_UNIVERSAL * temperature_k)


def choked_flow_critical_ratio(gamma: float = HE_GAMMA) -> float:
    return (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))


def sonic_flow_indicators(
    leak_rate_mbar_l_s: float,
    temperature_k: float,
    upstream_pressure_bar: float,
    downstream_pressure_bar: float = 1.0,
    leak_diameter_m: float = 50e-6,
) -> dict[str, float]:
    """Simple notional leak-path flow indicators for triage context."""
    rho = helium_density_kg_m3(temperature_k, upstream_pressure_bar)
    m_dot_kg_s = (
        leak_rate_to_mass_flow_g_s(leak_rate_mbar_l_s, temperature_k, upstream_pressure_bar)
        / 1000.0
    )
    area_m2 = pi * (leak_diameter_m**2) / 4.0
    velocity_m_s = m_dot_kg_s / max(rho * area_m2, 1e-30)

    pressure_ratio = downstream_pressure_bar / max(upstream_pressure_bar, 1e-12)
    critical_ratio = choked_flow_critical_ratio()
    is_choked = pressure_ratio <= critical_ratio

    a_sound_m_s = sqrt(max(HE_GAMMA * (8.314462618 / MOLAR_MASS_HE_KG_PER_MOL) * temperature_k, 1e-12))
    mach = velocity_m_s / a_sound_m_s

    return {
        "density_kg_m3": rho,
        "velocity_m_s": velocity_m_s,
        "speed_of_sound_m_s": a_sound_m_s,
        "mach_est": mach,
        "critical_pressure_ratio": critical_ratio,
        "actual_pressure_ratio": pressure_ratio,
        "is_choked": 1.0 if is_choked else 0.0,
    }


# ----------------------------
# Tabular builders
# ----------------------------

def build_conversion_grid(
    leak_classes: Iterable[float],
    temperatures_k: Iterable[float],
    pressures_bar_abs: Iterable[float],
) -> pd.DataFrame:
    rows: list[dict[str, float]] = []
    for leak in leak_classes:
        for t in temperatures_k:
            for p in pressures_bar_abs:
                g_s = leak_rate_to_mass_flow_g_s(leak, t, p)
                indicators = sonic_flow_indicators(leak, t, p)
                rows.append(
                    {
                        "leak_rate_mbar_l_s": leak,
                        "temperature_K": t,
                        "pressure_bar_abs": p,
                        "mass_flow_g_s": g_s,
                        "mass_flow_g_day": g_s * SECONDS_PER_DAY,
                        "mass_flow_g_year": g_s * SECONDS_PER_YEAR,
                        **indicators,
                    }
                )
    return pd.DataFrame(rows)


def dimensional_proof(leak_rate_mbar_l_s: float, temperature_k: float, pressure_bar_abs: float) -> dict[str, float]:
    """Return full worked conversion chain for transparency pages/tests."""
    q_pa_m3_s = mbar_l_s_to_pa_m3_s(leak_rate_mbar_l_s)
    pressure_ratio = pressure_bar_abs / 1.0
    n_dot = (q_pa_m3_s * pressure_ratio) / (R_UNIVERSAL * temperature_k)
    m_dot_g_s = n_dot * MOLAR_MASS_HE_G_PER_MOL
    return {
        "q_input_mbar_l_s": leak_rate_mbar_l_s,
        "q_si_pa_m3_s": q_pa_m3_s,
        "pressure_ratio": pressure_ratio,
        "temperature_k": temperature_k,
        "n_dot_mol_s": n_dot,
        "m_dot_g_s": m_dot_g_s,
        "m_dot_g_day": m_dot_g_s * SECONDS_PER_DAY,
        "m_dot_g_year": m_dot_g_s * SECONDS_PER_YEAR,
    }
