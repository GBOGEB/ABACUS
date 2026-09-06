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
