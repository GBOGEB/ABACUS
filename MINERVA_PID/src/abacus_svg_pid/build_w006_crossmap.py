"""
================================================================================
 Module : src/abacus_svg_pid/build_w006_crossmap.py
 Wave   : W006 — Design <-> As-Drawn Tag Cross-Map
 Status : ACTIVE
--------------------------------------------------------------------------------
 Purpose
 -------
 W005 proved the design register (circuit-sequential numbering, e.g. CV001/TT100)
 and the as-drawn catalog (SVG-instance numbering, e.g. CV560/TT514) use
 *orthogonal* tag schemes -> exact tag overlap is ZERO. This wave turns that
 finding into a *functional* bidirectional cross-map so a reviewer can ask
 "where is design tag CV001 physically drawn?" and get a ranked, confidence-
 scored answer.

 Method (honest, heuristic — NOT a spatial match)
 -------------------------------------------------
 The design register has NO drawing coordinates; only free-text locations and a
 circuit-sequential number. We therefore match on three observable, defensible
 features, type-partitioned (TYPE is a hard gate — we never cross instrument
 types):

   1. TYPE / ISA prefix         (mandatory gate)              .......... gate
   2. Circuit / temperature band (40K / 4.5K / 2K / WATER / ROOM)        0.45
        design  : parsed from the hundreds-digit + location keywords
        as-drawn: derived from the colour-class line (A/B/D/S/W/...)
   3. Within-group sequence order (design Nth <-> as-drawn Nth in the
        same TYPE+circuit bucket, ordered by tag number)                 0.35
   4. Signal / role consistency (analog 4-20mA control vs switch, etc.)  0.20

 A one-to-one greedy assignment (descending score) is applied *within each TYPE*
 so no as-drawn instance is claimed by two design tags.

 Confidence tiers
 ----------------
   HIGH   >= 0.80   TYPE + circuit + order agree
   MEDIUM 0.50-0.79 TYPE + circuit agree, order ambiguous
   LOW    0.30-0.49 TYPE (+ partial) only — flagged for engineering review
   (< 0.30 -> left UNMAPPED rather than assert a weak pairing)

 Honesty note
 ------------
 No HIGH-confidence pair is fabricated. Where evidence is thin the pair is left
 MEDIUM/LOW or unmapped and explicitly flagged. KNOWN_SEEDS holds *engineering-
 confirmed* design<->as-drawn pairs; it is intentionally empty until a reviewer
 confirms any (the W005 PPT re-allocations are TYPE re-assignments, not
 design<->as-drawn identities, so they are recorded separately as annotations).

 Inputs (produced by W005, regenerable via ./make.sh)
 ----------------------------------------------------
   data/excel/excel_register.json            (design register, 97 tags)
   data/excel/catalog_register.json          (as-drawn catalog, 141 real tags)
   data/excel/reconciliation_results.json    (W005 reallocations + type coverage)
   configs/isa_classes.json                  (prefix -> ISA meta, optional)

 Outputs
 -------
   data/crossmap/design_to_asdrawn.json      (bidirectional mapping + reverse idx)
   data/crossmap/crossmap_confidence.json    (per-pair score + reasons)
   reports/W006_crossmap_statistics.json     (coverage summary — tracked)
   reports/W006_CROSSMAP_REPORT.md           (validation report — tracked)
   data/excel/canonical_register_v2.yaml     (canonical register + cross-refs)

 Reproducible: PYTHONPATH=src python3 -m abacus_svg_pid.build_w006_crossmap
================================================================================
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EXCEL_DIR = os.path.join(ROOT, "data", "excel")
CROSSMAP_DIR = os.path.join(ROOT, "data", "crossmap")
REPORTS_DIR = os.path.join(ROOT, "reports")
CONFIGS_DIR = os.path.join(ROOT, "configs")

EXCEL_REGISTER = os.path.join(EXCEL_DIR, "excel_register.json")
CATALOG_REGISTER = os.path.join(EXCEL_DIR, "catalog_register.json")
RECON_RESULTS = os.path.join(EXCEL_DIR, "reconciliation_results.json")

OUT_MAPPING = os.path.join(CROSSMAP_DIR, "design_to_asdrawn.json")
OUT_CONFIDENCE = os.path.join(CROSSMAP_DIR, "crossmap_confidence.json")
OUT_STATS = os.path.join(REPORTS_DIR, "W006_crossmap_statistics.json")
OUT_REPORT = os.path.join(REPORTS_DIR, "W006_CROSSMAP_REPORT.md")
OUT_CANONICAL = os.path.join(EXCEL_DIR, "canonical_register_v2.yaml")

# --------------------------------------------------------------------------- #
# Domain knowledge
# --------------------------------------------------------------------------- #
# Circuit / temperature bands. Canonical labels used on BOTH sides.
BAND_40K = "40K"
BAND_45K = "4.5K"
BAND_2K = "2K"
BAND_WATER = "WATER"
BAND_ROOM = "ROOM"
BAND_VACUUM = "VACUUM"
BAND_UNKNOWN = "UNKNOWN"

# As-drawn colour-class line -> circuit band (from segmentation LINE_CLASSES +
# COLOR_MEANINGS; line letters as emitted by the W003/W004 catalog).
LINE_TO_BAND = {
    "A": BAND_45K,        # blue   #0000FF — 4.5 K / 3 bar supply
    "A_prime": BAND_WATER,  # navy #000080 — RFCELL water loop variant
    "B": BAND_2K,         # cyan   #00FFFF — 2 K / low-pressure return
    "D": BAND_40K,        # red/orange — 40 K thermal-shield circuit
    "S": BAND_40K,        # olive  #808000 — He-guard / 60 K return (warm shield family)
    "W": BAND_WATER,      # green  #00FF00 — DI cooling water
    "V": BAND_VACUUM,     # grey   #999999 — vacuum / structure
    "TBD": BAND_UNKNOWN,
    "": BAND_UNKNOWN,
}

# Design number hundreds-digit -> circuit band (CryoCell numbering convention).
#   0xx = room-temperature interface, 1xx = 40 K, 2xx = 4.5 K, 3xx = 2 K
HUNDREDS_TO_BAND = {
    0: BAND_ROOM,
    1: BAND_40K,
    2: BAND_45K,
    3: BAND_2K,
}

# Location free-text keywords -> circuit band (override / corroborate hundreds).
LOCATION_KEYWORDS = [
    ("40k", BAND_40K),
    ("5k circuit", BAND_45K),
    ("4.5k", BAND_45K),
    ("2k", BAND_2K),
    ("water", BAND_WATER),
    ("cooling water", BAND_WATER),
    ("vacuum", BAND_VACUUM),
    ("room temp", BAND_ROOM),
]

# Engineering-CONFIRMED design <-> as-drawn pairs. Intentionally empty until a
# reviewer signs off (see honesty note). Format: {design_tag: asdrawn_tag}.
#
# As of W009 the seeds are sourced from a *reviewed* file on disk
# (configs/known_seeds.json), produced by promoting the viewer's
# triage_decisions.json via `python -m abacus_svg_pid.ingest_triage`. The file
# is loaded at import time; if it is absent or empty the dict stays empty and
# no HIGH-confidence pair is fabricated (honesty invariant preserved).
KNOWN_SEEDS_FILE = os.path.join(CONFIGS_DIR, "known_seeds.json")


def load_known_seeds(path: str = KNOWN_SEEDS_FILE) -> "dict[str, str]":
    """Load engineering-confirmed {design_tag: asdrawn_tag} pairs from disk.

    Returns an empty dict when the file is missing or malformed — the pipeline
    must degrade gracefully to "no confirmed seeds" rather than crash, so a
    fresh checkout (with no reviewer sign-off yet) still builds.
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}
    seeds = doc.get("seeds", {}) if isinstance(doc, dict) else {}
    # Keep only well-formed string->string entries.
    return {str(k): str(v) for k, v in seeds.items()
            if isinstance(k, str) and isinstance(v, str) and k and v}


