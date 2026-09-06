"""QPLANT-specific helium provider routing.

Project rule:
- 2.0 K <= T <= 4.5 K: governing values MUST come from the child HEPAK receipt.
- outside that band: delegate to the existing CoolProp runtime provider.
- NIST remains validation/reference only and is never substituted as governing runtime.

This module intentionally does not alter the generic ABACUS helium provider.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import provider as coolprop_provider
from .qplant_hepak_runtime_export import HepakRuntimeReceipt, load_qplant_hepak_export

HEPAK_T_MIN_K = 2.0
HEPAK_T_MAX_K = 4.5


@dataclass(frozen=True)
class QplantHeliumState:
    temperature_K: float
    pressure_Pa: float
    density_kg_m3: float
    enthalpy_J_kg: float
    entropy_J_kgK: float
    cp_J_kgK: float
    cv_J_kgK: float
    viscosity_Pa_s: float
    conductivity_W_mK: float
    phase: str
    provider: str
    provider_version: str
    authority_role: str
    source_locator: str
    source_hash: str
    receipt_status: str


def governing_provider_for_temperature(temperature_K: float) -> str:
    t = float(temperature_K)
    return "HEPAK" if HEPAK_T_MIN_K <= t <= HEPAK_T_MAX_K else "CoolProp"


def _close(a: float, b: float, *, rtol: float = 1e-9, atol: float = 1e-7) -> bool:
    return abs(a - b) <= max(atol, rtol * max(abs(a), abs(b)))


def _hepak_exact_state(receipt: HepakRuntimeReceipt, temperature_K: float, pressure_Pa: float) -> QplantHeliumState:
    matches: list[dict[str, Any]] = []
    for row in receipt.rows:
        if _close(float(row["temperature_K"]), temperature_K) and _close(float(row["pressure_Pa_abs"]), pressure_Pa):
            matches.append(row)
    if not matches:
        raise RuntimeError(
            f"QPLANT_HEPAK_EXACT_STATE_MISSING: T={temperature_K} K P={pressure_Pa} Pa. "
            "No interpolation or CoolProp fallback is permitted for governing 2.0-4.5 K execution."
        )
    if len(matches) != 1:
        raise RuntimeError(f"QPLANT_HEPAK_STATE_AMBIGUOUS: {len(matches)} rows match T/P")
    row = matches[0]
    return QplantHeliumState(
        temperature_K=float(row["temperature_K"]),
        pressure_Pa=float(row["pressure_Pa_abs"]),
        density_kg_m3=float(row["density_kg_m3"]),
        enthalpy_J_kg=float(row["enthalpy_J_kg"]),
        entropy_J_kgK=float(row["entropy_J_kgK"]),
        cp_J_kgK=float(row["cp_J_kgK"]),
        cv_J_kgK=float(row["cv_J_kgK"]),
        viscosity_Pa_s=float(row["viscosity_Pa_s"]),
        conductivity_W_mK=float(row["thermal_conductivity_W_mK"]),
        phase=str(row.get("phase_status") or "UNKNOWN"),
        provider="HEPAK",
        provider_version=str(row["provider_version"]),
        authority_role="GOVERNING",
        source_locator=f"{row['source_workbook']}::{row['state_id']}",
        source_hash=str(row["source_workbook_sha256"]),
        receipt_status="GOVERNING_NUMERIC_RECEIPT_AVAILABLE",
    )


def state_tp(
    temperature_K: float,
    pressure_Pa: float,
    *,
    hepak_csv: Path | None = None,
    hepak_manifest: Path | None = None,
) -> QplantHeliumState:
    """Return QPLANT-governed helium state; fail closed in the HEPAK band."""
    t = float(temperature_K)
    p = float(pressure_Pa)
    if governing_provider_for_temperature(t) == "HEPAK":
        if hepak_csv is None:
            raise RuntimeError(
                "QPLANT_HEPAK_RECEIPT_REQUIRED: governing 2.0-4.5 K state requested without child HEPAK CSV"
            )
        receipt = load_qplant_hepak_export(hepak_csv, hepak_manifest)
        return _hepak_exact_state(receipt, t, p)

    cp = coolprop_provider.state_tp(t, p)
    return QplantHeliumState(
        temperature_K=cp.temperature_K,
        pressure_Pa=cp.pressure_Pa,
        density_kg_m3=cp.density_kg_m3,
        enthalpy_J_kg=cp.enthalpy_J_kg,
        entropy_J_kgK=cp.entropy_J_kgK,
        cp_J_kgK=cp.cp_J_kgK,
        cv_J_kgK=cp.cv_J_kgK,
        viscosity_Pa_s=cp.viscosity_Pa_s,
        conductivity_W_mK=cp.conductivity_W_mK,
        phase=cp.phase,
        provider="CoolProp",
        provider_version=cp.backend_version,
        authority_role="GOVERNING",
        source_locator="ABACUS/models/helium_properties/provider.py",
        source_hash="REPOSITORY_VERSION_BOUND",
        receipt_status="OUTSIDE_HEPAK_BAND_RUNTIME",
    )
