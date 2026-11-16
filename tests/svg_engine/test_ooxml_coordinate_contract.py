"""Adversarial tests: local OOXML coordinates must not masquerade as resolved geometry.

Source-safe, synthetic only. Independent PowerPoint COM oracle stays a separate gate.
"""
import copy

import pytest

from DMAIC_V3.svg_engine.ooxml_qa import compare_w1_w2


def fixtures():
    w1 = {"slides": [{"number": 1, "shapes": [
        {"native_id": "1", "name": "rotation-90", "parent_group_ids": [],
         "geometry_mm_off": {"x": 10.0, "y": 20.0},
         "geometry_mm_ext": {"cx": 40.0, "cy": 10.0}},
        {"native_id": "2", "name": "group-child", "parent_group_ids": ["7"],
         "geometry_mm_off": {"x": 1.0, "y": 2.0},
         "geometry_mm_ext": {"cx": 5.0, "cy": 3.0}},
    ]}]}
    w2 = {"object_count": 2, "slides": [{"slide": 1, "objects": [
        {"native_id": "1", "abs_centre_mm": [30.0, 25.0],
         "abs_size_mm": [40.0, 10.0],
         "abs_aabb_mm": {"left": 25.0, "top": 5.0, "right": 35.0, "bottom": 45.0}},
        {"native_id": "2", "abs_centre_mm": [92.0, 84.0],
         "abs_size_mm": [5.0, 3.0],
         "abs_aabb_mm": {"left": 89.5, "top": 82.5, "right": 94.5, "bottom": 85.5}},
    ]}]}
    return w1, w2


def test_rotated_top_level_compares_centre_and_size_not_aabb():
    a, b = fixtures()
    result = compare_w1_w2(a, b)
    assert result["result"] == "PASS"
    assert result["compared"] == 1
    assert result["max_abs_diff_mm"] == 0.0
    assert result["comparison_basis"] == "TOP_LEVEL_CENTRE_UNROTATED_SIZE"
    assert result["grouped_local_space_excluded"] == [(1, "2")]
    assert result["full_deck_parity"] == "DEFER_COM_ORACLE_REQUIRED"


def test_real_drift_on_top_level_object_fails_closed():
    a, b = fixtures()
    b["slides"][0]["objects"][0]["abs_centre_mm"][0] += 1.0
    result = compare_w1_w2(a, b)
    assert result["result"] == "FAIL"
    assert result["max_abs_diff_mm"] == 1.0


def test_missing_resolved_identity_fails_closed():
    a, b = fixtures()
    b["slides"][0]["objects"].pop()
    assert compare_w1_w2(a, b)["result"] == "FAIL"


def test_duplicate_native_ids_fail_closed():
    a, b = fixtures()
    a["slides"][0]["shapes"].append(copy.deepcopy(a["slides"][0]["shapes"][0]))
    result = compare_w1_w2(a, b)
    assert result["result"] == "FAIL"
    assert result["duplicate_w1_keys"]


def test_no_comparable_objects_defers_not_passes():
    a, b = fixtures()
    a["slides"][0]["shapes"].pop(0)
    result = compare_w1_w2(a, b)
    assert result["result"] == "DEFER"
    assert result["compared"] == 0


@pytest.mark.parametrize("tol", [-0.01, float("nan"), float("inf")])
def test_invalid_tolerances_refused(tol):
    a, b = fixtures()
    with pytest.raises(ValueError, match="K2501"):
        compare_w1_w2(a, b, tol_mm=tol)
