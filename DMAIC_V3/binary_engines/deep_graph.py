"""Deep reader for drawings: PPTX, SVG, VSDX, drawio, Mermaid and SVG inside HTML -> ONE drawing-graph format.

Read-only. Per file it writes deep/<name>.graph.json with:
  nodes  : id, page, kind (preset / element / master), text, fill, line, dash, bbox, group
  edges  : src, dst, how (bound = attached in the file | geometric = endpoint lands on a shape | unresolved),
           direction (forward / backward / both / none, from arrow heads), colour, dash, width, kind
  legend : entries found next to a 'Legend/Legende/Key' title, as style -> meaning; matching nodes/edges get the meaning
  styles : clusters by fill colour, line colour, dash pattern and shape kind (what separates things visually)
  qa     : bound %, geometric %, unresolved %, directed %, raster-wrapped SVG, runtime-rendered HTML
plus deep/keb_candidates.jsonl: one candidate KEB_KNOWLEDGE_ATOM per resolved edge whose two ends carry text
(source_locator = file#page/edge, source_digest = file sha256). Candidates only: not validated against keb_row.schema.

    python -I -X utf8 DMAIC_V3/binary_engines/deep_graph.py <file> [<file> ...] [--redraw]
    python -I -X utf8 DMAIC_V3/binary_engines/deep_graph.py --root-id ID [--redraw]
"""

from __future__ import annotations

import argparse
import base64
import collections
import hashlib
import html as htmlmod
import json
import math
import re
import sys
import urllib.parse
import zipfile
import zlib
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estate_spec import ESTATE, legend_registry  # noqa: E402
from ggmath_bridge import load as _load_kernel  # noqa: E402

PG = _load_kernel(
    "plane_geometry"
)  # gg_MATH kernels/plane_geometry.py, pinned in ggmath_bridge.PINS

EST = ESTATE
OUT = EST / "deep"
LEGEND_RX = re.compile(r"\b(legend|legende|légende|key|symbols?|symbolen)\b", re.I)
NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "v": "http://schemas.microsoft.com/office/visio/2012/main",
}
LINE_PRESETS = {
    "line",
    "straightConnector1",
    "bentConnector2",
    "bentConnector3",
    "bentConnector4",
    "bentConnector5",
    "curvedConnector2",
    "curvedConnector3",
    "curvedConnector4",
    "curvedConnector5",
}
BLOCK_ARROWS = {
    "rightArrow": (0, 1),
    "leftArrow": (0, -1),
    "upArrow": (1, -1),
    "downArrow": (1, 1),
    "leftRightArrow": (0, 2),
    "upDownArrow": (1, 2),
    "notchedRightArrow": (0, 1),
    "stripedRightArrow": (0, 1),
    "chevron": (0, 1),
    "homePlate": (0, 1),
}


# ============================================================ shared graph helpers
def new_graph(fmt: str, path: Path) -> dict:
    return {
        "schema": "gbogeb.estate.drawing_graph/0.1",
        "format": fmt,
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "pages": [],
        "nodes": [],
        "edges": [],
        "legend": [],
        "notes": [],
    }


contains = PG.box_contains  # point in box, edges included, grown by tol
dist_to_box = (
    PG.box_distance
)  # Euclidean distance from a point to a box, 0 on or inside it


def resolve_geometric(
    g: dict, page: str, page_w: float, page_h: float, tol_frac: float = 0.012
) -> None:
    """Edges that are not attached in the file: snap each endpoint to the smallest shape it lands on (or touches within tol)."""
    tol = tol_frac * max(page_w, page_h)
    area = page_w * page_h
    nodes = [
        n
        for n in g["nodes"]
        if n["page"] == page
        and n["bbox"]
        and n["kind"] != "group"
        and n["bbox"][2] * n["bbox"][3] < 0.4 * area
    ]
    shapes = [n for n in nodes if n["kind"] != "text"]
    labels = [
        n
        for n in nodes
        if n["kind"] == "text" or (n.get("text") and n["kind"] in ("rect", "custGeom"))
    ]

    def border_ok(n, x, y):
        """A big container only counts when the end touches its border; an end floating inside it is not a link (tuning rule T2)."""
        b = n["bbox"]
        if b[2] * b[3] < 0.05 * area:
            return True
        inner = PG.box_edge_margin(b, x, y)
        return inner <= 2 * tol

    for e in (
        e
        for e in g["edges"]
        if e["page"] == page and e["how"] != "bound" and e.get("p0")
    ):
        for end, key in ((e["p0"], "src"), (e["p1"], "dst")):
            if e.get(key):
                continue
            for pool, kind in (
                (shapes, "shape"),
                (labels, "label"),
            ):  # tuning rule T1: a text tag is a valid end (off-page / label)
                cands = [n for n in pool if n["id"] != e["id"] and border_ok(n, *end)]
                hit = PG.snap_to_box(
                    end, [n["bbox"] for n in cands], tol
                )  # touching first, then smallest, then first
                if hit is not None:
                    best = cands[hit]
                    e[key] = best["id"]
                    e[key + "_end"] = kind
                    break
        e["how"] = (
            "geometric"
            if e.get("src") and e.get("dst")
            else ("half" if e.get("src") or e.get("dst") else "unresolved")
        )


def attach_flow_markers(g: dict, page: str, page_w: float, page_h: float) -> None:
    """Short loose arrows drawn on top of a line are flow markers (P&ID convention): give the line their direction."""
    diag = math.hypot(page_w, page_h)
    E = [e for e in g["edges"] if e["page"] == page and e.get("p0") and e.get("p1")]
    for m in E:
        if m["how"] not in ("unresolved", "half") or m["direction"] == "none":
            continue
        if math.dist(m["p0"], m["p1"]) > 0.03 * diag:
            continue
        mid = ((m["p0"][0] + m["p1"][0]) / 2, (m["p0"][1] + m["p1"][1]) / 2)
        others = [
            e
            for e in E
            if e is not m
            and e.get("kind") != "flow_marker"
            and math.dist(e["p0"], e["p1"]) > math.dist(m["p0"], m["p1"])
        ]
        if not others:
            continue
        idx, gap = PG.nearest_segment(
            mid, [(e["p0"], e["p1"]) for e in others]
        )  # lowest index on a tie
        host = others[idx]
        if gap > 0.01 * diag:
            continue
        tail, tip = (
            (m["p1"], m["p0"]) if m["direction"] == "backward" else (m["p0"], m["p1"])
        )
        m.update(kind="flow_marker", how="flow_marker", on_edge=host["id"])
        if host["direction"] == "none":
            # marker along the host: forward; against it: backward; perpendicular (0) counts as forward
            host["direction"] = (
                "backward"
                if PG.project_direction(tail, tip, host["p0"], host["p1"]) < 0
                else "forward"
            )
            host["direction_from"] = "flow_marker"


def style_key_node(n):
    return ("node", n.get("kind"), n.get("fill"), n.get("line"))


def style_key_edge(e):
    return ("edge", e.get("colour"), e.get("dash"), e.get("direction") != "none")


