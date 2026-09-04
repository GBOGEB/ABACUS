"""Governed helium-4 property provider for ABACUS.

Runtime calculations use the repository-pinned CoolProp backend. HEPAK is an
independent validation oracle, not silently substituted when unavailable.
Results are engineering candidates and never grant compliance credit.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

try:
    import CoolProp
    from CoolProp.CoolProp import PropsSI
except ImportError:  # pragma: no cover
    CoolProp = None
    PropsSI = None

FLUID = "Helium"
BAR = 1e5
LAMBDA_K = 2.1768


@dataclass(frozen=True)
class HeliumState:
    temperature_K: float
    pressure_Pa: float
    density_kg_m3: float
    enthalpy_J_kg: float
    entropy_J_kgK: float
    cp_J_kgK: float
    cv_J_kgK: float
    viscosity_Pa_s: float
    conductivity_W_mK: float
    phase: str
    backend: str
    backend_version: str
    validation: str
    regime: str
    formal_credit_delta: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _require_backend() -> None:
    if PropsSI is None:
        raise RuntimeError("missing dependency: CoolProp==7.2.0")


def _regime(T: float) -> str:
    if T <= LAMBDA_K:
        return "HE_II_SUB_LAMBDA_REQUIRES_HEPAK_VALIDATION"
    if T <= 4.5:
        return "HE_I_CRYOGENIC"
    if T <= 80.0:
        return "HE_I_INTERMEDIATE"
    return "HE_I_WARM"


def state_tp(temperature_K: float, pressure_Pa: float) -> HeliumState:
    """Return He-4 properties at T/P with provenance and validation state."""
    _require_backend()
    T = float(temperature_K)
    P = float(pressure_Pa)
    if not (1.8 <= T <= 300.0):
        raise ValueError("temperature_K outside governed 1.8..300 K envelope")
    if P <= 0.0:
        raise ValueError("pressure_Pa must be positive")
    phase = str(PropsSI("Phase", "T", T, "P", P, FLUID))
    regime = _regime(T)
    validation = "HEPAK_REFERENCE_REQUIRED" if T <= LAMBDA_K else "RUNTIME_BACKEND_ONLY"
    return HeliumState(
        temperature_K=T,
        pressure_Pa=P,
        density_kg_m3=PropsSI("D", "T", T, "P", P, FLUID),
        enthalpy_J_kg=PropsSI("H", "T", T, "P", P, FLUID),
        entropy_J_kgK=PropsSI("S", "T", T, "P", P, FLUID),
        cp_J_kgK=PropsSI("C", "T", T, "P", P, FLUID),
        cv_J_kgK=PropsSI("O", "T", T, "P", P, FLUID),
        viscosity_Pa_s=PropsSI("V", "T", T, "P", P, FLUID),
        conductivity_W_mK=PropsSI("L", "T", T, "P", P, FLUID),
        phase=phase,
        backend="CoolProp",
        backend_version=getattr(CoolProp, "__version__", "unknown"),
        validation=validation,
        regime=regime,
    )
