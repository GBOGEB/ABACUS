"""Tests for QPLANT Config Service."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import yaml

# Ensure project root is importable
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config_service.schemas import QplantConfig, export_json_schema
from config_service.service import ConfigService
from config_service.client import DirectConfigClient
from config_service.migrate import ConfigMigration


# ── Fixtures ─────────────────────────────────────────────────────────────────

SAMPLE_CONFIG = {
    "version": "4.2.0",
    "last_updated": "2026-05-12T00:00:00Z",
    "description": "Test config",
    "system": {
        "name": "Test System",
        "design_basis": "Test Basis",
        "facility": "Test Facility",
    },
    "flow_parameters": {
        "wcs_hp": {
            "design_flow_gs": 350,
            "expected_flow_gs": 304,
            "max_flow_gs": 336,
            "redundancy_formula": "3/112 × (N+1), N=3",
        },
        "pvps": {
            "total_flow_gs": 50,
            "units_total": 10,
            "units_active": 9,
            "flow_per_unit_gs": 5,
            "n_minus_1_capable": True,
        },
    },
    "pressure_parameters": {
        "wcs_hp_outlet": {"nominal_barg": 14, "max_barg": 15, "min_barg": 10},
        "helium_inventory": {"storage_bar": 15, "vessel_count": 3, "vessel_volume_m3": 120},
        "hcc_inlet": {"nominal_mbar": 1050},
        "wcs_lcc_suction": {"nominal_mbar": 400, "min_mbar": 250, "max_mbar": 550, "control": "VFD"},
    },
    "monte_carlo_distributions": {
        "vlp_pressure": {"min_mbar": 250, "expected_mbar": 400, "max_mbar": 500, "distribution": "PERT"},
        "lp_outlet": {"min_mbar": 900, "expected_mbar": 1050, "max_mbar": 1200, "distribution": "PERT"},
    },
    "compressor_specifications": {
        "hp_compressors": {
            "count": 3,
            "model": "Kaeser FSD 575 SFC",
            "power_supply": "400V 3-phase",
            "redundancy": "N+1 where N=3",
            "configuration": "3 active compressors",
        },
        "fsd575": {
            "capacity_nm3h": 575,
            "motor_power_kW": 315,
            "package_power_kW": 348.54,
            "per_unit_flow_gs": 112.54,
            "frequency_hz": 72,
            "vfd_range_pct": [30, 100],
            "efficiency_percent": [70, 75],
            "cooling_water_m3h": 18.2,
            "heat_rejection_kW": 323.9,
            "noise_dba": 75,
            "dimensions_mm": "3240 × 2145 × 2360",
            "weight_kg": 6770,
            "oil_charge_L": 173,
            "mtbf_hours": 8760,
            "mttr_hours": 8,
            "capital_cost_eur": 200000,
            "annual_maint_eur": 15000,
        },
        "three_skid_totals": {
            "max_total_flow_gs": 337.62,
            "package_power_kW": 1045.62,
            "cooling_water_m3h": 54.6,
            "heat_rejection_kW": 971.7,
        },
    },
    "financial": {
        "electricity_cost_eur_kwh": 0.15,
        "helium_price_eur_kg": 120.0,
        "operating_hours_year": 8000,
        "discount_rate_pct": 5.0,
        "project_lifetime_years": 20,
    },
    "modeling_standards": {
        "fluid_properties": "Real Gas (NIST REFPROP)",
        "pressure_reference": "Absolute (unless marked barg)",
        "temperature_reference": "Kelvin",
    },
    "compliance": {
        "standards": ["PED 2014/68/EU", "ASME B31.3"],
    },
}


@pytest.fixture
def tmp_config(tmp_path):
    """Create a temporary config file."""
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(SAMPLE_CONFIG, f, default_flow_style=False)
    return config_file


@pytest.fixture
def config_svc(tmp_config):
    """Create a ConfigService instance."""
    return ConfigService(config_path=str(tmp_config))


# ── Schema Tests ─────────────────────────────────────────────────────────────

class TestSchema:
    def test_valid_config_parses(self):
        config = QplantConfig(**SAMPLE_CONFIG)
        assert config.version == "4.2.0"
        assert config.compressor_specifications.hp_compressors.count == 3

    def test_invalid_version_rejected(self):
        bad = {**SAMPLE_CONFIG, "version": "not-semver"}
        with pytest.raises(Exception):
            QplantConfig(**bad)

    def test_negative_flow_rejected(self):
        bad = dict(SAMPLE_CONFIG)
        bad["flow_parameters"] = {
            **SAMPLE_CONFIG["flow_parameters"],
            "wcs_hp": {**SAMPLE_CONFIG["flow_parameters"]["wcs_hp"], "design_flow_gs": -1},
        }
        with pytest.raises(Exception):
            QplantConfig(**bad)

    def test_json_schema_export(self):
        schema = export_json_schema()
        assert "properties" in schema
        assert "version" in schema["properties"]

    def test_compressor_count_range(self):
        bad = dict(SAMPLE_CONFIG)
        bad["compressor_specifications"] = {
            **SAMPLE_CONFIG["compressor_specifications"],
            "hp_compressors": {**SAMPLE_CONFIG["compressor_specifications"]["hp_compressors"], "count": 99},
        }
        with pytest.raises(Exception):
            QplantConfig(**bad)


# ── Service Tests ────────────────────────────────────────────────────────────

class TestService:
    def test_get_all(self, config_svc):
        config = config_svc.get_all()
        assert config["version"] == "4.2.0"

    def test_get_section(self, config_svc):
        system = config_svc.get_section("system")
        assert system["facility"] == "Test Facility"

    def test_get_section_not_found(self, config_svc):
        with pytest.raises(KeyError):
            config_svc.get_section("nonexistent")

    def test_get_value_dot_notation(self, config_svc):
        count = config_svc.get_value("compressor_specifications.hp_compressors.count")
        assert count == 3

    def test_get_value_not_found(self, config_svc):
        with pytest.raises(KeyError):
            config_svc.get_value("nonexistent.path")

    def test_set_value(self, config_svc):
        change = config_svc.set_value(
            "financial.electricity_cost_eur_kwh", 0.20,
            user="test", reason="price update"
        )
        assert change.old_value == 0.15
        assert change.new_value == 0.20
        assert config_svc.get_value("financial.electricity_cost_eur_kwh") == 0.20

    def test_validate(self, config_svc):
        result = config_svc.validate()
        assert result["valid"] is True

    def test_get_hash(self, config_svc):
        h = config_svc.get_hash()
        assert len(h) == 16

    def test_history(self, config_svc):
        config_svc.set_value("version", "4.2.1", user="test", reason="bump")
        history = config_svc.get_history()
        assert len(history) >= 1

    def test_reload(self, config_svc):
        result = config_svc.reload()
        assert isinstance(result, bool)

    def test_get_metrics(self, config_svc):
        metrics = config_svc.get_metrics()
        assert "config_hash" in metrics
        assert "version" in metrics


# ── Client Tests ─────────────────────────────────────────────────────────────

class TestDirectClient:
    def test_get_all(self, tmp_config):
        client = DirectConfigClient(str(tmp_config))
        config = client.get_all()
        assert config["version"] == "4.2.0"

    def test_get_section(self, tmp_config):
        client = DirectConfigClient(str(tmp_config))
        system = client.get_section("system")
        assert "name" in system

    def test_get_value(self, tmp_config):
        client = DirectConfigClient(str(tmp_config))
        count = client.get_value("compressor_specifications.hp_compressors.count")
        assert count == 3

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            DirectConfigClient("/nonexistent/config.yaml")


# ── Migration Tests ──────────────────────────────────────────────────────────

class TestMigration:
    def test_check(self, tmp_config):
        migration = ConfigMigration(str(tmp_config))
        report = migration.check()
        assert report["config_exists"] is True
        assert report["overall"] in ("PASS", "NEEDS_MIGRATION")

    def test_execute(self, tmp_config):
        migration = ConfigMigration(str(tmp_config))
        result = migration.execute(target_version="4.3.0")
        assert result["success"] is True
        # Verify version updated
        with open(tmp_config) as f:
            config = yaml.safe_load(f)
        assert config["version"] == "4.3.0"

    def test_rollback(self, tmp_config):
        migration = ConfigMigration(str(tmp_config))
        migration.execute(target_version="4.3.0")
        result = migration.rollback()
        assert result["status"] == "OK"
        with open(tmp_config) as f:
            config = yaml.safe_load(f)
        assert config["version"] == "4.2.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
