"""QPLANT HEPAK numeric-export ingest.

This module does not execute or embed HEPAK. It consumes an engineer-generated
numeric export from the already-governed licensed QPLANT runtime and preserves
provider/provenance fields for downstream CODEX/child disposition.
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_COLUMNS = {
    "state_id",
    "temperature_K",
    "pressure_Pa_abs",
    "enthalpy_J_kg",
    "entropy_J_kgK",
    "density_kg_m3",
    "cp_J_kgK",
    "cv_J_kgK",
    "viscosity_Pa_s",
    "thermal_conductivity_W_mK",
    "phase",
}

REQUIRED_PROVENANCE = {
    "provider",
    "provider_version",
    "runtime_identity",
    "unit_set",
    "pressure_basis",
    "execution_date",
}


@dataclass(frozen=True)
class HepakRuntimeReceipt:
    rows: list[dict[str, Any]]
    provenance: dict[str, Any]
    input_sha256: str
    output_sha256: str


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def load_qplant_hepak_export(csv_path: Path, provenance_path: Path) -> HepakRuntimeReceipt:
    """Load a governed engineer-generated HEPAK export and fail closed on gaps."""
    if not csv_path.exists():
        raise FileNotFoundError(f"HEPAK numeric export unavailable: {csv_path}")
    if not provenance_path.exists():
        raise FileNotFoundError(f"HEPAK provenance unavailable: {provenance_path}")

    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    missing_provenance = REQUIRED_PROVENANCE - set(provenance)
    if missing_provenance:
        raise ValueError(f"HEPAK provenance missing fields: {sorted(missing_provenance)}")
    if str(provenance.get("provider", "")).upper() != "HEPAK":
        raise ValueError("QPLANT low-temperature numeric export must identify provider=HEPAK")
    if str(provenance.get("pressure_basis", "")).upper() not in {"ABS", "ABSOLUTE", "PA_ABS"}:
        raise ValueError("QPLANT HEPAK export requires absolute-pressure provenance")

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(f"HEPAK numeric export missing columns: {sorted(missing_columns)}")
        rows = list(reader)

    if not rows:
        raise ValueError("HEPAK numeric export contains no rows")

    state_ids = [row["state_id"] for row in rows]
    if len(state_ids) != len(set(state_ids)):
        raise ValueError("HEPAK numeric export contains duplicate state_id values")

    request_identity = {
        "provider": provenance["provider"],
        "provider_version": provenance["provider_version"],
        "runtime_identity": provenance["runtime_identity"],
        "unit_set": provenance["unit_set"],
        "pressure_basis": provenance["pressure_basis"],
        "states": [
            {
                "state_id": row["state_id"],
                "temperature_K": row["temperature_K"],
                "pressure_Pa_abs": row["pressure_Pa_abs"],
            }
            for row in rows
        ],
    }
    output_identity = {"provenance": provenance, "rows": rows}
    return HepakRuntimeReceipt(
        rows=rows,
        provenance=provenance,
        input_sha256=_sha256(request_identity),
        output_sha256=_sha256(output_identity),
    )


def receipt_status(csv_path: Path, provenance_path: Path) -> dict[str, Any]:
    try:
        receipt = load_qplant_hepak_export(csv_path, provenance_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        return {"status": "DEFER", "reason": str(exc)}
    return {
        "status": "NUMERIC_RECEIPT_AVAILABLE",
        "rows": len(receipt.rows),
        "input_sha256": receipt.input_sha256,
        "output_sha256": receipt.output_sha256,
        "provider": receipt.provenance["provider"],
        "provider_version": receipt.provenance["provider_version"],
    }
