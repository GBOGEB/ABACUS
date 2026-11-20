"""OOXML geometry QA against PowerPoint's own object model, and W1-vs-W2 adapter regression.

The oracle JSON comes from ``oracles/ppt_com_oracle.ps1`` (PowerPoint through COM, read-only, Windows only).
CI has no PowerPoint, so CI compares against a committed oracle JSON for the synthetic fixture.
"""

from __future__ import annotations


def compare_with_oracle(adapter, oracle, tol_mm=0.05, tol_deg=0.01):
    """Match on (slide, native cNvPr id): COM display names can be localised ("Freeform 5" vs "Freeform: Shape 5").

    PowerPoint reports a rotated shape's unrotated box centred on its visual centre, so the compared quantities
    are centre (mm), size (mm), net rotation (deg mod 360) and the effective font of run 1.
    PowerPoint flattens groups (type 6), so group frames are compared through their leaves.
    """
    mine = {
        (o["slide"], str(o["native_id"])): o
        for s in adapter["slides"]
        for o in s["objects"]
    }
    rows, fails = [], []
    for r in oracle["shapes"]:
        if r["type"] == 6:
            continue
        m = mine.get((r["slide"], str(r["id"])))
        if m is None:
            fails.append(
                {
                    "slide": r["slide"],
                    "name": r["name"],
                    "id": r["id"],
                    "why": "missing in adapter",
                }
            )
            continue
        rec = {
            "slide": r["slide"],
            "name": m["name"],
            "id": r["id"],
            "group_depth": len(m["parent_group_ids"]),
            "geometry_from": m.get("geometry_inherited_from", "own xfrm"),
        }
        if "abs_centre_mm" not in m:
            rec.update({"ok": False, "why": "oracle has geometry, adapter has none"})
            rows.append(rec)
            fails.append(rec)
            continue
        oc = (r["left_mm"] + r["width_mm"] / 2, r["top_mm"] + r["height_mm"] / 2)
        rec["d_centre_mm"] = round(
            max(abs(oc[0] - m["abs_centre_mm"][0]), abs(oc[1] - m["abs_centre_mm"][1])),
            4,
        )
        rec["d_size_mm"] = round(
            max(
                abs(r["width_mm"] - m["abs_size_mm"][0]),
                abs(r["height_mm"] - m["abs_size_mm"][1]),
            ),
            4,
        )
        d = abs((r["rotation"] - m["net_rotation_deg"]) % 360)
        rec["d_rot_deg"] = round(min(d, 360 - d), 3)
        if r.get("font") and m.get("text_runs"):
            rec["font_oracle"] = r["font"]
            rec["font_adapter"] = m["text_runs"][0]["effective"]
            rec["font_by"] = m["text_runs"][0]["resolved_by"]
        bad = (
            rec["d_centre_mm"] > tol_mm
            or rec["d_size_mm"] > tol_mm
            or rec["d_rot_deg"] > tol_deg
            or rec.get("font_oracle", 1) != rec.get("font_adapter", 1)
        )
        rec["ok"] = not bad
        rows.append(rec)
        if bad:
            fails.append(rec)
    return {
        "oracle": oracle.get("oracle"),
        "adapter_file": adapter.get("file"),
        "adapter_sha256": adapter.get("sha256"),
        "tolerance_mm": tol_mm,
        "compared": len(rows),
        "failures": fails,
        "rows": rows,
        "max_d_centre_mm": max((r.get("d_centre_mm", 0) for r in rows), default=None),
        "result": "PASS" if not fails and rows else "FAIL",
    }


def compare_w1_w2(w1_deck, w2_geometry, tol_mm=0.01):
    """W1 local-geometry versus W2 resolved-geometry regression (NOT a COM oracle).

    W1 child offsets are in their parent-group coordinate systems. W2 child
    coordinates are slide-absolute, so raw comparison is invalid. For top-level
    objects, compare the unrotated centre and size; the rotated AABB is not the
    source geometry. Excluded child records remain explicit, not false PASS.
    """
    if not 0 <= tol_mm < float("inf"):
        raise ValueError("K2501_INVALID_GEOMETRY_TOLERANCE")
    indexed = {}
    duplicate_w2 = []
    for slide in w2_geometry["slides"]:
        for obj in slide["objects"]:
            key = (slide["slide"], str(obj.get("native_id")))
            if key in indexed:
                duplicate_w2.append(key)
            indexed[key] = obj

    compared = []
    missing_w2 = []
    grouped = []
    missing_geometry = []
    missing_id = []
    duplicate_w1 = []
    seen = set()
    for slide in w1_deck["slides"]:
        for obj in slide["shapes"]:
            native_id = obj.get("native_id")
            if native_id is None:
                missing_id.append([slide["number"], obj.get("name")])
                continue
            key = (slide["number"], str(native_id))
            if key in seen:
                duplicate_w1.append(key)
            seen.add(key)
            resolved = indexed.get(key)
            if resolved is None:
                missing_w2.append(key)
                continue
            if obj.get("parent_group_ids"):
                grouped.append(key)
                continue
            xy = obj.get("geometry_mm_off") or {}
            wh = obj.get("geometry_mm_ext") or {}
            centre = resolved.get("abs_centre_mm")
            size = resolved.get("abs_size_mm")
            if not all(k in xy for k in ("x", "y")) or not all(k in wh for k in ("cx", "cy")) or centre is None or size is None:
                missing_geometry.append(key)
                continue
            xcentre, ycentre = xy["x"] + wh["cx"] / 2, xy["y"] + wh["cy"] / 2
            delta = max(
                abs(xcentre - centre[0]), abs(ycentre - centre[1]),
                abs(wh["cx"] - size[0]), abs(wh["cy"] - size[1]),
            )
            compared.append({"slide": key[0], "native_id": key[1], "delta_mm": round(delta, 4)})

    worst = max((r["delta_mm"] for r in compared), default=0.0)
    failed = bool(missing_w2 or missing_id or duplicate_w1 or duplicate_w2 or worst > tol_mm)
    return {
        "w1_objects": sum(len(s["shapes"]) for s in w1_deck["slides"]),
        "w2_objects": w2_geometry["object_count"],
        "compared": len(compared),
        "max_abs_diff_mm": round(worst, 4),
        "compared_objects": compared,
        "w1_objects_without_geometry": len(missing_geometry),
        "without_geometry_keys": missing_geometry,
        "grouped_local_space_excluded": grouped,
        "missing_in_w2": missing_w2,
        "missing_native_ids": missing_id,
        "duplicate_w1_keys": duplicate_w1,
        "duplicate_w2_keys": duplicate_w2,
        "comparison_basis": "TOP_LEVEL_CENTRE_UNROTATED_SIZE",
        "full_deck_parity": "DEFER_COM_ORACLE_REQUIRED" if grouped or missing_geometry else "TOP_LEVEL_ONLY",
        "result": "FAIL" if failed else ("DEFER" if not compared else "PASS"),
    }
