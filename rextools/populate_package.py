"""Assemble the populated Applicant Response Package.

Binds three sources into one self-contained generated document:
  - applicant_response_package.md   (human-authored skeleton, SSOT)
  - generated/t_available_grid.md   (parametric grid from run_scenarios)
  - generated/applicant_rfi.md      (open gate list from rfi_package)

Gate enforcement via runtime.py verdict:
  exit 0  -> PROCEED_MDA (all gates resolved, full package)
  exit 1  -> ISSUE_RFI   (open gates; package emitted but marked DRAFT-GATED)
  exit 2  -> PIPELINE_FAIL (generated artefacts missing; no output written)
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKELETON = ROOT / "docs" / "qps_line_s_recovery" / "applicant_response_package.md"
GEN = ROOT / "docs" / "qps_line_s_recovery" / "generated"
OUT = GEN / "applicant_response_package.GENERATED.md"

_VERDICT_EXIT = {
    "PROCEED_MDA": 0,
    "ISSUE_RFI": 1,
    "PIPELINE_FAIL": 2,
}


def _status_block(status: dict) -> str:
    verdict = status["verdict"]
    n_gates = status["n_open_gates"]
    energy = status["energy_model"]
    timestamp = datetime.now(UTC).isoformat()
    gate_ids = ", ".join(g["id"] for g in status.get("open_gates", [])) or "none"

    lines = [
        "<!--",
        "GENERATED FILE — do not hand-edit.",
        "Producer : rextools/populate_package.py",
        f"Generated: {timestamp}",
        f"Verdict  : {verdict}",
        f"Open gates ({n_gates}): {gate_ids}",
        f"Energy model: {energy}",
        "-->",
        "",
        "## Package status (generated header)",
        "",
        f"| Field | Value |",
        f"|---|---|",
        f"| Verdict | `{verdict}` |",
        f"| Open gates | {n_gates} |",
        f"| Energy model | `{energy}` |",
        f"| Generated | {timestamp} |",
    ]
    if verdict == "ISSUE_RFI":
        lines += [
            "",
            "> **DRAFT-GATED.** This package is complete but gated: "
            f"{n_gates} open item(s) must be resolved before MDA closure. "
            "See Appendix R.",
        ]
    elif verdict == "PROCEED_MDA":
        lines += [
            "",
            "> **READY FOR MDA.** All gates resolved. Package may be submitted.",
        ]
    lines.append("")
    return "\n".join(lines)


def _divider(title: str) -> str:
    return f"\n---\n\n## {title}\n\n"


def assemble(status: dict) -> str:
    skeleton = SKELETON.read_text(encoding="utf-8")
    grid_md = (GEN / "t_available_grid.md").read_text(encoding="utf-8")
    rfi_md = (GEN / "applicant_rfi.md").read_text(encoding="utf-8")

    return "".join([
        _status_block(status),
        "\n---\n\n",
        skeleton,
        _divider("Appendix G: T-available parametric grid (generated)"),
        grid_md,
        _divider("Appendix R: Open RFI items (generated)"),
        rfi_md,
    ])


def main() -> int:
    # Import here so rextools itself stays import-safe with no side effects.
    from models.qps_line_s import runtime  # noqa: PLC0415

    status = runtime.runtime(regenerate=True, enforce=False)
    verdict = status["verdict"]

    if verdict == "PIPELINE_FAIL":
        print("PIPELINE_FAIL: generated artefacts missing — package not written", file=sys.stderr)
        return 2

    GEN.mkdir(parents=True, exist_ok=True)
    OUT.write_text(assemble(status), encoding="utf-8")

    n = status["n_open_gates"]
    label = "DRAFT-GATED" if verdict == "ISSUE_RFI" else "READY"
    print(f"{label} ({n} open gate(s)) -> {OUT.relative_to(ROOT)}")
    return _VERDICT_EXIT[verdict]


if __name__ == "__main__":
    raise SystemExit(main())