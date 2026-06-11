from __future__ import annotations

from src.config_loader import ConfigLoader, cfg


def test_default_config_loads_v4():
    loader = ConfigLoader()
    assert loader.version == "4.4.0"


def test_dot_path_access_key_values():
    assert cfg.get("compressor_specifications.hp_compressors.count") == 3
    assert cfg.get("pressure_parameters.wcs_hp_outlet.nominal_barg") == 14
    assert cfg.get("pressure_parameters.hcc_inlet.nominal_mbar") == 1050
    assert cfg.get("pressure_parameters.wcs_lcc_suction.nominal_mbar") == 400


def test_missing_key_returns_default():
    assert cfg.get("non.existing.path", default="fallback") == "fallback"
