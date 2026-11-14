"""E3_PARSE + E4_EXTRACT (L2/L3): first structural read of every root file listed in root_inventory.json.

Read-only. One JSON line per file in inventory/probe/<TYPE>.jsonl, e.g.:
  outline levels, bullet/number levels, fonts, colours, sizes, text boxes, groups, connectors (-> graph edges),
  tables, comments, tracked changes, formulas, pages, TOC, a text sample for the content epic (E5 pass).
Files classified E0_OTHER by name are re-classified from their text sample when it scores >= 4.

    python -I -X utf8 DMAIC_V3/binary_engines/estate_probe.py [--root-id ID] [--types PPTX,DOCX] [--limit N]
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estate_inventory import classify_epic  # noqa: E402  one classifier, not two
from estate_spec import ROOTS, inv_dir  # noqa: E402

CAP = 40_000_000  # bytes read per XML part; larger parts are counted as truncated
NS_RX = re.compile(r"<(/?)[a-zA-Z0-9]+:")


SECRET_RX = re.compile(
    r"ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)|xox[bpas]-[A-Za-z0-9-]{10,}"
    r"|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}|eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}"
    r"|(?i:password|passwd|pwd|secret|token|api[_-]?key|client[_-]?secret)\s*[:=]\s*[\"']?[^\s\"']{6,}[\"']?"
)


def scrub(text: str) -> tuple[str, int]:
    """Guard G2: stored text samples never keep secret-shaped strings (tokens, keys, password=...)."""
    return SECRET_RX.subn("[REDACTED]", text)


def _parts(zf: zipfile.ZipFile, rx: str) -> list[str]:
    return sorted(
        (n for n in zf.namelist() if re.fullmatch(rx, n)),
        key=lambda n: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", n)],
    )


def _read(zf: zipfile.ZipFile, name: str) -> str:
    with zf.open(name) as fh:
        return fh.read(CAP).decode("utf-8", "replace")


def _count(rx: str, s: str) -> int:
    return len(re.findall(rx, s))


def _tops(rx: str, s: str, n: int = 8) -> dict:
    return dict(collections.Counter(re.findall(rx, s)).most_common(n))


def _levels(rx: str, s: str) -> dict:
    return {
        str(k): v
        for k, v in sorted(
            collections.Counter(int(x) for x in re.findall(rx, s)).items()
        )
    }


def _text(s: str, tag: str, limit: int = 3000) -> str:
    return " ".join(re.findall(rf"<{tag}(?: [^>]*)?>([^<]*)</{tag}>", s))[:limit]


# ---------------------------------------------------------------------------------------- per type
def probe_docx(p: Path) -> dict:
    with zipfile.ZipFile(p) as zf:
        doc = _read(zf, "word/document.xml")
        styles = (
            _read(zf, "word/styles.xml") if "word/styles.xml" in zf.namelist() else ""
        )
        numbering = (
            _read(zf, "word/numbering.xml")
            if "word/numbering.xml" in zf.namelist()
            else ""
        )
        n_comments = (
            _count(r"<w:comment ", _read(zf, "word/comments.xml"))
            if "word/comments.xml" in zf.namelist()
            else 0
        )
        media = len([n for n in zf.namelist() if n.startswith("word/media/")])
    heading_styles = re.findall(
        r'<w:pStyle w:val="(?:Heading|Kop|heading)\s?(\d)"', doc
    )
    num_fmts = collections.Counter(re.findall(r'<w:numFmt w:val="(\w+)"', numbering))
    return {
        "paragraphs": _count(r"<w:p[ >]", doc),
        "tables": _count(r"<w:tbl>", doc),
        "sections": _count(r"<w:sectPr", doc),
        "outline_levels": {
            str(k): v
            for k, v in sorted(
                collections.Counter(int(x) for x in heading_styles).items()
            )
        },
        "outlineLvl_direct": _levels(r'<w:outlineLvl w:val="(\d)"', doc),
        "list_levels": _levels(r'<w:ilvl w:val="(\d)"', doc),
        "num_formats": dict(num_fmts.most_common(6)),
        "fonts": _tops(r'w:ascii="([^"]+)"', doc + styles),
        "colours": _tops(r'<w:color w:val="([0-9A-Fa-f]{6})"', doc),
        "sizes_halfpt": _tops(r'<w:sz w:val="(\d+)"', doc),
        "text_boxes": _count(r"<w:txbxContent", doc),
        "drawings": _count(r"<wp:(?:inline|anchor)", doc),
        "media": media,
        "comments": n_comments,
        "tracked_ins": _count(r"<w:ins ", doc),
        "tracked_del": _count(r"<w:del ", doc),
        "strike": _count(r"<w:strike/>|<w:dstrike/>", doc),
        "highlight": _tops(r'<w:highlight w:val="(\w+)"', doc, 4),
        "fields": _count(r"<w:fldSimple|<w:instrText", doc),
        "text_sample": _text(doc, "w:t"),
    }


def probe_pptx(p: Path) -> dict:
    slides, edges, totals = [], [], collections.Counter()
    fonts, colours, sizes, lvls = (
        collections.Counter(),
        collections.Counter(),
        collections.Counter(),
        collections.Counter(),
    )
    sample = []
    with zipfile.ZipFile(p) as zf:
        names = zf.namelist()
        for i, sn in enumerate(_parts(zf, r"ppt/slides/slide\d+\.xml"), 1):
            s = _read(zf, sn)
            sp = re.findall(r"<p:sp>.*?</p:sp>", s, re.S)
            tb = [x for x in sp if 'txBox="1"' in x]
            with_text = [x for x in sp if re.search(r"<a:t>[^<]*\S", x)]
            row = {
                "slide": i,
                "shapes": len(sp),
                "text_boxes": len(tb),
                "shapes_with_text": len(with_text),
                "groups": _count(r"<p:grpSp>", s),
                "connectors": _count(r"<p:cxnSp>", s),
                "pictures": _count(r"<p:pic>", s),
                "tables": _count(r"<a:tbl>", s),
                "charts": _count(
                    r'uri="http://schemas.openxmlformats.org/drawingml/2006/chart"', s
                ),
                "placeholders": _count(r"<p:ph[ />]", s),
                "words": len(_text(s, "a:t", 100000).split()),
            }
            slides.append(row)
            totals.update({k: v for k, v in row.items() if k != "slide"})
            # PPT as drawing office: connector begin/end -> graph edges between shape ids
            for cx in re.findall(r"<p:cxnSp>.*?</p:cxnSp>", s, re.S):
                a, b = re.search(r'<a:stCxn id="(\d+)"', cx), re.search(
                    r'<a:endCxn id="(\d+)"', cx
                )
                arrow = bool(re.search(r"<a:(?:head|tail)End type=\"(?!none)", cx))
                edges.append(
                    {
                        "slide": i,
                        "from": a.group(1) if a else None,
                        "to": b.group(1) if b else None,
                        "arrow": arrow,
                    }
                )
            fonts.update(re.findall(r'<a:latin typeface="([^"]+)"', s))
            colours.update(re.findall(r'<a:srgbClr val="([0-9A-Fa-f]{6})"', s))
            sizes.update(re.findall(r' sz="(\d+)"', s))
            lvls.update(re.findall(r'<a:pPr[^>]* lvl="(\d)"', s))
            if len(" ".join(sample)) < 3000:
                sample.append(_text(s, "a:t", 600))
        notes = len(_parts(zf, r"ppt/notesSlides/notesSlide\d+\.xml"))
        layouts = len(_parts(zf, r"ppt/slideLayouts/slideLayout\d+\.xml"))
        media = len([n for n in names if n.startswith("ppt/media/")])
    bound = [e for e in edges if e["from"] and e["to"]]
    return {
        "slides": len(slides),
        "layouts": layouts,
        "notes": notes,
        "media": media,
        **{f"total_{k}": v for k, v in totals.items()},
        "outline_levels": {str(int(k) + 1): v for k, v in sorted(lvls.items())},
        "fonts": dict(fonts.most_common(8)),
        "colours": dict(colours.most_common(10)),
        "sizes_pt": {str(int(k) // 100): v for k, v in sizes.most_common(8)},
        "connector_edges_bound": len(bound),
        "connector_edges_loose": len(edges) - len(bound),
        "graph_edges_sample": bound[:40],
        "per_slide": slides,
        "text_sample": " ".join(sample)[:3000],
    }


def probe_xlsx(p: Path) -> dict:
    if p.suffix.lower() == ".csv":
        head = p.read_text("utf-8", "replace")[:200_000].splitlines()
        return {
            "rows_sampled": len(head),
            "cols_first": len(head[0].split(",")) if head else 0,
            "text_sample": " ".join(head[:20])[:3000],
        }
    with zipfile.ZipFile(p) as zf:
        names = zf.namelist()
        wb = _read(zf, "xl/workbook.xml")
        sheets = re.findall(r'<sheet [^>]*name="([^"]+)"[^>]*?(?:state="(\w+)")?', wb)
        f_total, dims, cf, dv, merged = 0, {}, 0, 0, 0
        for sn in _parts(zf, r"xl/worksheets/sheet\d+\.xml"):
            s = _read(zf, sn)
            f_total += _count(r"<f[ >]", s)
            d = re.search(r'<dimension ref="([^"]+)"', s)
            dims[sn.rsplit("/", 1)[1]] = d.group(1) if d else "?"
            cf += _count(r"<conditionalFormatting", s)
            dv += _count(r"<dataValidation ", s)
            merged += _count(r"<mergeCell ", s)
        styles = _read(zf, "xl/styles.xml") if "xl/styles.xml" in names else ""
        shared = (
            _read(zf, "xl/sharedStrings.xml") if "xl/sharedStrings.xml" in names else ""
        )
    return {
        "sheets": len(sheets),
        "sheet_names": [s[0] for s in sheets][:40],
        "hidden": sum(1 for s in sheets if s[1] in ("hidden", "veryHidden")),
        "dimensions": dims,
        "formulas": f_total,
        "defined_names": _count(r"<definedName ", wb),
        "external_links": len([n for n in names if n.startswith("xl/externalLinks/")]),
        "charts": len([n for n in names if n.startswith("xl/charts/chart")]),
        "drawings": len([n for n in names if n.startswith("xl/drawings/drawing")]),
        "conditional_formats": cf,
        "data_validations": dv,
        "merged_cells": merged,
        "vba": "xl/vbaProject.bin" in names,
        "fonts": _tops(r'<name val="([^"]+)"', styles),
        "colours": _tops(r'rgb="FF([0-9A-Fa-f]{6})"', styles),
        "text_sample": _text(shared, "t"),
    }


def probe_pdf(p: Path) -> dict:
    if p.suffix.lower() == ".xps":
        return {"note": "XPS: planned engine (PyMuPDF opens XPS)"}
    import fitz  # PyMuPDF

    with fitz.open(p) as d:
        toc = d.get_toc(simple=True)
        fonts, chars, imgs, sample = collections.Counter(), 0, 0, []
        for pg in list(d)[:5]:
            t = pg.get_text()
            chars += len(t)
            sample.append(t[:800])
            fonts.update(f[3] for f in pg.get_fonts())
            imgs += len(pg.get_images())
        r = d[0].rect if d.page_count else None
        return {
            "pages": d.page_count,
            "encrypted": d.is_encrypted,
            "title": (d.metadata or {}).get("title", "")[:120],
            "producer": (d.metadata or {}).get("producer", "")[:80],
            "toc_entries": len(toc),
            "outline_levels": dict(collections.Counter(str(x[0]) for x in toc)),
            "text_chars_first5": chars,
            "scanned_suspect": d.page_count > 0 and chars < 50,
            "images_first5": imgs,
            "fonts": dict(fonts.most_common(8)),
            "page_size_pt": [round(r.width), round(r.height)] if r else None,
            "text_sample": " ".join(sample)[:3000],
        }


def probe_html(p: Path) -> dict:
    s = p.read_text("utf-8", "replace")
    title = re.search(r"<title>(.*?)</title>", s, re.S | re.I)
    body = re.sub(
        r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", s, flags=re.S | re.I
    )
    return {
        "title": (title.group(1).strip() if title else "")[:120],
        "outline_levels": {
            str(i): len(re.findall(rf"<h{i}[ >]", s, re.I))
            for i in range(1, 7)
            if re.search(rf"<h{i}[ >]", s, re.I)
        },
        "scripts": _count(r"<script", s),
        "external_scripts": re.findall(r'<script[^>]+src="(https?://[^"]+)"', s)[:6],
        "links": _count(r"<a [^>]*href", s),
        "svg_inline": _count(r"<svg", s),
        "tables": _count(r"<table", s),
        "colours": _tops(r"#([0-9a-fA-F]{6})\b", s),
        "fonts": _tops(r"font-family:\s*['\"]?([^;'\",]+)", s),
        "text_sample": re.sub(r"\s+", " ", body)[:3000],
    }


def probe_text(p: Path) -> dict:
    s = p.read_text("utf-8", "replace")
    lines = s.splitlines()
    bullets = collections.Counter(
        len(m.group(1)) // 2 + 1 for l in lines if (m := re.match(r"^(\s*)[-*+] ", l))
    )
    numbers = collections.Counter(
        len(m.group(1)) // 2 + 1 for l in lines if (m := re.match(r"^(\s*)\d+[.)] ", l))
    )
    heads = collections.Counter(
        len(m.group(1)) for l in lines if (m := re.match(r"^(#{1,6}) ", l))
    )
    return {
        "lines": len(lines),
        "chars": len(s),
        "outline_levels": {str(k): v for k, v in sorted(heads.items())},
        "bullet_levels": {str(k): v for k, v in sorted(bullets.items())},
        "number_levels": {str(k): v for k, v in sorted(numbers.items())},
        "code_fences": s.count("```") // 2,
        "md_tables": sum(1 for l in lines if re.match(r"^\s*\|.*\|\s*$", l)),
        "links": len(re.findall(r"\]\((?:https?://|\.?/)[^)]+\)", s)),
        "mermaid": s.count("```mermaid"),
        "looks_like_log": bool(
            re.search(r"Traceback|\bERROR\b|\[\d{2}:\d{2}:\d{2}\]", s[:20000])
        ),
        "text_sample": s[:3000],
    }


def probe_vsdx(p: Path) -> dict:
    ext = p.suffix.lower()
    if ext == ".drawio" or ext == ".mmd":
        s = p.read_text("utf-8", "replace")
        return {
            "vertices": _count(r'vertex="1"', s),
            "edges": _count(r'edge="1"', s),
            "pages": _count(r"<diagram ", s),
            "mermaid_edges": _count(r"--!?>|---", s) if ext == ".mmd" else 0,
            "text_sample": " ".join(re.findall(r'value="([^"]{2,80})"', s))[:3000],
        }
    with zipfile.ZipFile(p) as zf:
        pages = _parts(zf, r"visio/pages/page\d+\.xml")
        shapes = conns = 0
        txt = []
        for pn in pages:
            s = _read(zf, pn)
            shapes += _count(r"<Shape ", s)
            conns += _count(r"<Connect ", s)
            txt.append(" ".join(re.findall(r"<Text>([^<]*)", s)))
    return {
        "pages": len(pages),
        "shapes": shapes,
        "connects": conns,
        "text_sample": " ".join(txt)[:3000],
    }


def probe_image(p: Path) -> dict:
    from PIL import Image

    with Image.open(p) as im:
        return {
            "size_px": list(im.size),
            "mode": im.mode,
            "dpi": [round(x) for x in im.info.get("dpi", (0, 0))],
            "frames": getattr(im, "n_frames", 1),
            "ocr": "planned (no OCR engine on this PC)",
        }


def probe_svg(p: Path) -> dict:
    s = p.read_text("utf-8", "replace")
    vb = re.search(r'viewBox="([^"]+)"', s)
    return {
        "viewBox": vb.group(1) if vb else None,
        "elements": _count(r"<[a-zA-Z]", s),
        "groups": _count(r"<g[ >]", s),
        "text": _count(r"<text[ >]", s),
        "paths": _count(r"<path[ >]", s),
        "lines": _count(r"<(?:line|polyline)[ >]", s),
        "rects": _count(r"<rect[ >]", s),
        "markers_arrows": _count(r"<marker[ >]|marker-end", s),
        "fonts": _tops(r"font-family[=:]\s*['\"]?([^;'\",]+)", s),
        "colours": _tops(r"#([0-9a-fA-F]{6})\b", s),
        "text_sample": " ".join(re.findall(r"<text[^>]*>([^<]+)", s))[:3000],
    }


PROBES = {
    "DOCX": probe_docx,
    "PPTX": probe_pptx,
    "XLSX": probe_xlsx,
    "PDF": probe_pdf,
    "HTML": probe_html,
    "TXT": probe_text,
    "MD": probe_text,
    "VSDX": probe_vsdx,
    "PNG": probe_image,
    "SVG": probe_svg,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--types", default=",".join(PROBES))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--root-id", default="MI", choices=sorted(ROOTS))
    args = ap.parse_args()
    ROOT, INV = ROOTS[args.root_id][0], inv_dir(args.root_id)
    inv = json.loads((INV / "root_inventory.json").read_text("utf-8"))
    out = INV / "probe"
    out.mkdir(exist_ok=True)
    want = set(args.types.split(","))
    stats = collections.Counter()
    reclass = []
    for typ in sorted(want):
        rows = [r for r in inv["rows"] if r["type"] == typ]
        if args.limit:
            rows = rows[: args.limit]
        t0 = time.time()
        with (out / f"{typ}.jsonl").open("w", encoding="utf-8") as fh:
            for r in rows:
                p = ROOT / r["name"]
                rec = {
                    "name": r["name"],
                    "sha256": r["sha256"],
                    "epic_by_name": r["epic"],
                }
                if r.get("cloud_only"):
                    rec["error"] = (
                        "cloud_only: not downloaded (would hydrate from OneDrive)"
                    )
                elif r["ext"] in (".doc", ".xls", ".ppt", ".vsd"):
                    rec["error"] = (
                        "legacy OLE format: planned (convert via Office COM, never in place)"
                    )
                else:
                    try:
                        rec.update(PROBES[typ](p))
                        stats[(typ, "ok")] += 1
                    except Exception as exc:
                        rec["error"] = f"{type(exc).__name__}: {exc}"[:200]
                        stats[(typ, "error")] += 1
                if (
                    r["epic"] == "E0_OTHER"
                    and r.get("og5_repo") != "_personal"
                    and rec.get("text_sample")
                ):
                    e = classify_epic("", rec["text_sample"])
                    if e[2] >= 4:
                        rec["epic_by_content"] = e[0]
                        rec["epic_content_hits"] = e[3][:8]
                        reclass.append((r["name"], e[0]))
                if rec.get("text_sample"):
                    rec["text_sample"], n = scrub(rec["text_sample"])
                    if n:
                        rec["redactions"] = n
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(
            f"{typ:5} {len(rows):4} files {time.time() - t0:6.1f}s  ok={stats[(typ, 'ok')]} err={stats[(typ, 'error')]}"
        )
    (out / "content_reclass.json").write_text(
        json.dumps(reclass, indent=1, ensure_ascii=False), "utf-8"
    )
    print(
        f"E0_OTHER re-classified from content: {len(reclass)}",
        dict(collections.Counter(e for _, e in reclass)),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