KNOWN_SEEDS: dict[str, str] = load_known_seeds()

# Scoring weights. Calibrated so that the *unconfirmed structural inference*
# (TYPE + circuit + parallel-numbering order) tops out at MEDIUM (0.75) — it is
# a reasonable hypothesis, not proof. HIGH (>=0.80) is only reached with an
# independent corroborator (signal/role agreement) or an engineering-confirmed
# seed. Circuit-only (singleton bucket, no order discriminator) lands at LOW.
W_CIRCUIT = 0.45
W_ORDER = 0.30
W_SIGNAL = 0.25

TIER_HIGH = 0.80
TIER_MEDIUM = 0.50
TIER_FLOOR = 0.30


# --------------------------------------------------------------------------- #
# IO helpers
# --------------------------------------------------------------------------- #
def _load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _ensure_dirs():
    os.makedirs(CROSSMAP_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(EXCEL_DIR, exist_ok=True)


# --------------------------------------------------------------------------- #
# Feature extraction
# --------------------------------------------------------------------------- #
def _tag_number(tag):
    """Trailing integer of a tag (CV001 -> 1, TT514 -> 514). None if absent."""
    m = re.search(r"(\d+)\s*$", tag or "")
    return int(m.group(1)) if m else None


def design_band(inst):
    """Circuit band for a design-register instrument (keywords first, then hundreds)."""
    loc = (inst.get("location") or "").lower()
    for kw, band in LOCATION_KEYWORDS:
        if kw in loc:
            return band
    num = _tag_number(inst.get("tag", ""))
    if num is not None:
        hundreds = (num // 100) % 10
        return HUNDREDS_TO_BAND.get(hundreds, BAND_UNKNOWN)
    return BAND_UNKNOWN


def asdrawn_band(inst):
    """Circuit band for an as-drawn catalog instrument (from colour-class line)."""
    return LINE_TO_BAND.get(inst.get("line", ""), BAND_UNKNOWN)


def _signal_kind(text):
    """Coarse signal classification for the consistency bonus."""
    t = (text or "").lower()
    if "4-20" in t or "ma" in t or "analog" in t:
        return "analog"
    if "switch" in t or "do" in t or "di" in t:
        return "discrete"
    return "unknown"


def extract_design(excel_reg):
    out = []
    for i in excel_reg.get("instruments", []):
        out.append({
            "tag": i["tag"],
            "type": i.get("prefix", ""),
            "number": _tag_number(i["tag"]),
            "band": design_band(i),
            "location": i.get("location", ""),
            "section": i.get("section", ""),
            "signal": _signal_kind(i.get("signal") or i.get("io")),
            "isa_canonical": i.get("isa_canonical", ""),
        })
    return out


def extract_asdrawn(catalog_reg):
    out = []
    for c in catalog_reg.get("instruments", []):
        if c.get("template"):
            continue  # never map onto template placeholders
        out.append({
            "tag": c["tag"],
            "type": c.get("prefix", ""),
            "number": _tag_number(c["tag"]),
            "band": asdrawn_band(c),
            "line": c.get("line", ""),
            "sheet": c.get("sheet", ""),
            "layer": c.get("layer", ""),
            "x": c.get("x"),
            "y": c.get("y"),
            "role": c.get("role", ""),
            "isa_canonical": c.get("isa_canonical", ""),
            "signal": "discrete" if c.get("role") in ("switch",) else "unknown",
        })
    return out


# --------------------------------------------------------------------------- #
# Matching engine
# --------------------------------------------------------------------------- #
def _order_rank(items):
    """Map each tag -> its 0-based rank within a list sorted by tag number."""
    ordered = sorted(items, key=lambda d: (d["number"] is None, d["number"] or 0))
    return {d["tag"]: idx for idx, d in enumerate(ordered)}


def score_pair(d, a, d_rank_in_band, a_rank_in_band, d_bucket, a_bucket):
    """Return (confidence, reasons[]) for a design/as-drawn candidate pair.

    `d_bucket` / `a_bucket` are the TYPE+band bucket sizes on each side. Order
    evidence is only awarded when BOTH buckets have >= 2 members — otherwise the
    rank alignment (0 == 0) is automatic and carries no information, so we do not
    let it inflate confidence (honesty: a singleton match is circuit-only).
    """
    reasons = ["TYPE_MATCH"]  # TYPE is a gate, recorded for transparency
    score = 0.0

    # Circuit / temperature band agreement
    if d["band"] != BAND_UNKNOWN and d["band"] == a["band"]:
        score += W_CIRCUIT
        reasons.append("CIRCUIT_MATCH(%s)" % d["band"])
    elif d["band"] != BAND_UNKNOWN and a["band"] != BAND_UNKNOWN:
        # known-but-different bands carry no positive evidence
        reasons.append("CIRCUIT_MISMATCH(%s!=%s)" % (d["band"], a["band"]))

    # Within TYPE+circuit sequence-order alignment — ONLY discriminating when
    # both buckets have >= 2 members.
    discriminating = (d_bucket >= 2 and a_bucket >= 2)
    if (d["band"] == a["band"] and discriminating
            and d_rank_in_band is not None and a_rank_in_band is not None):
        if d_rank_in_band == a_rank_in_band:
            score += W_ORDER
            reasons.append("ORDER_MATCH(#%d/%d)" % (d_rank_in_band, d_bucket))
        elif abs(d_rank_in_band - a_rank_in_band) == 1:
            score += W_ORDER * 0.5
            reasons.append("ORDER_NEAR(%d~%d)" % (d_rank_in_band, a_rank_in_band))
    elif d["band"] == a["band"] and not discriminating and d["band"] != BAND_UNKNOWN:
        reasons.append("ORDER_TRIVIAL(bucket<=1)")

    # Signal / role consistency
    if d["signal"] != "unknown" and d["signal"] == a["signal"]:
        score += W_SIGNAL
        reasons.append("SIGNAL_MATCH(%s)" % d["signal"])

    return round(min(score, 1.0), 4), reasons


def build_crossmap(design, asdrawn):
    """Type-partitioned, one-to-one greedy assignment with confidence scoring."""
    by_type_d = defaultdict(list)
    by_type_a = defaultdict(list)
    for d in design:
        by_type_d[d["type"]].append(d)
    for a in asdrawn:
        by_type_a[a["type"]].append(a)

    mappings = []
    unmapped_design = []

    for typ, d_list in by_type_d.items():
        a_list = by_type_a.get(typ, [])
        if not a_list:
            for d in d_list:
                unmapped_design.append({
                    "design_tag": d["tag"], "type": typ, "band": d["band"],
                    "reason": "no as-drawn instance of TYPE %s" % typ,
                })
            continue

        # Per-band ranks + bucket sizes for the order heuristic
        d_ranks = {}
        a_ranks = {}
        d_bucket = {}
        a_bucket = {}
        for band in set([d["band"] for d in d_list] + [a["band"] for a in a_list]):
            d_in = [d for d in d_list if d["band"] == band]
            a_in = [a for a in a_list if a["band"] == band]
            d_ranks[band] = _order_rank(d_in)
            a_ranks[band] = _order_rank(a_in)
            d_bucket[band] = len(d_in)
            a_bucket[band] = len(a_in)

        # Score every candidate pair within this TYPE
        candidates = []  # (score, reasons, d, a)
        for d in d_list:
            for a in a_list:
                dr = d_ranks.get(d["band"], {}).get(d["tag"])
                ar = a_ranks.get(a["band"], {}).get(a["tag"])
                db = d_bucket.get(d["band"], 0)
                ab = a_bucket.get(a["band"], 0)
                # honour engineering-confirmed seeds
                if KNOWN_SEEDS.get(d["tag"]) == a["tag"]:
                    candidates.append((1.0, ["KNOWN_SEED"], d, a))
                    continue
                sc, reasons = score_pair(d, a, dr, ar, db, ab)
                candidates.append((sc, reasons, d, a))

        # Greedy one-to-one assignment (descending score)
        candidates.sort(key=lambda t: t[0], reverse=True)
        used_d, used_a = set(), set()
        for sc, reasons, d, a in candidates:
            if d["tag"] in used_d or a["tag"] in used_a:
                continue
            if sc < TIER_FLOOR:
                continue
            used_d.add(d["tag"])
            used_a.add(a["tag"])
            mappings.append({
                "design_tag": d["tag"],
                "asdrawn_tag": a["tag"],
                "type": typ,
                "confidence": sc,
                "tier": _tier(sc),
                "reasons": reasons,
                "design_band": d["band"],
                "asdrawn_band": a["band"],
                "asdrawn_sheet": a["sheet"],
                "asdrawn_xy": [a["x"], a["y"]],
                "validation_status": "auto_matched" if "KNOWN_SEED" not in reasons else "manually_verified",
            })

        for d in d_list:
            if d["tag"] not in used_d:
                unmapped_design.append({
                    "design_tag": d["tag"], "type": typ, "band": d["band"],
                    "reason": "no candidate >= floor (%.2f) of TYPE %s" % (TIER_FLOOR, typ),
                })

    mappings.sort(key=lambda m: (-m["confidence"], m["design_tag"]))
    return mappings, unmapped_design


def _tier(score):
    if score >= TIER_HIGH:
        return "HIGH"
    if score >= TIER_MEDIUM:
        return "MEDIUM"
    return "LOW"


# --------------------------------------------------------------------------- #
# Output emitters
# --------------------------------------------------------------------------- #
def _statistics(design, asdrawn, mappings, unmapped):
    tiers = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for m in mappings:
        tiers[m["tier"]] += 1
    mapped_asdrawn = {m["asdrawn_tag"] for m in mappings}
    return {
        "total_design_tags": len(design),
        "total_asdrawn_real_tags": len(asdrawn),
        "mapped": len(mappings),
        "mapped_pct_of_design": round(100.0 * len(mappings) / max(1, len(design)), 1),
        "high_confidence": tiers["HIGH"],
        "medium_confidence": tiers["MEDIUM"],
        "low_confidence": tiers["LOW"],
        "unmapped_design": len(unmapped),
        "asdrawn_unclaimed": len(asdrawn) - len(mapped_asdrawn),
        "known_seeds": len(KNOWN_SEEDS),
    }


def write_mapping_json(mappings, design, asdrawn):
    fwd = {}
    rev = {}
    for m in mappings:
        fwd[m["design_tag"]] = m["asdrawn_tag"]
        rev[m["asdrawn_tag"]] = m["design_tag"]
    payload = {
        "version": "1.0",
        "wave": "W006",
        "description": "Bidirectional design<->as-drawn tag cross-map (heuristic, "
                       "confidence-scored). See W006_CROSSMAP_REPORT.md for method.",
        "design_to_asdrawn": fwd,
        "asdrawn_to_design": rev,
        "mappings": mappings,
    }
    with open(OUT_MAPPING, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def write_confidence_json(mappings, unmapped):
    payload = {
        "version": "1.0",
        "wave": "W006",
        "tiers": {"HIGH": ">=0.80", "MEDIUM": "0.50-0.79", "LOW": "0.30-0.49"},
        "weights": {"circuit": W_CIRCUIT, "order": W_ORDER, "signal": W_SIGNAL},
        "pairs": [
            {
                "design_tag": m["design_tag"],
                "asdrawn_tag": m["asdrawn_tag"],
                "confidence": m["confidence"],
                "tier": m["tier"],
                "reasons": m["reasons"],
                "validation_status": m["validation_status"],
            }
            for m in mappings
        ],
        "unmapped_design": unmapped,
    }
    with open(OUT_CONFIDENCE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def write_statistics_json(stats):
    with open(OUT_STATS, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2)


def _yaml_escape(s):
    s = str(s).replace('"', '\\"')
    return '"%s"' % s


def write_canonical_v2(mappings, design, asdrawn, recon):
    """Emit a canonical register v2 with cross-references (hand-rolled YAML, stdlib)."""
    fwd = {m["design_tag"]: m for m in mappings}
    lines = [
        "# canonical_register_v2.yaml",
        "# W006 — canonical register with design<->as-drawn cross-references.",
        "# Generated by build_w006_crossmap.py (regenerable via ./make.sh).",
        "version: 2",
        "wave: W006",
        "design_tag_count: %d" % len(design),
        "asdrawn_real_tag_count: %d" % len(asdrawn),
        "crossmap_count: %d" % len(mappings),
        "instruments:",
    ]
    for d in sorted(design, key=lambda x: x["tag"]):
        m = fwd.get(d["tag"])
        lines.append("  - design_tag: %s" % _yaml_escape(d["tag"]))
        lines.append("    type: %s" % _yaml_escape(d["type"]))
        lines.append("    circuit_band: %s" % _yaml_escape(d["band"]))
        lines.append("    location: %s" % _yaml_escape(d["location"]))
        if m:
            lines.append("    asdrawn_tag: %s" % _yaml_escape(m["asdrawn_tag"]))
            lines.append("    crossmap_confidence: %.4f" % m["confidence"])
            lines.append("    crossmap_tier: %s" % _yaml_escape(m["tier"]))
            lines.append("    crossmap_validation: %s" % _yaml_escape(m["validation_status"]))
        else:
            lines.append("    asdrawn_tag: null")
            lines.append("    crossmap_confidence: 0.0")
            lines.append("    crossmap_tier: UNMAPPED")
    # record W005 PPT re-allocations as separate annotations (not crossmap pairs)
    lines.append("reallocations:  # TYPE re-assignments from PPT — NOT design<->as-drawn identities")
    for r in recon.get("reallocations", []):
        lines.append("  - tag: %s" % _yaml_escape(r.get("tag", "")))
        lines.append("    reallocated_to: %s" % _yaml_escape(r.get("reallocated_to", "")))
        lines.append("    target: %s" % _yaml_escape(r.get("target", "")))
    with open(OUT_CANONICAL, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join("---" for _ in headers) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def write_report(stats, mappings, unmapped, design, asdrawn, recon):
    hi = [m for m in mappings if m["tier"] == "HIGH"]
    med = [m for m in mappings if m["tier"] == "MEDIUM"]
    low = [m for m in mappings if m["tier"] == "LOW"]

    md = []
    md.append("# W006 — Design ↔ As-Drawn Cross-Map Report\n")
    md.append("> Turns the W005 *0 % exact-overlap* finding into a functional, "
              "confidence-scored bidirectional cross-map. **Heuristic, not a spatial "
              "match** — the design register has no drawing coordinates, so pairs are "
              "inferred from TYPE + circuit/temperature band + within-group ordering. "
              "No HIGH-confidence pair is fabricated.\n")

    md.append("## 1. Executive summary\n")
    md.append(_md_table(
        ["Metric", "Value"],
        [
            ["Design tags (total)", stats["total_design_tags"]],
            ["As-drawn real tags (total)", stats["total_asdrawn_real_tags"]],
            ["**Mapped design tags**", "**%d (%.1f%%)**" % (stats["mapped"], stats["mapped_pct_of_design"])],
            ["– HIGH confidence (≥0.80)", stats["high_confidence"]],
            ["– MEDIUM confidence (0.50–0.79)", stats["medium_confidence"]],
            ["– LOW confidence (0.30–0.49)", stats["low_confidence"]],
            ["Unmapped design tags", stats["unmapped_design"]],
            ["As-drawn instances left unclaimed", stats["asdrawn_unclaimed"]],
            ["Engineering-confirmed seeds", stats["known_seeds"]],
        ]))
    md.append("")

    md.append("## 2. Method & scoring\n")
    md.append("Type-partitioned (TYPE is a hard gate). Score per candidate pair:\n")
    md.append(_md_table(
        ["Feature", "Weight", "Source (design / as-drawn)"],
        [
            ["TYPE / ISA prefix", "gate", "prefix / prefix"],
            ["Circuit / temperature band", "%.2f" % W_CIRCUIT, "hundreds-digit + location text / colour-class line"],
            ["Within-group sequence order", "%.2f" % W_ORDER, "tag-number rank / tag-number rank"],
            ["Signal / role consistency", "%.2f" % W_SIGNAL, "4-20mA·IO / role"],
        ]))
    md.append("\nTiers: **HIGH ≥ 0.80**, **MEDIUM 0.50–0.79**, **LOW 0.30–0.49**; "
              "below 0.30 the design tag is left **UNMAPPED** rather than asserting a weak pairing. "
              "A greedy one-to-one assignment within each TYPE prevents double-claiming an as-drawn instance.\n")

    md.append("## 3. HIGH-confidence matches (≥ 0.80)\n")
    if hi:
        md.append(_md_table(
            ["Design", "As-drawn", "Conf.", "Band", "Reasons"],
            [[m["design_tag"], m["asdrawn_tag"], "%.2f" % m["confidence"],
              m["design_band"], ", ".join(m["reasons"])] for m in hi]))
    else:
        md.append("_None._ With no drawing coordinates on the design side and no "
                  "engineering-confirmed seeds yet, the order heuristic alone rarely "
                  "clears 0.80. This is reported honestly rather than inflated.")
    md.append("")

    md.append("## 4. MEDIUM-confidence matches (0.50–0.79)\n")
    md.append(_md_table(
        ["Design", "As-drawn", "Conf.", "Band", "Reasons"],
        [[m["design_tag"], m["asdrawn_tag"], "%.2f" % m["confidence"],
          m["design_band"], ", ".join(m["reasons"])] for m in med]) if med else "_None._")
    md.append("")

    md.append("## 5. LOW-confidence matches (0.30–0.49) — needs review\n")
    md.append(_md_table(
        ["Design", "As-drawn", "Conf.", "Band", "Reasons"],
        [[m["design_tag"], m["asdrawn_tag"], "%.2f" % m["confidence"],
          m["design_band"], ", ".join(m["reasons"])] for m in low]) if low else "_None._")
    md.append("")

    md.append("## 6. Unmapped design tags (%d)\n" % len(unmapped))
    md.append(_md_table(
        ["Design", "Type", "Band", "Reason"],
        [[u["design_tag"], u["type"], u["band"], u["reason"]] for u in unmapped]) if unmapped else "_None._")
    md.append("")

    md.append("## 7. W005 PPT re-allocations (carried as annotations)\n")
    md.append("These are TYPE re-assignments documented in the QM instrumentation deck — "
              "**not** design↔as-drawn identities — recorded in `canonical_register_v2.yaml`:\n")
    md.append(_md_table(
        ["Tag", "Reallocated to", "Target"],
        [[r.get("tag"), r.get("reallocated_to"), r.get("target")] for r in recon.get("reallocations", [])]))
    md.append("")

    md.append("## 8. Recommendations\n")
    md.append("1. **Engineering review** of MEDIUM pairs to promote/demote and seed `KNOWN_SEEDS`.\n"
              "2. **Investigate unmapped TYPEs** (`FV`, `FT`, `HX`, `J`, `LE`, `LI`, `PV`, `RD`, `SV`) — "
              "present in design, absent from the as-drawn catalog (drawing gap or different sheet).\n"
              "3. **Add coordinates to the design register** (or a sheet/zone hint) to unlock a true "
              "spatial match and lift confidence into the HIGH tier.\n"
              "4. **Re-run** after each seed confirmation: `PYTHONPATH=src python3 -m abacus_svg_pid.build_w006_crossmap`.\n")

    md.append("\n---\n_Generated by `build_w006_crossmap.py` — regenerable via `./make.sh`._\n")

    with open(OUT_REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def main():
    _ensure_dirs()
    # Re-load reviewed seeds at run time so a freshly-ingested
    # configs/known_seeds.json is honoured without re-importing the module.
    global KNOWN_SEEDS
    KNOWN_SEEDS = load_known_seeds()
    if not (os.path.exists(EXCEL_REGISTER) and os.path.exists(CATALOG_REGISTER)):
        raise SystemExit(
            "ERROR: W005 registers not found. Run build_w005 first (./make.sh)."
        )

    excel_reg = _load_json(EXCEL_REGISTER)
    catalog_reg = _load_json(CATALOG_REGISTER)
    recon = _load_json(RECON_RESULTS) if os.path.exists(RECON_RESULTS) else {"reallocations": []}

    design = extract_design(excel_reg)
    asdrawn = extract_asdrawn(catalog_reg)

    mappings, unmapped = build_crossmap(design, asdrawn)
    stats = _statistics(design, asdrawn, mappings, unmapped)

    write_mapping_json(mappings, design, asdrawn)
    write_confidence_json(mappings, unmapped)
    write_statistics_json(stats)
    write_canonical_v2(mappings, design, asdrawn, recon)
    write_report(stats, mappings, unmapped, design, asdrawn, recon)

    print(">>> W006 cross-map complete")
    print("    design tags        : %d" % stats["total_design_tags"])
    print("    as-drawn real tags : %d" % stats["total_asdrawn_real_tags"])
    print("    mapped             : %d (%.1f%%)  HIGH=%d MEDIUM=%d LOW=%d"
          % (stats["mapped"], stats["mapped_pct_of_design"],
             stats["high_confidence"], stats["medium_confidence"], stats["low_confidence"]))
    print("    unmapped design    : %d" % stats["unmapped_design"])
    print("    outputs            : data/crossmap/, reports/W006_*, data/excel/canonical_register_v2.yaml")
    return stats


if __name__ == "__main__":
    main()
