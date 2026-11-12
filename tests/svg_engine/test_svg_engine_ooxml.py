"""SVG-ENGINE OOXML adapter: PowerPoint frame model, font chain and W1 inventory.

``data/powerpoint_com_oracle_fixture.json`` is PowerPoint 16.0's own answer (through COM) for the synthetic
fixture built by ``svg_engine.fixtures.make_group_font_fixture``. CI has no PowerPoint, so this file is the
oracle; regenerate it on Windows with ``svg_engine/oracles/ppt_com_oracle.ps1`` if the fixture changes.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from tests.svg_engine.conftest import require

require("lxml", "pptx")

from svg_engine.fixtures import make_group_font_fixture  # noqa: E402
from svg_engine.ooxml_geometry import analyse, map_into_frame  # noqa: E402
from svg_engine.ooxml_inventory import (  # noqa: E402
    enhanced_pptx,
    review_bridge,
    slide_size_emu,
)
from svg_engine.ooxml_qa import compare_w1_w2, compare_with_oracle  # noqa: E402

ORACLE = Path(__file__).parent / "data" / "powerpoint_com_oracle_fixture.json"


@pytest.fixture(scope="module")
def fixture_deck(tmp_path_factory):
    return make_group_font_fixture(tmp_path_factory.mktemp("ooxml") / "group_font_fixture.pptx")


def _frame(cx, cy, w, h, rot=0.0, fh=False, fv=False):
    return {"cx": cx, "cy": cy, "w": w, "h": h, "rot": rot, "fh": fh, "fv": fv}


def _grp(x, y, cx, cy):
    return {"x": x, "y": y, "cx": cx, "cy": cy, "chx": x, "chy": y, "chcx": cx, "chcy": cy}


def test_frame_model_identity_group_leaves_child_unchanged():
    child = _frame(30, 20, 10, 4, rot=15)
    out = map_into_frame(child, _grp(0, 0, 100, 50), _frame(50, 25, 100, 50))
    assert out == pytest.approx({**child}, abs=1e-9)


def test_frame_model_flip_mirrors_about_frame_centre_and_negates_rotation():
    out = map_into_frame(_frame(30, 20, 10, 4, rot=15), _grp(0, 0, 100, 50), _frame(50, 25, 100, 50, fh=True))
    assert (out["cx"], out["cy"]) == pytest.approx((70, 20))
    assert out["rot"] == pytest.approx(345) and out["fh"] is True


def test_frame_model_non_uniform_scale_never_shears_a_rotated_child():
    # Group scaled 2x horizontally, 1x vertically; child rotated 30 deg keeps its rotation, sizes scale axis-wise.
    out = map_into_frame(_frame(10, 10, 4, 2, rot=30), _grp(0, 0, 20, 20), _frame(20, 10, 40, 20))
    assert out["rot"] == pytest.approx(30)
    assert (out["w"], out["h"]) == pytest.approx((8, 2))
    assert (out["cx"], out["cy"]) == pytest.approx((20, 10))


def test_frame_model_rotates_child_about_frame_centre():
    out = map_into_frame(_frame(15, 5, 2, 2), _grp(0, 0, 20, 10), _frame(10, 5, 20, 10, rot=90))
    assert (out["cx"], out["cy"]) == pytest.approx((10, 10))
    assert out["rot"] == pytest.approx(90)
    assert math.isfinite(out["cx"])


def test_fixture_geometry_and_fonts_match_powerpoint(fixture_deck):
    adapter = analyse(fixture_deck)
    oracle = json.loads(ORACLE.read_text(encoding="utf-8-sig"))
    res = compare_with_oracle(adapter, oracle, tol_mm=0.05)
    assert res["result"] == "PASS", res["failures"]
    assert res["compared"] == 11
    assert res["max_d_centre_mm"] <= 0.001
    assert sum("font_oracle" in r for r in res["rows"]) == 11
    assert adapter["max_group_depth"] == 3
    assert {o["name"] for o in adapter["out_of_slide"]} == {"R_overflow"}
    assert {"run.rPr", "shape.style.fontRef", "master.txStyles.titleStyle"} <= set(adapter["font_resolution_sources"])


def test_oracle_mismatch_is_reported(fixture_deck):
    adapter = analyse(fixture_deck)
    oracle = json.loads(ORACLE.read_text(encoding="utf-8-sig"))
    oracle["shapes"] = [dict(s) for s in oracle["shapes"]]
    moved = next(s for s in oracle["shapes"] if s["name"] == "R_in_b")
    moved["left_mm"] += 1.0
    res = compare_with_oracle(adapter, oracle)
    assert res["result"] == "FAIL" and [f["name"] for f in res["failures"]] == ["R_in_b"]


def test_w1_inventory_regression_against_w2_adapter(fixture_deck):
    w1 = enhanced_pptx(fixture_deck)
    assert w1["slide_count"] == 2 and w1["native_group_count"] == 3
    reg = compare_w1_w2(w1, analyse(fixture_deck))
    # Top-level, unrotated objects must agree; grouped children carry child-space offsets in W1.
    assert reg["compared"] > 0 and not reg["missing_in_w2"]
    bridge = review_bridge(w1, slide_size_emu(fixture_deck), anchor_patterns={"title": r"Title inherits"})
    assert [c["native_id"] for c in bridge["position_out_of_bounds_candidates"]] == ["9"]
    assert bridge["anchors"][0]["native_annotation_slides"] == [2]
