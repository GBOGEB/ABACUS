"""
================================================================================
 Module : src/abacus_svg_pid/ingest_triage.py
 Wave   : W009 — Commissioning: triage feedback -> engineering-confirmed seeds
 Status : ACTIVE
--------------------------------------------------------------------------------
 Purpose
 -------
 The W008 interactive viewer lets an engineer triage each heuristic cross-map
 pair (Confirm / Reject / Defer) and export the decisions as
 `triage_decisions.json`. This module is the *intake valve*: it validates those
 human decisions against the live cross-map and promotes the CONFIRMED pairs
 into `configs/known_seeds.json`, which build_w006_crossmap.py loads as
 KNOWN_SEEDS (each confirmed pair then scores 1.0 -> HIGH tier).

 Honesty invariant
 -----------------
 This script NEVER invents a confirmation. It only persists decisions a human
 made in the viewer. A pair is promoted to a seed ONLY when:
   * the viewer recorded decision == "confirm", AND
   * both the design tag and the as-drawn tag are real tags known to the
     cross-map inputs (typo / stale decisions are dropped with a warning), AND
   * the TYPE/ISA prefix of both sides agrees (we never seed a cross-type pair).

 Rejected / deferred decisions are NOT seeded; their counts are recorded in the
 audit block for traceability.

 Usage
 -----
   PYTHONPATH=src python3 -m abacus_svg_pid.ingest_triage path/to/triage_decisions.json
   PYTHONPATH=src python3 -m abacus_svg_pid.ingest_triage --dry-run decisions.json

 Then re-run the cross-map to apply the promotions:
   PYTHONPATH=src python3 -m abacus_svg_pid.build_w006_crossmap
================================================================================
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIGS_DIR = os.path.join(ROOT, "configs")
EXCEL_DIR = os.path.join(ROOT, "data", "excel")

KNOWN_SEEDS_FILE = os.path.join(CONFIGS_DIR, "known_seeds.json")
EXCEL_REGISTER = os.path.join(EXCEL_DIR, "excel_register.json")
CATALOG_REGISTER = os.path.join(EXCEL_DIR, "catalog_register.json")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _type_prefix(tag: str) -> str:
    """Leading alpha ISA prefix of a tag (CV560 -> 'CV', TT100 -> 'TT')."""
    m = re.match(r"\s*([A-Za-z]+)", tag or "")
    return m.group(1).upper() if m else ""


def _collect_tags(register, keys=("tag", "design_tag", "asdrawn_tag", "catalog_tag")):
    """Best-effort harvest of every tag string from a W005 register JSON."""
    tags = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in keys and isinstance(v, str) and v.strip():
                    tags.add(v.strip())
                else:
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(register)
    return tags


def _known_tag_sets():
    """Return (design_tags, asdrawn_tags) gathered from the W005 registers.

    Returns (None, None) when registers are unavailable so validation can be
    skipped gracefully (e.g. in isolated unit tests).
    """
    design = asdrawn = None
    if os.path.exists(EXCEL_REGISTER):
        design = _collect_tags(_load_json(EXCEL_REGISTER))
    if os.path.exists(CATALOG_REGISTER):
        asdrawn = _collect_tags(_load_json(CATALOG_REGISTER))
    return design, asdrawn


# --------------------------------------------------------------------------- #
# Core
# --------------------------------------------------------------------------- #
def extract_confirmed_pairs(triage_doc: dict):
    """Pull {design_tag: asdrawn_tag} from a viewer triage export.

    Prefers the explicit ``known_seeds`` block the viewer pre-computes; falls
    back to scanning ``decisions`` for entries with decision == 'confirm'.
    Also returns reject/defer counts for the audit trail.
    """
    seeds = {}
    rejected = deferred = 0

    decisions = triage_doc.get("decisions", {}) or {}
    for _key, d in decisions.items():
        if not isinstance(d, dict):
            continue
        decision = (d.get("decision") or "").lower()
        if decision == "confirm":
            dt, at = d.get("design"), d.get("asdrawn")
            if isinstance(dt, str) and isinstance(at, str) and dt and at:
                seeds[dt] = at
        elif decision == "reject":
            rejected += 1
        elif decision == "defer":
            deferred += 1

    # Merge the viewer's pre-extracted known_seeds (authoritative if present).
    for dt, at in (triage_doc.get("known_seeds", {}) or {}).items():
        if isinstance(dt, str) and isinstance(at, str) and dt and at:
            seeds[dt] = at

    return seeds, rejected, deferred


def validate_pairs(seeds: dict, design_tags, asdrawn_tags):
    """Split candidate seeds into (accepted, warnings).

    A pair is rejected (with a human-readable warning) when a tag is unknown to
    the registers or the ISA TYPE prefixes disagree. When a register is
    unavailable (None) the corresponding existence check is skipped.
    """
    accepted = {}
    warnings = []
    for dt, at in sorted(seeds.items()):
        if design_tags is not None and dt not in design_tags:
            warnings.append("drop %s->%s: design tag %r not in design register" % (dt, at, dt))
            continue
        if asdrawn_tags is not None and at not in asdrawn_tags:
            warnings.append("drop %s->%s: as-drawn tag %r not in as-drawn catalog" % (dt, at, at))
            continue
        if _type_prefix(dt) != _type_prefix(at):
            warnings.append("drop %s->%s: TYPE mismatch (%s != %s)"
                            % (dt, at, _type_prefix(dt), _type_prefix(at)))
            continue
        accepted[dt] = at
    return accepted, warnings


def build_seed_document(accepted: dict, source_file: str, rejected: int,
                        deferred: int, existing: "dict | None" = None) -> dict:
    """Assemble the configs/known_seeds.json document with provenance/audit."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    provenance = {}
    if existing and isinstance(existing.get("provenance"), dict):
        provenance.update(existing["provenance"])
    for dt, at in accepted.items():
        provenance[dt] = {
            "asdrawn_tag": at,
            "source": "viewer_triage_confirm",
            "ingested_at": now,
            "source_file": os.path.basename(source_file),
        }
    return {
        "version": "1.0",
        "wave": "W009",
        "description": (
            "Engineering-CONFIRMED design<->as-drawn seed pairs. A pair appears "
            "here ONLY after a human reviewer confirms it in the interactive "
            "viewer and the decision is promoted via "
            "`python -m abacus_svg_pid.ingest_triage`. build_w006_crossmap.py "
            "loads this file into KNOWN_SEEDS; each listed pair scores 1.0 "
            "(HIGH). No HIGH-confidence pair is fabricated."
        ),
        "seeds": dict(sorted(accepted.items())),
        "provenance": provenance,
        "audit": {
            "last_ingested": now,
            "source_file": os.path.basename(source_file),
            "confirmed_count": len(accepted),
            "rejected_recorded": rejected,
            "deferred_recorded": deferred,
        },
    }


