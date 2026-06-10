"""
================================================================================
 Module : tests/test_w008_viewer.py
 Purpose: Assertions over the W008 interactive cross-map viewer generator
          (src/abacus_svg_pid/build_viewer.py). Verifies the produced HTML is
          a single self-contained file that embeds: one table row per crossmap
          entry, hit-testable SVG markers whose data-tag values resolve to real
          as-drawn catalog instances, the full 21-layer contract, both sheets,
          and the confidence-tier colour scheme. Pure-function tests exercise
          the data-model joins without needing a browser.
 Current Wave : W008
 Status : ACTIVE
 Inputs  : data/crossmap/*.json, data/excel/catalog_register.json,
           configs/layers.yaml, output_v6/{QCELL,RFCELL}/*_13layers.svg
           (build first via ./make.sh — derived artifacts are git-ignored)
 Outputs : pass/fail to stdout (exit code 0 on success)
================================================================================
"""

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

CROSSMAP = os.path.join(ROOT, "data", "crossmap", "design_to_asdrawn.json")
CATALOG = os.path.join(ROOT, "data", "excel", "catalog_register.json")


def _data_available():
    return os.path.exists(CROSSMAP) and os.path.exists(CATALOG)


needs_data = pytest.mark.skipif(
    not _data_available(),
    reason="derived data/crossmap + catalog not built (run ./make.sh first)")


# --------------------------------------------------------------------------- #
# Pure-function tests (no built data required)
# --------------------------------------------------------------------------- #
def test_layers_contract_is_21():
    from abacus_svg_pid.build_viewer import _load_layers, LAYERS_YAML
    layers = _load_layers(LAYERS_YAML)
    assert len(layers) == 21, "layer contract must expose 21 named layers"
    # idx is dense 0..20 and maps directly to the lyr-NN class scheme
    assert [l["idx"] for l in layers] == list(range(21))
    assert layers[18]["id"].startswith("11_Text"), "lyr-18 is the text layer"


def test_overlay_injection_is_idempotent_and_hit_testable():
    from abacus_svg_pid.build_viewer import _inject_overlay
    svg = '<svg viewBox="0 0 10 10"><rect/></svg>'
    markers = [{"tag": "CV560", "x": 1.0, "y": 2.0, "type": "CV"}]
    out = _inject_overlay(svg, markers)
    assert 'id="tag-overlay"' in out
    assert 'data-tag="CV560"' in out
    assert 'class="tag-hit"' in out  # the clickable hit circle
    assert out.rstrip().endswith("</svg>")  # overlay sits *inside* the svg
    # empty marker list still produces a (harmless) overlay container
    assert 'id="tag-overlay"' in _inject_overlay(svg, [])


def test_design_rows_join_marks_unmapped():
    from abacus_svg_pid.build_viewer import _design_rows
    register = [
        {"design_tag": "CV001", "type": "CV", "circuit_band": "40K", "location": "x"},
        {"design_tag": "V001", "type": "V", "circuit_band": "ROOM", "location": "y"},
    ]
    mbd = {"CV001": {"asdrawn_tag": "CV560", "type": "CV", "confidence": 0.75,
                     "tier": "MEDIUM", "reasons": ["TYPE_MATCH"],
                     "asdrawn_sheet": "QCELL", "asdrawn_xy": [9.0, 4.0]}}
    rows = _design_rows(register, mbd)
    by = {r["design"]: r for r in rows}
    assert by["CV001"]["asdrawn"] == "CV560" and by["CV001"]["tier"] == "MEDIUM"
    assert by["V001"]["asdrawn"] == "" and by["V001"]["tier"] == "UNMAPPED"


# --------------------------------------------------------------------------- #
# Data-dependent tests (require ./make.sh first)
# --------------------------------------------------------------------------- #
@needs_data
def test_build_emits_self_contained_html():
    from abacus_svg_pid.build_viewer import build_html
    out, stats = build_html()
    assert os.path.exists(out)
    html = open(out).read()
    # single file: no external <script src> / <link rel=stylesheet>
    assert "<script src=" not in html
    assert 'rel="stylesheet"' not in html
    # core feature surfaces are present
    for token in ('id="mode-seg"', 'id="sheet-seg"', 'id="ltree"',
                  'id="meta"', 'exportTriage', 'exportLayer', 'highlightTag'):
        assert token in html, f"missing viewer feature token: {token}"
    # row counts match the data model
    assert stats["design_rows"] == 97
    assert stats["mapped"] == 43
    assert stats["layers"] == 21


@needs_data
def test_one_row_per_crossmap_entry_and_unmapped():
    from abacus_svg_pid.build_viewer import build_html
    _, stats = build_html()
    crossmap = json.load(open(CROSSMAP))
    # every mapped pair + every unmapped design tag is represented
    assert stats["medium"] + stats["low"] + stats["high"] == len(crossmap["mappings"])
    assert stats["mapped"] + stats["unmapped"] == stats["design_rows"]


@needs_data
def test_every_marker_data_tag_resolves_to_catalog_instance():
    import re
    from abacus_svg_pid.build_viewer import build_html
    out, _ = build_html()
    html = open(out).read()
    catalog = json.load(open(CATALOG))
    real_tags = {i.get("tag") or i.get("norm")
                 for i in catalog["instruments"] if not i.get("template")}
    data_tags = set(re.findall(r'class="tag-mk" data-tag="([^"]+)"', html))
    assert data_tags, "no SVG markers were injected"
    orphans = data_tags - real_tags
    assert not orphans, f"marker tags with no catalog instance: {sorted(orphans)[:5]}"