def find_legend(g: dict, page: str, page_w: float, page_h: float) -> None:
    titles = [
        n
        for n in g["nodes"]
        if n["page"] == page
        and n.get("text")
        and LEGEND_RX.search(n["text"][:40])
        and n["bbox"]
    ]
    for t in titles:
        x, y, w, h = t["bbox"]
        region = [
            x - 0.05 * page_w,
            y - 0.01 * page_h,
            max(3 * w, 0.3 * page_w),
            0.45 * page_h,
        ]
        inside = lambda b: b and contains(
            region, b[0] + b[2] / 2, b[1] + b[3] / 2, 0
        )  # noqa: E731
        texts = [
            n
            for n in g["nodes"]
            if n["page"] == page and n is not t and n.get("text") and inside(n["bbox"])
        ]
        symbols = [
            ("node", n)
            for n in g["nodes"]
            if n["page"] == page
            and n is not t
            and not n.get("text")
            and inside(n["bbox"])
            and n["kind"] not in ("group",)
        ]
        symbols += [
            ("edge", e)
            for e in g["edges"]
            if e["page"] == page and e.get("p0") and inside([*e["p0"], 1, 1])
        ]
        entries = []
        for kind, s in symbols:
            sb = (
                s["bbox"]
                if kind == "node"
                else [
                    min(s["p0"][0], s["p1"][0]),
                    min(s["p0"][1], s["p1"][1]),
                    abs(s["p1"][0] - s["p0"][0]),
                    abs(s["p1"][1] - s["p0"][1]),
                ]
            )
            cy = sb[1] + sb[3] / 2
            right = [
                tx
                for tx in texts
                if tx["bbox"][0] >= sb[0] + sb[2] * 0.5
                and abs((tx["bbox"][1] + tx["bbox"][3] / 2) - cy)
                < max(sb[3], tx["bbox"][3], 0.02 * page_h)
            ]
            if right:
                label = min(right, key=lambda tx: tx["bbox"][0] - sb[0])
                words = label["text"].split()
                if not words or len(words) > 6 or len(label["text"]) > 48:
                    continue  # tuning rule L1: a legend meaning is a short label, never a paragraph
                key = style_key_node(s) if kind == "node" else style_key_edge(s)
                entries.append(
                    {
                        "page": page,
                        "symbol": s["id"],
                        "style": list(key),
                        "meaning": label["text"][:48],
                    }
                )
        # a style that maps to two different meanings is ambiguous: DEFER it rather than pick one
        by_style = collections.defaultdict(set)
        for en in entries:
            by_style[tuple(en["style"])].add(en["meaning"])
        ambiguous = {k for k, v in by_style.items() if len(v) > 1}
        if ambiguous:
            g["notes"].append(
                f"{page}: legend maps {len(ambiguous)} style(s) to more than one meaning; those stay DEFER"
            )
        entries = [en for en in entries if tuple(en["style"]) not in ambiguous]
        if entries:
            g["legend"].append(
                {
                    "page": page,
                    "title": t["id"],
                    "entries": entries,
                    "source": "in_drawing_legend",
                }
            )
            meaning = {tuple(en["style"]): en["meaning"] for en in entries}
            legend_ids = {en["symbol"] for en in entries}
            for n in g["nodes"]:
                if (
                    n["page"] == page
                    and n["id"] not in legend_ids
                    and style_key_node(n) in meaning
                ):
                    n["legend_meaning"] = meaning[style_key_node(n)]
                    n["semantic_source"] = "in_drawing_legend"
            for e in g["edges"]:
                if (
                    e["page"] == page
                    and e["id"] not in legend_ids
                    and style_key_edge(e) in meaning
                ):
                    e["legend_meaning"] = meaning[style_key_edge(e)]
                    e["semantic_source"] = "in_drawing_legend"


EVIDENCE = {
    "bound": "FILE_CONNECTED",
    "geometric": "GEOMETRIC_TOUCH",
    "half": "PARTIAL",
    "unresolved": "NONE",
    "flow_marker": "MARKER",
    "pending": "NONE",
}
TAG_RX = re.compile(r"\b([A-Z]{1,4}[-_ ]?\d{2,4}[A-Z]?|[A-Z]{2,4}\d)\b")
REGISTRY = legend_registry()  # None = no owner-accepted rules


def _registry() -> list[dict]:
    """Owner-accepted style -> meaning rules. Empty until the owner adds entries; nothing is inferred into it."""
    if REGISTRY is None:
        return []
    import yaml

    return [
        r
        for r in (yaml.safe_load(REGISTRY.read_text("utf-8")) or {}).get("accepted", [])
        or []
        if r.get("authority")
    ]


def finish(g: dict) -> dict:
    # locators (file#page/id) are where an object sits in THIS file; they do not survive a revision.
    # stable-ID candidates (eq:P-101) come from tag-like text and are what a crosswalk joins on. Candidates only.
    for n in g["nodes"]:
        n["locator"] = f"{g['file']}#{n['id']}"
        tags = sorted(
            {re.sub(r"[-_ ]", "-", t) for t in TAG_RX.findall(n.get("text") or "")}
        )
        if tags:
            n["eq_candidates"] = [f"eq:{t}" for t in tags[:6]]
    reg = [r for r in _registry() if re.search(r.get("file_regex", "."), g["file"])]
    for e in g["edges"]:
        e["locator"] = f"{g['file']}#{e['id']}"
        e["evidence"] = EVIDENCE.get(e["how"], "NONE")
        e["drawn"] = (
            "arrow" if e["direction"] != "none" else "line"
        )  # what is drawn, not what it means
        if not e.get("semantic_source"):
            hit = next(
                (
                    r
                    for r in reg
                    if all(
                        str(e.get(k)) == str(v)
                        for k, v in (r.get("style") or {}).items()
                    )
                ),
                None,
            )
            if hit:
                e["legend_meaning"], e["semantic_source"] = (
                    hit["meaning"],
                    f"registry:{hit['authority']}",
                )
        e["semantic_type"] = e.get("legend_meaning") or "DEFER"
    E = g["edges"]
    n_e = len(E) or 1
    how = collections.Counter(e["how"] for e in E)
    g["qa"] = {
        "nodes": len(g["nodes"]),
        "edges": len(E),
        "pages": len(g["pages"]),
        "bound_pct": round(100 * how["bound"] / n_e, 1),
        "geometric_pct": round(100 * how["geometric"] / n_e, 1),
        "half_pct": round(100 * how["half"] / n_e, 1),
        "unresolved_pct": round(100 * how["unresolved"] / n_e, 1),
        "flow_marker_pct": round(100 * how["flow_marker"] / n_e, 1),
        "directed_pct": round(
            100
            * sum(e["direction"] != "none" for e in E if e["how"] != "flow_marker")
            / n_e,
            1,
        ),
        "direction_from_markers": sum(
            e.get("direction_from") == "flow_marker" for e in E
        ),
        "nodes_with_text": sum(bool(n.get("text")) for n in g["nodes"]),
        "legend_entries": sum(len(l["entries"]) for l in g["legend"]),
        "legend_applied": sum("legend_meaning" in x for x in g["nodes"] + E),
    }
    g["styles"] = {
        "node_fill": dict(
            collections.Counter(
                n.get("fill") for n in g["nodes"] if n["kind"] != "text"
            ).most_common(8)
        ),
        "node_kind": dict(
            collections.Counter(n["kind"] for n in g["nodes"]).most_common(10)
        ),
        "edge_colour": dict(
            collections.Counter(e.get("colour") for e in E).most_common(8)
        ),
        "edge_dash": dict(collections.Counter(e.get("dash") for e in E).most_common(5)),
        "edge_direction": dict(collections.Counter(e["direction"] for e in E)),
    }
    return g


