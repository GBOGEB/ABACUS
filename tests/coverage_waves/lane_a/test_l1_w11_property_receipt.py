"""Lane A wave 11: Line-B property receipt adapter."""

import pytest

from models.qps_line_b import property_receipt as pr

PROV = dict(
    provider_id="abacus.he4",
    provider_version="1.0",
    validity_regime="NORMAL_FLUID",
    source_sha="abc123",
)
STATE = {
    "temperature_K": "4.0",
    "pressure_mbar_abs": 27,
    "density_kg_m3": 5.5,
    "viscosity_Pa_s": 1.2e-6,
}


def _receipt(**overrides):
    fields = dict(
        temperature_K=4.0,
        pressure_mbar_abs=27.0,
        density_kg_m3=5.5,
        viscosity_Pa_s=1.2e-6,
        **PROV,
    )
    fields.update(overrides)
    return pr.PropertyReceipt(**fields)


def test_validate_returns_dict_with_default_classification():
    data = _receipt().validate()
    assert data["classification"] == "DIAGNOSTIC_ONLY"
    assert data["density_kg_m3"] == 5.5
    assert data["source_sha"] == "abc123"


@pytest.mark.parametrize(
    "overrides, message",
    [
        (dict(temperature_K=0.0), "positive T"),
        (dict(pressure_mbar_abs=-1.0), "positive T"),
        (dict(density_kg_m3=0.0), "density and viscosity"),
        (dict(viscosity_Pa_s=-1e-6), "density and viscosity"),
        (dict(provider_id=""), "provenance"),
        (dict(source_sha=""), "provenance"),
        (dict(validity_regime="heii_low_t"), "He-II"),
    ],
)
def test_validate_rejects(overrides, message):
    with pytest.raises(ValueError, match=message):
        _receipt(**overrides).validate()


def test_heii_validated_regime_is_accepted():
    data = _receipt(validity_regime="HEII_VALIDATED_REFERENCE").validate()
    assert data["validity_regime"] == "HEII_VALIDATED_REFERENCE"


def test_from_provider_state_coerces_floats():
    receipt = pr.from_provider_state(STATE, **PROV)
    assert receipt.temperature_K == 4.0
    assert isinstance(receipt.pressure_mbar_abs, float)
    assert receipt.provider_id == "abacus.he4"


def test_from_provider_state_validates_and_requires_keys():
    bad = dict(STATE, density_kg_m3=0)
    with pytest.raises(ValueError, match="density"):
        pr.from_provider_state(bad, **PROV)
    missing = {k: v for k, v in STATE.items() if k != "viscosity_Pa_s"}
    with pytest.raises(KeyError):
        pr.from_provider_state(missing, **PROV)


# Reproduction of a production_defect (see WAVE_LEDGER.jsonl). Named check_*
# so the governed suite does not collect it: a pinned defect must never block the fix.
# Run on demand: pytest -o python_functions=check_* <this file>
def check_production_defect_unvalidated_heii_regime_accepted():
    # Pins the defect: "UNVALIDATED" contains the substring "VALIDATED", so an
    # explicitly unvalidated He-II regime passes the fail-closed gate.
    # This check will fail once property_receipt.py:29 is fixed.
    data = _receipt(validity_regime="HEII_UNVALIDATED").validate()
    assert data["validity_regime"] == "HEII_UNVALIDATED"
