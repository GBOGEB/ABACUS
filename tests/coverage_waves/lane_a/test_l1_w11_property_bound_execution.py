"""Lane A wave 11: provenance-bound execution wrapper."""

import pytest

from models.qps_line_b import property_bound_execution as pbe


def _receipt(**overrides):
    fields = dict(
        temperature_K=4.0,
        pressure_mbar_abs=27.0,
        density_kg_m3=5.5,
        viscosity_pa_s=1.2e-6,
        provider_id="abacus.he4",
        provider_version="1.0",
        validity_regime="NORMAL_FLUID",
        source_sha="abc123",
    )
    fields.update(overrides)
    return pbe.PropertyReceipt(**fields)


def test_execute_returns_diagnostic_bundle():
    result = pbe.execute(_receipt())
    assert result["classification"] == "DIAGNOSTIC_ONLY"
    assert result["population_size"] == 243
    assert result["property_receipt"]["provider_id"] == "abacus.he4"
    assert result["worst_case"]["classification"] == "DIAGNOSTIC_ONLY"
    factors = {r["factor"] for r in result["sensitivity_ranking"]}
    assert factors == {
        "distance_m",
        "diameter_m",
        "roughness_m",
        "k_local",
        "mass_flow_kg_s",
    }


@pytest.mark.parametrize(
    "overrides, message",
    [
        (dict(temperature_K=-1.0), "thermodynamic"),
        (dict(pressure_mbar_abs=0.0), "thermodynamic"),
        (dict(density_kg_m3=0.0), "density"),
        (dict(viscosity_pa_s=0.0), "density"),
        (dict(provider_version=""), "provenance"),
        (dict(validity_regime=""), "provenance"),
    ],
)
def test_execute_fails_closed_on_invalid_receipt(overrides, message):
    with pytest.raises(ValueError, match=message):
        pbe.execute(_receipt(**overrides))
