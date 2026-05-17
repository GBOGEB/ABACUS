"""Tests for the FastAPI REST API layer (Phase 2).

Validates endpoint responses, request/response schemas,
and integration with the Python physics engine.
"""
import sys
from pathlib import Path

import pytest

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


def test_root_returns_service_info(client):
    """Root endpoint should return service name and version."""
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["service"] == "QPLANT Cryogenic Dashboard API"
    assert data["version"] == "4.4.0"
    assert "endpoints" in data


def test_health_check(client):
    """Health endpoint should return healthy status."""
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["version"] == "4.4.0"
    assert data["config_valid"] is True


def test_config_summary(client):
    """Config summary should return key SSoT parameters."""
    r = client.get("/api/v1/config")
    assert r.status_code == 200
    data = r.json()
    assert data["hp_compressor_count"] == 3
    assert data["motor_power_kw"] == 315
    assert data["design_flow_gs"] == 350


def test_config_section(client):
    """Config section endpoint should return specific values."""
    r = client.get("/api/v1/config/compressor_specifications.fsd575")
    assert r.status_code == 200
    data = r.json()
    assert data["value"]["motor_power_kW"] == 315


def test_config_section_not_found(client):
    """Missing config section should return 404."""
    r = client.get("/api/v1/config/nonexistent.path")
    assert r.status_code == 404


def test_leak_rate_calculation(client):
    """Leak rate endpoint should compute correct values."""
    r = client.post("/api/v1/leak-rate", json={
        "leak_rate_mbar_l_s": 1.0,
        "temperature_k": 300,
        "pressure_bar_abs": 1.0,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["pa_m3_s"] > 0
    assert data["molar_flow_mol_s"] > 0
    assert data["mass_flow_g_s"] > 0
    assert data["mass_flow_kg_year"] > 0


def test_leak_rate_batch(client):
    """Batch leak rate should process multiple items."""
    r = client.post("/api/v1/leak-rate/batch", json={
        "items": [
            {"leak_rate_mbar_l_s": 1e-6, "temperature_k": 300, "pressure_bar_abs": 1.0},
            {"leak_rate_mbar_l_s": 1e-5, "temperature_k": 4.2, "pressure_bar_abs": 14.0},
        ],
        "he_price_eur_kg": 120.0,
    })
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) == 2
    assert data["totals"]["item_count"] == 2


def test_monte_carlo_simulation(client):
    """Monte Carlo should return statistical results."""
    r = client.post("/api/v1/monte-carlo", json={
        "n_simulations": 1000,
        "include_histogram": True,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["n_simulations"] == 1000
    assert data["mean_annual_cost_eur"] > 0
    assert data["p5_cost_eur"] < data["p95_cost_eur"]
    assert "histogram_data" in data


def test_compressor_reliability(client):
    """Compressor reliability should calculate availability."""
    r = client.post("/api/v1/compressors/reliability", json={
        "total_units": 3,
        "required_units": 2,
        "mtbf_hours": 8760,
        "mttr_hours": 8,
        "has_vfd": True,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["availability_pct"] > 99.0
    assert data["total_units"] == 3
    assert data["has_vfd"] is True


def test_compressor_specs(client):
    """Compressor specs should return SSoT data."""
    r = client.get("/api/v1/compressors/specs")
    assert r.status_code == 200
    data = r.json()
    assert data["hp_compressors"]["count"] == 3
    assert data["fsd575"]["motor_power_kW"] == 315


def test_visualization_catalog(client):
    """Visualization catalog should list chart files."""
    r = client.get("/api/v1/visualizations/catalog")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 0
    assert len(data["visualizations"]) > 0


def test_compressor_availability_chart(client):
    """Compressor availability chart data should be valid Plotly format."""
    r = client.get("/api/v1/visualizations/compressor-availability")
    assert r.status_code == 200
    data = r.json()
    assert data["chart_type"] == "bar"
    assert len(data["data"]) > 0
    assert "layout" in data


def test_build_status(client):
    """Build status should return version and manifest data."""
    r = client.get("/api/v1/build/status")
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == "4.4.0"
