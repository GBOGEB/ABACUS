"""Adversarial contracts for W1 local vs W2 absolute OOXML geometry.

Source-safe synthetic dicts. COM/visual oracle remains an independent gate.
These tests must not interpret review-bridge collisions as engineering defects.
"""

from __future__ import annotations

import copy

import pytest

from DMAIC_V3.svg_engine.ooxml_qa import compare_w1_w2


def _case(*, rotate=False, grouped=False):
    w1_obj = {
        "native_id": "7",
        "name": "Synthetic connector",
        "parent_group_ids": ["3"] if grouped else [],
        "geometry_mm_off": {"x": 20.0, "y": 15.0},
        "geometry_mm_ext": {"cx": 10.0, "cy": 6.0},
    }
    w2_obj = {
        "native_id": "7",
        "parent_group_ids": ["3"] if grouped else [],
        "abs_centre_mm": [25.0 if not grouped else 88.0, 18.0 if not grouped else 43.0],
        "abs_size_mm": [10.0, 6.0],
        "abs_aabb_mm": (
            {"left": 22.0, "top": 13.0, "right": 28.0, "bottom": 23.0}
            if rotate else {"left": 20.0, "top": 15.0, "right": 30.0, "bottom": 21.0}
        ),
        "net_rotation_deg": 90.0 if rotate else 0.0,
    }
    return (
        {"slides": [{"number": 1, "shapes": [w1_obj]}]},
        {"slides": [{"slide": 1, "objects": [w2_obj]}], "object_count": 1},
    )


def test_top_level_unrotated_object_matches():
    w1, w2 = _case()
    got = compare_w1_w2(w1, w2)
    assert got["result"] == "PASS"
    assert got["compared"] == 1
    assert got["max_abs_diff_mm"] == 0.0


def test_rotated_object_does_not_compare_local_box_against_expanded_aabb():
    w1, w2 = _case(rotate=True)
    got = compare_w1_w2(w1, w2)
    assert got["result"] == "PASS"
    assert got["compared"] == 1
    assert got["comparison_basis"] == "TOP_LEVEL_CENTRE_UNROTATED_SIZE"


def test_group_child_is_excluded_not_called_global_geometry_mismatch():
    w1, w2 = _case(grouped=True)
    got = compare_w1_w2(w1, w2)
    assert got["result"] == "DEFER"
    assert got["compared"] == 0
    assert got["grouped_local_space_excluded"] == [(1, "7")]
    assert got["full_deck_parity"] == "DEFER_COM_ORACLE_REQUIRED"


def test_true_top_level_source_drift_is_red():
    w1, w2 = _case()
    w2["slides"][0]["objects"][0]["abs_centre_mm"][0] += 1.0
    got = compare_w1_w2(w1, w2)
    assert got["result"] == "FAIL"
    assert got["max_abs_diff_mm"] == 1.0


def test_dangling_native_shape_id_is_red():
    w1, w2 = _case()
    w2["slides"][0]["objects"][0]["native_id"] = "999"
    got = compare_w1_w2(w1, w2)
    assert got["result"] == "FAIL"
    assert got["missing_in_w2"] == [(1, "7")]


def test_duplicate_native_id_in_both_adapters_is_red():
    w1, w2 = _case()
    w1["slides"][0]["shapes"].append(copy.deepcopy(w1["slides"][0]["shapes"][0]))
    w2["slides"][0]["objects"].append(copy.deepcopy(w2["slides"][0]["objects"][0]))
    w2["object_count"] = 2
    got = compare_w1_w2(w1, w2)
    assert got["result"] == "FAIL"
    assert got["duplicate_w1_keys"] and got["duplicate_w2_keys"]


def test_missing_geometry_is_visible_not_falsely_compared():
    w1, w2 = _case()
    del w2["slides"][0]["objects"][0]["abs_centre_mm"]
    got = compare_w1_w2(w1, w2)
    assert got["result"] == "DEFER"
    assert got["compared"] == 0
    assert got["w1_objects_without_geometry"] == 1
    assert got["full_deck_parity"] == "DEFER_COM_ORACLE_REQUIRED"


@pytest.mark.parametrize("bad_tolerance", [-0.01, float("inf"), float("nan")])
def test_invalid_tolerance_fails_closed(bad_tolerance):
    w1, w2 = _case()
    with pytest.raises(ValueError, match="K2501_INVALID_GEOMETRY_TOLERANCE"):
        compare_w1_w2(w1, w2, tol_mm=bad_tolerance)
