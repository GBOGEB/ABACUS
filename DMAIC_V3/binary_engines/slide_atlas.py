"""Slide atlas: every slide of every deck in the real roots, compared across decks.

Per slide: title, words, shapes, text boxes, pictures, tables, charts, groups, connectors, fonts, font sizes,
colours (hard-coded vs theme), layout, image reuse, a layout fingerprint and a text fingerprint.
Across slides:
  EXACT_COPY  same text, same layout, same colours          -> the same slide pasted into another deck
  RESTYLED    same text, different layout or colours         -> look changed, content did not
  EDITED      60-99 % of the wording shared (MinHash + LSH)   -> remade slide: a before / after pair to choose from
  families    connected slides (union-find); the newest deck's version is the tip
Style flags per slide: DENSE, SMALL_FONT, FONT_SPRAWL, COLOUR_SPRAWL, HARDCODED_COLOUR, OFF_SLIDE.
Writes deep/slide_atlas.json, deep/SLIDE_ATLAS.md and deep/COMPARE.html (static; choices are exported as JSON).

    python -I -X utf8 DMAIC_V3/binary_engines/slide_atlas.py
"""

from __future__ import annotations

import collections
import hashlib
import html
import json
import re
import statistics
import sys
import zipfile
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estate_spec import ESTATE, REAL_ROOTS, ROOTS, inv_dir  # noqa: E402
from ggmath_bridge import load as _load_kernel  # noqa: E402

EST = ESTATE

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
RELNS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
ROOT_IDS = tuple(
    r for r in REAL_ROOTS if ROOTS[r][1] != "light"
)  # light roots are not probed
N_HASH, BANDS = (
    48,
    16,
)  # MinHash size and LSH bands (3 rows each): finds pairs above ~0.5 Jaccard
LIMITS = {
    "DENSE_WORDS": 120,
    "DENSE_BOXES": 12,
    "SMALL_PT": 10,
    "FONTS": 3,
    "COLOURS": 6,
}
SS = _load_kernel(
    "set_similarity"
)  # gg_MATH kernels/set_similarity.py, pinned in ggmath_bridge.PINS


norm_words = SS.words  # lower-case word tokens, one decimal part kept


def minhash(sh: set[int]) -> tuple[int, ...]:
    return SS.minhash(sh, N_HASH)  # seeded MinHash, identical on every platform


def read_deck(path: Path, deck_id: str) -> list[dict]:
    out = []
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        pres = etree.fromstring(zf.read("ppt/presentation.xml"))
        sz = pres.find("p:sldSz", NS)
        W, H = int(sz.get("cx")), int(sz.get("cy"))
        # slide order comes from presentation.xml (sldIdLst -> rels), not from file names
        prels = {
            r.get("Id"): r.get("Target")
            for r in etree.fromstring(zf.read("ppt/_rels/presentation.xml.rels")).iter(
                RELNS + "Relationship"
            )
        }
        order = [
            prels[s.get("{%s}id" % NS["r"])]
            for s in pres.iterfind("p:sldIdLst/p:sldId", NS)
        ]
        media = {
            i.filename: f"{i.CRC:08x}-{i.file_size}"
            for i in zf.infolist()
            if i.filename.startswith("ppt/media/")
        }
        for idx, target in enumerate(order, 1):
            sn = "ppt/" + target.lstrip("/").replace("../", "")
            if sn not in names:
                continue
            root = etree.fromstring(zf.read(sn))
            relp = sn.replace("slides/", "slides/_rels/") + ".rels"
            rels = (
                {
                    r.get("Id"): r.get("Target")
                    for r in etree.fromstring(zf.read(relp)).iter(
                        RELNS + "Relationship"
                    )
                }
                if relp in names
                else {}
            )
            layout = ""
            lay = next((t for t in rels.values() if "slideLayout" in t), None)
            if lay:
                ln = "ppt/slideLayouts/" + lay.split("/")[-1]
                if ln in names:
                    c = etree.fromstring(zf.read(ln)).find("p:cSld", NS)
                    layout = c.get("name", "") if c is not None else ""
            imgs = sorted(
                media.get("ppt/media/" + t.split("/")[-1], "")
                for t in rels.values()
                if "media/" in t
            )
            out.append(slide_facts(root, W, H, deck_id, idx, layout, imgs))
    return out


