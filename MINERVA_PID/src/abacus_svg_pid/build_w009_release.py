"""
================================================================================
 Module : src/abacus_svg_pid/build_w009_release.py
 Wave   : W009 — Final Deliverables & Commissioning
 Status : ACTIVE
--------------------------------------------------------------------------------
 Purpose
 -------
 Produce the *commissioned* v1.0 canonical instrument register and an engineering
 sign-off record. This is the final deliverable wave: it consolidates the W005
 reconciliation, the W006 heuristic cross-map, and any W008/W009 reviewer-
 confirmed seeds (configs/known_seeds.json) into a single, status-bearing
 release artifact.

 Commissioning status (per design tag)
 -------------------------------------
   commissioned : engineering-confirmed seed OR HIGH-tier cross-map pair
   provisional  : MEDIUM/LOW heuristic pair, awaiting reviewer confirmation
   open         : no cross-map candidate (unmapped) — needs investigation

 Honesty invariant
 -----------------
 A tag is only "commissioned" when backed by a HIGH-tier score (>=0.80), which
 in turn requires either an independent signal corroborator or a human-confirmed
 seed. Nothing here fabricates a confirmation; with an empty known_seeds file
 the register is honestly all-provisional/open and the sign-off record says so.

 Inputs
 ------
   data/crossmap/crossmap_confidence.json   (W006 pairs + unmapped + tiers)
   data/excel/reconciliation_results.json   (W005 coverage + reallocations)
   configs/known_seeds.json                 (W009 reviewer-confirmed seeds)

 Outputs
 -------
   data/excel/canonical_register_release_v1.0.yaml  (final commissioned register)
   reports/W009_SIGNOFF_RECORD.json                 (machine-readable sign-off)
   reports/W009_SIGNOFF_RECORD.md                   (human sign-off sheet)
   reports/W009_COMMISSIONING_REPORT.md             (release summary)

 Reproducible:
   PYTHONPATH=src python3 -m abacus_svg_pid.build_w009_release
================================================================================
"""

from __future__ import annotations

import datetime
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXCEL_DIR = os.path.join(ROOT, "data", "excel")
CROSSMAP_DIR = os.path.join(ROOT, "data", "crossmap")
CONFIGS_DIR = os.path.join(ROOT, "configs")
REPORTS_DIR = os.path.join(ROOT, "reports")

CONFIDENCE = os.path.join(CROSSMAP_DIR, "crossmap_confidence.json")
RECON_RESULTS = os.path.join(EXCEL_DIR, "reconciliation_results.json")
KNOWN_SEEDS_FILE = os.path.join(CONFIGS_DIR, "known_seeds.json")

OUT_REGISTER = os.path.join(EXCEL_DIR, "canonical_register_release_v1.0.yaml")
OUT_STATS = os.path.join(REPORTS_DIR, "W009_commissioning_statistics.json")
OUT_SIGNOFF_JSON = os.path.join(REPORTS_DIR, "W009_SIGNOFF_RECORD.json")
OUT_SIGNOFF_MD = os.path.join(REPORTS_DIR, "W009_SIGNOFF_RECORD.md")
OUT_REPORT = os.path.join(REPORTS_DIR, "W009_COMMISSIONING_REPORT.md")

RELEASE_VERSION = "1.0"

STATUS_COMMISSIONED = "commissioned"
STATUS_PROVISIONAL = "provisional"
STATUS_OPEN = "open"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _ensure_dirs():
    os.makedirs(EXCEL_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)


def _yaml_escape(s):
    if s is None:
        return "null"
    s = str(s)
    if s == "":
        return "''"
    if any(c in s for c in ":#{}[],&*?|<>=!%@`\"'") or s != s.strip():
        return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')
    return s