def direction(head: bool, tail: bool) -> str:
    """head = arrow at the start point, tail = arrow at the end point (DrawingML naming)."""
    return (
        "both"
        if head and tail
        else "forward" if tail else "backward" if head else "none"
    )


# ============================================================ PPTX
def _clr(el):
    if el is None:
        return None
    s = el.find("a:solidFill", NS)
    if s is not None:
        c = s.find("a:srgbClr", NS)
        if c is not None:
            return "#" + c.get("val")
        c = s.find("a:schemeClr", NS)
        if c is not None:
            return "scheme:" + c.get("val")
    if el.find("a:noFill", NS) is not None:
        return "none"
    return None


def read_pptx(path: Path) -> dict:
    g = new_graph("pptx", path)
    with zipfile.ZipFile(path) as zf:
        pres = etree.fromstring(zf.read("ppt/presentation.xml"))
        sz = pres.find("p:sldSz", NS)
        W, H = int(sz.get("cx")), int(sz.get("cy"))
        slides = sorted(
            (n for n in zf.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
            key=lambda n: int(re.findall(r"\d+", n)[0]),
        )
        for sn in slides:
            page = "s" + re.findall(r"\d+", sn)[0]
            g["pages"].append({"id": page, "w": W, "h": H})
            root = etree.fromstring(zf.read(sn))
            tree = root.find(".//p:cSld/p:spTree", NS)
            _walk_pptx(g, tree, page, (1.0, 1.0, 0.0, 0.0), None, W, H)
            resolve_geometric(g, page, W, H)
            attach_flow_markers(g, page, W, H)
            find_legend(g, page, W, H)
    return finish(g)


def _xfrm(el):
    x = el.find("a:xfrm", NS) if el is not None else None
    if x is None:
        return None
    off, ext = x.find("a:off", NS), x.find("a:ext", NS)
    if off is None or ext is None:
        return None
    return (
        int(float(off.get("x"))),
        int(float(off.get("y"))),
        int(float(ext.get("cx"))),
        int(float(ext.get("cy"))),
        x.get("flipH") == "1",
        x.get("flipV") == "1",
        x,
        int(x.get("rot", "0")),
    )


def _walk_pptx(g, tree, page, T, group, W, H):
    sx, sy, tx, ty = T
    for el in tree:
        tag = etree.QName(el).localname
        nv = el.find(".//p:cNvPr", NS)
        sid = f"{page}:{nv.get('id')}" if nv is not None else None
        if tag == "grpSp":
            gx = _xfrm(el.find("p:grpSpPr", NS))
            if gx is None:
                continue
            x, y, cx, cy, *_ = gx
            ch_off, ch_ext = gx[6].find("a:chOff", NS), gx[6].find("a:chExt", NS)
            kx = cx / max(int(float(ch_ext.get("cx"))), 1) if ch_ext is not None else 1
            ky = cy / max(int(float(ch_ext.get("cy"))), 1) if ch_ext is not None else 1
            cox, coy = (
                (int(float(ch_off.get("x"))), int(float(ch_off.get("y"))))
                if ch_off is not None
                else (x, y)
            )
            bbox = [sx * x + tx, sy * y + ty, sx * cx, sy * cy]
            g["nodes"].append(
                {
                    "id": sid,
                    "page": page,
                    "kind": "group",
                    "text": "",
                    "bbox": bbox,
                    "group": group,
                }
            )
            T2 = (sx * kx, sy * ky, sx * (x - cox * kx) + tx, sy * (y - coy * ky) + ty)
            _walk_pptx(g, el, page, T2, group or sid, W, H)
            continue
        if tag not in ("sp", "cxnSp", "pic", "graphicFrame"):
            continue
        sppr = el.find("p:spPr", NS)
        xf = (
            _xfrm(sppr)
            if tag != "graphicFrame"
            else (
                _xfrm(el.find("p:xfrm", NS).getparent())
                if el.find("p:xfrm", NS) is not None
                else None
            )
        )
        if tag == "graphicFrame" and el.find("p:xfrm", NS) is not None:
            o, e2 = el.find("p:xfrm/a:off", NS), el.find("p:xfrm/a:ext", NS)
            xf = (
                int(float(o.get("x"))),
                int(float(o.get("y"))),
                int(float(e2.get("cx"))),
                int(float(e2.get("cy"))),
                False,
                False,
                None,
                0,
            )
        if xf is None:
            continue
        x, y, cx, cy, fh, fv, _, rot = xf
        bbox = [sx * x + tx, sy * y + ty, sx * cx, sy * cy]
        prst_el = sppr.find("a:prstGeom", NS) if sppr is not None else None
        prst = (
            prst_el.get("prst")
            if prst_el is not None
            else (
                "custGeom"
                if sppr is not None and sppr.find("a:custGeom", NS) is not None
                else tag
            )
        )
        ln = sppr.find("a:ln", NS) if sppr is not None else None
        line = _clr(ln)
        if line is None:  # theme style reference
            lr = el.find("p:style/a:lnRef/a:schemeClr", NS)
            line = "style:" + lr.get("val") if lr is not None else None
        fill = _clr(sppr)
        if fill is None:
            fr = el.find("p:style/a:fillRef/a:schemeClr", NS)
            fill = "style:" + fr.get("val") if fr is not None else None
        dash_el = ln.find("a:prstDash", NS) if ln is not None else None
        dash = dash_el.get("val") if dash_el is not None else "solid"
        text = " ".join(t.text or "" for t in el.iter("{%s}t" % NS["a"])).strip()
        if tag == "cxnSp" or prst in LINE_PRESETS:
            p0 = (bbox[0] + (bbox[2] if fh else 0), bbox[1] + (bbox[3] if fv else 0))
            p1 = (bbox[0] + (0 if fh else bbox[2]), bbox[1] + (0 if fv else bbox[3]))
            he = ln.find("a:headEnd", NS) if ln is not None else None
            te = ln.find("a:tailEnd", NS) if ln is not None else None
            head = he is not None and he.get("type", "none") != "none"
            tail = te is not None and te.get("type", "none") != "none"
            st, en = el.find(".//a:stCxn", NS), el.find(".//a:endCxn", NS)
            e = {
                "id": sid,
                "page": page,
                "kind": prst,
                "p0": p0,
                "p1": p1,
                "colour": line,
                "dash": dash,
                "width": int(ln.get("w", "0")) if ln is not None else None,
                "direction": direction(head, tail),
                "src": f"{page}:{st.get('id')}" if st is not None else None,
                "dst": f"{page}:{en.get('id')}" if en is not None else None,
                "group": group,
                "label": text,
            }
            e["how"] = "bound" if e["src"] and e["dst"] else "pending"
            g["edges"].append(e)
            continue
        if prst in BLOCK_ARROWS:  # a block arrow is an edge drawn as a shape
            axis, sign = BLOCK_ARROWS[prst]
            if fh and axis == 0 or fv and axis == 1:
                sign = -sign if sign in (1, -1) else sign
            mx, my = bbox[0] + bbox[2] / 2, bbox[1] + bbox[3] / 2
            if axis == 0:
                a, b = (bbox[0], my), (bbox[0] + bbox[2], my)
            else:
                a, b = (mx, bbox[1]), (mx, bbox[1] + bbox[3])
            p0, p1 = (a, b) if sign in (1, 2) else (b, a)
            g["edges"].append(
                {
                    "id": sid,
                    "page": page,
                    "kind": "block:" + prst,
                    "p0": p0,
                    "p1": p1,
                    "colour": fill,
                    "dash": "solid",
                    "width": None,
                    "direction": "both" if sign == 2 else "forward",
                    "src": None,
                    "dst": None,
                    "group": group,
                    "label": text,
                    "how": "pending",
                }
            )
            continue
        kind = (
            "text"
            if (
                el.find("p:nvSpPr/p:cNvSpPr", NS) is not None
                and el.find("p:nvSpPr/p:cNvSpPr", NS).get("txBox") == "1"
            )
            else prst
        )
        if tag == "pic":
            kind = "picture"
        elif tag == "graphicFrame":
            kind = (
                "table"
                if el.find(".//a:tbl", NS) is not None
                else (
                    "chart"
                    if "chart" in etree.tostring(el).decode("utf-8", "ignore")[:3000]
                    else "frame"
                )
            )
        g["nodes"].append(
            {
                "id": sid,
                "page": page,
                "kind": kind,
                "text": text[:300],
                "fill": fill,
                "line": line,
                "dash": dash,
                "bbox": bbox,
                "group": group,
                "rot": rot,
            }
        )


# ============================================================ SVG
NUM = PG.NUMBER  # SVG number grammar
_affine_mul = PG.affine_multiply  # SVG affine maps (a, b, c, d, e, f)
_parse_transform = PG.parse_transform  # SVG transform attribute -> one affine map
_ap = PG.affine_apply  # map a point


def _path_points(d):
    toks = re.findall(r"[MmZzLlHhVvCcSsQqTtAa]|" + NUM, d or "")
    pts, i, cmd, cur, start, closed, first = (
        [],
        0,
        None,
        (0.0, 0.0),
        (0.0, 0.0),
        False,
        None,
    )
    nargs = {
        "M": 2,
        "L": 2,
        "H": 1,
        "V": 1,
        "C": 6,
        "S": 4,
        "Q": 4,
        "T": 2,
        "A": 7,
        "Z": 0,
    }
    while i < len(toks):
        if re.fullmatch(r"[A-Za-z]", toks[i]):
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                closed, cur = True, start
                pts.append(cur)
                continue
        if cmd is None:
            break
        n = nargs[cmd.upper()]
        if i + n > len(toks):
            break
        v = [float(t) for t in toks[i : i + n]]
        i += n
        rel = cmd.islower()
        U = cmd.upper()
        if U == "H":
            cur = (cur[0] * rel + v[0], cur[1])
        elif U == "V":
            cur = (cur[0], cur[1] * rel + v[0])
        else:
            nx, ny = v[-2], v[-1]
            cur = (cur[0] + nx, cur[1] + ny) if rel else (nx, ny)
        if U == "M":
            start = cur
            if first is None:
                first = cur
            cmd = "l" if rel else "L"
        pts.append(cur)
    return pts, closed


def _css_classes(root):
    rules = {}
    for st in root.iter("{*}style"):
        for sel, body in re.findall(r"([^{}]+)\{([^}]*)\}", st.text or ""):
            props = dict(
                (k.strip(), v.strip())
                for k, v in (p.split(":", 1) for p in body.split(";") if ":" in p)
            )
            for s in sel.split(","):
                s = s.strip()
                if s.startswith("."):
                    rules.setdefault(s[1:], {}).update(props)
    return rules


INHERIT = (
    "fill",
    "stroke",
    "stroke-dasharray",
    "marker-start",
    "marker-end",
    "font-family",
    "stroke-width",
)


def read_svg_root(root, g: dict, page: str, notes_prefix: str = "") -> None:
    css = _css_classes(root)
    vb = [float(x) for x in re.findall(NUM, root.get("viewBox", ""))] or [
        0,
        0,
        float(
            re.findall(NUM, root.get("width", "1000"))[0]
            if re.findall(NUM, root.get("width", "1000"))
            else 1000
        ),
        float(
            re.findall(NUM, root.get("height", "1000"))[0]
            if re.findall(NUM, root.get("height", "1000"))
            else 1000
        ),
    ]
    W, H = (vb[2], vb[3]) if len(vb) == 4 else (1000, 1000)
    g["pages"].append({"id": page, "w": W, "h": H})
    counter = collections.Counter()
    raster_area = 0.0
    texts = []

    def style_of(el, inherited):
        s = dict(inherited)
        for c in (el.get("class") or "").split():
            s.update(css.get(c, {}))
        for k in INHERIT:
            if el.get(k) is not None:
                s[k] = el.get(k)
        for part in (el.get("style") or "").split(";"):
            if ":" in part:
                k, v = part.split(":", 1)
                s[k.strip()] = v.strip()
        return s

    def walk(el, M, inherited, group):
        nonlocal raster_area
        if not isinstance(el.tag, str):
            return
        tag = etree.QName(el).localname
        if tag in (
            "defs",
            "marker",
            "clipPath",
            "mask",
            "symbol",
            "style",
            "title",
            "desc",
            "metadata",
            "linearGradient",
            "radialGradient",
            "pattern",
        ):
            return
        M2 = _affine_mul(M, _parse_transform(el.get("transform")))
        st = style_of(el, inherited)
        sid = f"{page}:{el.get('id') or tag + str(counter[tag])}"
        counter[tag] += 1
        fill, stroke = st.get("fill", "black"), st.get("stroke", "none")
        dash = (
            "dash"
            if st.get("stroke-dasharray", "none") not in ("none", "")
            else "solid"
        )
        if tag == "g" or tag == "svg" and el is not root:
            for ch in el:
                walk(
                    ch,
                    M2,
                    {k: v for k, v in st.items() if k in INHERIT},
                    group or (sid if tag == "g" and el.get("id") else group),
                )
            return
        if tag == "svg":
            for ch in el:
                walk(ch, M2, {k: v for k, v in st.items() if k in INHERIT}, group)
            return
        if tag == "image":
            x, y = float(el.get("x", 0) or 0), float(el.get("y", 0) or 0)
            w, h = float(re.findall(NUM, el.get("width", "0"))[0] or 0), float(
                re.findall(NUM, el.get("height", "0"))[0] or 0
            )
            raster_area += abs(w * h * M2[0] * M2[3])
            g["nodes"].append(
                {
                    "id": sid,
                    "page": page,
                    "kind": "raster_image",
                    "text": "",
                    "fill": None,
                    "line": None,
                    "dash": None,
                    "bbox": _bbox([_ap(M2, x, y), _ap(M2, x + w, y + h)]),
                    "group": group,
                }
            )
            return
        if tag in ("text",):
            content = " ".join(t.strip() for t in el.itertext() if t.strip())
            x, y = float((re.findall(NUM, el.get("x", "0")) or [0])[0]), float(
                (re.findall(NUM, el.get("y", "0")) or [0])[0]
            )
            p = _ap(M2, x, y)
            fs = float((re.findall(NUM, st.get("font-size", "10")) or [10])[0]) * abs(
                M2[3] or 1
            )
            texts.append(
                {
                    "id": sid,
                    "page": page,
                    "kind": "text",
                    "text": content[:300],
                    "fill": fill,
                    "line": None,
                    "dash": None,
                    "bbox": [
                        p[0],
                        p[1] - fs,
                        max(len(content) * fs * 0.55, fs),
                        fs * 1.2,
                    ],
                    "group": group,
                }
            )
            return
        pts, closed = [], False
        if tag == "rect":
            x, y, w, h = (
                float((re.findall(NUM, el.get(k, "0")) or [0])[0])
                for k in ("x", "y", "width", "height")
            )
            pts, closed = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], True
        elif tag in ("circle", "ellipse"):
            cx, cy = float(el.get("cx", 0) or 0), float(el.get("cy", 0) or 0)
            rx = float(el.get("r", el.get("rx", 0)) or 0)
            ry = float(el.get("r", el.get("ry", 0)) or 0)
            pts, closed = [(cx - rx, cy - ry), (cx + rx, cy + ry)], True
        elif tag in ("polygon", "polyline"):
            v = [float(x) for x in re.findall(NUM, el.get("points", ""))]
            pts, closed = list(zip(v[0::2], v[1::2])), tag == "polygon"
        elif tag == "line":
            pts = [
                (float(el.get("x1", 0) or 0), float(el.get("y1", 0) or 0)),
                (float(el.get("x2", 0) or 0), float(el.get("y2", 0) or 0)),
            ]
        elif tag == "path":
            pts, closed = _path_points(el.get("d"))
        elif tag == "use":
            g["notes"].append(
                f"{notes_prefix}<use> {el.get('{http://www.w3.org/1999/xlink}href') or el.get('href')} not expanded"
            )
            return
        else:
            return
        if not pts:
            return
        P = [_ap(M2, *q) for q in pts]
        has_marker = any(
            st.get(k, "none") not in ("none", "")
            for k in ("marker-start", "marker-end")
        )
        if closed and not has_marker:
            g["nodes"].append(
                {
                    "id": sid,
                    "page": page,
                    "kind": tag,
                    "text": "",
                    "fill": fill,
                    "line": stroke,
                    "dash": dash,
                    "bbox": _bbox(P),
                    "group": group,
                }
            )
        elif stroke != "none" or has_marker:
            head = st.get("marker-start", "none") not in ("none", "")
            tail = st.get("marker-end", "none") not in ("none", "")
            g["edges"].append(
                {
                    "id": sid,
                    "page": page,
                    "kind": tag,
                    "p0": P[0],
                    "p1": P[-1],
                    "colour": stroke,
                    "dash": dash,
                    "width": st.get("stroke-width"),
                    "direction": direction(head, tail),
                    "src": None,
                    "dst": None,
                    "group": group,
                    "label": "",
                    "how": "pending",
                }
            )

    walk(
        root,
        (1, 0, 0, 1, -vb[0] if len(vb) == 4 else 0, -vb[1] if len(vb) == 4 else 0),
        {},
        None,
    )
    # attach each text to the smallest shape that contains its anchor; free text stays a text node (tags, labels)
    shapes = [
        n
        for n in g["nodes"]
        if n["page"] == page and n["kind"] not in ("raster_image",)
    ]
    for t in texts:
        cx, cy = t["bbox"][0] + t["bbox"][2] / 2, t["bbox"][1] + t["bbox"][3] / 2
        hosts = [
            n
            for n in shapes
            if contains(n["bbox"], cx, cy, 0)
            and n["bbox"][2] * n["bbox"][3] < 0.25 * W * H
        ]
        if hosts:
            host = min(hosts, key=lambda n: n["bbox"][2] * n["bbox"][3])
            host["text"] = (host["text"] + " " + t["text"]).strip()[:300]
        else:
            g["nodes"].append(t)
    if raster_area > 0.5 * W * H:
        g["notes"].append(
            f"{notes_prefix}RASTER-WRAPPED: an embedded image covers {100 * raster_area / (W * H):.0f}% of the page; "
            "its content has no vector semantics (needs the vision lane)"
        )
    resolve_geometric(g, page, W, H, 0.01)
    attach_flow_markers(g, page, W, H)
    find_legend(g, page, W, H)