def slide_facts(root, W, H, deck_id, idx, layout, imgs) -> dict:
    tree = root.find(".//p:cSld/p:spTree", NS)
    shapes, title, chrome = [], "", []
    k = dict(sp=0, txbox=0, pic=0, tbl=0, chart=0, grp=0, cxn=0, off=0)
    for el in tree:
        tag = etree.QName(el).localname
        if tag not in ("sp", "pic", "graphicFrame", "grpSp", "cxnSp"):
            continue
        k[
            {
                "sp": "sp",
                "pic": "pic",
                "graphicFrame": (
                    "tbl" if el.find(".//a:tbl", NS) is not None else "chart"
                ),
                "grpSp": "grp",
                "cxnSp": "cxn",
            }[tag]
        ] += 1
        x = (
            el.find("p:spPr/a:xfrm", NS)
            if tag in ("sp", "pic", "cxnSp")
            else (
                el.find("p:grpSpPr/a:xfrm", NS)
                if tag == "grpSp"
                else el.find("p:xfrm", NS)
            )
        )
        bbox = None
        if (
            x is not None
            and x.find("a:off", NS) is not None
            and x.find("a:ext", NS) is not None
        ):
            o, e = x.find("a:off", NS), x.find("a:ext", NS)
            bbox = [
                float(o.get("x")) / W,
                float(o.get("y")) / H,
                float(e.get("cx")) / W,
                float(e.get("cy")) / H,
            ]  # some generators write floats
            if (
                bbox[0] < -0.02
                or bbox[1] < -0.02
                or bbox[0] + bbox[2] > 1.02
                or bbox[1] + bbox[3] > 1.02
            ):
                k["off"] += 1
        txt = " ".join(t.text or "" for t in el.iter("{%s}t" % NS["a"])).strip()
        ph = el.find("p:nvSpPr/p:nvPr/p:ph", NS)
        if ph is not None and ph.get("type") in ("title", "ctrTitle") and not title:
            title = txt
        if ph is not None and ph.get("type") in ("sldNum", "ftr", "dt"):
            chrome.append(
                txt
            )  # tuning rule S1: slide number / footer / date are not content
        if (
            tag == "sp"
            and el.find("p:nvSpPr/p:cNvSpPr", NS) is not None
            and el.find("p:nvSpPr/p:cNvSpPr", NS).get("txBox") == "1"
        ):
            k["txbox"] += 1
        fill = el.find("p:spPr/a:solidFill/a:srgbClr", NS)
        shapes.append(
            {
                "k": tag,
                "b": [round(v, 3) for v in bbox] if bbox else None,
                "f": "#" + fill.get("val") if fill is not None else None,
                "t": txt[:60],
            }
        )
    xml = etree.tostring(root).decode("utf-8", "ignore")
    text = " ".join(t.text or "" for t in root.iter("{%s}t" % NS["a"]))
    words = norm_words(text)
    for c in chrome:  # drop placeholder chrome once, so '8' vs '9' is not an edit
        for w in norm_words(c):
            if w in words:
                words.remove(w)
    fonts = sorted(set(re.findall(r'<a:latin typeface="([^"+][^"]*)"', xml)))
    sizes = [int(s) / 100 for s in re.findall(r'<a:rPr[^>]* sz="(\d+)"', xml)]
    srgb = sorted(set(re.findall(r'<a:srgbClr val="([0-9A-Fa-f]{6})"', xml)))
    scheme = len(re.findall(r"<a:schemeClr ", xml))
    layout_fp = hashlib.sha1(
        json.dumps(
            sorted((s["k"], *(round(v * 10) for v in s["b"])) for s in shapes if s["b"])
        ).encode(),
        usedforsecurity=False,
    ).hexdigest()[:12]
    shingles = SS.shingles(words, 3)  # CRC-32 of each 3-word window
    flags = [
        f
        for f, ok in (
            (
                "DENSE",
                len(words) > LIMITS["DENSE_WORDS"]
                or k["txbox"] > LIMITS["DENSE_BOXES"],
            ),
            ("SMALL_FONT", bool(sizes) and min(sizes) < LIMITS["SMALL_PT"]),
            ("FONT_SPRAWL", len(fonts) > LIMITS["FONTS"]),
            ("COLOUR_SPRAWL", len(srgb) > LIMITS["COLOURS"]),
            ("HARDCODED_COLOUR", len(srgb) > 0 and scheme == 0),
            ("OFF_SLIDE", k["off"] > 0),
        )
        if ok
    ]
    return {
        "deck": deck_id,
        "slide": idx,
        "title": title[:120],
        "layout": layout,
        "words": len(words),
        **k,
        "fonts": fonts,
        "size_min": min(sizes) if sizes else None,
        "size_med": statistics.median(sizes) if sizes else None,
        "colours": srgb,
        "theme_refs": scheme,
        "images": imgs,
        "flags": flags,
        "text_fp": hashlib.sha1(
            " ".join(words).encode(), usedforsecurity=False
        ).hexdigest()[:12],
        "layout_fp": layout_fp,
        "_mh": minhash(shingles),
        "_words": words,
        "_shapes": shapes,
    }