def _commissioning_status(pair):
    """Map a cross-map pair (or None) to a commissioning status."""
    if pair is None:
        return STATUS_OPEN
    if pair.get("tier") == "HIGH":
        return STATUS_COMMISSIONED
    return STATUS_PROVISIONAL


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #
def assemble_register(confidence: dict, seeds_doc: dict):
    """Build the list of release entries + summary counts from W006 outputs."""
    pairs = confidence.get("pairs", []) or []
    unmapped = confidence.get("unmapped_design", []) or []
    seeds = (seeds_doc or {}).get("seeds", {}) or {}

    entries = []
    for p in pairs:
        dt = p.get("design_tag")
        status = _commissioning_status(p)
        entries.append({
            "design_tag": dt,
            "asdrawn_tag": p.get("asdrawn_tag"),
            "confidence": round(float(p.get("confidence", 0.0)), 4),
            "tier": p.get("tier"),
            "validation_status": p.get("validation_status"),
            "engineering_confirmed": dt in seeds,
            "commissioning_status": status,
            "reasons": p.get("reasons", []),
        })
    for u in unmapped:
        entries.append({
            "design_tag": u.get("design_tag"),
            "asdrawn_tag": None,
            "confidence": 0.0,
            "tier": "UNMAPPED",
            "validation_status": "unmapped",
            "engineering_confirmed": False,
            "commissioning_status": STATUS_OPEN,
            "reasons": [u.get("reason", "no candidate")],
        })

    entries.sort(key=lambda e: (e["design_tag"] or ""))

    summary = {
        "total_design_tags": len(entries),
        "commissioned": sum(1 for e in entries if e["commissioning_status"] == STATUS_COMMISSIONED),
        "provisional": sum(1 for e in entries if e["commissioning_status"] == STATUS_PROVISIONAL),
        "open": sum(1 for e in entries if e["commissioning_status"] == STATUS_OPEN),
        "engineering_confirmed_seeds": len(seeds),
        "tier_high": sum(1 for e in entries if e["tier"] == "HIGH"),
        "tier_medium": sum(1 for e in entries if e["tier"] == "MEDIUM"),
        "tier_low": sum(1 for e in entries if e["tier"] == "LOW"),
        "tier_unmapped": sum(1 for e in entries if e["tier"] == "UNMAPPED"),
    }
    return entries, summary