def _bbox(P):
    return list(PG.bbox(P))  # [x, y, w, h] of the points


def read_svg(path: Path) -> dict:
    g = new_graph("svg", path)
    root = etree.parse(
        str(path), etree.XMLParser(huge_tree=True, recover=True)
    ).getroot()
    read_svg_root(root, g, "p1")
    return finish(g)


def read_html(path: Path) -> dict:
    g = new_graph("html", path)
    s = path.read_text("utf-8", "replace")
    blocks = re.findall(r"<svg\b.*?</svg>", s, re.S | re.I)
    body = re.sub(
        r"<script\b[^>]*>.*?</script\b[^>]*>|<style\b[^>]*>.*?</style\b[^>]*>",
        "",
        s,
        flags=re.S | re.I,
    )
    in_body = re.findall(r"<svg\b.*?</svg>", body, re.S | re.I)
    g["notes"].append(
        f"{len(blocks)} <svg> block(s): {len(in_body)} in the page markup, {len(blocks) - len(in_body)} built inside script; "
        f"markup SVG is {100 * sum(map(len, in_body)) / max(len(body), 1):.0f}% of the page body"
    )
    if re.search(r"d3\.|mermaid|cytoscape|vis-network|new Chart\(|<canvas", s):
        g["notes"].append(
            "RUNTIME-RENDERED: the page draws (more) graphics with script at load time; static parsing misses them (needs Playwright DOM capture)"
        )
    for i, b in enumerate(blocks[:40], 1):
        try:
            root = etree.fromstring(
                b.encode("utf-8"), etree.XMLParser(recover=True, huge_tree=True)
            )
        except etree.XMLSyntaxError:
            g["notes"].append(f"svg{i}: not well-formed XML")
            continue
        if root is not None and len(root):
            read_svg_root(root, g, f"svg{i}", f"svg{i}: ")
    if not g["nodes"] and not g["edges"]:
        captured = _dom_capture(path)
        if captured is None:
            g["notes"].append(
                "UNSUPPORTED (static): no drawing in the markup and the page could not be rendered here"
            )
        else:
            g["notes"].append(
                f"DOM capture (Playwright/Chromium): {len(captured)} rendered <svg> element(s) read after script ran"
            )
            g["capture"] = "rendered_dom"
            for i, b in enumerate(captured[:40], 1):
                root = etree.fromstring(
                    b.encode("utf-8"), etree.XMLParser(recover=True, huge_tree=True)
                )
                if root is not None and len(root):
                    read_svg_root(root, g, f"dom{i}", f"dom{i}: ")
    return finish(g)