def main() -> int:
    decks, slides = {}, []
    for rid in ROOT_IDS:
        root, inv = ROOTS[rid][0], inv_dir(rid)
        final = inv / "root_inventory_final.json"
        if (
            not final.exists()
        ):  # a fresh ESTATE_HOME need not have inventoried every root yet
            continue
        rows = {r["name"]: r for r in json.loads(final.read_text("utf-8"))}
        for name, r in rows.items():
            if (
                r["type"] != "PPTX"
                or r["ext"] not in (".pptx", ".pptm")
                or not (root / name).exists()
            ):
                continue
            did = f"{rid}:{name}"
            try:
                ss = read_deck(root / name, did)
            except Exception as exc:  # a broken deck is a finding, not a crash
                decks[did] = {
                    "error": f"{type(exc).__name__}: {exc}"[:160],
                    "mtime": r["mtime"],
                }
                continue
            decks[did] = {
                "mtime": r["mtime"],
                "slides": len(ss),
                "epic": r.get("epic_final"),
                "sha256": r["sha256"],
            }
            slides += ss
    for i, s in enumerate(slides):
        s["i"] = i
    # ---- candidate pairs: exact text buckets + LSH bands over MinHash
    pairs = {}
    by_text = collections.defaultdict(list)
    for s in slides:
        if s["words"] >= 8:
            by_text[s["text_fp"]].append(s["i"])
    eligible = [s["i"] for s in slides if s["words"] >= 8]
    lsh = SS.lsh_candidates([slides[i]["_mh"] for i in eligible], BANDS, max_bucket=200)
    cand = SS.bucket_pairs(by_text.values(), max_bucket=200) | {
        (eligible[x], eligible[y]) for x, y in lsh
    }
    for a, b in sorted(cand):
        A, B = slides[a], slides[b]
        same_deck = A["deck"] == B["deck"]
        est = SS.estimated_jaccard(A["_mh"], B["_mh"])
        if A["text_fp"] == B["text_fp"]:
            kind = (
                "EXACT_COPY"
                if A["layout_fp"] == B["layout_fp"] and A["colours"] == B["colours"]
                else "RESTYLED"
            )
        elif est >= 0.6:
            kind = "EDITED"
        else:
            continue
        if (
            same_deck
        ):  # tuning rule S2: inside one deck only a true duplicate counts; shared template wording is not a remake
            if kind != "EXACT_COPY":
                continue
            kind = "DUP_IN_DECK"
        pairs[(a, b)] = {
            "a": a,
            "b": b,
            "kind": kind,
            "similarity": round(est, 2),
            "same_deck": same_deck,
        }
    # ---- families (union-find over cross-deck pairs only)
    cross_pairs = {k: p for k, p in pairs.items() if not p["same_deck"]}
    ds = SS.DisjointSet()  # union-find
    for a, b in cross_pairs:
        ds.union(a, b)
    comps = ds.components()
    fam = {c[0]: c for c in comps}
    rep_of = {i: c[0] for c in comps for i in c}
    kind_by_root = collections.defaultdict(collections.Counter)
    for (a, b), p in cross_pairs.items():
        kind_by_root[rep_of[a]][p["kind"]] += 1
    families = []
    for rootid, members in fam.items():
        members.sort(
            key=lambda i: (
                decks[slides[i]["deck"]]["mtime"],
                slides[i]["deck"],
                slides[i]["slide"],
            )
        )
        versions = (
            collections.OrderedDict()
        )  # distinct versions = distinct text_fp + layout_fp
        for i in members:
            versions.setdefault(
                (slides[i]["text_fp"], slides[i]["layout_fp"]), []
            ).append(i)
        kinds = kind_by_root[rootid]
        families.append(
            {
                "members": members,
                "decks": len({slides[i]["deck"] for i in members}),
                "versions": [v[0] for v in versions.values()],
                "copies": {str(v[0]): len(v) for v in versions.values()},
                "kinds": dict(kinds),
                "tip": members[-1],
                "title": next(
                    (
                        slides[i]["title"]
                        for i in reversed(members)
                        if slides[i]["title"]
                    ),
                    slides[members[-1]]["_words"][:8]
                    and " ".join(slides[members[-1]]["_words"][:8]),
                ),
            }
        )
    families.sort(key=lambda f: (-len(f["versions"]), -f["decks"], -len(f["members"])))
    # ---- before/after diffs for consecutive distinct versions
    for f in families:
        f["steps"] = []
        for a, b in zip(f["versions"], f["versions"][1:]):
            A, B = slides[a], slides[b]
            wa, wb = collections.Counter(A["_words"]), collections.Counter(B["_words"])
            f["steps"].append(
                {
                    "before": a,
                    "after": b,
                    "added": [w for w in (wb - wa)][:25],
                    "removed": [w for w in (wa - wb)][:25],
                    "words": [A["words"], B["words"]],
                    "fonts": [A["fonts"], B["fonts"]],
                    "colours": [len(A["colours"]), len(B["colours"])],
                    "layout_changed": A["layout_fp"] != B["layout_fp"],
                    "flags": [A["flags"], B["flags"]],
                }
            )
    # ---- deck style summary
    deck_style = {}
    by_deck = collections.defaultdict(list)
    for s in slides:
        by_deck[s["deck"]].append(s)
    for d, ss in by_deck.items():
        deck_style[d] = {
            "slides": len(ss),
            "fonts": sorted({f for s in ss for f in s["fonts"]}),
            "palette": len({c for s in ss for c in s["colours"]}),
            "median_words": statistics.median(s["words"] for s in ss),
            "dense_pct": round(100 * sum("DENSE" in s["flags"] for s in ss) / len(ss)),
            "hardcoded_pct": round(
                100 * sum("HARDCODED_COLOUR" in s["flags"] for s in ss) / len(ss)
            ),
            "small_font_pct": round(
                100 * sum("SMALL_FONT" in s["flags"] for s in ss) / len(ss)
            ),
        }
    # ---- write
    pub = [{k: v for k, v in s.items() if not k.startswith("_")} for s in slides]
    (EST / "deep").mkdir(parents=True, exist_ok=True)
    (EST / "deep" / "slide_atlas.json").write_text(
        json.dumps(
            {
                "schema": "gbogeb.estate.slide_atlas/0.1",
                "limits": LIMITS,
                "decks": decks,
                "slides": pub,
                "pairs": list(pairs.values()),
                "families": families,
                "deck_style": deck_style,
            },
            ensure_ascii=False,
        ),
        "utf-8",
    )
    kinds = collections.Counter(p["kind"] for p in pairs.values())
    cross = collections.Counter(p["kind"] for p in pairs.values() if not p["same_deck"])
    flags = collections.Counter(f for s in slides for f in s["flags"])
    multi = [f for f in families if len(f["versions"]) > 1]
    L = [
        "# Slide atlas",
        "",
        f"{len(decks)} decks, {len(slides)} slides ({' + '.join(ROOT_IDS)} roots). Errors: {sum('error' in d for d in decks.values())}.",
        "",
        "## Re-use and remakes",
        "",
        "| Pair kind | Pairs | Across decks |",
        "|---|---:|---:|",
    ]
    L += [f"| {k} | {v} | {cross[k]} |" for k, v in kinds.most_common()]
    L += [
        "",
        f"Slide families: {len(families)}; with more than one distinct version (before/after to choose): {len(multi)}; "
        f"slides that exist in 3+ decks: {sum(1 for f in families if f['decks'] >= 3)}.",
        "",
        "Top families (most versions first):",
        "",
        "| Title (newest) | Versions | Decks | Copies | Kinds |",
        "|---|---:|---:|---:|---|",
    ]
    for f in families[:25]:
        L.append(
            f"| {html.escape(str(f['title'])[:70])} | {len(f['versions'])} | {f['decks']} | {len(f['members'])} | {', '.join(f'{k} {v}' for k, v in f['kinds'].items())} |"
        )
    L += [
        "",
        "## Style, density, colour (per slide flags)",
        "",
        "| Flag | Slides | % | Rule |",
        "|---|---:|---:|---|",
    ]
    rule = {
        "DENSE": f"> {LIMITS['DENSE_WORDS']} words or > {LIMITS['DENSE_BOXES']} text boxes",
        "SMALL_FONT": f"a run below {LIMITS['SMALL_PT']} pt",
        "FONT_SPRAWL": f"> {LIMITS['FONTS']} font families",
        "COLOUR_SPRAWL": f"> {LIMITS['COLOURS']} hard-coded colours",
        "HARDCODED_COLOUR": "hard-coded RGB and no theme colour",
        "OFF_SLIDE": "a shape outside the slide",
    }
    L += [
        f"| {k} | {v} | {100 * v / max(len(slides), 1):.0f} | {rule[k]} |"
        for k, v in flags.most_common()
    ]
    L += [
        "",
        "Decks with the most style debt (dense % + hard-coded % + small-font %):",
        "",
        "| Deck | Slides | Fonts | Palette | Median words | Dense % | Hard-coded % | Small font % |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for d, s in sorted(
        deck_style.items(),
        key=lambda kv: -(
            kv[1]["dense_pct"] + kv[1]["hardcoded_pct"] + kv[1]["small_font_pct"]
        ),
    )[:15]:
        L.append(
            f"| {d.split(':', 1)[1][:60]} | {s['slides']} | {len(s['fonts'])} | {s['palette']} | {s['median_words']} | {s['dense_pct']} | {s['hardcoded_pct']} | {s['small_font_pct']} |"
        )
    (EST / "deep" / "SLIDE_ATLAS.md").write_text("\n".join(L) + "\n", "utf-8")
    write_compare(slides, decks, multi[:80])
    print("\n".join(L[:14]))
    print(f"flags: {dict(flags)}")
    return 0