# --------------------------------------------------------------------------- #
# Writers
# --------------------------------------------------------------------------- #
def write_register_yaml(entries, summary, seeds_doc, generated):
    lines = [
        "# canonical_register_release_v%s.yaml" % RELEASE_VERSION,
        "# MINERVA QCELL/RFCELL — COMMISSIONED canonical instrument register (W009).",
        "# Generated by build_w009_release.py — regenerable via ./make.sh.",
        "# status: commissioned = HIGH/confirmed | provisional = MEDIUM/LOW | open = unmapped.",
        "release_version: '%s'" % RELEASE_VERSION,
        "wave: W009",
        "generated: %s" % _yaml_escape(generated),
        "system: MINERVA_QCELL_RFCELL",
        "summary:",
    ]
    for k, v in summary.items():
        lines.append("  %s: %d" % (k, v))
    lines.append("instruments:")
    for e in entries:
        lines.append("  - design_tag: %s" % _yaml_escape(e["design_tag"]))
        lines.append("    asdrawn_tag: %s" % _yaml_escape(e["asdrawn_tag"]))
        lines.append("    confidence: %.4f" % e["confidence"])
        lines.append("    tier: %s" % _yaml_escape(e["tier"]))
        lines.append("    commissioning_status: %s" % _yaml_escape(e["commissioning_status"]))
        lines.append("    engineering_confirmed: %s" % ("true" if e["engineering_confirmed"] else "false"))
        lines.append("    validation_status: %s" % _yaml_escape(e["validation_status"]))
    with open(OUT_REGISTER, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def write_signoff(summary, seeds_doc, generated):
    """Emit machine + human sign-off records (reviewer fields left blank)."""
    audit = (seeds_doc or {}).get("audit", {}) or {}
    record = {
        "release_version": RELEASE_VERSION,
        "wave": "W009",
        "generated": generated,
        "summary": summary,
        "seed_audit": audit,
        "signoff": {
            "reviewer_name": None,
            "reviewer_role": None,
            "date": None,
            "decision": None,           # approved | approved_with_exceptions | rejected
            "notes": None,
        },
        "honesty_note": (
            "commissioned entries are backed by HIGH-tier scores (engineering-"
            "confirmed seeds or independent corroboration). With no confirmed "
            "seeds the register is honestly provisional/open."
        ),
    }
    with open(OUT_SIGNOFF_JSON, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
        fh.write("\n")

    md = [
        "# W009 — Engineering Sign-Off Record",
        "",
        "**Release version:** %s  " % RELEASE_VERSION,
        "**Generated:** %s  " % generated,
        "**Wave:** W009 — Final Deliverables & Commissioning",
        "",
        "## Commissioning summary",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
        "| Total design tags | %d |" % summary["total_design_tags"],
        "| Commissioned (HIGH / confirmed) | %d |" % summary["commissioned"],
        "| Provisional (MEDIUM / LOW) | %d |" % summary["provisional"],
        "| Open (unmapped) | %d |" % summary["open"],
        "| Engineering-confirmed seeds | %d |" % summary["engineering_confirmed_seeds"],
        "",
        "## Sign-off",
        "",
        "> To approve this release, complete the fields below and commit " +
        "`reports/W009_SIGNOFF_RECORD.json` (mirror the same values there).",
        "",
        "- **Reviewer name:** ______________________________",
        "- **Reviewer role:** ______________________________",
        "- **Date:** ____________________",
        "- **Decision:** ☐ approved  ☐ approved with exceptions  ☐ rejected",
        "- **Notes:**",
        "",
        "  _________________________________________________",
        "",
        "---",
        "_Generated by `build_w009_release.py` — regenerable via `./make.sh`._",
    ]
    with open(OUT_SIGNOFF_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")


def write_report(entries, summary, seeds_doc, generated):
    total = summary["total_design_tags"] or 1
    pct = lambda n: 100.0 * n / total
    md = [
        "# W009 — Commissioning & Final Deliverables Report",
        "",
        "**Release version:** %s  " % RELEASE_VERSION,
        "**Generated:** %s" % generated,
        "",
        "## 1. What W009 does",
        "",
        "W009 consolidates the W005 reconciliation and the W006 heuristic cross-map " +
        "into a single **commissioned v1.0 canonical register** plus an engineering " +
        "**sign-off record**. Reviewer confirmations captured in the W008 viewer are " +
        "promoted into `configs/known_seeds.json` (via `ingest_triage`) and lift the " +
        "affected pairs to the HIGH tier / `commissioned` status.",
        "",
        "## 2. Commissioning status breakdown",
        "",
        "| Status | Definition | Count | % |",
        "| --- | --- | ---: | ---: |",
        "| commissioned | HIGH tier or engineering-confirmed seed | %d | %.1f |"
        % (summary["commissioned"], pct(summary["commissioned"])),
        "| provisional | MEDIUM / LOW heuristic pair | %d | %.1f |"
        % (summary["provisional"], pct(summary["provisional"])),
        "| open | unmapped (no candidate) | %d | %.1f |"
        % (summary["open"], pct(summary["open"])),
        "",
        "Confidence tiers: HIGH=%d, MEDIUM=%d, LOW=%d, UNMAPPED=%d."
        % (summary["tier_high"], summary["tier_medium"],
           summary["tier_low"], summary["tier_unmapped"]),
        "",
        "## 3. Engineering-confirmed seeds",
        "",
        "Confirmed seeds in `configs/known_seeds.json`: **%d**."
        % summary["engineering_confirmed_seeds"],
        "",
    ]
    if summary["engineering_confirmed_seeds"] == 0:
        md += [
            "> No seeds are confirmed yet, so **no tag is commissioned**. This is the " +
            "honest baseline: the register is entirely provisional/open until a " +
            "reviewer triages pairs in the viewer and the decisions are ingested.",
            "",
        ]
    md += [
        "## 4. Commissioning workflow (to reach sign-off)",
        "",
        "1. Open `output/interactive_viewer.html`, triage pairs (Confirm/Reject/Defer).",
        "2. Export `triage_decisions.json` from the viewer.",
        "3. `PYTHONPATH=src python3 -m abacus_svg_pid.ingest_triage triage_decisions.json`",
        "4. `PYTHONPATH=src python3 -m abacus_svg_pid.build_w006_crossmap` (applies seeds).",
        "5. `PYTHONPATH=src python3 -m abacus_svg_pid.build_w009_release` (regenerates this).",
        "6. Complete `reports/W009_SIGNOFF_RECORD.md` and commit.",
        "",
        "## 5. Deliverables",
        "",
        "- `data/excel/canonical_register_release_v%s.yaml` — commissioned register" % RELEASE_VERSION,
        "- `reports/W009_SIGNOFF_RECORD.json` / `.md` — sign-off record",
        "- `reports/W009_COMMISSIONING_REPORT.md` — this report",
        "",
        "---",
        "_Generated by `build_w009_release.py` — regenerable via `./make.sh`._",
    ]
    with open(OUT_REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def main():
    _ensure_dirs()
    confidence = _load_json(CONFIDENCE)
    if confidence is None:
        raise SystemExit(
            "ERROR: %s not found. Run build_w006_crossmap first (./make.sh)." % CONFIDENCE)
    seeds_doc = _load_json(KNOWN_SEEDS_FILE, default={})
    generated = datetime.datetime.now(datetime.timezone.utc).isoformat()

    entries, summary = assemble_register(confidence, seeds_doc)
    # Stable, timestamp-free counts for the CI golden-gate (semantic drift).
    with open(OUT_STATS, "w", encoding="utf-8") as fh:
        json.dump({"release_version": RELEASE_VERSION, "wave": "W009",
                   "summary": summary}, fh, indent=2)
        fh.write("\n")
    write_register_yaml(entries, summary, seeds_doc, generated)
    write_signoff(summary, seeds_doc, generated)
    write_report(entries, summary, seeds_doc, generated)

    print(">>> W009 release build complete")
    print("    total design tags  : %d" % summary["total_design_tags"])
    print("    commissioned       : %d" % summary["commissioned"])
    print("    provisional        : %d" % summary["provisional"])
    print("    open (unmapped)    : %d" % summary["open"])
    print("    confirmed seeds    : %d" % summary["engineering_confirmed_seeds"])
    print("    outputs            : data/excel/canonical_register_release_v%s.yaml, reports/W009_*" % RELEASE_VERSION)
    return summary


if __name__ == "__main__":
    main()
