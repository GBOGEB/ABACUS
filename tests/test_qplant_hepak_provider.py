from pathlib import Path

import pytest

from models.helium_properties.qplant_provider import governing_provider_for_temperature, state_tp


def test_hepak_band_includes_both_boundaries():
    assert governing_provider_for_temperature(2.0) == "HEPAK"
    assert governing_provider_for_temperature(4.5) == "HEPAK"
    assert governing_provider_for_temperature(4.500001) == "CoolProp"


def test_low_temperature_fails_closed_without_receipt():
    with pytest.raises(RuntimeError, match="QPLANT_HEPAK_RECEIPT_REQUIRED"):
        state_tp(4.5, 300000.0)


def test_missing_receipt_file_fails_closed(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="QPLANT governing HEPAK CSV unavailable"):
        state_tp(3.8, 2600.0, hepak_csv=tmp_path / "missing.csv")


@pytest.mark.parametrize("t", [1.8, 1.99, 2.1768])
def test_he_ii_below_lambda_is_hepak_governed(t):
    # Owner decision 2026-10-11: HEPAK governs all T <= 4.5 K, including He-II.
    assert governing_provider_for_temperature(t) == "HEPAK"


def test_he_ii_fails_closed_without_receipt():
    with pytest.raises(RuntimeError, match="QPLANT_HEPAK_RECEIPT_REQUIRED"):
        state_tp(1.8, 1640.0)


@pytest.mark.parametrize("t", [0.0, -1.0, float("nan")])
def test_non_positive_temperature_is_rejected(t):
    with pytest.raises(ValueError, match="QPLANT_INVALID_TEMPERATURE"):
        governing_provider_for_temperature(t)
