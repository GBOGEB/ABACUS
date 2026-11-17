"""Lane A wave 12: models/helium_properties/hepak_reference.py loader."""

import pytest

from tests.coverage_waves.lane_a._load import load

mod = load("models/helium_properties/hepak_reference.py")

HEADER = "temperature_K,pressure_Pa,density_kg_m3,enthalpy_J_kg\n"


def _csv(tmp_path, text):
    path = tmp_path / "ref.csv"
    path.write_bytes(text.encode("utf-8"))
    return path


def test_default_reference_location():
    parts = mod.DEFAULT_REFERENCE.parts
    assert parts[-2:] == ("qps_line_s_recovery", "he_reference_hepak.csv")
    assert "density_kg_m3" in mod.REQUIRED_COLUMNS


def test_load_reference_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match="unavailable"):
        mod.load_reference(tmp_path / "none.csv")


def test_load_reference_missing_columns(tmp_path):
    path = _csv(tmp_path, "temperature_K,pressure_Pa\n4.2,100000\n")
    with pytest.raises(ValueError, match="density_kg_m3"):
        mod.load_reference(path)


def test_load_reference_empty_file(tmp_path):
    with pytest.raises(ValueError, match="missing columns"):
        mod.load_reference(_csv(tmp_path, ""))


def test_load_reference_rows(tmp_path):
    path = _csv(tmp_path, HEADER + "4.2,100000,125.0,10000\n5.0,200000,130.0,12000\n")
    rows = mod.load_reference(path)
    assert len(rows) == 2
    assert rows[1]["density_kg_m3"] == "130.0"


def test_reference_status_variants(tmp_path):
    missing = mod.reference_status(tmp_path / "none.csv")
    assert missing["status"] == "UNVALIDATED"
    assert missing["reason"] == "HEPAK_REFERENCE_MISSING"

    bad = mod.reference_status(_csv(tmp_path, "a,b\n1,2\n"))
    assert bad["status"] == "UNVALIDATED"
    assert "missing columns" in bad["reason"]

    good = mod.reference_status(_csv(tmp_path, HEADER + "4.2,1,2,3\n"))
    assert good["status"] == "REFERENCE_AVAILABLE"
    assert good["rows"] == 1
