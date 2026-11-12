"""OOXML adapter (SVG-ENGINE W2): recursive group geometry and effective Latin font resolution. Read-only.

Geometry: DrawingML groups (ECMA-376 20.1.7.5/20.1.7.6) evaluated with PowerPoint's *frame* model, verified
against PowerPoint COM: each group is first mapped to an absolute frame (centre, size, net rotation, net flips);
children are placed in the frame's unrotated rectangle by axis-wise scaling chExt -> frame size, then mirrored
and rotated about the frame centre. Non-uniform group scale therefore never shears a rotated child (a pure
affine composition does, and disagrees with PowerPoint by several mm). Output: absolute centre/size/rotation,
corners, axis-aligned bounding box (AABB) and out-of-slide overhang.

Fonts: run rPr/latin -> paragraph-level lstStyle in the shape -> (placeholder) layout ph lstStyle -> master ph
lstStyle -> master txStyles (title/body) | (non-placeholder) shape p:style fontRef -> presentation
defaultTextStyle -> theme minor. '+mj-lt'/'+mn-lt' resolve to the master theme's major/minor Latin face.
Every resolved value records which level supplied it.

Verified oracle: PowerPoint's own object model via ``oracles/ppt_com_oracle.ps1`` (Windows only).
CLI: ``python -m svg_engine ooxml-geometry <deck.pptx> <out.json>``
"""
from __future__ import annotations

import hashlib
import math
import posixpath
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
EMU_MM = 36000.0
ln = lambda e: etree.QName(e).localname


def xfrm_of(el):
    x = el.find("./p:spPr/a:xfrm", NS)
    if x is None: x = el.find("./p:grpSpPr/a:xfrm", NS)
    if x is None: x = el.find("./p:xfrm", NS)
    if x is None: return None
    g = lambda tag, a: int(x.find(f"a:{tag}", NS).get(a)) if x.find(f"a:{tag}", NS) is not None else None
    return {"x": g("off", "x"), "y": g("off", "y"), "cx": g("ext", "cx"), "cy": g("ext", "cy"),
            "chx": g("chOff", "x"), "chy": g("chOff", "y"), "chcx": g("chExt", "cx"), "chcy": g("chExt", "cy"),
            "rot": int(x.get("rot", "0")) / 60000.0, "flipH": x.get("flipH") in ("1", "true"), "flipV": x.get("flipV") in ("1", "true")}


class Deck:
    def __init__(self, path):
        self.path = Path(path)
        self.z = ZipFile(path)
        self.names = set(self.z.namelist())
        self.pres = self.xml("ppt/presentation.xml")
        sz = self.pres.find("p:sldSz", NS)
        self.size = (int(sz.get("cx")), int(sz.get("cy")))

    def xml(self, part): return etree.fromstring(self.z.read(part))

    def rels(self, part):
        rp = posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")
        if rp not in self.names: return {}
        out = {}
        for r in self.xml(rp):
            t = r.get("Target")
            out[r.get("Id")] = (r.get("Type").rsplit("/", 1)[-1], t if r.get("TargetMode") == "External" else posixpath.normpath(posixpath.join(posixpath.dirname(part), t)))
        return out

    def rel_of_type(self, part, typ):
        return next((t for k, (ty, t) in self.rels(part).items() if ty == typ), None)


def theme_fonts(deck, master_part):
    th = deck.rel_of_type(master_part, "theme")
    x = deck.xml(th)
    maj = x.find(".//a:fontScheme/a:majorFont/a:latin", NS).get("typeface")
    mnr = x.find(".//a:fontScheme/a:minorFont/a:latin", NS).get("typeface")
    return {"+mj-lt": maj, "+mn-lt": mnr, "theme_part": th}


def lvl_latin(container, lvl):
    """latin typeface from a lstStyle/txStyle-like container at paragraph level lvl (1-based)."""
    if container is None: return None
    for tag in (f"a:lvl{lvl}pPr", "a:defPPr"):
        e = container.find(f"{tag}/a:defRPr/a:latin", NS)
        if e is not None: return e.get("typeface")
    return None


def ph_key(sp):
    ph = sp.find("./p:nvSpPr/p:nvPr/p:ph", NS)
    if ph is None: return None
    return {"type": ph.get("type", "body"), "idx": ph.get("idx")}


def find_ph(tree, key):
    best = None
    for sp in tree.iter(f"{{{NS['p']}}}sp"):
        k = ph_key(sp)
        if not k: continue
        if key["idx"] is not None and k["idx"] == key["idx"]: return sp
        if k["type"] == key["type"] or (key["type"] in ("ctrTitle",) and k["type"] == "title") or (key["type"] in ("subTitle", "obj") and k["type"] == "body"):
            best = best or sp
    return best