def _dom_capture(path: Path) -> list[str] | None:
    """Render the page in headless Chromium, let its script draw, return the outerHTML of every <svg>. None if unavailable."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            p = b.new_page(viewport={"width": 1600, "height": 1200})
            p.goto(path.resolve().as_uri(), wait_until="load", timeout=30000)
            p.wait_for_timeout(1500)
            svgs = p.evaluate(
                "Array.from(document.querySelectorAll('svg')).filter(s => s.querySelectorAll('*').length > 3).map(s => s.outerHTML)"
            )
            b.close()
            return svgs
    except Exception:
        return None


# ============================================================ VSDX
def read_vsdx(path: Path) -> dict:
    g = new_graph("vsdx", path)
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        masters = {}
        if "visio/masters/masters.xml" in names:
            for m in etree.fromstring(zf.read("visio/masters/masters.xml")).iter(
                "{%s}Master" % NS["v"]
            ):
                masters[m.get("ID")] = m.get("NameU") or m.get("Name")
        pages = sorted(
            (n for n in names if re.fullmatch(r"visio/pages/page\d+\.xml", n)),
            key=lambda n: int(re.findall(r"\d+", n)[0]),
        )
        pnames = {}
        if "visio/pages/pages.xml" in names:
            for i, pg in enumerate(
                etree.fromstring(zf.read("visio/pages/pages.xml")).iter(
                    "{%s}Page" % NS["v"]
                ),
                1,
            ):
                pnames[i] = pg.get("NameU") or pg.get("Name")
        for pn in pages:
            k = int(re.findall(r"\d+", pn)[0])
            page = f"p{k}"
            root = etree.fromstring(zf.read(pn))
            ext = [0, 0]

            def cells(sh):
                return {c.get("N"): c.get("V") for c in sh.findall("v:Cell", NS)}

            def walk(container, ox, oy, group):
                for sh in container.findall("v:Shape", NS):
                    c = cells(sh)
                    sid = f"{page}:{sh.get('ID')}"
                    master = masters.get(sh.get("Master"), sh.get("Master"))
                    text = " ".join(
                        t.strip()
                        for t in (
                            sh.find("v:Text", NS).itertext()
                            if sh.find("v:Text", NS) is not None
                            else []
                        )
                        if t.strip()
                    )
                    f = lambda n, d=0.0: (
                        float(c[n])
                        if c.get(n) not in (None, "") and re.fullmatch(NUM, c[n])
                        else d
                    )  # noqa: E731
                    if "BeginX" in c and "EndX" in c:
                        p0, p1 = (ox + f("BeginX"), oy + f("BeginY")), (
                            ox + f("EndX"),
                            oy + f("EndY"),
                        )
                        ext[0], ext[1] = max(ext[0], p0[0], p1[0]), max(
                            ext[1], p0[1], p1[1]
                        )
                        head, tail = f("BeginArrow") > 0, f("EndArrow") > 0
                        g["edges"].append(
                            {
                                "id": sid,
                                "page": page,
                                "kind": master or "1-D",
                                "p0": p0,
                                "p1": p1,
                                "colour": c.get("LineColor") or "inherit",
                                "dash": (
                                    "solid"
                                    if c.get("LinePattern") in (None, "1")
                                    else "pattern" + c["LinePattern"]
                                ),
                                "width": c.get("LineWeight"),
                                "direction": direction(head, tail),
                                "src": None,
                                "dst": None,
                                "group": group,
                                "label": text[:120],
                                "how": "pending",
                            }
                        )
                        continue
                    w, h = f("Width"), f("Height")
                    x0, y0 = ox + f("PinX") - f("LocPinX", w / 2), oy + f("PinY") - f(
                        "LocPinY", h / 2
                    )
                    ext[0], ext[1] = max(ext[0], x0 + w), max(ext[1], y0 + h)
                    g["nodes"].append(
                        {
                            "id": sid,
                            "page": page,
                            "kind": master or sh.get("Type", "Shape"),
                            "text": text[:300],
                            "fill": c.get("FillForegnd") or "inherit",
                            "line": c.get("LineColor") or "inherit",
                            "dash": "solid",
                            "bbox": [x0, y0, w, h],
                            "group": group,
                        }
                    )
                    sub = sh.find("v:Shapes", NS)
                    if sub is not None:
                        walk(sub, x0, y0, group or sid)

            top = root.find("v:Shapes", NS)
            if top is not None:
                walk(top, 0.0, 0.0, None)
            byid = {e["id"]: e for e in g["edges"] if e["page"] == page}
            for cn in root.iter("{%s}Connect" % NS["v"]):
                e = byid.get(f"{page}:{cn.get('FromSheet')}")
                if e is not None:
                    e["src" if cn.get("FromCell") == "BeginX" else "dst"] = (
                        f"{page}:{cn.get('ToSheet')}"
                    )
            for e in byid.values():
                if e["src"] and e["dst"]:
                    e["how"] = "bound"
            W, H = max(ext[0], 1e-6), max(ext[1], 1e-6)
            g["pages"].append(
                {"id": page, "name": pnames.get(k), "w": W, "h": H, "y_up": True}
            )
            resolve_geometric(g, page, W, H)
            attach_flow_markers(g, page, W, H)
            find_legend(g, page, W, H)
    g["notes"].append(
        "Visio y-axis points up; bboxes are in inches. Cells not set on a shape are inherited from its master (marked 'inherit')."
    )
    return finish(g)


# ============================================================ drawio + mermaid
def _drawio_models(path: Path):
    root = etree.parse(
        str(path), etree.XMLParser(recover=True, huge_tree=True)
    ).getroot()  # hand-edited drawio files carry bare '&'
    for i, d in enumerate(root.iter("diagram"), 1):
        m = d.find("mxGraphModel")
        if m is None and (d.text or "").strip():
            raw = zlib.decompress(base64.b64decode(d.text.strip()), -15)
            m = etree.fromstring(
                urllib.parse.unquote(raw.decode("utf-8")).encode("utf-8")
            )
        if m is not None:
            yield f"p{i}", d.get("name"), m
    if root.tag == "mxGraphModel":
        yield "p1", None, root


def read_drawio(path: Path) -> dict:
    g = new_graph("drawio", path)
    for page, name, model in _drawio_models(path):
        cells = {c.get("id"): c for c in model.iter("mxCell")}
        absxy = {}

        def origin(cid):
            if cid in absxy:
                return absxy[cid]
            c = cells.get(cid)
            if c is None or c.get("vertex") != "1":
                return (0.0, 0.0)
            geo = c.find("mxGeometry")
            px, py = origin(c.get("parent"))
            xy = (
                (px + float(geo.get("x", 0)), py + float(geo.get("y", 0)))
                if geo is not None
                else (px, py)
            )
            absxy[cid] = xy
            return xy

        W = H = 1.0
        for cid, c in cells.items():
            st = dict(
                kv.split("=", 1) if "=" in kv else (kv, "1")
                for kv in (c.get("style") or "").split(";")
                if kv
            )
            text = re.sub(
                r"<[^>]+>", " ", htmlmod.unescape(c.get("value") or "")
            ).strip()
            geo = c.find("mxGeometry")
            if c.get("vertex") == "1" and geo is not None:
                x, y = origin(cid)
                w, h = float(geo.get("width", 0)), float(geo.get("height", 0))
                W, H = max(W, x + w), max(H, y + h)
                kind = next(
                    (
                        k
                        for k in (
                            "ellipse",
                            "rhombus",
                            "swimlane",
                            "text",
                            "triangle",
                            "cylinder",
                        )
                        if k in st
                    ),
                    st.get("shape", "rect"),
                )
                g["nodes"].append(
                    {
                        "id": f"{page}:{cid}",
                        "page": page,
                        "kind": kind,
                        "text": re.sub(r"\s+", " ", text)[:300],
                        "fill": st.get("fillColor", "default"),
                        "line": st.get("strokeColor", "default"),
                        "dash": "dash" if st.get("dashed") == "1" else "solid",
                        "bbox": [x, y, w, h],
                        "group": None,
                    }
                )
            elif c.get("edge") == "1":
                px, py = origin(c.get("parent"))
                pts = {
                    p.get("as"): (px + float(p.get("x", 0)), py + float(p.get("y", 0)))
                    for p in (geo.iter("mxPoint") if geo is not None else [])
                    if p.get("as")
                }
                head = st.get("startArrow", "none") != "none"
                tail = (
                    st.get("endArrow", "classic") != "none"
                )  # drawio default edge has an end arrow
                e = {
                    "id": f"{page}:{cid}",
                    "page": page,
                    "kind": st.get("edgeStyle", "straight"),
                    "p0": pts.get("sourcePoint"),
                    "p1": pts.get("targetPoint"),
                    "colour": st.get("strokeColor", "default"),
                    "dash": "dash" if st.get("dashed") == "1" else "solid",
                    "width": st.get("strokeWidth"),
                    "direction": direction(head, tail),
                    "src": f"{page}:{c.get('source')}" if c.get("source") else None,
                    "dst": f"{page}:{c.get('target')}" if c.get("target") else None,
                    "group": None,
                    "label": re.sub(r"\s+", " ", text)[:120],
                }
                e["how"] = "bound" if e["src"] and e["dst"] else "pending"
                g["edges"].append(e)
        xs = [
            v
            for n in g["nodes"]
            if n["page"] == page and n.get("bbox")
            for v in (n["bbox"][0], n["bbox"][0] + n["bbox"][2])
        ]
        ys = [
            v
            for n in g["nodes"]
            if n["page"] == page and n.get("bbox")
            for v in (n["bbox"][1], n["bbox"][1] + n["bbox"][3])
        ]
        x0, y0 = (min(xs), min(ys)) if xs else (0.0, 0.0)
        W, H = (max(xs) - x0, max(ys) - y0) if xs else (1.0, 1.0)
        g["pages"].append(
            {"id": page, "name": name, "w": W, "h": H, "x0": x0, "y0": y0}
        )
        # attached drawio edges store no coordinates (drawio routes them at render): use the end shapes' centres
        box = {
            n["id"]: n["bbox"]
            for n in g["nodes"]
            if n["page"] == page and n.get("bbox")
        }
        for e in g["edges"]:
            if e["page"] == page:
                for end, key in (("p0", "src"), ("p1", "dst")):
                    if not e.get(end) and e.get(key) in box:
                        b = box[e[key]]
                        e[end] = (b[0] + b[2] / 2, b[1] + b[3] / 2)
        resolve_geometric(g, page, W, H)
        attach_flow_markers(g, page, W, H)
        find_legend(g, page, W, H)
    return finish(g)


def read_mermaid(path: Path) -> dict:
    g = new_graph("mermaid", path)
    g["pages"].append({"id": "p1", "w": None, "h": None})
    s = path.read_text("utf-8", "replace")
    labels = {}
    for nid, lab in re.findall(r"\b([A-Za-z_][\w-]*)\s*[\[\(\{>]+\"?([^\]\)\}\"]+)", s):
        labels.setdefault(
            nid,
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", htmlmod.unescape(lab))).strip(),
        )
    arrow = r"(-{2,3}>|-\.->|={2,3}>|<-->|-{3}|<-->|--o|--x)"
    for a, ar, lab, b in re.findall(
        r"\b([A-Za-z_][\w-]*)[^\s-]*\s*"
        + arrow
        + r"\s*(?:\|([^|]*)\|)?\s*([A-Za-z_][\w-]*)",
        s,
    ):
        for n in (a, b):
            if not any(x["id"] == f"p1:{n}" for x in g["nodes"]):
                g["nodes"].append(
                    {
                        "id": f"p1:{n}",
                        "page": "p1",
                        "kind": "mermaid",
                        "text": labels.get(n, n),
                        "bbox": None,
                        "group": None,
                    }
                )
        g["edges"].append(
            {
                "id": f"p1:{a}->{b}:{len(g['edges'])}",
                "page": "p1",
                "kind": "mermaid",
                "src": f"p1:{a}",
                "dst": f"p1:{b}",
                "how": "bound",
                "direction": (
                    "both"
                    if ar.startswith("<")
                    else "none" if ar == "---" else "forward"
                ),
                "colour": None,
                "dash": "dash" if "." in ar else "solid",
                "label": lab.strip(),
                "group": None,
            }
        )
    return finish(g)


# ============================================================ outputs
def keb_candidates(g: dict) -> list[dict]:
    """Mycelium level only: candidate links with their evidence. Nothing here is accepted.
    relation stays DEFER unless an in-drawing legend or the owner registry types the style; an arrow is a drawn mark, not a flow.
    Promotion to the golden thread needs evidence and an authority (tools/thread_promote.py).
    """
    nodes = {n["id"]: n for n in g["nodes"]}
    out = []
    for e in g["edges"]:
        A, B = nodes.get(e.get("src")), nodes.get(e.get("dst"))
        if (
            e["how"] in ("bound", "geometric")
            and A
            and B
            and A.get("text")
            and B.get("text")
        ):
            if e["direction"] == "backward":
                A, B = B, A
            arrow = e["direction"] in ("forward", "backward")
            out.append(
                {
                    "object_type": "KEB_KNOWLEDGE_ATOM",
                    "level": "mycelium",
                    "candidate": True,
                    "statement": f"{A['text'][:80]} {'->' if arrow else '--'} {B['text'][:80]}",
                    "relation": e.get("semantic_type", "DEFER"),
                    "semantic_source": e.get("semantic_source"),
                    "drawn": e.get("drawn"),
                    "drawn_direction": e["direction"],
                    "evidence": e.get("evidence"),
                    "from": {"locator": A["locator"], "eq": A.get("eq_candidates", [])},
                    "to": {"locator": B["locator"], "eq": B.get("eq_candidates", [])},
                    "label": e.get("label") or None,
                    "source_locator": e["locator"],
                    "source_digest": g["sha256"],
                    "source_repo": None,
                    "source_pr": None,
                    "source_sha": None,
                    "replay_status": "NOT_RUN",
                    "validation_result": "UNVALIDATED",
                    "promotion": (
                        "needs evidence + authority"
                        if e["how"] == "bound"
                        else "needs reviewer confirmation (geometry only)"
                    ),
                }
            )
    return out


def redraw(g: dict, page: str, out: Path) -> Path | None:
    """Redraw one page from the extracted graph only: proves what the reader understood (boxes, text, arrows)."""
    pg = next((p for p in g["pages"] if p["id"] == page), None)
    if not pg or not pg.get("w"):
        return None
    W, H = pg["w"], pg["h"]
    X0, Y0, up = pg.get("x0", 0.0), pg.get("y0", 0.0), pg.get("y_up", False)
    k = 1200 / W
    tx = lambda x: (x - X0) * k  # noqa: E731
    ty = lambda y: (H - (y - Y0)) * k if up else (y - Y0) * k  # noqa: E731
    col = {
        "bound": "#1f7a3d",
        "geometric": "#0f6bb5",
        "half": "#c77700",
        "unresolved": "#b3261e",
        "flow_marker": "#7a3db3",
    }
    nodes = {n["id"]: n for n in g["nodes"] if n["page"] == page}
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 {H * k:.0f}" font-family="Segoe UI,Arial" font-size="9">',
        '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0L10,5L0,10z" fill="context-stroke"/></marker></defs>',
        f'<rect width="1200" height="{H * k:.0f}" fill="white"/>',
    ]
    for n in nodes.values():
        if n["kind"] == "group" or not n.get("bbox"):
            continue
        bx, by, bw, bh = n["bbox"]
        x, w, h = tx(bx), bw * k, bh * k
        y = ty(by + bh) if up else ty(by)
        fill = n.get("fill") if (n.get("fill") or "").startswith("#") else "none"
        s.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" fill-opacity="0.35" stroke="#555" stroke-width="0.6"/>'
        )
        if n.get("text"):
            s.append(
                f'<text x="{x + 2:.1f}" y="{y + 10:.1f}">{htmlmod.escape(n["text"][:40])}</text>'
            )
    for e in (e for e in g["edges"] if e["page"] == page and e.get("p0")):
        (x0, y0), (x1, y1) = e["p0"], e["p1"]
        if e["direction"] == "backward":
            x0, y0, x1, y1 = x1, y1, x0, y0
        mk = ' marker-end="url(#a)"' if e["direction"] != "none" else ""
        dash = (
            ' stroke-dasharray="4 3"' if e.get("dash") not in ("solid", None) else ""
        )  # kept outside the f-string: 3.11-safe
        colour = col[e["how"]]
        s.append(
            f'<line x1="{tx(x0):.1f}" y1="{ty(y0):.1f}" x2="{tx(x1):.1f}" y2="{ty(y1):.1f}" stroke="{colour}" stroke-width="1.6"'
            f"{dash}{mk}/>"
        )
    s.append(
        f'<text x="8" y="{H * k - 8:.0f}" font-size="11">green = attached in file · blue = resolved by geometry · orange = one end · red = unresolved</text></svg>'
    )
    out.write_text("\n".join(s), "utf-8")
    return out


READERS = {
    ".pptx": read_pptx,
    ".pptm": read_pptx,
    ".svg": read_svg,
    ".html": read_html,
    ".htm": read_html,
    ".vsdx": read_vsdx,
    ".drawio": read_drawio,
    ".mmd": read_mermaid,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument(
        "--redraw",
        action="store_true",
        help="redraw the richest page of each file from the extracted graph",
    )
    ap.add_argument(
        "--root-id",
        help="pick every drawing in this root from its probe (pipeline mode)",
    )
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    files = list(map(Path, a.files))
    if a.root_id:
        from estate_spec import ROOTS, inv_dir

        root, inv = ROOTS[a.root_id][0], inv_dir(a.root_id)
        pick = {
            "VSDX": lambda r: "error" not in r,
            "SVG": lambda r: "error" not in r,
            "PPTX": lambda r: r.get("total_connectors", 0) >= 20,
            "HTML": lambda r: r.get("svg_inline", 0) > 0,
        }
        for t, ok in pick.items():
            p = inv / "probe" / f"{t}.jsonl"
            if p.exists():
                files += [
                    root / r["name"]
                    for r in map(
                        json.loads, filter(str.strip, p.read_text("utf-8").split("\n"))
                    )
                    if ok(r) and (root / r["name"]).exists()
                ]
    summary = []
    atoms = []
    for f in files:
        if f.suffix.lower() not in READERS:
            continue
        try:
            g = READERS[f.suffix.lower()](f)
        except (
            Exception
        ) as exc:  # one bad drawing must not stop the batch; it is reported
            print(f"{f.name[:58]:58} ERROR {type(exc).__name__}: {str(exc)[:100]}")
            summary.append(
                {"file": f.name, "error": f"{type(exc).__name__}: {exc}"[:200]}
            )
            continue
        summary.append({"file": f.name, "format": g["format"], **g["qa"]})
        g = READERS[f.suffix.lower()](f)
        stem = re.sub(r"[^\w.-]+", "_", f.stem)[:60]
        (OUT / f"{stem}{f.suffix.lower()}.graph.json").write_text(
            json.dumps(g, ensure_ascii=False, default=list), "utf-8"
        )
        ka = keb_candidates(g)
        (OUT / f"{stem}{f.suffix.lower()}.keb.jsonl").write_text(
            "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in ka), "utf-8"
        )
        q = g["qa"]
        print(
            f"{f.name[:58]:58} {g['format']:7} pages={q['pages']:3} nodes={q['nodes']:5} edges={q['edges']:4} bound={q['bound_pct']:5}% "
            f"geom={q['geometric_pct']:5}% half={q['half_pct']:5}% unres={q['unresolved_pct']:5}% marker={q['flow_marker_pct']:5}% "
            f"directed={q['directed_pct']:5}% (+{q['direction_from_markers']} via markers) "
            f"legend={q['legend_entries']}/{q['legend_applied']} atoms={len(ka)}"
        )
        for n in g["notes"][:3]:
            print("      note:", n[:150])
        if a.redraw and g["edges"]:
            best = collections.Counter(
                e["page"] for e in g["edges"] if e.get("p0")
            ).most_common(1)
            if best:
                r = redraw(
                    g,
                    best[0][0],
                    OUT / f"{stem}{f.suffix.lower()}.{best[0][0]}.redraw.svg",
                )
                if r:
                    print("      redraw:", r.relative_to(EST))
    tag = a.root_id or "adhoc"
    (OUT / f"DEEP_SUMMARY_{tag}.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False), "utf-8"
    )
    # legend candidates for owner review (never applied outside their own drawing until accepted in LEGEND_REGISTRY.yaml)
    cands = []
    for gf in sorted(OUT.glob("*.graph.json")):
        gg_ = json.loads(gf.read_text("utf-8"))
        for lg in gg_.get("legend", []):
            cands.append(
                {
                    "file": gg_["file"],
                    "page": lg["page"],
                    "entries": [
                        {"style": en["style"], "meaning": en["meaning"]}
                        for en in lg["entries"]
                    ],
                }
            )
    (OUT / "legend_candidates.json").write_text(
        json.dumps(cands, indent=1, ensure_ascii=False), "utf-8"
    )
    for kf in sorted(
        OUT.glob("*.keb.jsonl")
    ):  # aggregate every file read so far, not only this run
        atoms += [json.loads(l) for l in kf.read_text("utf-8").split("\n") if l.strip()]
    with (OUT / "keb_candidates.jsonl").open("w", encoding="utf-8") as fh:
        for x in atoms:
            fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    print(f"KEB candidate atoms: {len(atoms)} -> deep/keb_candidates.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