def wire(s: dict, w: int = 300) -> str:
    h = int(w * 0.5625)
    parts = [
        f'<svg viewBox="0 0 {w} {h}" class="wf" role="img" aria-label="slide wireframe"><rect width="{w}" height="{h}" class="bg"/>'
    ]
    for sh in s["_shapes"]:
        if not sh["b"]:
            continue
        x, y, bw, bh = sh["b"][0] * w, sh["b"][1] * h, sh["b"][2] * w, sh["b"][3] * h
        if sh["k"] == "cxnSp":
            parts.append(
                f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + bw:.1f}" y2="{y + bh:.1f}" class="ln"/>'
            )
            continue
        fill = f' style="fill:{sh["f"]};fill-opacity:.55"' if sh["f"] else ""
        cls = "pic" if sh["k"] == "pic" else "sh"
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(bw, 1):.1f}" height="{max(bh, 1):.1f}" class="{cls}"{fill}/>'
        )
        if sh["t"]:
            parts.append(
                f'<text x="{x + 2:.1f}" y="{y + 7:.1f}">{html.escape(sh["t"][:28])}</text>'
            )
    return "".join(parts) + "</svg>"


def write_compare(slides, decks, fams) -> None:
    cards = []
    for n, f in enumerate(fams):
        vs = []
        for j, i in enumerate(f["versions"][-4:]):
            s = slides[i]
            d = s["deck"].split(":", 1)
            vs.append(
                f'<label class="ver"><input type="radio" name="f{n}" value="{html.escape(s["deck"])}#{s["slide"]}">'
                f'{wire(s)}<div class="meta"><b>{html.escape(d[1][:48])}</b> · slide {s["slide"]} · {decks[s["deck"]]["mtime"][:10]}<br>'
                f'{s["words"]} words · {len(s["fonts"])} fonts · {len(s["colours"])} colours'
                f'{" · " + ", ".join(s["flags"]) if s["flags"] else ""}</div></label>'
            )
        step = f["steps"][-1] if f["steps"] else None
        diff = ""
        if step:
            diff = (
                f'<p class="diff"><span class="add">+ {html.escape(" ".join(step["added"][:14]))}</span>'
                f'<span class="del">- {html.escape(" ".join(step["removed"][:14]))}</span></p>'
            )
        cards.append(
            f'<section class="fam" data-id="f{n}"><h2>{html.escape(str(f["title"])[:90])}</h2>'
            f'<p class="sub">{len(f["versions"])} versions in {f["decks"]} decks · {len(f["members"])} copies · {html.escape(", ".join(f"{k} {v}" for k, v in f["kinds"].items()))}</p>'
            f'{diff}<div class="vers">{"".join(vs)}</div>'
            f'<label class="keepall"><input type="radio" name="f{n}" value="KEEP_ALL"> keep all versions</label></section>'
        )
    page = COMPARE_HTML.replace("__CARDS__", "\n".join(cards)).replace(
        "__N__", str(len(fams))
    )
    (EST / "deep" / "COMPARE.html").write_text(page, "utf-8")


