"""
================================================================================
 Module : tests/test_aux_inventory.py
 Purpose: Assertions over the AD_01 Auxiliary-Building inventory builder
          (src/abacus_svg_pid/build_aux_inventory.py). Verifies the ISA-style
          tag extractor (keeps AA#### instruments, drops BR pipe-line fragments
          and the "P&ID" false hit), the AD_01.N drawing-number / system-code
          parser, and — when the inventory has been built — the honest
          cross-check numbers (19 PDFs, design=97, as-drawn=141, measured tag
          overlap reported exactly as found, never fabricated).
 Current Wave : W008 (integration pass)
 Status : ACTIVE
 Inputs  : reports/aux_building_inventory.json  (built by ./make.sh step 7,
           requires data/aux_building/pdfs/*.pdf — git-ignored input binaries)
 Outputs : pass/fail to stdout (exit code 0 on success). NO pytest dependency.
================================================================================
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(ROOT, "reports")
INV_JSON = os.path.join(REPORTS, "aux_building_inventory.json")
sys.path.insert(0, os.path.join(ROOT, "src"))


def _load(path):
    with open(path) as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# Pure-function tests (no built data required)
# --------------------------------------------------------------------------- #
def test_extract_tags_keeps_instruments():
    """AA#### air-actuated valve tags are kept as instrument tags."""
    from abacus_svg_pid.build_aux_inventory import _extract_tags
    tags, lines = _extract_tags("Valve AA7021 and AA0017 on sheet, CV560 too.")
    assert "AA7021" in tags, "AA7021 instrument tag not extracted"
    assert "AA0017" in tags, "AA0017 instrument tag not extracted"
    assert "CV560" in tags, "CV560 instrument tag not extracted"


def test_extract_tags_drops_pipeline_and_pid_noise():
    """BR#### pipe-line fragments and the P&ID header false hit are excluded
    from the instrument-tag set; the pipe-line goes to the lines set instead."""
    from abacus_svg_pid.build_aux_inventory import _extract_tags
    text = 'Line BR4017-1"-PAC3-BA shown on the P&ID (PID header).'
    tags, lines = _extract_tags(text)
    assert not any(t.startswith("BR") for t in tags), \
        f"BR pipe-line leaked into instrument tags: {tags}"
    assert "PID" not in tags, "PID header false hit not filtered"
    assert any(l.startswith("BR4017") for l in lines), \
        f"BR pipe-line not captured in lines set: {lines}"


def test_extract_tags_empty():
    from abacus_svg_pid.build_aux_inventory import _extract_tags
    tags, lines = _extract_tags(None)
    assert tags == set() and lines == set()
    tags, lines = _extract_tags("")
    assert tags == set() and lines == set()


def test_drawing_number_and_system_code():
    """The AD_01.N drawing number is parsed from the filename and the system
    code (=NA.PSxx / PSxx.yyy) from the title when present."""
    from abacus_svg_pid.build_aux_inventory import _drawing_number
    ad, sysc = _drawing_number(
        "AD_01.10  P_ID_PCW  (TP2=PS01.PAB12).pdf",
        "=NA.PS01_PFB712 Adiabatic Cooling")
    assert ad == "AD_01.10", f"drawing number wrong: {ad}"
    assert sysc is not None and "PS01" in sysc, f"system code wrong: {sysc}"
    ad2, sysc2 = _drawing_number("AD_01.2  Masterplan.pdf", None)
    assert ad2 == "AD_01.2" and sysc2 is None


# --------------------------------------------------------------------------- #
# Data-dependent tests (require ./make.sh step 7 to have run)
# --------------------------------------------------------------------------- #
def test_inventory_pdf_count():
    inv = _load(INV_JSON)
    assert inv["summary"]["pdf_count"] == 19, \
        f"expected 19 AD_01 PDFs, got {inv['summary']['pdf_count']}"
    assert len(inv["documents"]) == 19


def test_inventory_reference_set_sizes():
    """The honest reference sets must match the W005/W006 record: 97 design
    tags, 141 as-drawn real tags."""
    inv = _load(INV_JSON)
    s = inv["summary"]
    assert s["design_register_size"] == 97, \
        f"design register size drifted: {s['design_register_size']}"
    assert s["asdrawn_real_size"] == 141, \
        f"as-drawn real size drifted: {s['asdrawn_real_size']}"


def test_inventory_overlap_is_honest():
    """Overlap counts must equal the length of the listed overlapping tags —
    the report may never claim a count it cannot enumerate."""
    inv = _load(INV_JSON)
    s = inv["summary"]
    assert s["overlap_design_count"] == len(s["overlap_with_design_register"]), \
        "design overlap count does not match enumerated tags (fabrication guard)"
    assert s["overlap_asdrawn_count"] == len(s["overlap_with_asdrawn_real"]), \
        "as-drawn overlap count does not match enumerated tags (fabrication guard)"
    # every claimed overlap tag must actually be in the extracted universe
    universe = set(inv["all_instrument_tags"])
    for t in s["overlap_with_design_register"] + s["overlap_with_asdrawn_real"]:
        assert t in universe, f"overlap tag {t} not in extracted tag universe"


def test_inventory_has_tags_and_known_valves():
    """Extraction actually produced tags, and the known AA valves from the PCW
    and Instrument-Air sheets are present."""
    inv = _load(INV_JSON)
    assert inv["summary"]["unique_instrument_tags"] > 0, "no tags extracted"
    universe = set(inv["all_instrument_tags"])
    for known in ("AA7021", "AA0017"):
        assert known in universe, f"known AA valve {known} missing from universe"
    # BR pipe-line fragments must never appear as instrument tags
    assert not any(t.startswith("BR") for t in universe), \
        "BR pipe-line fragment leaked into the instrument-tag universe"


def test_inventory_pcw_and_air_sheets_present():
    """The PCW (AD_01.10) and Instrument-Air (AD_01.11) P&ID sheets are in the
    inventory with their system codes."""
    inv = _load(INV_JSON)
    by_ad = {d["drawing_number"]: d for d in inv["documents"]}
    assert "AD_01.10" in by_ad and "AD_01.11" in by_ad
    assert by_ad["AD_01.10"]["system_code"], "PCW sheet missing system code"
    assert by_ad["AD_01.11"]["system_code"], "Instrument-Air sheet missing system code"


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #
def _data_available():
    return os.path.exists(INV_JSON)


PURE_TESTS = [
    "test_extract_tags_keeps_instruments",
    "test_extract_tags_drops_pipeline_and_pid_noise",
    "test_extract_tags_empty",
    "test_drawing_number_and_system_code",
]


def _run_all():
    g = globals()
    pure = [g[n] for n in PURE_TESTS]
    data_fns = [v for k, v in sorted(g.items())
                if k.startswith("test_") and k not in PURE_TESTS]

    passed = 0
    for fn in pure:
        fn()
        print(f"  PASS  {fn.__name__}")
        passed += 1

    if not _data_available():
        print("SKIP  AD_01 inventory data-dependent assertions — "
              "reports/aux_building_inventory.json not built. Run ./make.sh "
              "first (step 7 requires data/aux_building/pdfs/*.pdf).")
        print(f"\n{passed}/{len(pure)} pure-function assertions passed "
              f"({len(data_fns)} data tests skipped).")
        return passed

    for fn in data_fns:
        fn()
        print(f"  PASS  {fn.__name__}")
        passed += 1
    total = len(pure) + len(data_fns)
    print(f"\n{passed}/{total} AD_01 aux-inventory assertions passed.")
    return passed


if __name__ == "__main__":
    _run_all()
