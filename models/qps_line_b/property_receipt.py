"""W53/P05E property receipt adapter for Line-B VLP execution.

Normal-fluid execution may use the governed He-4 provider. He-II/sub-lambda states
remain fail-closed unless an independently validated low-temperature provider/reference
is available. No fallback constants are permitted.
"""
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class PropertyReceipt:
    temperature_K: float
    pressure_mbar_abs: float
    density_kg_m3: float
    viscosity_Pa_s: float
    provider_id: str
    provider_version: str
    validity_regime: str
    source_sha: str
    classification: str = "DIAGNOSTIC_ONLY"

    def validate(self) -> dict:
        if self.temperature_K <= 0 or self.pressure_mbar_abs <= 0:
            raise ValueError("positive T and absolute P required")
        if self.density_kg_m3 <= 0 or self.viscosity_Pa_s <= 0:
            raise ValueError("positive density and viscosity required")
        if not all((self.provider_id, self.provider_version, self.validity_regime, self.source_sha)):
            raise ValueError("provider provenance and source SHA required")
        if "HEII" in self.validity_regime.upper() and "VALIDATED" not in self.validity_regime.upper():
            raise ValueError("He-II receipt requires independent validation")
        return asdict(self)


def from_provider_state(state: dict, *, provider_id: str, provider_version: str,
                        validity_regime: str, source_sha: str) -> PropertyReceipt:
    """Create the typed receipt from an already-governed provider state.

    This adapter intentionally does not invent properties or invoke an ungoverned
    fallback. The upstream provider must supply density and dynamic viscosity.
    """
    receipt = PropertyReceipt(
        temperature_K=float(state["temperature_K"]),
        pressure_mbar_abs=float(state["pressure_mbar_abs"]),
        density_kg_m3=float(state["density_kg_m3"]),
        viscosity_Pa_s=float(state["viscosity_Pa_s"]),
        provider_id=provider_id,
        provider_version=provider_version,
        validity_regime=validity_regime,
        source_sha=source_sha,
    )
    receipt.validate()
    return receipt
