"""JSON Schema definitions for QPLANT configuration validation.

Provides both Pydantic models for runtime validation and JSON Schema
export for external consumers (Next.js, monitoring, etc.).
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field, field_validator


# ── Enums ────────────────────────────────────────────────────────────────────

class Environment(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "prod"
    DR = "dr"


class DistributionType(str, Enum):
    PERT = "PERT"
    NORMAL = "normal"
    UNIFORM = "uniform"
    TRIANGULAR = "triangular"


# ── Sub-Models ───────────────────────────────────────────────────────────────

class SystemInfo(BaseModel):
    name: str = Field(..., description="System name")
    design_basis: str = Field(..., description="Design basis reference")
    facility: str = Field(..., description="Facility name")


class WcsHpFlow(BaseModel):
    design_flow_gs: float = Field(..., gt=0, description="Max user demand (g/s)")
    expected_flow_gs: float = Field(..., gt=0, description="Expected operational flow (g/s)")
    max_flow_gs: float = Field(..., gt=0, description="WCS.HCC|WCS.HP limit (g/s)")
    redundancy_formula: str = Field(..., description="Redundancy formula")


class PvpsFlow(BaseModel):
    total_flow_gs: float = Field(..., gt=0)
    units_total: int = Field(..., ge=1)
    units_active: int = Field(..., ge=1)
    flow_per_unit_gs: float = Field(..., gt=0)
    n_minus_1_capable: bool


class FlowParameters(BaseModel):
    wcs_hp: WcsHpFlow
    pvps: PvpsFlow


class PressureSpec(BaseModel):
    nominal_barg: Optional[float] = None
    max_barg: Optional[float] = None
    min_barg: Optional[float] = None
    nominal_mbar: Optional[float] = None
    min_mbar: Optional[float] = None
    max_mbar: Optional[float] = None
    control: Optional[str] = None
    storage_bar: Optional[float] = None
    vessel_count: Optional[int] = None
    vessel_volume_m3: Optional[float] = None


class PressureParameters(BaseModel):
    wcs_hp_outlet: PressureSpec
    helium_inventory: PressureSpec
    hcc_inlet: PressureSpec
    wcs_lcc_suction: PressureSpec
    pressure_drops: Optional[Dict[str, Any]] = None
    heat_loads: Optional[Dict[str, Any]] = None


class MonteCarloDistribution(BaseModel):
    min_mbar: float
    expected_mbar: float
    max_mbar: float
    distribution: DistributionType = DistributionType.PERT


class MonteCarloDistributions(BaseModel):
    vlp_pressure: MonteCarloDistribution
    lp_outlet: MonteCarloDistribution


class HpCompressors(BaseModel):
    count: int = Field(..., ge=1, le=10, description="Number of HP compressors")
    model: str
    power_supply: str
    redundancy: str
    configuration: str


class Fsd575Specs(BaseModel):
    capacity_nm3h: float = Field(..., gt=0)
    motor_power_kW: float = Field(..., gt=0)
    package_power_kW: float = Field(..., gt=0)
    per_unit_flow_gs: float = Field(..., gt=0)
    frequency_hz: float = Field(..., gt=0)
    vfd_range_pct: List[float]
    efficiency_percent: List[float]
    cooling_water_m3h: float = Field(..., gt=0)
    heat_rejection_kW: float = Field(..., gt=0)
    noise_dba: float
    dimensions_mm: str
    weight_kg: float
    oil_charge_L: float
    mtbf_hours: int = Field(..., gt=0)
    mttr_hours: float = Field(..., gt=0)
    capital_cost_eur: float = Field(..., gt=0)
    annual_maint_eur: float = Field(..., gt=0)


class ThreeSkidTotals(BaseModel):
    max_total_flow_gs: float
    package_power_kW: float
    cooling_water_m3h: float
    heat_rejection_kW: float


class CompressorSpecifications(BaseModel):
    hp_compressors: HpCompressors
    fsd575: Fsd575Specs
    three_skid_totals: ThreeSkidTotals


class Financial(BaseModel):
    electricity_cost_eur_kwh: float = Field(..., gt=0)
    helium_price_eur_kg: float = Field(..., gt=0)
    operating_hours_year: int = Field(..., gt=0)
    discount_rate_pct: float = Field(..., ge=0, le=100)
    project_lifetime_years: int = Field(..., gt=0)
    compressor_capex: Optional[Dict[str, Any]] = None
    annual_energy: Optional[Dict[str, Any]] = None


class ModelingStandards(BaseModel):
    fluid_properties: str
    pressure_reference: str
    temperature_reference: str


class Compliance(BaseModel):
    standards: List[str]


# ── Root Config Model ────────────────────────────────────────────────────────

class QplantConfig(BaseModel):
    """Root configuration model for QPLANT Cryogenic System."""

    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    last_updated: str
    description: str
    system: SystemInfo
    flow_parameters: FlowParameters
    pressure_parameters: PressureParameters
    monte_carlo_distributions: MonteCarloDistributions
    compressor_specifications: CompressorSpecifications
    financial: Financial
    modeling_standards: ModelingStandards
    compliance: Compliance

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        parts = v.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValueError(f"Version must be semver: {v}")
        return v


# ── Change Audit Models ─────────────────────────────────────────────────────

class ConfigChange(BaseModel):
    """Records a single configuration change."""
    timestamp: str
    user: str = "system"
    path: str = Field(..., description="Dot-notation path e.g. 'compressor_specifications.hp_compressors.count'")
    old_value: Any
    new_value: Any
    reason: str = ""


class ConfigVersion(BaseModel):
    """A versioned snapshot of configuration."""
    version: str
    timestamp: str
    changes: List[ConfigChange] = []
    config_hash: str = ""


class ConfigHistory(BaseModel):
    """Full version history of config changes."""
    versions: List[ConfigVersion] = []


# ── Schema Export ────────────────────────────────────────────────────────────

def export_json_schema(output_path: Optional[str] = None) -> dict:
    """Export the full JSON Schema for external validation."""
    schema = QplantConfig.model_json_schema()
    if output_path:
        Path(output_path).write_text(json.dumps(schema, indent=2))
    return schema


if __name__ == "__main__":
    schema = export_json_schema("config_schema.json")
    print(f"Schema exported: {len(json.dumps(schema))} bytes")
    print(f"Properties: {list(schema.get('properties', {}).keys())}")
