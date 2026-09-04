"""Frozen HEPAK reference-table loader.

The licensed HEPAK runtime is deliberately not bundled. An engineer-generated
CSV may be committed with provenance. Absence is UNVALIDATED, never PASS.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

DEFAULT_REFERENCE = Path(__file__).resolve().parents[2] / "docs" / "qps_line_s_recovery" / "he_reference_hepak.csv"
REQUIRED_COLUMNS = {"temperature_K", "pressure_Pa", "density_kg_m3", "enthalpy_J_kg"}


def load_reference(path: Path = DEFAULT_REFERENCE) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"HEPAK independent reference unavailable: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"HEPAK reference missing columns: {sorted(missing)}")
        return list(reader)


def reference_status(path: Path = DEFAULT_REFERENCE) -> dict[str, Any]:
    if not path.exists():
        return {"status": "UNVALIDATED", "reason": "HEPAK_REFERENCE_MISSING", "path": str(path)}
    try:
        rows = load_reference(path)
    except ValueError as exc:
        return {"status": "UNVALIDATED", "reason": str(exc), "path": str(path)}
    return {"status": "REFERENCE_AVAILABLE", "rows": len(rows), "path": str(path)}
