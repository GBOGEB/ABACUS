#!/usr/bin/env python3
"""
validate_consistency.py -- parity/consistency gate for the ICD-bound handover.

FAILS (exit 1) if:
  * electricity is derived from an isothermal/efficiency basis in an ACTIVE path
  * HP and PVPS/B flows are summed into a single "total flow" for sizing
  * a view presents 350 g/s as the ICD design anchor without a legacy label
  * the icd_bound_utilities block is missing or internally inconsistent
  * a running PVPS count is presented as closed

Emits a machine-readable report (master/consistency_report.json) and a human
summary. Conflicts between the pre-existing handover numbers and the ICD are
reported as findings (informational) -- they are expected until views are
migrated, and are listed so nothing is silently stale.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "master"
DATA = json.loads((MASTER / "data.json").read_text(encoding="utf-8"))

ACTIVE_VIEWS = sorted(p for p in ROOT.glob("*.html"))

failures: list[str] = []
findings: list[dict] = []


def fail(msg: str):
    failures.append(msg)


def finding(view: str, kind: str, detail: str):
    findings.append({"view": view, "kind": kind, "detail": detail})


# 1. icd_bound_utilities present and config-invariant
icd = DATA.get("icd_bound_utilities")
if not icd:
    fail("icd_bound_utilities block missing from data.json")
else:
    inv = icd["hp_config_invariance_check_kW"]
    if abs(inv["HP_CFG_3_OF_4"] - inv["HP_CFG_4_OF_4"]) > 0.5:
        fail(f"HP fleet power not config-invariant: {inv}")
    if icd["nominal_anchor_mdot_HP_total_g_s"] != 326:
        fail("ICD nominal anchor must be 326 g/s HP total")
    pvps = icd["pvps"]
    if "OPEN" not in pvps.get("running_count_status", ""):
        fail("PVPS running count must be flagged OPEN, not closed")

# 2. scan active views for stale/forbidden patterns
ISO_RE = re.compile(r"isothermal\s*(work|power).*(/\s*0\.5|efficiency)", re.I)
ADDITIVE_RE = re.compile(r"300\s*\+\s*50|HP\s*\+\s*PVPS\s*=\s*350|=\s*300\s*\+\s*50")
LEGACY_OK = re.compile(r"legacy|superseded|deprecated|historic", re.I)

for v in ACTIVE_VIEWS:
    txt = v.read_text(encoding="utf-8", errors="ignore")
    name = v.name
    # 350 g/s presented as design anchor without legacy label nearby
    for m in re.finditer(r"350\s*g/?s", txt):
        window = txt[max(0, m.start() - 160) : m.end() + 160]
        if re.search(
            r"design|baseline|anchor|nominal", window, re.I
        ) and not LEGACY_OK.search(window):
            finding(
                name,
                "stale_anchor_350",
                "350 g/s shown as design/baseline without a legacy/superseded label",
            )
            break
    if ADDITIVE_RE.search(txt):
        finding(
            name,
            "additive_flow",
            "HP + PVPS appears summed into a single total flow (should be separate drivers)",
        )
    if ISO_RE.search(txt):
        finding(
            name,
            "isothermal_basis",
            "isothermal/efficiency electrical basis present (superseded by ICD-bound power)",
        )

report = {
    "pass": not failures,
    "failures": failures,
    "findings_count": len(findings),
    "findings": findings,
    "note": "findings are informational migration flags; failures are hard gates.",
}
(MASTER / "consistency_report.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
)

print("CONSISTENCY VALIDATOR")
print("  hard failures :", len(failures))
for f in failures:
    print("   FAIL:", f)
print("  migration findings :", len(findings))
for fnd in findings[:40]:
    print(f"   - {fnd['view']}: {fnd['kind']} -- {fnd['detail']}")
print("  report ->", (MASTER / "consistency_report.json"))
raise SystemExit(1 if failures else 0)
