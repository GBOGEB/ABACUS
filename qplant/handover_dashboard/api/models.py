"""Pydantic models for API request/response schemas.

All models use strict typing and validation to ensure
data integrity between the Python engine and Next.js frontend.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────

class AudienceType(str, Enum):
    """Stakeholder presentation audience types."""
    executive = "executive"
    technical = "technical"
    financial = "financial"


class CompressorModel(str, Enum):
    """Supported compressor model identifiers."""
    FSD575 = "FSD575"
    HSD_TWIN_COMBI = "HSD_TWIN_COMBI"


# ── Config Models ────────────────────────────────────────────────────

class ConfigSummary(BaseModel):
    """Summary of SSoT configuration."""
    version: str
    last_updated: str
    hp_compressor_count: int
    motor_power_kw: float
    total_capex_eur: float
    design_flow_gs: float
    compliance_score: Optional[float] = None


class ConfigDetail(BaseModel):
    """Full SSoT configuration export."""
    version: str
    config: Dict[str, Any]


# ── Leak Rate Models ─────────────────────────────────────────────────

class LeakRateRequest(BaseModel):
    """Request for leak-rate calculation."""
    leak_rate_mbar_l_s: float = Field(..., gt=0, description="Leak rate in mbar·L/s")
    temperature_k: float = Field(..., gt=0, description="Temperature in Kelvin")
    pressure_bar_abs: float = Field(default=1.0, gt=0, description="Absolute pressure in bar")
    reference_pressure_bar: float = Field(default=1.0, gt=0, description="Reference pressure in bar")


class LeakRateResponse(BaseModel):
    """Response with calculated leak-rate conversions."""
    leak_rate_mbar_l_s: float
    temperature_k: float
    pressure_bar_abs: float
    pa_m3_s: float
    molar_flow_mol_s: float
    mass_flow_g_s: float
    mass_flow_kg_year: float
    cost_eur_year: Optional[float] = None


class BatchLeakRateRequest(BaseModel):
    """Request for multiple leak-rate calculations."""
    items: List[LeakRateRequest]
    he_price_eur_kg: float = Field(default=120.0, gt=0)


# ── Monte Carlo Models ───────────────────────────────────────────────

class MonteCarloRequest(BaseModel):
    """Request for Monte Carlo simulation."""
    n_simulations: int = Field(default=10000, ge=100, le=100000)
    he_price_min: float = Field(default=117.0, gt=0)
    he_price_mode: float = Field(default=120.0, gt=0)
    he_price_max: float = Field(default=300.0, gt=0)
    geopolitical_disruption_prob: float = Field(default=0.0, ge=0, le=1)
    include_histogram: bool = Field(default=True)


class MonteCarloResult(BaseModel):
    """Response with Monte Carlo simulation results."""
    n_simulations: int
    mean_annual_cost_eur: float
    median_annual_cost_eur: float
    p5_cost_eur: float
    p95_cost_eur: float
    std_dev_eur: float
    histogram_data: Optional[Dict[str, List[float]]] = None
    scenarios: Optional[List[Dict[str, Any]]] = None


# ── Compressor Models ────────────────────────────────────────────────

class CompressorConfigRequest(BaseModel):
    """Request for compressor reliability analysis."""
    total_units: int = Field(default=3, ge=1, le=10)
    required_units: int = Field(default=2, ge=1)
    mtbf_hours: float = Field(default=8760.0, gt=0)
    mttr_hours: float = Field(default=8.0, gt=0)
    has_vfd: bool = Field(default=True)


class CompressorReliabilityResponse(BaseModel):
    """Response with compressor reliability metrics."""
    configuration: str
    total_units: int
    required_units: int
    availability_pct: float
    mtbf_system_hours: float
    annual_downtime_hours: float
    energy_cost_eur_year: float
    total_capex_eur: float
    has_vfd: bool
    vfd_savings_pct: Optional[float] = None


# ── Health & Status Models ───────────────────────────────────────────

class BuildStatus(BaseModel):
    """System build status."""
    version: str
    build_time: Optional[str] = None
    tests_passing: int
    tests_total: int
    compliance_score: float
    last_build: Optional[str] = None
    git_commit: Optional[str] = None


class HealthResponse(BaseModel):
    """System health check response."""
    status: str  # "healthy" | "degraded" | "error"
    version: str
    uptime_seconds: float
    build: BuildStatus
    config_valid: bool
    timestamp: str


# ── Visualization Models ─────────────────────────────────────────────

class PlotlyChartData(BaseModel):
    """Plotly chart data for frontend rendering."""
    chart_id: str
    title: str
    chart_type: str  # bar, scatter, line, heatmap, etc.
    data: List[Dict[str, Any]]  # Plotly trace objects
    layout: Dict[str, Any]  # Plotly layout config
    metadata: Optional[Dict[str, Any]] = None
