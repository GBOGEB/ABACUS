"""W53/P05A deterministic Line-B hydraulic proof harness.

Engineering acceptance requires source-bound geometry and a validated helium-property
provider. This module deliberately refuses to turn bounded geometry or unvalidated
He-II properties into accepted results.
"""
from dataclasses import dataclass
from math import log10, pi


@dataclass(frozen=True)
class Segment:
    length_m: float
    diameter_m: float
    roughness_m: float
    k_local: float = 0.0


def friction_factor(reynolds: float, rel_roughness: float) -> float:
    if reynolds <= 0:
        raise ValueError("reynolds must be positive")
    if reynolds < 2300:
        return 64.0 / reynolds
    # Swamee-Jain explicit approximation; deterministic and auditable.
    return 0.25 / (log10(rel_roughness / 3.7 + 5.74 / reynolds**0.9) ** 2)


def pressure_drop_pa(segment: Segment, mass_flow_kg_s: float, density_kg_m3: float,
                     viscosity_pa_s: float) -> float:
    if min(segment.length_m, segment.diameter_m, density_kg_m3, viscosity_pa_s) <= 0:
        raise ValueError("positive geometry and fluid properties required")
    area = pi * segment.diameter_m**2 / 4.0
    velocity = mass_flow_kg_s / (density_kg_m3 * area)
    reynolds = density_kg_m3 * velocity * segment.diameter_m / viscosity_pa_s
    f = friction_factor(reynolds, segment.roughness_m / segment.diameter_m)
    dynamic = density_kg_m3 * velocity**2 / 2.0
    return (f * segment.length_m / segment.diameter_m + segment.k_local) * dynamic


def qcell_pressure_mbar(boundary_mbar_abs: float, cumulative_dp_pa: float) -> float:
    if boundary_mbar_abs <= 0 or cumulative_dp_pa < 0:
        raise ValueError("invalid pressure inputs")
    return boundary_mbar_abs + cumulative_dp_pa / 100.0


def pressure_margin_mbar(required_max_mbar_abs: float, predicted_mbar_abs: float) -> float:
    """Positive margin means predicted suction pressure is below the allowed maximum."""
    return required_max_mbar_abs - predicted_mbar_abs


def acceptance_class(*, exact_geometry: bool, heii: bool, low_t_provider_validated: bool) -> str:
    if not exact_geometry:
        return "DIAGNOSTIC_ONLY"
    if heii and not low_t_provider_validated:
        return "DEFER"
    return "ELIGIBLE_FOR_CHILD_REVIEW"
