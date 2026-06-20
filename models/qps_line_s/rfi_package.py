"""Generate Applicant RFI package from the assumptions register.

The register remains the source of truth. This renderer selects unresolved
`gate: true` items and emits a Markdown RFI package into the generated output
folder. Generated output is ignored by git.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTER = ROOT / "docs" / "qps_line_s_recovery" / "assumptions_register.yaml"
OUT = ROOT / "docs" / "qps_line_s_recovery" / "generated" / "applicant_rfi.md"
RESOLVED_STATES = {"RESOLVED", "ACCEPTED"}


def load_register(path: Path = REGISTER) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("assumptions register must be a mapping")
    return data


def gate_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key in ("blockers", "assumptions"):
        value = data.get(key, [])
        if isinstance(value, list):
            items.extend(item for item in value if isinstance(item, dict))
    return [item for item in items if item.get("gate")]


def open_gate_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    open_items = []
    for item in gate_items(data):
        status = str(item.get("status", "")).upper()
        if status not in RESOLVED_STATES:
            open_items.append(item)
    return open_items


def _as_lines(value: Any) -> list[str]:
    if value is None:
        return ["UNRESOLVED"]
    if isinstance(value, list):
        return [f"- {item}" for item in value]
    return [str(value).strip()]


def render_rfi(items: list[dict[str, Any]]) -> str:
    lines = [
        "# QPS Line S - Applicant RFI package",
        "",
        "Generated from `docs/qps_line_s_recovery/assumptions_register.yaml`.",
        "Do not hand-edit this rendered file; update the register instead.",
        "",
        f"Open gate count: {len(items)}",
        "",
    ]
    for index, item in enumerate(items, start=1):
        item_id = item.get("id", f"GATE-{index}")
        title = item.get("title") or item.get("quantity") or item_id
        lines.extend([
            f"## RFI-{index}: {item_id} - {title}",
            "",
            f"Status: {item.get('status', 'UNKNOWN')}",
            f"Severity: {item.get('severity', 'not_specified')}",
            f"Value: {item.get('value', 'UNRESOLVED')}",
            "",
            "### Rationale",
            "",
        ])
        lines.extend(_as_lines(item.get("rationale") or item.get("why_it_matters") or "Rationale not supplied."))
        lines.extend(["", "### Resolution options", ""])
        lines.extend(_as_lines(item.get("resolution_options") or "Provide confirmed value / acceptance basis."))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    items = open_gate_items(load_register())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render_rfi(items))
    print(f"wrote {len(items)} open gates -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
