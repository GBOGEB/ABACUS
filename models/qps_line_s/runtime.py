"""QPS Line S recovery runtime verdict.

This file adds no new modelling. It regenerates existing outputs, reads the
assumptions register, counts open gates, reads energy provenance, and writes a
machine-readable status file.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from . import run_scenarios

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "docs" / "qps_line_s_recovery" / "generated"
REGISTER = ROOT / "docs" / "qps_line_s_recovery" / "assumptions_register.yaml"
MATRIX = GEN / "scenario_matrix.csv"
STATUS_OUT = GEN / "runtime_status.json"

REQUIRED_ARTEFACTS = [
    GEN / "scenario_matrix.csv",
    GEN / "scenario_matrix.md",
    GEN / "t_available_grid.csv",
    GEN / "t_available_grid.md",
]
RESOLVED_STATES = {"RESOLVED", "ACCEPTED"}


def run_generators() -> None:
    run_scenarios.main()


def missing_artefacts() -> list[str]:
    return [str(path.relative_to(ROOT)) for path in REQUIRED_ARTEFACTS if not path.exists()]


def read_register(path: Path = REGISTER) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("assumptions register must be a mapping")
    return data


def iter_gate_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key in ("blockers", "assumptions"):
        value = data.get(key, [])
        if isinstance(value, list):
            items.extend(item for item in value if isinstance(item, dict))
    return items


def open_gates(data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    data = read_register() if data is None else data
    gates = []
    for item in iter_gate_items(data):
        status = str(item.get("status", "")).upper()
        if item.get("gate") and status not in RESOLVED_STATES:
            gates.append({
                "id": item.get("id"),
                "status": item.get("status"),
                "severity": item.get("severity"),
            })
    return gates


def energy_provenance(matrix: Path = MATRIX) -> str:
    if not matrix.exists():
        return "unknown"
    with matrix.open(newline="") as f:
        rows = list(csv.DictReader(f))
    sources = {(row.get("energy_source") or "").lower() for row in rows}
    if any("gamma" in source for source in sources):
        return "bound"
    if sources and sources != {""}:
        return "integrated"
    return "unknown"


def decide(missing: list[str], gates: list[dict[str, Any]]) -> str:
    if missing:
        return "PIPELINE_FAIL"
    return "PROCEED_MDA" if not gates else "ISSUE_RFI"


def runtime(regenerate: bool = True, enforce: bool = False) -> dict[str, Any]:
    if regenerate:
        run_generators()
    missing = missing_artefacts()
    gates = [] if missing else open_gates()
    verdict = decide(missing, gates)
    status = {
        "verdict": verdict,
        "n_open_gates": len(gates),
        "open_gates": gates,
        "energy_model": energy_provenance(),
        "missing_artefacts": missing,
    }
    GEN.mkdir(parents=True, exist_ok=True)
    STATUS_OUT.write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2))
    if verdict == "PIPELINE_FAIL":
        raise SystemExit(2)
    if enforce and verdict != "PROCEED_MDA":
        raise SystemExit(1)
    return status


if __name__ == "__main__":
    runtime(regenerate="--no-regen" not in sys.argv, enforce="--gate" in sys.argv)
