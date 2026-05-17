"""QPLANT Config Service — RESTful API.

Exposes the centralised configuration service via FastAPI.

Run:
    uvicorn config_service.api:app --host 0.0.0.0 --port 8200 --reload

Docs:
    http://localhost:8200/docs       (Swagger UI)
    http://localhost:8200/redoc      (ReDoc)
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .schemas import Environment, export_json_schema
from .service import ConfigService

logger = logging.getLogger(__name__)

# ── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="QPLANT Configuration Service API",
    description="Centralised Single Source of Truth (SSOT) for QPLANT Cryogenic System configuration",
    version="4.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8100", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config Service Instance ──────────────────────────────────────────────────

CONFIG_PATH = os.environ.get(
    "QPLANT_CONFIG_PATH",
    str(Path(__file__).resolve().parent.parent / "handover_dashboard" / "data" / "config.yaml"),
)
ENV = Environment(os.environ.get("QPLANT_ENV", "dev"))

try:
    config_service = ConfigService(
        config_path=CONFIG_PATH,
        env=ENV,
        auto_reload=True,
        reload_interval=10,
    )
except FileNotFoundError:
    logger.warning(f"Config file not found at {CONFIG_PATH}, using fallback")
    config_service = None

_start_time = time.time()


# ── Request/Response Models ──────────────────────────────────────────────────

class SetValueRequest(BaseModel):
    path: str = Field(..., description="Dot-notation path e.g. 'compressor_specifications.hp_compressors.count'")
    value: Any = Field(..., description="New value to set")
    user: str = Field(default="api", description="User making the change")
    reason: str = Field(default="", description="Reason for change")


class ConfigDiffRequest(BaseModel):
    version1: str
    version2: str


class ExportRequest(BaseModel):
    environment: Environment = Environment.DEV


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "QPLANT Configuration Service",
        "version": "4.2.0",
        "docs": "/docs",
        "environment": ENV.value,
    }


@app.get("/api/v1/health")
async def health():
    """Health check."""
    uptime = time.time() - _start_time
    return {
        "status": "healthy" if config_service else "degraded",
        "uptime_seconds": round(uptime, 1),
        "config_loaded": config_service is not None,
        "environment": ENV.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/config")
async def get_config():
    """Get full configuration."""
    if not config_service:
        raise HTTPException(status_code=503, detail="Config service not initialized")
    return config_service.get_all()


@app.get("/api/v1/config/section/{section}")
async def get_section(section: str):
    """Get a specific configuration section."""
    if not config_service:
        raise HTTPException(status_code=503, detail="Config service not initialized")
    try:
        return config_service.get_section(section)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Section not found: {section}")


@app.get("/api/v1/config/value")
async def get_value(path: str = Query(..., description="Dot-notation path")):
    """Get a specific configuration value by dot-notation path."""
    if not config_service:
        raise HTTPException(status_code=503, detail="Config service not initialized")
    try:
        value = config_service.get_value(path)
        return {"path": path, "value": value}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")


@app.post("/api/v1/config/set")
async def set_value(request: SetValueRequest):
    """Set a configuration value with audit trail."""
    if not config_service:
        raise HTTPException(status_code=503, detail="Config service not initialized")
    try:
        change = config_service.set_value(
            path=request.path,
            value=request.value,
            user=request.user,
            reason=request.reason,
        )
        return {"status": "updated", "change": change.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/config/validate")
async def validate_config():
    """Validate current configuration against schema."""
    if not config_service:
        raise HTTPException(status_code=503, detail="Config service not initialized")
    return config_service.validate()


@app.get("/api/v1/config/schema")
async def get_schema():
    """Get the JSON Schema for configuration validation."""
    return export_json_schema()


@app.get("/api/v1/config/history")
async def get_history():
    """Get configuration change history."""
    if not config_service:
        raise HTTPException(status_code=503, detail="Config service not initialized")
    return config_service.get_history()


@app.post("/api/v1/config/diff")
async def get_diff(request: ConfigDiffRequest):
    """Get changes between two configuration versions."""
    if not config_service:
        raise HTTPException(status_code=503, detail="Config service not initialized")
    return config_service.get_diff(request.version1, request.version2)


@app.get("/api/v1/config/hash")
async def get_hash():
    """Get current configuration hash."""
    if not config_service:
        raise HTTPException(status_code=503, detail="Config service not initialized")
    return {"hash": config_service.get_hash()}


@app.post("/api/v1/config/reload")
async def reload_config():
    """Force reload configuration from disk."""
    if not config_service:
        raise HTTPException(status_code=503, detail="Config service not initialized")
    changed = config_service.reload()
    return {"reloaded": changed, "hash": config_service.get_hash()}


@app.post("/api/v1/config/export")
async def export_config(request: ExportRequest):
    """Export configuration for a specific environment."""
    if not config_service:
        raise HTTPException(status_code=503, detail="Config service not initialized")
    return config_service.export_env_config(request.environment)


@app.get("/api/v1/metrics")
async def get_metrics():
    """Get config service metrics for monitoring."""
    if not config_service:
        raise HTTPException(status_code=503, detail="Config service not initialized")
    metrics = config_service.get_metrics()
    metrics["uptime_seconds"] = round(time.time() - _start_time, 1)
    return metrics


@app.get("/api/v1/environments")
async def list_environments():
    """List available environments."""
    return {
        "environments": [e.value for e in Environment],
        "current": ENV.value,
    }
