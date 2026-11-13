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
    """Regression: every object W1 (``enhanced_pptx``) positioned must sit where W2 (``analyse``) puts it."""
    m2 = {
        (o["slide"], o["native_id"]): o
        for s in w2_geometry["slides"]
        for o in s["objects"]
    }
    diffs, missing_geom, missing_w2 = [], 0, []
    for s in w1_deck["slides"]:
        for o in s["shapes"]:
            if "geometry_mm_off" not in o:
                missing_geom += 1
                continue
            b = m2.get((s["number"], o["native_id"]))
            if b is None or "abs_aabb_mm" not in b:
                missing_w2.append([s["number"], o["native_id"]])
                continue
            box = b["abs_aabb_mm"]
            diffs.append(
                max(
                    abs(o["geometry_mm_off"]["x"] - box["left"]),
                    abs(o["geometry_mm_off"]["y"] - box["top"]),
                    abs(o["geometry_mm_ext"]["cx"] - (box["right"] - box["left"])),
                )
            )
    worst = max(diffs, default=0.0)
    return {
        "w1_objects": sum(len(s["shapes"]) for s in w1_deck["slides"]),
        "w2_objects": w2_geometry["object_count"],
        "compared": len(diffs),
        "max_abs_diff_mm": round(worst, 4),
        "w1_objects_without_geometry": missing_geom,
        "missing_in_w2": missing_w2,
        "result": "PASS" if worst <= tol_mm and not missing_w2 else "FAIL",
    }
