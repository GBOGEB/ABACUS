"""
================================================================================
 Module : tests/test_w005_reconciliation.py
 Purpose: Assertions over the W005 XLSX tag/instrument register reconciliation.
          Verifies tag normalization, template detection, parse counts, the
          match/missing/extra arithmetic invariants, per-TYPE coverage and the
          PPT re-allocations.
 Current Wave : W005
 Status : ACTIVE
 Inputs  : data/excel/*.json + reports/W005_coverage_statistics.json
           (build first via:  PYTHONPATH=src python3 -m abacus_svg_pid.build_w005
            or ./make.sh — derived data/excel/ is git-ignored)
 Outputs : pass/fail to stdout (exit code 0 on success)
================================================================================
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL_DIR = os.path.join(ROOT, "data", "excel")
REPORTS = os.path.join(ROOT, "reports")
sys.path.insert(0, os.path.join(ROOT, "src"))


def _load(path):
    with open(path) as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# Pure-function tests (no built data required)
# --------------------------------------------------------------------------- #
def test_norm_tag_variations():
    from abacus_svg_pid.build_w005 import norm_tag
    assert norm_tag("CV001") == "CV001"
    assert norm_tag("CV-001") == "CV001"
    assert norm_tag("cv 001") == "CV001"
    assert norm_tag("LS-021") == "LS021"
    assert norm_tag(None) == ""
    # all three notations collapse to the same key
    assert norm_tag("CV001") == norm_tag("CV-001") == norm_tag("cv_001")


def test_prefix_of():
    from abacus_svg_pid.build_w005 import prefix_of
    assert prefix_of("CV001") == "CV"
    assert prefix_of("TT535") == "TT"
    assert prefix_of("LS-021") == "LS"
    assert prefix_of("V001") == "V"


def test_is_template():
    from abacus_svg_pid.build_w005 import is_template
    assert is_template("TTxxx") is True
    assert is_template("EHx11") is True
    assert is_template("PTx21") is True
    assert is_template("LSx13") is True
    # real instance tags are NOT templates
    assert is_template("TT535") is False
    assert is_template("CV560") is False
    # the 2-letter real prefix HX must not be mistaken for a template
    assert is_template("HX001") is False


# --------------------------------------------------------------------------- #
# Data-dependent tests
# --------------------------------------------------------------------------- #
def test_excel_register():
    d = _load(os.path.join(EXCEL_DIR, "excel_register.json"))
    assert d["instrument_count"] == 97
    h = d["prefix_histogram"]
    assert h["TT"] == 37 and h["CV"] == 12 and h["FV"] == 9
    # 15 distinct design TYPES
    assert len(h) == 15
    # two sheets parsed
    assert {s["sheet"] for s in d["sheets"]} == {"valve box-jumper", "cryomodule"}
    # legend glossary captured separately from instrument data
    assert len(d["legend_glossary"]) > 0


def test_catalog_register():
    d = _load(os.path.join(EXCEL_DIR, "catalog_register.json"))
    assert d["real_count"] == 141
    assert d["template_count"] == 24
    h = d["real_prefix_histogram"]
    assert h == {"CV": 10, "EH": 22, "HV": 12, "LS": 25, "PT": 9, "TT": 63}
    # template tags all flagged
    assert "TTxxx" in d["template_tags"] and "EHx11" in d["template_tags"]


def test_reconciliation_arithmetic():
    r = _load(os.path.join(EXCEL_DIR, "reconciliation_results.json"))
    s = r["summary"]
    # headline finding: zero exact overlap (orthogonal schemes)
    assert s["exact_matches"] == 0
    # invariants
    assert s["missing_in_catalog"] + s["exact_matches"] == s["excel_instruments"]
    assert s["extra_in_catalog"] + s["exact_matches"] == s["catalog_real_instruments"]
    assert s["excel_instruments"] == 97
    assert s["catalog_real_instruments"] == 141
    assert len(r["matched"]) == s["exact_matches"]
    assert len(r["missing"]) == s["missing_in_catalog"]
    assert len(r["extra"]) == s["extra_in_catalog"]


def test_type_coverage():
    r = _load(os.path.join(EXCEL_DIR, "reconciliation_results.json"))
    # 10 design TYPES entirely missing from the as-drawn catalog
    assert r["types_missing_from_catalog"] == [
        "FT", "FV", "HX", "J", "LE", "LI", "PV", "RD", "SV", "V"
    ]
    # LS (limit switches) is as-drawn only
    assert r["types_missing_from_excel"] == ["LS"]
    tc = r["type_coverage"]
    assert tc["LS"]["excel_count"] == 0 and tc["LS"]["catalog_count"] == 25
    assert tc["TT"]["excel_count"] == 37 and tc["TT"]["catalog_count"] == 63


def test_reallocations():
    r = _load(os.path.join(EXCEL_DIR, "reconciliation_results.json"))
    by_tag = {x["tag"]: x for x in r["reallocations"]}
    assert "TT535" in by_tag and "TT525" in by_tag
    assert by_tag["TT535"]["reallocated_to"] == "PZ"
    # TT535 is present in the as-drawn catalog; TT525 is not
    assert by_tag["TT535"]["in_catalog"] is True
    assert by_tag["TT525"]["in_catalog"] is False


def test_coverage_statistics():
    c = _load(os.path.join(REPORTS, "W005_coverage_statistics.json"))
    assert c["n_excel_design_tags"] == 97
    assert c["n_catalog_real_tags"] == 141
    assert c["exact_tag_coverage_pct"] == 0.0
    assert c["design_types_count"] == 15
    assert c["catalog_types_count"] == 6
    assert c["types_present_in_both"] == ["CV", "EH", "HV", "PT", "TT"]


def test_canonical_register_yaml():
    import yaml
    with open(os.path.join(EXCEL_DIR, "canonical_register_v1.yaml")) as fh:
        doc = yaml.safe_load(fh)
    reg = doc["canonical_instrument_register"]
    assert reg["counts"]["total"] == 238   # 97 design + 141 as-drawn
    assert reg["counts"]["matched"] == 0
    assert len(reg["entries"]) == 238


def test_outputs_exist():
    for p in [
        os.path.join(EXCEL_DIR, "excel_register.json"),
        os.path.join(EXCEL_DIR, "catalog_register.json"),
        os.path.join(EXCEL_DIR, "reconciliation_results.json"),
        os.path.join(EXCEL_DIR, "canonical_register_v1.yaml"),
        os.path.join(REPORTS, "W005_coverage_statistics.json"),
        os.path.join(REPORTS, "W005_XLSX_RECONCILIATION_REPORT.md"),
        os.path.join(REPORTS, "W005_validation_report.md"),
        os.path.join(REPORTS, "COMPONENT_CATALOG_v2.xlsx"),
    ]:
        assert os.path.exists(p), f"missing output: {p}"


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #
def _data_available():
    """Derived outputs are git-ignored; data-dependent tests run after build."""
    return os.path.exists(os.path.join(EXCEL_DIR, "excel_register.json"))


PURE_TESTS = ["test_norm_tag_variations", "test_prefix_of", "test_is_template"]


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
        print("SKIP  W005 data-dependent assertions — data/excel/ not built. "
              "Run ./make.sh (or build_w005) first; derived outputs are git-ignored.")
        print(f"\n{passed}/{len(pure)} pure-function assertions passed "
              f"({len(data_fns)} data tests skipped).")
        return passed

    for fn in data_fns:
        fn()
        print(f"  PASS  {fn.__name__}")
        passed += 1
    total = len(pure) + len(data_fns)
    print(f"\n{passed}/{total} W005 assertions passed.")
    return passed


if __name__ == "__main__":
    _run_all()
