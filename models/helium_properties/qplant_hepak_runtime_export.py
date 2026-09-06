"""QPLANT HEPAK numeric-receipt ingest.

Consumes the engineer-generated child receipt emitted by cryoplant-project:
  - he_reference_hepak_lowT_grid.csv
  - he_reference_hepak_lowT_grid.csv.manifest.json

This module never executes or embeds HEPAK. It verifies exact provenance and
fails closed when the governing 2.0-4.5 K receipt is absent or inconsistent.
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
    "phase_status",
    "solve_pair_used",
    "provider",
    "provider_version",
    "unit_set",
    "pressure_basis",
    "source_workbook",
    "source_workbook_sha256",
    "execution_utc",
    "receipt_status",
    "row_sha256",
}

REQUIRED_MANIFEST_FIELDS = {
    "schema",
    "status",
    "csv_sha256",
    "source_workbook",
    "source_workbook_sha256",
    "provider",
    "provider_version",
    "unit_set",
    "pressure_basis",
    "execution_utc",
    "row_count",
    "state_ids",
    "solve_policy",
}


@dataclass(frozen=True)
class HepakRuntimeReceipt:
    rows: list[dict[str, Any]]
    manifest: dict[str, Any]
    csv_sha256: str
    manifest_sha256: str


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _manifest_path(csv_path: Path, explicit: Path | None) -> Path:
    return explicit if explicit is not None else csv_path.with_suffix(csv_path.suffix + ".manifest.json")


def load_qplant_hepak_export(csv_path: Path, manifest_path: Path | None = None) -> HepakRuntimeReceipt:
    """Load the child governed HEPAK receipt and fail closed on any lineage gap."""
    manifest_path = _manifest_path(csv_path, manifest_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"QPLANT governing HEPAK CSV unavailable: {csv_path}")
    if not manifest_path.exists():
        raise FileNotFoundError(f"QPLANT HEPAK manifest unavailable: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    missing_manifest = REQUIRED_MANIFEST_FIELDS - set(manifest)
    if missing_manifest:
        raise ValueError(f"HEPAK manifest missing fields: {sorted(missing_manifest)}")
    if manifest["status"] != "PASS":
        raise ValueError("HEPAK manifest status must be PASS")
    if str(manifest["provider"]).upper() != "HEPAK":
        raise ValueError("QPLANT 2.0-4.5 K governing provider must be HEPAK")
    if manifest["unit_set"] != 1:
        raise ValueError("QPLANT HEPAK receipt requires unit_set=1")
    if manifest["pressure_basis"] != "ABSOLUTE_PA":
        raise ValueError("QPLANT HEPAK receipt requires ABSOLUTE_PA")
    if manifest["solve_policy"] != "H_FIRST_S_SECOND_TP_SOURCE_BOUND_DENSITY_LAST":
        raise ValueError("QPLANT HEPAK solve policy mismatch")

    csv_sha = _sha256_file(csv_path)
    if manifest["csv_sha256"] != csv_sha:
        raise ValueError("HEPAK manifest csv_sha256 mismatch")

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(f"HEPAK numeric export missing columns: {sorted(missing_columns)}")
        rows = list(reader)

    if not rows:
        raise ValueError("HEPAK numeric export contains no rows")
    if manifest["row_count"] != len(rows):
        raise ValueError("HEPAK manifest row_count mismatch")
    state_ids = [row["state_id"] for row in rows]
    if len(state_ids) != len(set(state_ids)):
        raise ValueError("HEPAK numeric export contains duplicate state_id values")
    if set(manifest["state_ids"]) != set(state_ids):
        raise ValueError("HEPAK manifest state_ids mismatch")

    workbook_hashes = {row["source_workbook_sha256"] for row in rows}
    provider_versions = {row["provider_version"] for row in rows}
    for row in rows:
        if row["provider"] != "HEPAK" or row["receipt_status"] != "PASS":
            raise ValueError(f"{row['state_id']}: HEPAK provider/PASS receipt required")
        if row["unit_set"] != "1" or row["pressure_basis"] != "ABSOLUTE_PA":
            raise ValueError(f"{row['state_id']}: unit/pressure provenance mismatch")
        if row["solve_pair_used"] != "T+P_SOURCE_BOUND":
            raise ValueError(f"{row['state_id']}: unexpected solve pair")
    if workbook_hashes != {manifest["source_workbook_sha256"]}:
        raise ValueError("HEPAK source workbook digest mismatch across rows/manifest")
    if provider_versions != {manifest["provider_version"]}:
        raise ValueError("HEPAK provider version mismatch across rows/manifest")

    return HepakRuntimeReceipt(
        rows=rows,
        manifest=manifest,
        csv_sha256=csv_sha,
        manifest_sha256=_sha256_file(manifest_path),
    )


def receipt_status(csv_path: Path, manifest_path: Path | None = None) -> dict[str, Any]:
    try:
        receipt = load_qplant_hepak_export(csv_path, manifest_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        return {"status": "BLOCKING_MUST_EXECUTE", "reason": str(exc), "formal_credit_delta": 0}
    return {
        "status": "GOVERNING_NUMERIC_RECEIPT_AVAILABLE",
        "rows": len(receipt.rows),
        "csv_sha256": receipt.csv_sha256,
        "manifest_sha256": receipt.manifest_sha256,
        "provider": receipt.manifest["provider"],
        "provider_version": receipt.manifest["provider_version"],
        "formal_credit_delta": 0,
    }
