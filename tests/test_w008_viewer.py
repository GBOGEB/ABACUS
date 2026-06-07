"""
================================================================================
 Module : tests/test_w008_viewer.py
 Purpose: Assertions over the W008 full interactive viewer build. Verifies the
          SVG tag-annotation injector (data-pidtag), the unified row builder,
          honest count reconciliation against the authoritative W006 statistics,
          and that the emitted single-file HTML is self-contained (no external
          CDN/script/style refs), embeds the atlas, exposes tag->element links,
          and contains the triage/export/keyboard machinery.
 Current Wave : W008
 Status : ACTIVE
 Inputs  : data/crossmap/*.json + reports/W006_crossmap_statistics.json
           + output_v6/QCELL/*_13layers.svg  (build first via ./make.sh —
            derived data/ and output_v6/ are git-ignored)
 Outputs : pass/fail to stdout (exit code 0 on success). NO pytest dependency.
================================================================================
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CROSSMAP_DIR = os.path.join(ROOT, "data", "crossmap")
REPORTS = os.path.join(ROOT, "reports")
PUBLISH = os.path.join(ROOT, "publish")
sys.path.insert(0, os.path.join(ROOT, "src"))


def _load(path):
    with open(path) as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# Pure-function tests (no built data required)
# --------------------------------------------------------------------------- #
def test_annotate_svg_exact_and_multi_token():
    from abacus_svg_pid.build_viewer import _annotate_svg
    svg = ('<svg><text><tspan>CV560</tspan></text>'
           '<text><tspan>TT535 TT536 TT546</tspan></text>'
           '<tspan>NOISE</tspan></svg>')
    out, found = _annotate_svg(svg, ["CV560", "TT535", "TT546", "ZZ999"])
    # exact single-token match annotated
    assert 'data-pidtag="CV560"' in out, "single-token tag not annotated"
    # multi-token tspan annotated only with the known tags it contains
    assert 'data-pidtag="TT535 TT546"' in out, "multi-token annotation wrong"
    # found set is exactly the tags present in the SVG (ZZ999 absent)
    assert found == {"CV560", "TT535", "TT546"}, f"unexpected found set: {found}"
    # unknown text left untouched
    assert "NOISE</tspan>" in out and out.count("data-pidtag") == 2


def test_annotate_svg_empty():
    from abacus_svg_pid.build_viewer import _annotate_svg
    out, found = _annotate_svg(None, ["CV560"])
    assert out is None and found == set()


def test_rows_builder_synthetic():
    from abacus_svg_pid import build_viewer
    cm = {
        "design_to_asdrawn": {"CV001": "CV560"},
        "mappings": [{
            "design_tag": "CV001", "asdrawn_tag": "CV560", "type": "CV",
            "confidence": 0.75, "tier": "MEDIUM",
            "reasons": ["TYPE_MATCH"], "asdrawn_sheet": "QCELL",
        }],
    }
    # monkeypatch the confidence loader to inject an unmapped design tag
    orig = build_viewer._load_json
    build_viewer._load_json = lambda p: (
        {"unmapped_design": [{"design_tag": "V001", "type": "V",
                              "band": "ROOM", "reason": "no as-drawn"}]}
        if p == build_viewer.CONFIDENCE else orig(p))
    try:
        rows = build_viewer._rows(cm)
    finally:
        build_viewer._load_json = orig
    designs = {r["design"] for r in rows}
    assert designs == {"CV001", "V001"}, f"rows mismatch: {designs}"
    mapped = [r for r in rows if r["asdrawn"]]
    unmapped = [r for r in rows if not r["asdrawn"]]
    assert len(mapped) == 1 and mapped[0]["asdrawn"] == "CV560"
    assert len(unmapped) == 1 and unmapped[0]["tier"] == "UNMAPPED"


# --------------------------------------------------------------------------- #
# Data-dependent tests (require built crossmap + atlas SVG)
# --------------------------------------------------------------------------- #
def test_build_emits_html():
    from abacus_svg_pid.build_viewer import build_html
    out, stats, derived = build_html()
    assert os.path.exists(out), "viewer HTML not written"
    assert os.path.getsize(out) > 100_000, "viewer HTML implausibly small"


def test_counts_match_authoritative_statistics():
    """Honesty gate: row-derived counts MUST equal the real W006 stats file."""
    from abacus_svg_pid.build_viewer import build_html
    _, stats, derived = build_html()
    auth = _load(os.path.join(REPORTS, "W006_crossmap_statistics.json"))
    assert stats["design_tags"] == auth["total_design_tags"]
    assert stats["mapped"] == auth["mapped"] == derived["mapped"]
    assert stats["high"] == auth["high_confidence"] == derived["high"]
    assert stats["medium"] == auth["medium_confidence"] == derived["medium"]
    assert stats["low"] == auth["low_confidence"] == derived["low"]
    assert stats["unmapped"] == auth["unmapped_design"] == derived["unmapped"]
    # mapped + unmapped must equal the design universe (no fabricated rows)
    assert derived["mapped"] + derived["unmapped"] == derived["total"]


def test_html_self_contained_and_featured():
    out = os.path.join(PUBLISH, "interactive_viewer.html")
    if not os.path.exists(out):
        from abacus_svg_pid.build_viewer import build_html
        build_html()
    html = open(out).read()
    # self-contained: no external resource loads (xmlns="http://www.w3.org" URIs
    # are XML namespaces, not network fetches, so they are explicitly allowed).
    assert "<script src=" not in html, "external <script src> not allowed"
    assert "<link" not in html, "external <link> stylesheet not allowed"
    assert 'src="http' not in html, "external src= resource not allowed"
    assert "@import" not in html, "@import of external CSS not allowed"
    assert "url(http" not in html, "external url() resource not allowed"
    # embeds the QCELL atlas and exposes tag->element links
    assert html.count("<svg ") >= 1, "atlas SVG not embedded"
    assert "data-pidtag=" in html, "no tag->SVG element annotations injected"
    # one table row per design tag
    n_rows = html.count('<tr class="row"')
    auth = _load(os.path.join(REPORTS, "W006_crossmap_statistics.json"))
    assert n_rows == auth["total_design_tags"], \
        f"expected {auth['total_design_tags']} rows, found {n_rows}"
    # feature machinery present (triage / export / highlight / shortcuts)
    for needle in ["highlightTag", "exportCSV", "exportJSON", "exportPNG",
                   "setVal", "PanZoom", "setView", "applyFilters",
                   "localStorage", "Ctrl+F"]:
        assert needle in html, f"missing viewer feature hook: {needle}"


def test_every_mapped_tag_locatable_or_accounted():
    """Each mapped as-drawn tag should resolve in the atlas (data-pidtag) — and
    the build's 'locatable' count must equal the number of mapped pairs whose
    as-drawn tag is actually annotated in the embedded SVG (no overcount)."""
    from abacus_svg_pid.build_viewer import (build_html, _read_svg, _rows,
                                             _annotate_svg, QCELL_DIR, CROSSMAP)
    _, stats, _ = build_html()
    cm = _load(CROSSMAP)
    rows = _rows(cm)
    asdrawn = [r["asdrawn"] for r in rows if r["asdrawn"]]
    svg, _vb = _read_svg(QCELL_DIR)
    _, found = _annotate_svg(svg, asdrawn)
    locatable = sum(1 for t in asdrawn if t in found)
    assert locatable == stats["locatable"], "locatable count mismatch"
    assert locatable <= stats["mapped"], "locatable cannot exceed mapped"


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #
def _data_available():
    return (os.path.exists(os.path.join(CROSSMAP_DIR, "design_to_asdrawn.json"))
            and os.path.exists(os.path.join(REPORTS, "W006_crossmap_statistics.json")))


PURE_TESTS = [
    "test_annotate_svg_exact_and_multi_token",
    "test_annotate_svg_empty",
    "test_rows_builder_synthetic",
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
        print("SKIP  W008 data-dependent assertions — data/crossmap/ or "
              "reports/W006_crossmap_statistics.json not built. Run ./make.sh "
              "first; derived outputs are git-ignored.")
        print(f"\n{passed}/{len(pure)} pure-function assertions passed "
              f"({len(data_fns)} data tests skipped).")
        return passed

    for fn in data_fns:
        fn()
        print(f"  PASS  {fn.__name__}")
        passed += 1
    total = len(pure) + len(data_fns)
    print(f"\n{passed}/{total} W008 assertions passed.")
    return passed


if __name__ == "__main__":
    _run_all()
