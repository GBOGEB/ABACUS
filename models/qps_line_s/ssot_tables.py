"""SSOT Tables 27 / 28 / 29 — Python mirror and NIST AISI 304 conductivity.

All constants transcribed from the SSOT (QPS Addendum II mirror).
CONDUCTION_AL_CONSTANT is CLOSED: a_cond [m] in Table 28 is the empirical
lumped coefficient, used directly as Q_cond = a_cond * INT(lambda_SS dT).
"""

from __future__ import annotations

import math
from bisect import bisect_left
from dataclasses import dataclass
from typing import Literal

LinacConfig = Literal["LINAC_24", "LINAC_30"]
LumpName = Literal["cold", "ts"]


@dataclass(frozen=True)
class LumpedMassKg:
    cold_mass_kg: float
    ts_mass_kg: float


@dataclass(frozen=True)
class HeatLoadAValues:
    # Q1: TS Mass → Cold Mass
    q1_cond_a_m: float        # signed lumped coefficient [m]
    q1_rad_a_w_per_k4: float  # [W/K^4]
    # Q2: Ambient → TS Mass
    q2_cond_a_m: float        # signed lumped coefficient [m]
    q2_rad_a_w_per_k4: float  # [W/K^4]


# SSOT Table 27 — lumped masses
SSOT_TABLE_27_MASS_KG: dict[LinacConfig, LumpedMassKg] = {
    "LINAC_24": LumpedMassKg(cold_mass_kg=9885.0,  ts_mass_kg=8602.0),
    "LINAC_30": LumpedMassKg(cold_mass_kg=12356.0, ts_mass_kg=10753.0),
}

# SSOT Table 28 — static heat-load a coefficients.
# Q_cond = a_cond [m] * INT(lambda_SS dT) [W/m]  -> W
# Q_rad  = a_rad [W/K^4] * (T_hot^4 - T_cold^4) [K^4] -> W
# Negative a_cond is intentional: SSOT integration order is source→receiver,
# so the sign produces positive heat flow from hotter to colder node.
SSOT_TABLE_28_A_VALUES: dict[LinacConfig, HeatLoadAValues] = {
    "LINAC_24": HeatLoadAValues(
        q1_cond_a_m=-2.93,      q1_rad_a_w_per_k4=1.82e-5,
        q2_cond_a_m=-1.13,      q2_rad_a_w_per_k4=5.40e-7,
    ),
    "LINAC_30": HeatLoadAValues(
        q1_cond_a_m=-3.60,      q1_rad_a_w_per_k4=2.24e-5,
        q2_cond_a_m=-1.38,      q2_rad_a_w_per_k4=6.58e-7,
    ),
}

# SSOT Table 29 — specific enthalpy J/kg: (T_K, h_cold, h_ts)
SSOT_TABLE_29_ENTHALPY_J_PER_KG: tuple[tuple[float, float, float], ...] = (
    (1.0,   0.0,     0.0),
    (2.0,   0.6,     0.1),
    (3.0,   1.2,     0.2),
    (4.0,   2.2,     0.4),
    (6.0,   4.9,     0.9),
    (8.0,   9.9,     2.7),
    (10.0,  16.0,    4.9),
    (15.0,  40.3,    17.6),
    (20.0,  84.2,    46.5),
    (25.0,  159.2,   107.9),
    (30.0,  280.4,   218.5),
    (35.0,  465.4,   401.0),
    (40.0,  729.3,   670.7),
    (50.0,  1534.9,  1518.9),
    (60.0,  2685.0,  2810.3),
    (70.0,  4173.2,  4547.0),
    (77.0,  5409.5,  6017.7),
    (80.0,  5982.0,  6710.4),
    (90.0,  8073.3,  9248.1),
    (100.0, 10413.9, 12096.5),
    (120.0, 15695.1, 18566.3),
    (140.0, 21679.0, 25911.4),
    (160.0, 28262.6, 33951.3),
    (180.0, 35377.0, 42530.5),
    (200.0, 42937.0, 51512.2),
    (220.0, 50797.2, 60789.0),
    (240.0, 58829.0, 70288.9),
    (260.0, 66978.2, 79970.8),
    (280.0, 75256.0, 89822.2),
    (300.0, 83753.4, 99870.3),
)

# NIST AISI 304 / UNS S30400 thermal conductivity.
# log10(k [W/m/K]) = sum(c_i * x^i),  x = log10(T [K]),  valid 1–300 K.
_NIST_304_COEFFS = (
    -1.4087,  1.3982,  0.2543, -0.6260,
     0.2334,  0.4256, -0.4658,  0.1650, -0.0199,
)


