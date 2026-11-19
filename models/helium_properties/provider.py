"""Governed helium-4 property provider for ABACUS.

Runtime calculations use the repository-pinned CoolProp backend. HEPAK is an
independent validation oracle, not silently substituted when unavailable.
Results are engineering candidates and never grant compliance credit.

He II guard: the CoolProp helium EOS has its lower limit (Tmin) at the lambda
point. Below it, CoolProp still returns numbers for single-phase T/P calls,
extrapolated across the lambda transition (cp comes out several times too high
at 1.8 K). Those numbers are not He II properties, so ``state_tp`` refuses
T < LAMBDA_K unless the caller asks for the extrapolation explicitly, and then
tags the result as not physical.
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
LAMBDA_K = 2.1768  # lambda point at saturation; equals CoolProp's helium Tmin
SUB_LAMBDA_EXTRAPOLATED = "COOLPROP_EXTRAPOLATED_BELOW_TMIN_NOT_PHYSICAL"


class SubLambdaOutOfRangeError(ValueError):
    """T is below the lambda point (He II), outside the range of the CoolProp helium EOS."""


def require_above_lambda(temperature_K: float, *, context: str = "") -> float:
    """Return T as a float, or raise ``SubLambdaOutOfRangeError`` if T < LAMBDA_K.

    For modules that call CoolProp directly (saturation and flash calls that
    ``state_tp`` does not cover). Wrap every temperature they pass to, or get back
    from, CoolProp. A NaN temperature is refused too.
    """
    T = float(temperature_K)
    if not T >= LAMBDA_K:
        where = f" [{context}]" if context else ""
        raise SubLambdaOutOfRangeError(
            f"HE_II_SUB_LAMBDA_OUT_OF_COOLPROP_RANGE{where}: T={T} K is below the "
            f"lambda point ({LAMBDA_K} K), the lower limit of the CoolProp helium EOS. "
            "Use the HEPAK receipt (qplant_provider) for He II states."
        )
    return T


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


def state_tp(
    temperature_K: float,
    pressure_Pa: float,
    *,
    allow_sub_lambda_extrapolation: bool = False,
) -> HeliumState:
    """Return He-4 properties at T/P with provenance and validation state.

    Below the lambda point this raises ``SubLambdaOutOfRangeError``: governing He II
    values come from the HEPAK receipt (``qplant_provider``). With
    ``allow_sub_lambda_extrapolation=True`` it returns CoolProp's extrapolated numbers
    for diagnostics and V&V comparison only, with ``validation`` set to
    ``SUB_LAMBDA_EXTRAPOLATED``.
    """
    _require_backend()
    T = float(temperature_K)
    P = float(pressure_Pa)
    if not (1.8 <= T <= 300.0):
        raise ValueError("temperature_K outside governed 1.8..300 K envelope")
    if P <= 0.0:
        raise ValueError("pressure_Pa must be positive")
    sub_lambda = T < LAMBDA_K
    if sub_lambda and not allow_sub_lambda_extrapolation:
        raise SubLambdaOutOfRangeError(
            f"HE_II_SUB_LAMBDA_OUT_OF_COOLPROP_RANGE: T={T} K is below the lambda point "
            f"({LAMBDA_K} K), the lower limit of the CoolProp helium EOS. Use the HEPAK "
            "receipt (qplant_provider), or pass allow_sub_lambda_extrapolation=True for a "
            "diagnostic value that is not a He II property."
        )
    phase = str(PropsSI("Phase", "T", T, "P", P, FLUID))
    regime = _regime(T)
    if sub_lambda:
        validation = SUB_LAMBDA_EXTRAPOLATED
    elif T <= LAMBDA_K:
        validation = "HEPAK_REFERENCE_REQUIRED"
    else:
        validation = "RUNTIME_BACKEND_ONLY"
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
