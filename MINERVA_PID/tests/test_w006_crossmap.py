"""
================================================================================
 Module : tests/test_w006_crossmap.py
 Purpose: Assertions over the W006 design<->as-drawn cross-map. Verifies
          feature extraction (circuit-band derivation), confidence-score bounds
          and tiering, type-gating (never cross instrument TYPEs), one-to-one
          assignment (no double-claim), bidirectional-index consistency, and
          golden seeds on the produced mapping.
 Current Wave : W006
 Status : ACTIVE
 Inputs  : data/crossmap/*.json + reports/W006_crossmap_statistics.json
           (build first via:  PYTHONPATH=src python3 -m abacus_svg_pid.build_w006_crossmap
            or ./make.sh — derived data/crossmap/ is git-ignored)
 Outputs : pass/fail to stdout (exit code 0 on success)
================================================================================
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CROSSMAP_DIR = os.path.join(ROOT, "data", "crossmap")
REPORTS = os.path.join(ROOT, "reports")
sys.path.insert(0, os.path.join(ROOT, "src"))


def _load(path):
    with open(path) as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# Pure-function tests (no built data required)
# --------------------------------------------------------------------------- #
def test_tag_number():
    from abacus_svg_pid.build_w006_crossmap import _tag_number
    assert _tag_number("CV001") == 1
    assert _tag_number("TT514") == 514
    assert _tag_number("PZ") is None


def test_design_band_from_location_and_number():
    from abacus_svg_pid.build_w006_crossmap import design_band, BAND_40K, BAND_45K, BAND_2K, BAND_WATER
    # location keywords take priority
    assert design_band({"tag": "CV100", "location": "40K circuit inlet"}) == BAND_40K
    assert design_band({"tag": "CV200", "location": "4.5K circuit outlet"}) == BAND_45K
    assert design_band({"tag": "CV003", "location": "cavity cooling water outlet"}) == BAND_WATER
    # fall back to the hundreds-digit convention when location is silent
    assert design_band({"tag": "XX300", "location": ""}) == BAND_2K
    assert design_band({"tag": "XX100", "location": ""}) == BAND_40K


def test_asdrawn_band_from_line():
    from abacus_svg_pid.build_w006_crossmap import asdrawn_band, BAND_45K, BAND_2K, BAND_40K, BAND_WATER
    assert asdrawn_band({"line": "A"}) == BAND_45K
    assert asdrawn_band({"line": "B"}) == BAND_2K
    assert asdrawn_band({"line": "D"}) == BAND_40K
    assert asdrawn_band({"line": "W"}) == BAND_WATER


def test_confidence_bounds_and_tiers():
    from abacus_svg_pid.build_w006_crossmap import score_pair, _tier, TIER_HIGH, TIER_MEDIUM
    d = {"band": "40K", "signal": "analog"}
    a = {"band": "40K", "signal": "analog"}
    # multi-member buckets: circuit + order + signal -> HIGH, bounded <= 1.0
    sc, reasons = score_pair(d, a, 0, 0, 3, 3)
    assert 0.0 <= sc <= 1.0
    assert sc >= TIER_HIGH and _tier(sc) == "HIGH"
    assert "CIRCUIT_MATCH(40K)" in reasons
    # singleton bucket: order is non-discriminating -> circuit-only -> LOW
    sc2, reasons2 = score_pair({"band": "2K", "signal": "unknown"},
                               {"band": "2K", "signal": "unknown"}, 0, 0, 1, 1)
    assert sc2 < TIER_MEDIUM
    assert _tier(sc2) == "LOW"
    assert "ORDER_TRIVIAL(bucket<=1)" in reasons2


def test_tier_thresholds():
    from abacus_svg_pid.build_w006_crossmap import _tier
    assert _tier(0.80) == "HIGH"
    assert _tier(0.79) == "MEDIUM"
    assert _tier(0.50) == "MEDIUM"
    assert _tier(0.49) == "LOW"


# --------------------------------------------------------------------------- #
# Data-dependent tests (require ./make.sh / build_w006_crossmap first)
# --------------------------------------------------------------------------- #
def test_mapping_file_shape():
    m = _load(os.path.join(CROSSMAP_DIR, "design_to_asdrawn.json"))
    for key in ("design_to_asdrawn", "asdrawn_to_design", "mappings"):
        assert key in m, f"missing key: {key}"
    assert isinstance(m["mappings"], list) and len(m["mappings"]) > 0


def test_bidirectional_consistency():
    """Forward and reverse indexes must agree for every mapped pair."""
    m = _load(os.path.join(CROSSMAP_DIR, "design_to_asdrawn.json"))
    fwd, rev = m["design_to_asdrawn"], m["asdrawn_to_design"]
    for d_tag, a_tag in fwd.items():
        assert rev.get(a_tag) == d_tag, f"reverse mismatch for {d_tag}->{a_tag}"
    assert len(fwd) == len(rev), "forward/reverse index size mismatch"


def test_type_gating_never_crosses_types():
    """A design tag may only map to an as-drawn tag of the SAME ISA prefix."""
    m = _load(os.path.join(CROSSMAP_DIR, "design_to_asdrawn.json"))
    import re
    def prefix(t):
        return re.match(r"[A-Za-z]+", t).group(0)
    for pair in m["mappings"]:
        assert prefix(pair["design_tag"]) == prefix(pair["asdrawn_tag"]), \
            f"TYPE crossed: {pair['design_tag']} -> {pair['asdrawn_tag']}"


def test_one_to_one_no_double_claim():
    """No as-drawn instance is claimed by more than one design tag, and vice versa."""
    m = _load(os.path.join(CROSSMAP_DIR, "design_to_asdrawn.json"))
    d_tags = [p["design_tag"] for p in m["mappings"]]
    a_tags = [p["asdrawn_tag"] for p in m["mappings"]]
    assert len(d_tags) == len(set(d_tags)), "a design tag mapped twice"
    assert len(a_tags) == len(set(a_tags)), "an as-drawn tag claimed twice"


def test_confidence_values_in_range():
    c = _load(os.path.join(CROSSMAP_DIR, "crossmap_confidence.json"))
    for pair in c["pairs"]:
        assert 0.0 <= pair["confidence"] <= 1.0
        assert pair["tier"] in ("HIGH", "MEDIUM", "LOW")
        # tier must be consistent with the score
        if pair["confidence"] >= 0.80:
            assert pair["tier"] == "HIGH"
        elif pair["confidence"] >= 0.50:
            assert pair["tier"] == "MEDIUM"
        else:
            assert pair["tier"] == "LOW"


def test_statistics_arithmetic():
    s = _load(os.path.join(REPORTS, "W006_crossmap_statistics.json"))
    assert s["mapped"] == s["high_confidence"] + s["medium_confidence"] + s["low_confidence"]
    assert s["mapped"] + s["unmapped_design"] == s["total_design_tags"]
    assert 0 <= s["mapped"] <= s["total_design_tags"]
    assert s["asdrawn_unclaimed"] == s["total_asdrawn_real_tags"] - s["mapped"]


def test_golden_circuit_band_pairing():
    """Golden check: every mapped pair with a CIRCUIT_MATCH reason has equal bands."""
    m = _load(os.path.join(CROSSMAP_DIR, "design_to_asdrawn.json"))
    checked = 0
    for pair in m["mappings"]:
        if any(r.startswith("CIRCUIT_MATCH") for r in pair["reasons"]):
            assert pair["design_band"] == pair["asdrawn_band"], \
                f"band mismatch on {pair['design_tag']}->{pair['asdrawn_tag']}"
            checked += 1
    assert checked > 0, "expected at least one circuit-matched pair"


def test_no_fabricated_high_without_corroboration():
    """Honesty invariant: a HIGH pair must cite a SEED or a SIGNAL corroborator,
    never circuit+order alone (which is an unconfirmed structural inference)."""
    c = _load(os.path.join(CROSSMAP_DIR, "crossmap_confidence.json"))
    for pair in c["pairs"]:
        if pair["tier"] == "HIGH":
            assert any(r.startswith("SIGNAL_MATCH") or r == "KNOWN_SEED"
                       for r in pair["reasons"]), \
                f"HIGH pair {pair['design_tag']} lacks an independent corroborator"


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #
def _data_available():
    return os.path.exists(os.path.join(CROSSMAP_DIR, "design_to_asdrawn.json"))


PURE_TESTS = [
    "test_tag_number",
    "test_design_band_from_location_and_number",
    "test_asdrawn_band_from_line",
    "test_confidence_bounds_and_tiers",
    "test_tier_thresholds",
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
        print("SKIP  W006 data-dependent assertions — data/crossmap/ not built. "
              "Run ./make.sh (or build_w006_crossmap) first; derived outputs are git-ignored.")
        print(f"\n{passed}/{len(pure)} pure-function assertions passed "
              f"({len(data_fns)} data tests skipped).")
        return passed

    for fn in data_fns:
        fn()
        print(f"  PASS  {fn.__name__}")
        passed += 1
    total = len(pure) + len(data_fns)
    print(f"\n{passed}/{total} W006 assertions passed.")
    return passed


if __name__ == "__main__":
    _run_all()
