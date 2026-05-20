#!/usr/bin/env python3
"""
Physics Validator — Helium-4 Cryogenic Property Engine
=======================================================

Provides thermodynamic validation for cryogenic engineering data:
  • NIST polynomial fits for He-4 enthalpy, density, viscosity
  • Lambda-point detection (He-II / He-I boundary)
  • Mass-balance verification:  ṁ = (Q_static + Q_dynamic) / Δh
  • Integration hook for GBOGEB/ABACUS verification_hook engine

References:
  - NIST Cryogenics Technologies Group, REFPROP v10
  - Donnelly & Barenghi, J. Phys. Chem. Ref. Data 27, 1217 (1998)
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ============================================================================
# Constants
# ============================================================================
LAMBDA_POINT_K: float = 2.1768          # He-4 superfluid transition
CRITICAL_TEMP_K: float = 5.1953         # He-4 critical temperature
CRITICAL_PRESS_BAR: float = 2.2746      # He-4 critical pressure
R_SPECIFIC_HE: float = 2077.22         # J/(kg·K) — specific gas constant He-4


# ============================================================================
# NIST Polynomial Coefficients (6th-order fits, valid 1.8–5.2 K, 1–3 bar)
# ============================================================================
# Enthalpy h(T) in J/g — fitted to REFPROP v10 isobaric data at ~1.2 bar
ENTHALPY_COEFFS: list[float] = [
    -1.48593e+00,   # a0
     2.09441e+00,   # a1 · T
    -6.31820e-01,   # a2 · T²
     3.82714e-01,   # a3 · T³
    -7.19620e-02,   # a4 · T⁴
     6.84100e-03,   # a5 · T⁵
    -2.55000e-04,   # a6 · T⁶
]

# Density ρ(T) in kg/m³ — saturated liquid at ~1.2 bar
DENSITY_COEFFS: list[float] = [
     1.46200e+02,   # a0
     1.23800e+01,   # a1 · T
    -1.57600e+01,   # a2 · T²
     5.42300e+00,   # a3 · T³
    -9.31000e-01,   # a4 · T⁴
     7.80000e-02,   # a5 · T⁵
    -2.50000e-03,   # a6 · T⁶
]

# Dynamic viscosity μ(T) in μPa·s — He-I regime (T > λ)
VISCOSITY_COEFFS: list[float] = [
     3.67000e+00,
    -1.14200e+00,
     2.31000e-01,
    -2.52000e-02,
     1.50000e-03,
    -4.60000e-05,
     5.70000e-07,
]


def _eval_poly(coeffs: list[float], T: float) -> float:
    """Evaluate polynomial Σ aₙ·Tⁿ."""
    return sum(c * T**n for n, c in enumerate(coeffs))


# ============================================================================
# HeliumPropertyEngine
# ============================================================================
@dataclass
class HeliumPropertyEngine:
    """
    Thermodynamic property calculator for Helium-4.

    Usage::

        engine = HeliumPropertyEngine()
        h = engine.enthalpy(T=2.0)          # J/g
        rho = engine.density(T=2.0)         # kg/m³
        mu = engine.viscosity(T=3.0)        # μPa·s
        phase = engine.phase(T=2.0)         # 'He-II'
    """

    valid_range_K: tuple[float, float] = (1.8, 5.2)

    def _check_range(self, T: float) -> None:
        lo, hi = self.valid_range_K
        if not (lo <= T <= hi):
            raise ValueError(
                f"Temperature {T:.3f} K outside valid range [{lo}, {hi}] K"
            )

    def enthalpy(self, T: float) -> float:
        """Specific enthalpy h(T) in J/g at ~1.2 bar."""
        self._check_range(T)
        return _eval_poly(ENTHALPY_COEFFS, T)

    def density(self, T: float) -> float:
        """Saturated liquid density ρ(T) in kg/m³ at ~1.2 bar."""
        self._check_range(T)
        return _eval_poly(DENSITY_COEFFS, T)

    def viscosity(self, T: float) -> float:
        """Dynamic viscosity μ(T) in μPa·s (He-I regime only)."""
        self._check_range(T)
        if T < LAMBDA_POINT_K:
            raise ValueError(
                f"Viscosity model invalid below λ-point ({LAMBDA_POINT_K} K); "
                f"He-II is a superfluid with vanishing bulk viscosity."
            )
        return _eval_poly(VISCOSITY_COEFFS, T)

    def phase(self, T: float) -> str:
        """Return 'He-II' (superfluid) or 'He-I' (normal fluid)."""
        self._check_range(T)
        return "He-II" if T < LAMBDA_POINT_K else "He-I"

    def is_superfluid(self, T: float) -> bool:
        return self.phase(T) == "He-II"


# ============================================================================
# Mass-Balance Validator
# ============================================================================
@dataclass
class MassBalanceResult:
    """Structured result of a mass-balance check."""
    Q_static_W: float
    Q_dynamic_W: float
    Q_total_W: float
    delta_h_J_g: float
    m_dot_calculated_g_s: float
    m_dot_design_g_s: float
    safety_factor: float
    passed: bool
    message: str


def verify_mass_balance(
    Q_static_W: float,
    Q_dynamic_W: float,
    h_supply_J_g: float,
    h_return_J_g: float,
    m_dot_design_g_s: float,
    safety_factor: float = 1.5,
    tolerance_percent: float = 5.0,
) -> MassBalanceResult:
    """
    Verify cryogenic mass balance:  ṁ = (Q_static + Q_dynamic) / Δh

    Parameters
    ----------
    Q_static_W : float
        Total static heat load [W].
    Q_dynamic_W : float
        Total dynamic heat load [W].
    h_supply_J_g : float
        Supply-side specific enthalpy [J/g].
    h_return_J_g : float
        Return-side specific enthalpy [J/g].
    m_dot_design_g_s : float
        Design mass-flow rate [g/s] (including safety margin).
    safety_factor : float
        Applied safety factor on heat load.
    tolerance_percent : float
        Acceptable deviation between calculated and design flow [%].

    Returns
    -------
    MassBalanceResult
        Structured validation result with PASS/FAIL status.
    """
    Q_total = Q_static_W + Q_dynamic_W
    delta_h = h_return_J_g - h_supply_J_g

    if delta_h <= 0:
        return MassBalanceResult(
            Q_static_W=Q_static_W,
            Q_dynamic_W=Q_dynamic_W,
            Q_total_W=Q_total,
            delta_h_J_g=delta_h,
            m_dot_calculated_g_s=float("nan"),
            m_dot_design_g_s=m_dot_design_g_s,
            safety_factor=safety_factor,
            passed=False,
            message=f"FAIL: Δh = {delta_h:.2f} J/g ≤ 0 — invalid enthalpy difference",
        )

    m_dot_calc = Q_total / delta_h
    m_dot_with_sf = m_dot_calc * safety_factor
    deviation = abs(m_dot_with_sf - m_dot_design_g_s) / m_dot_design_g_s * 100

    passed = deviation <= tolerance_percent
    status = "PASS" if passed else "FAIL"

    msg = (
        f"{status}: ṁ_calc = {m_dot_calc:.3f} g/s, "
        f"ṁ_design = {m_dot_design_g_s:.3f} g/s (SF={safety_factor}), "
        f"deviation = {deviation:.1f}%"
    )

    return MassBalanceResult(
        Q_static_W=Q_static_W,
        Q_dynamic_W=Q_dynamic_W,
        Q_total_W=Q_total,
        delta_h_J_g=delta_h,
        m_dot_calculated_g_s=m_dot_calc,
        m_dot_design_g_s=m_dot_design_g_s,
        safety_factor=safety_factor,
        passed=passed,
        message=msg,
    )


# ============================================================================
# YAML Loader + Full Validation Pipeline
# ============================================================================
def load_engineering_data(yaml_path: str | Path) -> dict[str, Any]:
    """Load and return engineering YAML data."""
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"YAML not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def validate_from_yaml(yaml_path: str | Path) -> dict[str, Any]:
    """
    Run full validation pipeline from YAML SSOT.

    Returns a dict with:
      - property_checks: He-4 property evaluations at key temperatures
      - mass_balance: MassBalanceResult as dict
      - overall_status: 'PASS' or 'FAIL'
    """
    data = load_engineering_data(yaml_path)
    engine = HeliumPropertyEngine()

    cryo = data["cryogenic"]
    metrics = data["engineering_metrics"]
    mb = metrics["mass_balance"]
    summary = metrics["heat_loads"]["summary"]

    # --- Property checks at supply & return temperatures ---
    T_supply = cryo["supply_temperature_K"]
    T_return = cryo["return_temperature_K"]

    props = {
        "supply": {
            "T_K": T_supply,
            "phase": engine.phase(T_supply),
            "enthalpy_J_g": engine.enthalpy(T_supply),
            "density_kg_m3": engine.density(T_supply),
        },
        "return": {
            "T_K": T_return,
            "phase": engine.phase(T_return),
            "enthalpy_J_g": engine.enthalpy(T_return),
            "density_kg_m3": engine.density(T_return),
            "viscosity_uPa_s": engine.viscosity(T_return),
        },
    }

    # --- Mass-balance verification ---
    mb_result = verify_mass_balance(
        Q_static_W=summary["Q_static_W"],
        Q_dynamic_W=summary["Q_dynamic_W"],
        h_supply_J_g=cryo["enthalpy_supply_J_g"],
        h_return_J_g=cryo["enthalpy_return_J_g"],
        m_dot_design_g_s=mb["m_dot_design_g_s"],
        safety_factor=summary["safety_factor"],
    )

    overall = "PASS" if mb_result.passed else "FAIL"

    return {
        "property_checks": props,
        "mass_balance": {
            "Q_static_W": mb_result.Q_static_W,
            "Q_dynamic_W": mb_result.Q_dynamic_W,
            "Q_total_W": mb_result.Q_total_W,
            "delta_h_J_g": mb_result.delta_h_J_g,
            "m_dot_calculated_g_s": mb_result.m_dot_calculated_g_s,
            "m_dot_design_g_s": mb_result.m_dot_design_g_s,
            "safety_factor": mb_result.safety_factor,
            "passed": mb_result.passed,
            "message": mb_result.message,
        },
        "overall_status": overall,
    }


# ============================================================================
# CLI Entry Point
# ============================================================================
def main() -> None:
    """Run validation from command line."""
    yaml_path = Path(__file__).parent / "engineering_data.yaml"
    if len(sys.argv) > 1:
        yaml_path = Path(sys.argv[1])

    print(f"╔══════════════════════════════════════════════════════╗")
    print(f"║  GBOGEB/ABACUS — Physics Validator                  ║")
    print(f"║  Helium-4 Cryogenic Property Engine                  ║")
    print(f"╚══════════════════════════════════════════════════════╝")
    print(f"\nLoading: {yaml_path}\n")

    result = validate_from_yaml(yaml_path)

    # Property checks
    print("── Helium-4 Property Checks ─────────────────────────")
    for side, props in result["property_checks"].items():
        print(f"  [{side.upper()}] T = {props['T_K']} K  →  {props['phase']}")
        print(f"    enthalpy = {props['enthalpy_J_g']:.3f} J/g")
        print(f"    density  = {props['density_kg_m3']:.1f} kg/m³")
        if "viscosity_uPa_s" in props:
            print(f"    viscosity = {props['viscosity_uPa_s']:.3f} μPa·s")
        print()

    # Mass balance
    mb = result["mass_balance"]
    print("── Mass-Balance Verification ────────────────────────")
    print(f"  Formula:   ṁ = (Q_static + Q_dynamic) / Δh")
    print(f"  Q_static  = {mb['Q_static_W']:.1f} W")
    print(f"  Q_dynamic = {mb['Q_dynamic_W']:.1f} W")
    print(f"  Q_total   = {mb['Q_total_W']:.1f} W")
    print(f"  Δh        = {mb['delta_h_J_g']:.2f} J/g")
    print(f"  ṁ_calc    = {mb['m_dot_calculated_g_s']:.3f} g/s")
    print(f"  ṁ_design  = {mb['m_dot_design_g_s']:.3f} g/s (SF={mb['safety_factor']})")
    print(f"\n  ▶ {mb['message']}")

    print(f"\n══ Overall: {result['overall_status']} ══")
    sys.exit(0 if result["overall_status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