def resolve_font(deck, sp, run, plvl, slide_ctx):
    chain = []
    rp = run.find("a:rPr/a:latin", NS)
    if rp is not None: chain.append(("run.rPr", rp.get("typeface")))
    chain.append(("shape.lstStyle", lvl_latin(sp.find("./p:txBody/a:lstStyle", NS), plvl)))
    key = ph_key(sp)
    if key:
        lph = find_ph(slide_ctx["layout"], key)
        chain.append(("layout.placeholder.lstStyle", lvl_latin(lph.find("./p:txBody/a:lstStyle", NS), plvl) if lph is not None else None))
        mph = find_ph(slide_ctx["master"], key)
        chain.append(("master.placeholder.lstStyle", lvl_latin(mph.find("./p:txBody/a:lstStyle", NS), plvl) if mph is not None else None))
        style = "a:titleStyle" if key["type"] in ("title", "ctrTitle") else "a:bodyStyle"
        chain.append((f"master.txStyles.{style[2:]}", lvl_latin(slide_ctx["master"].find(f"./p:txStyles/{style.replace('a:', 'p:')}", NS), plvl)))
    else:
        fr = sp.find("./p:style/a:fontRef", NS)
        if fr is not None: chain.append(("shape.style.fontRef", "+mj-lt" if fr.get("idx") == "major" else "+mn-lt"))
        chain.append(("presentation.defaultTextStyle", lvl_latin(deck.pres.find("p:defaultTextStyle", NS), plvl)))
    chain.append(("theme.minor (fallback)", "+mn-lt"))
    src, face = next((s, f) for s, f in chain if f)
    eff = slide_ctx["theme"].get(face, face)
    return {"declared": face, "effective": eff, "resolved_by": src}


def local_box(x):
    return {"cx": x["x"] + x["cx"] / 2, "cy": x["y"] + x["cy"] / 2, "w": x["cx"], "h": x["cy"], "rot": x["rot"], "fh": x["flipH"], "fv": x["flipV"]}


def map_into_frame(b, g, frame):
    """PowerPoint frame model. `g` is the parent group's xfrm (gives chOff/chExt), `frame` its already-mapped
    absolute box. The child's unrotated box is placed in the frame's unrotated rectangle by axis-wise scaling
    chExt -> frame size, then mirrored by the frame's net flips and rotated by its net rotation, about the frame centre."""
    sx = frame["w"] / (g["chcx"] or g["cx"] or 1)
    sy = frame["h"] / (g["chcy"] or g["cy"] or 1)
    ux = frame["cx"] - frame["w"] / 2 + (b["cx"] - (g["chx"] if g["chx"] is not None else g["x"])) * sx
    uy = frame["cy"] - frame["h"] / 2 + (b["cy"] - (g["chy"] if g["chy"] is not None else g["y"])) * sy
    w, h, rot, fh, fv = b["w"] * sx, b["h"] * sy, b["rot"], b["fh"], b["fv"]
    if frame["fh"]: ux, rot, fh = 2 * frame["cx"] - ux, -rot, not fh
    if frame["fv"]: uy, rot, fv = 2 * frame["cy"] - uy, -rot, not fv
    t = math.radians(frame["rot"]); dx, dy = ux - frame["cx"], uy - frame["cy"]
    cx, cy = frame["cx"] + dx * math.cos(t) - dy * math.sin(t), frame["cy"] + dx * math.sin(t) + dy * math.cos(t)
    return {"cx": cx, "cy": cy, "w": w, "h": h, "rot": (rot + frame["rot"]) % 360, "fh": fh, "fv": fv}


