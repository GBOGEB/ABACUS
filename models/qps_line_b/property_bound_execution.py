"""W53/P05D provenance-bound execution wrapper for the P05C sensitivity runner."""
from dataclasses import dataclass
from .bounded_sensitivity import diagnostic_population, worst_case, one_at_a_time_sensitivity


@dataclass(frozen=True)
class PropertyReceipt:
    temperature_K: float
    pressure_mbar_abs: float
    density_kg_m3: float
    viscosity_pa_s: float
    provider_id: str
    provider_version: str
    validity_regime: str
    source_sha: str

    def validate(self) -> None:
        if self.temperature_K <= 0 or self.pressure_mbar_abs <= 0:
            raise ValueError("positive thermodynamic state required")
        if self.density_kg_m3 <= 0 or self.viscosity_pa_s <= 0:
            raise ValueError("positive density and viscosity required")
        if not all((self.provider_id, self.provider_version, self.validity_regime, self.source_sha)):
            raise ValueError("complete provider provenance required")


def execute(receipt: PropertyReceipt) -> dict:
    receipt.validate()
    rows = diagnostic_population(
        density_kg_m3=receipt.density_kg_m3,
        viscosity_pa_s=receipt.viscosity_pa_s,
    )
    return {
        "classification": "DIAGNOSTIC_ONLY",
        "property_receipt": receipt.__dict__,
        "population_size": len(rows),
        "worst_case": worst_case(rows),
        "sensitivity_ranking": one_at_a_time_sensitivity(rows),
    }
