"""Command line: ``python -m DMAIC_V3.svg_engine <command> ...``.

  nested-pdf  SOURCE OUT.pdf [--member M] [--presets presets.json] [--previews DIR]
              writes OUT.pdf and OUT.build.json (nested OCGs, true parent semantics)
  flat-pdf    SOURCE OUT.pdf [--member M]                      W1 flat baseline (+ OUT.build.json)
  fidelity    SOURCE OUT.pdf RECEIPT.json [--member M] [--build OUT.build.json] [--baseline-pdf P]
              [--authored-pdf P] [--cascade-ids a,b] [--hidden-parent-ids c,d]
  ooxml-geometry DECK.pptx OUT.json
  ooxml-qa    ADAPTER.json ORACLE.json OUT.json [--tol-mm 0.05]
  fixture     OUT.pptx                                         synthetic group/font fixture
  page-identity AUTHORED.pdf OUT.json SVG [SVG ...]

SOURCE is an ``.svg`` or a ``.zip`` holding one (or name it with ``--member``).
A presets file is JSON ``{"1": {"title": ..., "skip_subtrees": [...], "force_on": [...]}, "2": {...}}``.
Exit status is 1 when a fidelity or OOXML QA receipt contains a FAIL.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _dump(obj, path):
    Path(path).write_text(
        json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8"
    )


def _ids(s):
    return [x for x in (s or "").split(",") if x] if s is not None else None


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="python -m DMAIC_V3.svg_engine",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("nested-pdf", "flat-pdf"):
        p = sub.add_parser(name)
        p.add_argument("source")
        p.add_argument("out")
        p.add_argument("--member")
        if name == "nested-pdf":
            p.add_argument("--presets")
            p.add_argument("--previews")
    p = sub.add_parser("fidelity")
    p.add_argument("source")
    p.add_argument("pdf")
    p.add_argument("receipt")
    p.add_argument("--member")
    p.add_argument("--build")
    p.add_argument("--baseline-pdf")
    p.add_argument("--authored-pdf")
    p.add_argument("--cascade-ids")
    p.add_argument("--hidden-parent-ids")
    p = sub.add_parser("ooxml-geometry")
    p.add_argument("deck")
    p.add_argument("out")
    p = sub.add_parser("ooxml-qa")
    p.add_argument("adapter")
    p.add_argument("oracle")
    p.add_argument("out")
    p.add_argument("--tol-mm", type=float, default=0.05)
    p = sub.add_parser("fixture")
    p.add_argument("out")
    p = sub.add_parser("page-identity")
    p.add_argument("pdf")
    p.add_argument("out")
    p.add_argument("svgs", nargs="+")
    a = ap.parse_args(argv)

    if a.cmd in ("nested-pdf", "flat-pdf"):
        from .ingress import load_svg
        from .pdf_ocg import build_flat_ocg_pdf, build_nested_ocg_pdf, save_previews

        root, raw = load_svg(a.source, a.member)
        out = Path(a.out)
        if a.cmd == "nested-pdf":
            presets = (
                json.loads(Path(a.presets).read_text(encoding="utf-8"))
                if a.presets
                else None
            )
            rep = build_nested_ocg_pdf(
                root, out, page_presets=presets, source_bytes=raw
            )
            if a.previews:
                Path(a.previews).mkdir(parents=True, exist_ok=True)
                rep["previews"] = save_previews(out, a.previews)
        else:
            rep = build_flat_ocg_pdf(root, out, source_bytes=raw)
        _dump(rep, out.with_suffix(".build.json"))
        print(
            json.dumps(
                {k: v for k, v in rep.items() if k != "ocg_xref_by_layer"}, indent=1
            )
        )
        return 0
    if a.cmd == "fidelity":
        from .fidelity import check_pdf_fidelity
        from .ingress import load_svg

        root, _ = load_svg(a.source, a.member)
        build_path = (
            Path(a.build) if a.build else Path(a.pdf).with_suffix(".build.json")
        )
        build = json.loads(build_path.read_text(encoding="utf-8"))
        rec = check_pdf_fidelity(
            a.pdf,
            build,
            root,
            baseline_pdf=a.baseline_pdf,
            authored_pdf=a.authored_pdf,
            cascade_ids=_ids(a.cascade_ids),
            hidden_parent_ids=_ids(a.hidden_parent_ids),
        )
        _dump(rec, a.receipt)
        for c in rec["checks"]:
            print(c["result"], c["id"], c["title"], "|", c["evidence"][:200])
        print(rec["summary"])
        return 1 if rec["summary"]["FAIL"] else 0
    if a.cmd == "ooxml-geometry":
        from .ooxml_geometry import analyse

        res = analyse(a.deck)
        _dump(res, a.out)
        print(
            json.dumps(
                {k: v for k, v in res.items() if k != "slides"},
                indent=1,
                ensure_ascii=False,
            )
        )
        return 0
    if a.cmd == "ooxml-qa":
        from .ooxml_qa import compare_with_oracle

        res = compare_with_oracle(
            json.loads(Path(a.adapter).read_text(encoding="utf-8")),
            json.loads(Path(a.oracle).read_text(encoding="utf-8-sig")),
            a.tol_mm,
        )
        _dump(res, a.out)
        print(
            res["result"], "compared", res["compared"], "failures", len(res["failures"])
        )
        return 0 if res["result"] == "PASS" else 1
    if a.cmd == "fixture":
        from .fixtures import make_group_font_fixture

        print("fixture written", make_group_font_fixture(a.out))
        return 0
    if a.cmd == "page-identity":
        from .page_identity import page_identity

        res = page_identity(a.pdf, a.svgs)
        _dump(res, a.out)
        for pg in res["pages"]:
            print(pg["page"], pg["best_match"])
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