def walk(deck, el, parent, parents, slide_no, slide_ctx, out):
    """parent: None at slide level, else (group xfrm, group's absolute frame)."""
    for ch in el:
        tag = ln(ch)
        if tag not in ("sp", "pic", "cxnSp", "grpSp", "graphicFrame"): continue
        nv = ch.find("./*/p:cNvPr", NS)
        sid, name = (nv.get("id"), nv.get("name")) if nv is not None else (None, None)
        x = xfrm_of(ch)
        rec = {"slide": slide_no, "type": tag, "native_id": sid, "name": name, "parent_group_ids": parents}
        key = ph_key(ch) if tag == "sp" else None
        if key:
            rec["placeholder"] = key
        if (x is None or x["cx"] is None) and key:
            # placeholder geometry inherits: slide -> layout placeholder -> master placeholder
            for level in ("layout", "master"):
                ph = find_ph(slide_ctx[level], key)
                px_ = xfrm_of(ph) if ph is not None else None
                if px_ and px_["cx"] is not None:
                    x, rec["geometry_inherited_from"] = px_, f"{level}.placeholder"
                    break
        if x and x["cx"] is not None:
            b = local_box(x) if parent is None else map_into_frame(local_box(x), *parent)
            rec["_frame"] = b
            t = math.radians(b["rot"]); c, s = math.cos(t), math.sin(t)
            pts = [(b["cx"] + dx * c - dy * s, b["cy"] + dx * s + dy * c) for dx, dy in
                   ((-b["w"] / 2, -b["h"] / 2), (b["w"] / 2, -b["h"] / 2), (b["w"] / 2, b["h"] / 2), (-b["w"] / 2, b["h"] / 2))]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            rec.update({"local_xfrm": x, "abs_corners_emu": [[round(a), round(q)] for a, q in pts],
                        "abs_aabb_mm": {"left": round(min(xs) / EMU_MM, 3), "top": round(min(ys) / EMU_MM, 3), "right": round(max(xs) / EMU_MM, 3), "bottom": round(max(ys) / EMU_MM, 3)},
                        "abs_centre_mm": [round(b["cx"] / EMU_MM, 3), round(b["cy"] / EMU_MM, 3)],
                        "abs_size_mm": [round(b["w"] / EMU_MM, 3), round(b["h"] / EMU_MM, 3)],
                        "net_rotation_deg": round(b["rot"], 3), "net_flipH": b["fh"], "net_flipV": b["fv"]})
            W, H = deck.size
            rec["out_of_slide_mm"] = {k: round(v / EMU_MM, 3) for k, v in
                                      {"left": max(0, -min(xs)), "top": max(0, -min(ys)), "right": max(0, max(xs) - W), "bottom": max(0, max(ys) - H)}.items() if v > 0.5}
        if tag == "sp" and ch.find("./p:txBody", NS) is not None:
            fonts = []
            for p in ch.findall("./p:txBody/a:p", NS):
                lvl = int(p.find("a:pPr", NS).get("lvl", "0") if p.find("a:pPr", NS) is not None else "0") + 1
                for r in p.findall("a:r", NS):
                    fonts.append({"text": (r.findtext("a:t", namespaces=NS) or "")[:40], **resolve_font(deck, ch, r, lvl, slide_ctx)})
            rec["text_runs"] = fonts
        frame = rec.pop("_frame", None)
        out.append(rec)
        if tag == "grpSp" and x and frame:
            walk(deck, ch, (x, frame), parents + [sid], slide_no, slide_ctx, out)


def analyse(path):
    deck = Deck(path)
    slides = []
    ids = [r.get(f"{{{NS['r']}}}id") for r in deck.pres.findall("p:sldIdLst/p:sldId", NS)]
    prels = deck.rels("ppt/presentation.xml")
    for n, rid in enumerate(ids, 1):
        part = prels[rid][1]
        layout = deck.rel_of_type(part, "slideLayout")
        master = deck.rel_of_type(layout, "slideMaster")
        ctx = {"layout": deck.xml(layout), "master": deck.xml(master), "theme": theme_fonts(deck, master)}
        out = []
        walk(deck, deck.xml(part).find(".//p:cSld/p:spTree", NS), None, [], n, ctx, out)
        slides.append({"slide": n, "part": part, "layout": layout, "master": master,
                       "theme_fonts": {k: v for k, v in ctx["theme"].items() if k != "theme_part"}, "objects": out})
    objs = [o for s in slides for o in s["objects"]]
    return {"schema": "svg-engine/ooxml-geometry-w2.0", "file": deck.path.name,
            "sha256": hashlib.sha256(deck.path.read_bytes()).hexdigest(),
            "slide_size_mm": [round(deck.size[0] / EMU_MM, 3), round(deck.size[1] / EMU_MM, 3)],
            "slide_count": len(slides), "object_count": len(objs),
            "group_count": sum(o["type"] == "grpSp" for o in objs),
            "max_group_depth": max((len(o["parent_group_ids"]) for o in objs), default=0),
            "out_of_slide": [{k: o[k] for k in ("slide", "type", "native_id", "name", "out_of_slide_mm")} for o in objs if o.get("out_of_slide_mm")],
            "font_resolution_sources": sorted({r["resolved_by"] for o in objs for r in o.get("text_runs", [])}),
            "slides": slides, "engineering_approval": False}

