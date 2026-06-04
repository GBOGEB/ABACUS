"""
================================================================================
 Module : tests/test_w003_w004.py
 Purpose: Assertions over the W003 (layer hierarchy) + W004 (geometric tracing)
          model outputs. Verifies every phase produced non-zero, internally
          consistent results.
 Current Wave : W003 + W004
 Status : ACTIVE
 Inputs  : data/model/*.json + data/pemo/*.yaml (build first via the engines)
 Outputs : pass/fail to stdout (exit code 0 on success)
================================================================================
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(ROOT, "data", "model")


def _load(name):
    with open(os.path.join(MODEL, name)) as fh:
        return json.load(fh)


def test_unmapped_reduction():
    d = _load("unmapped_reduction.json")
    assert d["unmapped_before"] == 982
    assert d["still_unresolved_count"] == 112
    assert d["reclassified_count"] == d["unmapped_before"] - d["still_unresolved_count"]
    assert sum(d["categories_reclassified"].values()) == d["reclassified_count"]


def test_pairing():
    d = _load("paired_elements.json")["stats"] if "stats" in _load("paired_elements.json") else _load("paired_elements.json")
    # tolerate either flat or nested shape
    flat = _load("w003_w004_stats.json")["phase2"]
    assert flat["text_to_component_pairs"] == 315
    assert flat["dots_paired"] == 205
    assert flat["arrows_paired"] == 132
    assert flat["arrows_floating"] == 77


def test_text_standardization():
    d = _load("text_standardization.json")
    assert d["total_text_nodes"] == 533
    assert d["target_font"].startswith("Consolas")
    assert sum(d["assigned_tier_counts"].values()) == 533
    assert set(d["size_tiers_mm"]) == {
        "major_header", "segment_label_vertical", "instrument_tag", "annotation"
    }


def test_layer_assignment():
    d = _load("layer_assignment.json")
    assert d["total_layers"] == 21
    counts = d["element_counts_per_layer"]
    assert counts["11_Text_ColorCoded"] == 516
    assert counts["12_Dots_SpecChanges_ALL"] == 205
    assert counts["05_HeatLoads_ALL"] == 100
    assert counts["06_SegmentNames_Vertical_Black"] == 17


def test_flow_topology():
    d = _load("flow_topology.json")
    s = _load("w003_w004_stats.json")["phase5"]
    assert s["total_flow_arrows"] == 132
    assert s["total_junctions"] == 36
    assert d is not None


def test_nomenclature():
    d = _load("segment_nomenclature.json")
    assert d["parsed_count"] == 33
    tree = d["nomenclature_tree"]
    assert "A'" in tree["A"]
    assert set(tree) >= {"A", "B", "D", "E", "W", "S", "V"}


def test_spec_dots():
    d = _load("spec_dots_catalog.json")
    per = d["dots_per_line"]
    assert per["S"]["count"] == 40
    assert per["uncoloured"]["count"] == 153


def test_component_catalog():
    d = _load("component_line_assignment.json")
    assert d["count"] == 297
    assert len(d["components"]) == 297


def test_scope_boundaries():
    d = _load("scope_boundary_validation.json")
    assert d["handover_count"] == 22
    assert len(d["handover_diamonds_TPXYYYY"]) == 22
    assert set(d["boundaries_detected"]) >= {"QM", "QVB", "Jumper", "QINFRA"}
    assert d["W_line_bottom_right_elements"] == 19


def test_pemo_yaml_exists():
    p = os.path.join(ROOT, "data", "pemo", "ic_system_v1.2.yaml")
    assert os.path.exists(p)
    txt = open(p).read()
    assert "1.2" in txt


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS  {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} W003+W004 assertions passed.")


if __name__ == "__main__":
    _run_all()