COMPARE_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Slide Versions Compare</title><style>
:root{--bg:#f7f7f4;--card:#fff;--ink:#1d2321;--muted:#5d6763;--line:#d9ddd8;--accent:#0f6b5c;--add:#1f7a3d;--del:#b3261e;--wf:#fbfbfa}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#141816;--card:#1c211f;--ink:#e6ebe8;--muted:#9aa5a0;--line:#2e3633;--accent:#4fb3a1;--add:#5cc184;--del:#ef7c74;--wf:#222826}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,Segoe UI,sans-serif}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;z-index:2}
header h1{font-size:17px;margin:0;flex:1}button{border:1px solid var(--accent);background:var(--card);color:var(--accent);border-radius:6px;padding:6px 12px;cursor:pointer;font-weight:600}
main{max-width:1280px;margin:0 auto;padding:16px}.fam{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px;margin-bottom:14px}
.fam h2{font-size:15px;margin:0 0 2px}.sub{color:var(--muted);margin:0 0 6px;font-size:12px}.diff{font-size:12px;margin:0 0 8px;display:flex;flex-direction:column;gap:2px}
.add{color:var(--add)}.del{color:var(--del)}.vers{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}
.ver{border:1px solid var(--line);border-radius:6px;padding:6px;cursor:pointer;display:block}.ver:has(input:checked){border-color:var(--accent);box-shadow:0 0 0 2px var(--accent)}
.ver input{margin:0 0 4px}.wf{width:100%;height:auto;display:block}.wf .bg{fill:var(--wf);stroke:var(--line)}.wf .sh{fill:none;stroke:var(--muted);stroke-width:.6}
.wf .pic{fill:var(--line);stroke:var(--muted);stroke-width:.4}.wf .ln{stroke:var(--accent);stroke-width:.8}.wf text{font-size:6px;fill:var(--ink)}
.meta{font-size:11px;color:var(--muted);margin-top:4px}.keepall{display:inline-block;margin-top:8px;font-size:12px;color:var(--muted)}
#count{color:var(--muted);font-size:12px}</style></head><body>
<header><h1>Slide versions: choose the one to keep</h1><span id="count"></span><button id="export">Export choices (JSON)</button></header>
<main><p class="sub">__N__ slide families with more than one version, newest versions last. Wireframes are drawn from shape positions in the file (no renderer needed). Your choices stay in this browser until you export them.</p>
__CARDS__</main>
<script>
const KEY="slide-compare-choices";let st={};try{st=JSON.parse(localStorage.getItem(KEY)||"{}")}catch(e){st={}}
function save(){try{localStorage.setItem(KEY,JSON.stringify(st))}catch(e){};document.getElementById("count").textContent=Object.keys(st).length+" chosen"}
document.querySelectorAll(".fam").forEach(f=>{const id=f.dataset.id;f.querySelectorAll("input[type=radio]").forEach(r=>{if(st[id]===r.value)r.checked=true;r.addEventListener("change",()=>{st[id]=r.value;save()})})});
document.getElementById("export").onclick=()=>{const b=new Blob([JSON.stringify({schema:"gbogeb.estate.slide_choices/0.1",at:new Date().toISOString(),choices:st},null,1)],{type:"application/json"});const a=document.createElement("a");a.href=URL.createObjectURL(b);a.download="slide_choices.json";a.click()};
save();
</script></body></html>"""


if __name__ == "__main__":
    raise SystemExit(main())
