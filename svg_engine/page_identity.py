"""Identify what each page of an authored PDF is, by native text-token overlap with candidate source SVGs.

Used when an authored PDF merges several exports: each page is matched to the SVG (or layer state) whose
native ``<text>`` tokens it reproduces best. Read-only.
"""
from __future__ import annotations

from pathlib import Path

from .ingress import layer_tree_report, parse_svg, sha, simple, tokens


def svg_tokens(root):
    out = tokens("")
    for e in root.iter():
        if simple(e) == "text":
            out += tokens(" ".join("".join(e.itertext()).split()))
    return out


def overlap(page, svg):
    inter = sum((page & svg).values())
    return {"shared_tokens": inter, "page_tokens": sum(page.values()), "svg_tokens": sum(svg.values()),
            "page_recall": round(inter / max(1, sum(page.values())), 4),
            "svg_recall": round(inter / max(1, sum(svg.values())), 4)}


def pdf_page_tokens(pdf_path):
    import fitz
    with fitz.open(pdf_path) as d:
        return [tokens(p.get_text()) for p in d]


def page_identity(pdf_path, svg_paths):
    """Best-matching candidate SVG per page of ``pdf_path``."""
    import fitz
    cands = {}
    for s in svg_paths:
        data = Path(s).read_bytes()
        cands[Path(s).name] = (svg_tokens(parse_svg(data, validate=False, huge_tree=True)), sha(data))
    res = {"authored_pdf": Path(pdf_path).name, "authored_pdf_sha256": sha(Path(pdf_path).read_bytes()), "pages": []}
    with fitz.open(pdf_path) as d:
        res["metadata"] = {k: d.metadata.get(k) for k in ("title", "creator", "producer", "modDate")}
        for i, p in enumerate(d):
            pt = tokens(p.get_text())
            scores = {n: {**overlap(pt, c[0]), "svg_sha256": c[1]} for n, c in cands.items()}
            best = max(scores, key=lambda n: scores[n]["page_recall"]) if scores else None
            res["pages"].append({"page": i + 1, "size_pt": [round(p.rect.width, 2), round(p.rect.height, 2)],
                                 "best_match": best, "scores": scores,
                                 "top_unmatched_page_tokens": [t for t, _ in (pt - cands[best][0]).most_common(15)] if best else []})
    return res


def layer_page_presence(root, pdf_path):
    """Per native layer: which share of its own text tokens appears on each page of ``pdf_path``."""
    return layer_tree_report(root, pdf_page_tokens(pdf_path))