def ingest(triage_path: str, seeds_out: str = KNOWN_SEEDS_FILE,
           dry_run: bool = False):
    """Read a triage export, validate, and (optionally) write known_seeds.json.

    Returns the assembled seed document (also when dry-run).
    """
    triage_doc = _load_json(triage_path)
    seeds, rejected, deferred = extract_confirmed_pairs(triage_doc)
    design_tags, asdrawn_tags = _known_tag_sets()
    accepted, warnings = validate_pairs(seeds, design_tags, asdrawn_tags)

    existing = None
    if os.path.exists(seeds_out):
        try:
            existing = _load_json(seeds_out)
        except (json.JSONDecodeError, OSError):
            existing = None

    doc = build_seed_document(accepted, triage_path, rejected, deferred, existing)

    for w in warnings:
        print("  [warn] %s" % w, file=sys.stderr)

    if not dry_run:
        os.makedirs(os.path.dirname(seeds_out), exist_ok=True)
        with open(seeds_out, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2)
            fh.write("\n")

    print(">>> triage ingest %s" % ("(dry-run)" if dry_run else "complete"))
    print("    source            : %s" % triage_path)
    print("    confirmed pairs   : %d" % len(accepted))
    print("    dropped (warnings): %d" % len(warnings))
    print("    rejected recorded : %d" % rejected)
    print("    deferred recorded : %d" % deferred)
    if not dry_run:
        print("    written           : %s" % seeds_out)
        print("    next              : re-run build_w006_crossmap to apply promotions")
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Promote viewer triage_decisions.json confirmations into "
                    "configs/known_seeds.json (KNOWN_SEEDS).")
    ap.add_argument("triage_file", help="path to triage_decisions.json exported from the viewer")
    ap.add_argument("--out", default=KNOWN_SEEDS_FILE,
                    help="output known_seeds.json path (default: configs/known_seeds.json)")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate and report without writing the seeds file")
    args = ap.parse_args(argv)

    if not os.path.exists(args.triage_file):
        raise SystemExit("ERROR: triage file not found: %s" % args.triage_file)
    ingest(args.triage_file, seeds_out=args.out, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