def k_aisi304_w_m_k(temperature_k: float) -> float:
    """AISI 304 stainless thermal conductivity [W/(m·K)], valid 1–300 K."""
    if not (1.0 <= temperature_k <= 300.0):
        raise ValueError(
            f"AISI 304 fit valid 1–300 K; got {temperature_k:g} K"
        )
    x = math.log10(temperature_k)
    log10_k = sum(c * x ** i for i, c in enumerate(_NIST_304_COEFFS))
    return 10.0 ** log10_k


def integrate_k_signed_w_per_m(
    t_from_k: float,
    t_to_k: float,
    n: int = 64,
) -> float:
    """Signed ∫_{t_from}^{t_to} λ(T) dT  [W/m], Simpson's rule.

    Sign follows SSOT convention: negative when t_to < t_from
    (so a_cond [negative] times this negative integral = positive Q).
    """
    if t_from_k == t_to_k:
        return 0.0
    if n % 2:
        n += 1
    sign = 1.0
    lo, hi = t_from_k, t_to_k
    if t_to_k < t_from_k:
        sign, lo, hi = -1.0, t_to_k, t_from_k
    h = (hi - lo) / n
    total = k_aisi304_w_m_k(lo) + k_aisi304_w_m_k(hi)
    for i in range(1, n):
        total += (4.0 if i % 2 else 2.0) * k_aisi304_w_m_k(lo + i * h)
    return sign * total * h / 3.0


def static_heat_loads_w(
    config: LinacConfig,
    t_cold_k: float,
    t_ts_k: float,
    t_ambient_k: float = 300.0,
) -> dict[str, float]:
    """SSOT Table 28 heat loads [W].

    Q1 > 0 means heat flows from TS Mass into Cold Mass.
    Q2 > 0 means heat flows from ambient into TS Mass.
    """
    a = SSOT_TABLE_28_A_VALUES[config]
    q1_cond = a.q1_cond_a_m * integrate_k_signed_w_per_m(t_ts_k, t_cold_k)
    q1_rad  = a.q1_rad_a_w_per_k4 * (t_ts_k ** 4 - t_cold_k ** 4)
    q2_cond = a.q2_cond_a_m * integrate_k_signed_w_per_m(t_ambient_k, t_ts_k)
    q2_rad  = a.q2_rad_a_w_per_k4 * (t_ambient_k ** 4 - t_ts_k ** 4)
    return {
        "q1_cond_w": q1_cond, "q1_rad_w": q1_rad,
        "q1_total_w": q1_cond + q1_rad,
        "q2_cond_w": q2_cond, "q2_rad_w": q2_rad,
        "q2_total_w": q2_cond + q2_rad,
    }


def specific_enthalpy_j_per_kg(lump: LumpName, temperature_k: float) -> float:
    """Linear interpolation of SSOT Table 29 [J/kg]."""
    pts = SSOT_TABLE_29_ENTHALPY_J_PER_KG
    temps = [r[0] for r in pts]
    if not (temps[0] <= temperature_k <= temps[-1]):
        raise ValueError(
            f"Table 29 range {temps[0]}–{temps[-1]} K; got {temperature_k:g} K"
        )
    col = 1 if lump == "cold" else 2
    idx = bisect_left(temps, temperature_k)
    if idx < len(temps) and pts[idx][0] == temperature_k:
        return pts[idx][col]
    t0, t1 = pts[idx - 1][0], pts[idx][0]
    h0, h1 = pts[idx - 1][col], pts[idx][col]
    return h0 + (h1 - h0) * (temperature_k - t0) / (t1 - t0)


def inverse_ts_enthalpy_k(h_ts_j_per_kg: float) -> float:
    """Inverse of Table 29 TS column: h_ts [J/kg] → T [K]."""
    pts = SSOT_TABLE_29_ENTHALPY_J_PER_KG
    if h_ts_j_per_kg <= pts[0][2]:
        return pts[0][0]
    if h_ts_j_per_kg >= pts[-1][2]:
        return pts[-1][0]
    for i in range(len(pts) - 1):
        t0, _, h0 = pts[i]
        t1, _, h1 = pts[i + 1]
        if h0 <= h_ts_j_per_kg <= h1:
            return t0 + (t1 - t0) * (h_ts_j_per_kg - h0) / (h1 - h0)
    return pts[-1][0]