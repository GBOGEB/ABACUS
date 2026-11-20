"""Reference tests for the drawing reader (E mode). Numbers, not impressions.

R1 answer key   a Mermaid file with all links declared (reference.answer_key) scores other renderings of the same diagram: nodes matched, key edges found,
                direction right. Caveat: the .mmd may be another revision; a miss is a finding to check, not proof of a bug.
R2 crosswalk    a configured pair of files (reference.crosswalk) joined on stable-ID candidates (eq:<tag>), never on file IDs.
R3 adversarial  synthetic drawings that must NOT produce a confident answer: dangling arrow, touching boxes without a line,
                paragraph posing as a legend, dashed line without legend, legend with one style -> two meanings,
                raster-wrapped SVG, raster-only PNG.
R4 read-only    sha256 of every input before and after reading must be unchanged.
R5 pilot        hand-labelled set (pilot/PILOT_MANIFEST.yaml). Label templates are generated UNREVIEWED; gates score only
                REVIEWED labels. Until the owner labels them the result is DEFER, never PASS.

    python -I -X utf8 DMAIC_V3/binary_engines/reference_test.py
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deep_graph as dg  # noqa: E402
from estate_spec import CONFIG, ESTATE, ROOTS  # noqa: E402
from ggmath_bridge import load as _load_kernel  # noqa: E402

SS = _load_kernel(
    "set_similarity"
)  # gg_MATH kernels/set_similarity.py, pinned in ggmath_bridge.PINS

EST = ESTATE

REF = (
    CONFIG.get("reference") or {}
)  # answer key and crosswalk pair come from the configuration, never from code
FIX = EST / "fixtures" / "adversarial"
PILOT = EST / "pilot"
OUT = EST / "deep"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def toks(t: str) -> set[str]:
    return set(SS.words(t, r"[a-z0-9]+"))


def match_nodes(key_nodes, cand_nodes):
    """Each answer-key node -> the candidate node whose text covers most of its words (>= 60 %)."""
    m = {}
    for k in key_nodes:
        kt = toks(k["text"])
        if not kt:
            continue
        best = max(
            cand_nodes,
            key=lambda c: SS.containment(kt, toks(c.get("text"))),
            default=None,
        )
        if best and SS.containment(kt, toks(best.get("text"))) >= 0.6:
            m[k["id"]] = best["id"]
    return m


def cfg_path(item: dict) -> Path:
    return ROOTS[item["root"]][0] / item["file"]


def r1_answer_key() -> dict:
    ak = REF.get("answer_key")
    if not ak:
        return {
            "result": "DEFER",
            "why": "no answer_key configured (reference.answer_key)",
        }
    root = ROOTS[ak["root"]][0]
    key = dg.read_mermaid(root / ak["key"])
    res = {}
    for f in ak.get("candidates", []):
        g = dg.READERS[Path(f).suffix.lower()](root / f)
        cands = [n for n in g["nodes"] if n.get("text")]
        m = match_nodes(key["nodes"], cands)
        # comparability gate: score only when the key describes the same drawing (>= 50 % of its labels are present)
        if len(m) < 0.5 * len(key["nodes"]):
            res[f] = {
                "result": "NOT_COMPARABLE",
                "why": f"only {len(m)}/{len(key['nodes'])} answer-key labels occur in this file: "
                "a different drawing or revision; no score",
                "capture": g.get("capture", "static"),
            }
            continue
        found = right = 0
        for e in key["edges"]:
            a, b = m.get(e["src"]), m.get(e["dst"])
            if not (a and b):
                continue
            hits = [
                x
                for x in g["edges"]
                if {x.get("src"), x.get("dst")} == {a, b}
                and x["how"] in ("bound", "geometric")
            ]
            if hits:
                found += 1
                h = hits[0]
                head_to_b = (h["src"] == a and h["direction"] == "forward") or (
                    h["dst"] == a and h["direction"] == "backward"
                )
                right += head_to_b
        n_k, e_k = len(key["nodes"]), len(key["edges"])
        res[f] = {
            "key_nodes": n_k,
            "nodes_matched": len(m),
            "key_edges": e_k,
            "edges_found": found,
            "direction_right": right,
            "node_match_pct": round(100 * len(m) / n_k, 1),
            "edge_recall_pct": round(100 * found / e_k, 1),
            "direction_pct_of_found": round(100 * right / found, 1) if found else None,
            "capture": g.get("capture", "static"),
        }
    return res


def r2_crosswalk() -> dict:
    cw = REF.get("crosswalk")
    if not cw:
        return {
            "verdict": "DEFER",
            "why": "no crosswalk pair configured (reference.crosswalk)",
            "shared_eq": 0,
        }
    file_a, file_b = cfg_path(cw["a"]), cfg_path(cw["b"])
    a = dg.READERS[file_a.suffix.lower()](file_a)
    b = dg.READERS[file_b.suffix.lower()](file_b)

    def eqs(g):
        return {e for n in g["nodes"] for e in n.get("eq_candidates", [])}

    def eq_pairs(g):
        nodes = {n["id"]: n for n in g["nodes"]}
        out = set()
        for e in g["edges"]:
            if e["how"] in ("bound", "geometric"):
                A, B = nodes.get(e["src"], {}), nodes.get(e["dst"], {})
                for x in A.get("eq_candidates", []):
                    for y in B.get("eq_candidates", []):
                        if x != y:
                            out.add(tuple(sorted((x, y))))
        return out

    ea, eb, pa, pb = eqs(a), eqs(b), eq_pairs(a), eq_pairs(b)
    verdict = (
        "SAME_DRAWING"
        if SS.overlap(ea, eb) >= 0.5
        else "NOT_COMPARABLE (disjoint equipment IDs)"
    )
    return {
        "pair": f"{file_a.name} vs {file_b.name}",
        "verdict": verdict,
        "svg_eq": len(ea),
        "vsdx_eq": len(eb),
        "shared_eq": len(ea & eb),
        "eq_jaccard": round(SS.jaccard(ea, eb), 3),
        "svg_links_by_eq": len(pa),
        "vsdx_links_by_eq": len(pb),
        "shared_links": len(pa & pb),
        "link_jaccard": round(SS.jaccard(pa, pb), 3),
        "sample_shared_eq": sorted(ea & eb)[:15],
        "only_svg": sorted(ea - eb)[:10],
        "only_vsdx": sorted(eb - ea)[:10],
    }


SVG_HEAD = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"><defs><marker id="m" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0L10,5L0,10z"/></marker></defs>'
BOXES = '<rect x="20" y="80" width="60" height="40" fill="#ddd" stroke="#000"/><text x="30" y="105">PUMP P-101</text><rect x="300" y="80" width="60" height="40" fill="#ddd" stroke="#000"/><text x="310" y="105">TANK T-201</text>'
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def r3_adversarial() -> list[dict]:
    FIX.mkdir(parents=True, exist_ok=True)
    cases = {
        "dangling_arrow.svg": (
            SVG_HEAD
            + BOXES
            + '<line x1="80" y1="100" x2="190" y2="100" stroke="#000" marker-end="url(#m)"/></svg>',
            lambda g: not any(e["how"] == "geometric" for e in g["edges"]),
            "an arrow ending in empty space is not a link",
        ),
        "touching_no_line.svg": (
            SVG_HEAD
            + '<rect x="20" y="80" width="60" height="40" fill="#ddd" stroke="#000"/><text x="30" y="105">A-101</text>'
            '<rect x="80" y="80" width="60" height="40" fill="#ddd" stroke="#000"/><text x="90" y="105">B-102</text></svg>',
            lambda g: not g["edges"],
            "touching shapes are not connected",
        ),
        "paragraph_legend.svg": (
            SVG_HEAD
            + BOXES
            + '<text x="20" y="20">Legend</text><line x1="20" y1="40" x2="50" y2="40" stroke="#c00"/>'
            '<text x="60" y="44">How to read this diagram before you start and what every line style could mean in general</text></svg>',
            lambda g: sum(len(l["entries"]) for l in g["legend"]) == 0,
            "a paragraph next to a symbol is not a legend meaning",
        ),
        "dashed_no_legend.svg": (
            SVG_HEAD
            + BOXES
            + '<line x1="80" y1="100" x2="300" y2="100" stroke="#000" stroke-dasharray="4 3" marker-end="url(#m)"/></svg>',
            lambda g: all(e.get("semantic_type") == "DEFER" for e in g["edges"])
            and any(e["how"] == "geometric" for e in g["edges"]),
            "a dashed arrow links P-101 to T-201 but its meaning stays DEFER",
        ),
        "conflicting_legend.svg": (
            SVG_HEAD + BOXES + '<text x="20" y="20">Legend</text>'
            '<line x1="20" y1="40" x2="50" y2="40" stroke="#00c"/><text x="60" y="44">signal</text>'
            '<line x1="20" y1="60" x2="50" y2="60" stroke="#00c"/><text x="60" y="64">power</text>'
            '<line x1="80" y1="100" x2="300" y2="100" stroke="#00c"/></svg>',
            lambda g: all(
                e.get("semantic_type") == "DEFER"
                for e in g["edges"]
                if e["how"] == "geometric"
            ),
            "one style with two legend meanings stays DEFER",
        ),
        "raster_wrapped.svg": (
            SVG_HEAD
            + '<image x="0" y="0" width="400" height="200" href="data:image/png;base64,'
            + base64.b64encode(PNG_1PX).decode()
            + '"/></svg>',
            lambda g: any("RASTER-WRAPPED" in n for n in g["notes"]) and not g["edges"],
            "an embedded picture is flagged, not read as vectors",
        ),
    }
    out = []
    for name, (svg, ok, why) in cases.items():
        p = FIX / name
        p.write_text(svg, "utf-8")
        g = dg.read_svg(p)
        out.append(
            {
                "case": name,
                "expect": why,
                "result": "PASS" if ok(g) else "FAIL",
                "edges": len(g["edges"]),
                "how": sorted({e["how"] for e in g["edges"]}),
                "semantic": sorted({e.get("semantic_type") for e in g["edges"]}),
            }
        )
    png = FIX / "raster_only.png"
    png.write_bytes(PNG_1PX)
    out.append(
        {
            "case": png.name,
            "expect": "a raster-only PNG has no reader: UNSUPPORTED, never a guessed graph",
            "result": "PASS" if png.suffix not in dg.READERS else "FAIL",
            "edges": 0,
            "how": [],
            "semantic": [],
        }
    )
    return out


def pilot_files() -> list[dict]:
    """Hand-labelled pilot set from the configuration (pilot: [{role, root, file, page}]); missing files are skipped."""
    out = []
    for p in CONFIG.get("pilot") or []:
        path = cfg_path(p)
        if path.exists():
            out.append({"role": p["role"], "path": path, "page": p.get("page")})
    return out


def r2b_discover() -> list[dict]:
    """Find drawings that really are the same object in different files/formats: by shared equipment-ID candidates,
    not by file name. These pairs are the crosswalk test set."""
    sets = {}
    for gf in OUT.glob("*.graph.json"):
        g = json.loads(gf.read_text("utf-8"))
        eq = {e for n in g["nodes"] for e in n.get("eq_candidates", [])}
        if len(eq) >= 5:
            sets[(g["file"], g["format"])] = eq
    keys = sorted(sets)
    out = []
    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            if a[0] == b[0]:
                continue
            inter = sets[a] & sets[b]
            score = SS.overlap(sets[a], sets[b])
            if score >= 0.5 and len(inter) >= 5:
                out.append(
                    {
                        "a": a[0],
                        "a_format": a[1],
                        "b": b[0],
                        "b_format": b[1],
                        "shared_eq": len(inter),
                        "overlap": round(score, 2),
                        "cross_format": a[1] != b[1],
                    }
                )
    return sorted(
        out, key=lambda x: (-x["cross_format"], -x["overlap"], -x["shared_eq"])
    )[:30]


def r2c_links(p: dict) -> dict:
    """On a discovered same-drawing pair: do both files connect the same equipment? (links joined on eq IDs, both directions)."""

    def load(name, fmt):
        for gf in OUT.glob("*.graph.json"):
            g = json.loads(gf.read_text("utf-8"))
            if g["file"] == name and g["format"] == fmt:
                return g
        return None

    def links(g):
        nodes = {n["id"]: n for n in g["nodes"]}
        s = set()
        for e in g["edges"]:
            if e["how"] in ("bound", "geometric"):
                for x in nodes.get(e["src"], {}).get("eq_candidates", []):
                    for y in nodes.get(e["dst"], {}).get("eq_candidates", []):
                        if x != y:
                            s.add(tuple(sorted((x, y))))
        return s

    A, B = load(p["a"], p["a_format"]), load(p["b"], p["b_format"])
    la, lb = links(A), links(B)
    return {
        "pair": f"{p['a']} ({p['a_format']}) <-> {p['b']} ({p['b_format']})",
        "links_a": len(la),
        "links_b": len(lb),
        "shared": len(la & lb),
        "link_jaccard": round(SS.jaccard(la, lb), 3),
        "sample_shared": [" -- ".join(x) for x in sorted(la & lb)[:6]],
        "sample_only_a": [" -- ".join(x) for x in sorted(la - lb)[:4]],
    }


def r5_pilot(graphs: dict) -> list[dict]:
    (PILOT / "labels").mkdir(parents=True, exist_ok=True)
    res = []
    for pf in pilot_files():
        p, page = pf["path"], pf["page"]
        if p.suffix.lower() not in dg.READERS:
            res.append(
                {
                    "file": p.name,
                    "role": pf["role"],
                    "result": "PASS",
                    "why": "control: no reader for raster, reported UNSUPPORTED (needs the vision lane), no guessed graph",
                }
            )
            continue
        lab = (
            PILOT / "labels" / (re.sub(r"[^\w.-]+", "_", p.stem)[:50] + ".labels.json")
        )
        g = graphs.get(p)
        if not lab.exists():
            tpl = {
                "file": p.name,
                "sha256": sha(p),
                "page": page,
                "role": pf["role"],
                "status": "UNREVIEWED",
                "how_to": "For each object set truth to ACCEPT or REJECT; for each edge set truth ACCEPT/REJECT and direction "
                "(forward = from -> to, backward, none). Add missed objects/edges under 'missing'. Then set status REVIEWED.",
                "objects": [
                    {
                        "locator": n["locator"],
                        "text": n.get("text", "")[:80],
                        "eq": n.get("eq_candidates", []),
                        "truth": "UNREVIEWED",
                    }
                    for n in (g["nodes"] if g else [])
                    if n["page"] == page and n["kind"] not in ("group",)
                ][:400],
                "edges": [
                    {
                        "locator": e["locator"],
                        "from": e.get("src"),
                        "to": e.get("dst"),
                        "evidence": e.get("evidence"),
                        "drawn_direction": e["direction"],
                        "truth": "UNREVIEWED",
                        "direction": None,
                    }
                    for e in (g["edges"] if g else [])
                    if e["page"] == page
                ][:600],
                "missing": [],
            }
            lab.write_text(json.dumps(tpl, indent=1, ensure_ascii=False), "utf-8")
        L = json.loads(lab.read_text("utf-8"))
        if L.get("status") != "REVIEWED":
            res.append(
                {
                    "file": p.name,
                    "role": pf["role"],
                    "result": "DEFER",
                    "why": "labels not reviewed by the owner yet",
                    "labels": str(lab.relative_to(EST)),
                }
            )
            continue
        # reviewed labels are scored against the graph read now, never against themselves: a label file
        # for other input bytes, or accepted objects/edges the reader no longer produces, must FAIL
        if L.get("sha256") != sha(p):
            res.append(
                {
                    "file": p.name,
                    "role": pf["role"],
                    "result": "FAIL",
                    "why": "labels were reviewed against other input bytes (sha256 mismatch); re-review",
                    "labels": str(lab.relative_to(EST)),
                }
            )
            continue
        cur_nodes = {
            n["locator"]
            for n in (g["nodes"] if g else [])
            if n["page"] == page and n["kind"] not in ("group",)
        }
        cur_edges = {
            e["locator"]: e for e in (g["edges"] if g else []) if e["page"] == page
        }
        objs = L["objects"]
        acc_edges = [e for e in L["edges"] if e["truth"] == "ACCEPT"]
        accounted = sum(o["truth"] in ("ACCEPT", "REJECT") for o in objs) / max(
            len(objs), 1
        )
        dropped_objects = [
            o["locator"]
            for o in objs
            if o["truth"] == "ACCEPT" and o["locator"] not in cur_nodes
        ]
        dropped_edges = [
            e["locator"] for e in acc_edges if e["locator"] not in cur_edges
        ]
        dir_ok = sum(
            e["locator"] in cur_edges
            and e["direction"] == cur_edges[e["locator"]]["direction"]
            for e in acc_edges
        ) / max(len(acc_edges), 1)
        res.append(
            {
                "file": p.name,
                "role": pf["role"],
                "objects_accounted_pct": round(100 * accounted, 1),
                "accepted_edges_direction_pct": round(100 * dir_ok, 1),
                "accepted_objects_not_in_graph": len(dropped_objects),
                "accepted_edges_not_in_graph": len(dropped_edges),
                "missing": len(L.get("missing", [])),
                "result": (
                    "PASS"
                    if accounted == 1
                    and dir_ok == 1
                    and not dropped_objects
                    and not dropped_edges
                    and not L.get("missing")
                    else "FAIL"
                ),
            }
        )
    return res


def main() -> int:
    inputs = [pf["path"] for pf in pilot_files()]
    if REF.get("answer_key"):
        ak = REF["answer_key"]
        inputs += [
            ROOTS[ak["root"]][0] / f for f in [ak["key"], *ak.get("candidates", [])]
        ]
    if REF.get("crosswalk"):
        inputs += [cfg_path(REF["crosswalk"]["a"]), cfg_path(REF["crosswalk"]["b"])]
    inputs = list(dict.fromkeys(p for p in inputs if p.exists()))
    before = {str(p): sha(p) for p in inputs}
    graphs = {
        pf["path"]: dg.READERS[pf["path"].suffix.lower()](pf["path"])
        for pf in pilot_files()
        if pf["path"].suffix.lower() in dg.READERS
    }
    pairs = r2b_discover()
    report = {
        "R1_answer_key": r1_answer_key(),
        "R2_crosswalk": r2_crosswalk(),
        "R2b_same_drawing_pairs": pairs,
        "R2c_links_on_discovered_pairs": [
            r2c_links(p) for p in pairs if p["cross_format"]
        ][:5],
        "R3_adversarial": r3_adversarial(),
        "R5_pilot": r5_pilot(graphs),
    }
    after = {str(p): sha(p) for p in inputs}
    report["R4_read_only"] = {
        "files": len(before),
        "changed": [k for k in before if before[k] != after[k]],
        "result": "PASS" if before == after else "FAIL",
    }
    import yaml  # a real serializer: a page-less file gets YAML null, never the string "None"

    manifest = {
        "schema": "gbogeb.estate.pilot/0.1",
        "files": [
            {
                "role": pf["role"],
                "file": pf["path"].name,
                "page": pf["page"],
                "sha256": before.get(str(pf["path"])) or sha(pf["path"]),
            }
            for pf in pilot_files()
        ],
    }
    (PILOT / "PILOT_MANIFEST.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), "utf-8"
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "REFERENCE_TESTS.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False, default=str), "utf-8"
    )
    print(
        json.dumps(
            {k: v for k, v in report.items() if k != "R3_adversarial"},
            indent=1,
            ensure_ascii=False,
            default=str,
        )[:3500]
    )
    for c in report["R3_adversarial"]:
        print(f"  R3 {c['result']:4} {c['case']:24} {c['expect']}")
    hard_fail = report["R4_read_only"]["result"] == "FAIL" or any(
        c["result"] == "FAIL" for c in report["R3_adversarial"]
    )
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
