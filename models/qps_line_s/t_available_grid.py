#!/usr/bin/env python3
"""Generate QPS Line S time-to-limit grid.

Post-processes the generated scenario matrix into the decision variable the
Applicant needs:

    t_available = (P_LIMIT - P_initial) / dPdt

P_LIMIT and P_initial are still gated RFI placeholders, not resolved answers.
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IN_CSV = ROOT / "docs" / "qps_line_s_recovery" / "generated" / "scenario_matrix.csv"
OUT_DIR = ROOT / "docs" / "qps_line_s_recovery" / "generated"

COL_VEFF = "V_eff_m3"
COL_CASE = "case"
COL_DPDT_ISO = "dPdt_isothermal_bar_min"
COL_DPDT_ENERGY = "dPdt_energy_bar_min"

# RFI placeholders. These are parametric candidate values only.
P_INITIAL_BAR = 1.2
P_LIMIT_CANDIDATES_BAR = [2.0, 3.0, 4.0, 5.0]
BASIS = "linearized_RFI_placeholders"


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def t_available_min(p_limit: float, p_initial: float, dpdt: float) -> float:
    """Return linearized time-to-limit in minutes.

    If the candidate pressure limit is not above the initial pressure, the
    scenario is invalid and returns NaN rather than a misleading negative time.
    """
    if p_limit <= p_initial:
        return math.nan
    if dpdt <= 0:
        return math.inf
    return (p_limit - p_initial) / dpdt


def build_grid(rows: list[dict[str, str]]) -> list[dict[str, float | str]]:
    grid = []
    for row in rows:
        veff = float(row[COL_VEFF])
        case = row[COL_CASE]
        iso = float(row[COL_DPDT_ISO])
        energy = float(row[COL_DPDT_ENERGY])
        for p_limit in P_LIMIT_CANDIDATES_BAR:
            dpa = p_limit - P_INITIAL_BAR
            grid.append({
                "V_eff_m3": veff,
                "case": case,
                "P_LIMIT_bar": p_limit,
                "P_initial_bar": P_INITIAL_BAR,
                "dP_allowed_bar": dpa,
                "t_avail_energy_min": t_available_min(p_limit, P_INITIAL_BAR, energy),
                "t_avail_isothermal_min": t_available_min(p_limit, P_INITIAL_BAR, iso),
                "basis": BASIS,
            })
    return grid


def fmt(value: float | str) -> str:
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        if math.isinf(value):
            return "inf"
        return f"{value:.3f}"
    return str(value)


def write_csv(grid: list[dict[str, float | str]], path: Path) -> None:
    cols = list(grid[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(grid)


def write_md(grid: list[dict[str, float | str]], path: Path) -> None:
    cols = list(grid[0].keys())
    lines = [
        "# QPS Line S - t_available grid (time-to-limit)",
        "",
        "GATED: depends on unresolved P_LIMIT and P_initial. Conservative column uses the energy bound. Values are linearized estimates pending resolved inputs and time-integrated energy balance.",
        "",
    ]
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "|".join(["---"] * len(cols)) + "|")
    for item in grid:
        lines.append("| " + " | ".join(fmt(item[col]) for col in cols) + " |")
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    if not IN_CSV.exists():
        sys.exit(f"missing input matrix: {IN_CSV}; run run_scenarios.py first")
    rows = load_rows(IN_CSV)
    grid = build_grid(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(grid, OUT_DIR / "t_available_grid.csv")
    write_md(grid, OUT_DIR / "t_available_grid.md")
    print(f"wrote {len(grid)} rows -> t_available_grid.csv and t_available_grid.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
