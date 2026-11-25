"""Build the TYPE.gg_Engine scaffold and the golden-thread graph from the inventory and probe outputs.

Regenerable: rerun after estate_inventory.py / estate_probe.py. Hand-written notes go in each engine's
NOTES.md, which this script creates once and never overwrites.

    python -I -X utf8 DMAIC_V3/binary_engines/estate_scaffold.py
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estate_spec as _spec  # noqa: E402

BOUND, ESTATE, PRIVATE_LADDER, REAL_ROOTS = (
    _spec.BOUND,
    _spec.ESTATE,
    _spec.PRIVATE_LADDER,
    _spec.REAL_ROOTS,
)
ROOTS, inv_dir, CAPABILITIES, DAG = (
    _spec.ROOTS,
    _spec.inv_dir,
    _spec.CAPABILITIES,
    _spec.DAG,
)
DECISIONS, EPICS, LANES, OG5 = _spec.DECISIONS, _spec.EPICS, _spec.LANES, _spec.OG5
OTHER_EPIC, SCHEMA, TYPES = _spec.OTHER_EPIC, _spec.SCHEMA, _spec.TYPES

EST = ESTATE
ROOT = EST.parent
INV, ENG, GRAPH = EST / "inventory", EST / "engines", EST / "graph"
PUBLIC_CATALOG = BOUND.get("public_catalog", "<engine catalogue>")
PRIVATE_REGISTRY = BOUND.get("private_registry", "<private registry>")
LADDER = PRIVATE_LADDER  # private K-ladder ranges per type, from configuration
CATALOG_CHECKS = {
    "DOCX": "K-DOCX-01..06",
    "XLSX": "K-XLSX-01..05",
    "PPTX": "K-PPTX-01..07",
    "PDF": "K-PDF-01..05",
    "HTML": "K-HTML-01..04",
    "SVG": "K-SVG-01..02",
}

# capability -> (status, engine/how). now = runs today via estate_probe.py or an installed engine.
N, P, X = "now", "planned", "na"
_common = {
    "READ": (N, "estate_probe.py"),
    "PARSE": (N, "estate_probe.py"),
    "SCAN": (N, "estate_inventory.py (identity, hash, family)"),
    "GREP": (P, "full-text index over probe text extraction"),
    "DEBUG": (N, "probe 'error' field + K-ANY-01 magic check"),
    "QA_K": (
        P,
        "bind catalogue K-checks; run the private registry's binary QA (configuration: binary_qa_tool)",
    ),
}
CAPS: dict[str, dict[str, tuple[str, str]]] = {
    "DOCX": {
        **_common,
        "WRITE": (N, "python-docx (copies only)"),
        "PATCH": (N, "python-docx / OOXML part patch, copy-on-write"),
        "LINT": (P, "style lint: heading skips, direct formatting, field errors"),
        "SLICE": (P, "split by section/heading"),
        "SEMANTIC_SECTIONS": (P, "heading tree -> sections -> RTM atoms"),
        "OUTLINE_LEVELS": (N, "Heading N + w:outlineLvl"),
        "BULLET_LEVELS": (N, "w:ilvl + numFmt=bullet"),
        "NUMBER_LEVELS": (N, "w:ilvl + numFmt=decimal/..."),
        "FONTS": (N, "w:rFonts"),
        "COLOURS": (N, "w:color, w:highlight"),
        "SIZE": (N, "w:sz (half-points)"),
        "TEXT_BOXES": (N, "w:txbxContent count"),
        "SHAPES_GRAPH": (P, "wps shapes + connectors -> edges"),
    },
    "PPTX": {
        **_common,
        "WRITE": (N, "python-pptx (copies only)"),
        "PATCH": (N, "python-pptx / slide XML patch, copy-on-write"),
        "LINT": (P, "deck lint: off-slide shapes, font sprawl, empty placeholders"),
        "SLICE": (N, "per-slide records"),
        "SEMANTIC_SECTIONS": (P, "title -> section -> storyline"),
        "OUTLINE_LEVELS": (N, "a:pPr lvl"),
        "BULLET_LEVELS": (N, "a:pPr lvl (buChar)"),
        "NUMBER_LEVELS": (P, "a:buAutoNum"),
        "FONTS": (N, "a:latin"),
        "COLOURS": (N, "a:srgbClr"),
        "SIZE": (N, "a:rPr sz"),
        "TEXT_BOXES": (N, "txBox=1 + shapes_with_text, per slide"),
        "SHAPES_GRAPH": (
            N,
            "p:cxnSp stCxn/endCxn -> nodes+edges (PPT as drawing office)",
        ),
    },
    "XLSX": {
        **_common,
        "WRITE": (N, "openpyxl (copies only)"),
        "PATCH": (N, "openpyxl, copy-on-write; never on pinned SSOT"),
        "LINT": (
            P,
            "formula errors, hard-coded numbers in formula ranges, broken names",
        ),
        "SLICE": (N, "per-sheet dims"),
        "SEMANTIC_SECTIONS": (P, "header rows -> tables -> keyed records"),
        "OUTLINE_LEVELS": (P, "row/col outline levels"),
        "BULLET_LEVELS": (X, ""),
        "NUMBER_LEVELS": (X, ""),
        "FONTS": (N, "styles.xml fonts"),
        "COLOURS": (N, "styles.xml fills"),
        "SIZE": (P, "font sizes from styles"),
        "TEXT_BOXES": (P, "drawings/*.xml shapes"),
        "SHAPES_GRAPH": (P, "formula dependency graph"),
    },
    "PDF": {
        **_common,
        "WRITE": (P, "ReportLab / export from source; PDFs are outputs"),
        "PATCH": (X, "patch the source, re-export"),
        "LINT": (P, "qpdf --check (not installed), veraPDF (not installed)"),
        "SLICE": (N, "PyMuPDF pages"),
        "SEMANTIC_SECTIONS": (N, "TOC levels; heading font-size heuristics planned"),
        "OUTLINE_LEVELS": (N, "get_toc levels"),
        "BULLET_LEVELS": (P, "glyph + indent heuristics"),
        "NUMBER_LEVELS": (P, "numbered heading regex"),
        "FONTS": (N, "page.get_fonts"),
        "COLOURS": (P, "span colours"),
        "SIZE": (P, "span sizes"),
        "TEXT_BOXES": (P, "text blocks per page"),
        "SHAPES_GRAPH": (P, "page.get_drawings -> lines/arrows"),
    },
    "HTML": {
        **_common,
        "WRITE": (N, "source-owned generators"),
        "PATCH": (N, "text patch, source first"),
        "LINT": (P, "Playwright console + axe-core"),
        "SLICE": (P, "section/article split"),
        "SEMANTIC_SECTIONS": (N, "h1-h6 tree"),
        "OUTLINE_LEVELS": (N, "h1-h6"),
        "BULLET_LEVELS": (P, "ul/ol nesting"),
        "NUMBER_LEVELS": (P, "ol nesting"),
        "FONTS": (N, "font-family"),
        "COLOURS": (N, "hex colours"),
        "SIZE": (P, "computed styles via Playwright"),
        "TEXT_BOXES": (X, ""),
        "SHAPES_GRAPH": (P, "inline SVG / links graph"),
    },
    "TXT": {
        **_common,
        "WRITE": (N, "stdlib"),
        "PATCH": (N, "stdlib diff/patch"),
        "LINT": (P, "encoding, line endings, log vs note"),
        "SLICE": (N, "lines"),
        "SEMANTIC_SECTIONS": (P, "prompt / log / note classifier"),
        "OUTLINE_LEVELS": (N, "# headings if any"),
        "BULLET_LEVELS": (N, "indent depth"),
        "NUMBER_LEVELS": (N, "indent depth"),
        "FONTS": (X, ""),
        "COLOURS": (X, ""),
        "SIZE": (N, "chars/lines"),
        "TEXT_BOXES": (X, ""),
        "SHAPES_GRAPH": (X, ""),
    },
    "MD": {
        **_common,
        "WRITE": (N, "stdlib"),
        "PATCH": (N, "stdlib"),
        "LINT": (P, "markdownlint (not installed)"),
        "SLICE": (N, "heading split"),
        "SEMANTIC_SECTIONS": (N, "heading tree"),
        "OUTLINE_LEVELS": (N, "#..######"),
        "BULLET_LEVELS": (N, "- * + indent"),
        "NUMBER_LEVELS": (N, "1. indent"),
        "FONTS": (X, ""),
        "COLOURS": (X, ""),
        "SIZE": (N, "chars/lines"),
        "TEXT_BOXES": (X, ""),
        "SHAPES_GRAPH": (N, "mermaid blocks counted; edge parse planned"),
    },
    "VSDX": {
        **_common,
        "WRITE": (P, "Visio COM or drawio XML"),
        "PATCH": (P, "XML part patch"),
        "LINT": (P, "unconnected connectors"),
        "SLICE": (N, "pages"),
        "SEMANTIC_SECTIONS": (P, "containers/swimlanes"),
        "OUTLINE_LEVELS": (X, ""),
        "BULLET_LEVELS": (X, ""),
        "NUMBER_LEVELS": (X, ""),
        "FONTS": (P, ""),
        "COLOURS": (P, ""),
        "SIZE": (P, ""),
        "TEXT_BOXES": (N, "Shape <Text>"),
        "SHAPES_GRAPH": (N, "<Connect> / drawio edge=1 -> edges"),
    },
    "PNG": {
        **_common,
        "WRITE": (N, "Pillow (derivatives only)"),
        "PATCH": (X, "regenerate from source"),
        "LINT": (P, "dpi, size, alpha"),
        "SLICE": (P, "tiles"),
        "SEMANTIC_SECTIONS": (P, "OCR (no engine installed)"),
        "OUTLINE_LEVELS": (X, ""),
        "BULLET_LEVELS": (X, ""),
        "NUMBER_LEVELS": (X, ""),
        "FONTS": (X, ""),
        "COLOURS": (P, "palette extraction"),
        "SIZE": (N, "px, dpi"),
        "TEXT_BOXES": (P, "OCR boxes"),
        "SHAPES_GRAPH": (X, ""),
    },
    "SVG": {
        **_common,
        "WRITE": (N, "source-owned diagram code"),
        "PATCH": (N, "XML patch"),
        "LINT": (P, "viewBox, fonts embedded, text-as-path"),
        "SLICE": (N, "groups"),
        "SEMANTIC_SECTIONS": (P, "group ids/labels"),
        "OUTLINE_LEVELS": (X, ""),
        "BULLET_LEVELS": (X, ""),
        "NUMBER_LEVELS": (X, ""),
        "FONTS": (N, "font-family"),
        "COLOURS": (N, "hex fills/strokes"),
        "SIZE": (N, "viewBox"),
        "TEXT_BOXES": (N, "<text> count"),
        "SHAPES_GRAPH": (N, "paths/lines/markers; edge binding planned"),
    },
    "ZIP": {
        **_common,
        "WRITE": (X, "never repack originals"),
        "PATCH": (X, ""),
        "LINT": (N, "reverse-Kahn status + kind"),
        "SLICE": (N, "entries up to depth 5"),
        "SEMANTIC_SECTIONS": (N, "top folders, repo/handover markers, OG5 hits"),
        "OUTLINE_LEVELS": (N, "entry depth"),
        "BULLET_LEVELS": (X, ""),
        "NUMBER_LEVELS": (X, ""),
        "FONTS": (X, ""),
        "COLOURS": (X, ""),
        "SIZE": (N, "compressed / uncompressed"),
        "TEXT_BOXES": (X, ""),
        "SHAPES_GRAPH": (N, "zip lineage graph (Kahn layers)"),
    },
}

OUTPUTS = {
    "same": "repaired or rebuilt copy beside the original: <name>.gg-<step>.<ext>; pinned originals never overwritten",
    "facts": "inventory/probe/<TYPE>.jsonl (one record per file)",
    "debug": "probe 'error' field, magic mismatch list, Office lock list",
    "lint": "planned: <TYPE>.lint.jsonl",
    "qa": "receipt with catalogue K-ids + LADDER ids, engine versions, sha256 in and out",
}


def sipoc(code: str) -> dict:
    src = "configured root folders (estate configuration: roots)"
    return {
        "L1_INTAKE": {
            "S": src,
            "I": f"{code} files",
            "P": "E0 discover, E1 identify (magic+sha256), E2 classify (type, epic, family)",
            "O": "root_inventory.csv/json",
            "C": "L2, owner (move plan)",
        },
        "L2_READ_PARSE": {
            "S": "L1",
            "I": "inventory rows",
            "P": "E3 open read-only, parse parts, slice",
            "O": f"probe/{code}.jsonl",
            "C": "L3",
        },
        "L3_EXTRACT": {
            "S": "L2",
            "I": "parsed parts",
            "P": "E4 outline, bullets, numbers, fonts, colours, sizes, text boxes, shapes graph",
            "O": "KNOWN_ELEMENTS.md, graph edges",
            "C": "L4, design QA",
        },
        "L4_SEMANTIC": {
            "S": "L3 + OG5 repos (RTM, ledger, lanes)",
            "I": "sections, text samples",
            "P": "E5 semantic map, E6 decide",
            "O": "decision per file (" + ", ".join(DECISIONS) + ")",
            "C": "owner, L5",
        },
        "L5_WRITE_PATCH": {
            "S": "L4 decisions",
            "I": "REWORK items",
            "P": "E7 build/patch copy-on-write",
            "O": "*.gg-<step> copies",
            "C": "L6",
        },
        "L6_QA_RELEASE": {
            "S": "L5 + catalogue",
            "I": "candidates",
            "P": "E8 K-checks, E9 receipt",
            "O": "receipt, release to OG5 repo or archive",
            "C": "OG5 repo owners, point release",
        },
    }


def agg_known(code: str) -> dict:
    recs = []
    for rid in REAL_ROOTS:
        p = inv_dir(rid) / "probe" / f"{code}.jsonl"
        if p.exists():
            recs += [
                json.loads(l) for l in p.read_text("utf-8").split("\n") if l.strip()
            ]
    if not recs:
        return {}
    num = collections.Counter()
    fonts = collections.Counter()
    colours = collections.Counter()
    outl = collections.Counter()
    errors = []
    for r in recs:
        if "error" in r:
            errors.append(f"{r['name']}: {r['error']}")
        for k, v in r.items():
            if isinstance(v, bool):
                num[k] += int(v)
            elif isinstance(v, (int, float)) and k not in ("sha256",):
                num[k] += v
        fonts.update(r.get("fonts") or {})
        colours.update(r.get("colours") or {})
        outl.update(r.get("outline_levels") or {})
    return {
        "files": len(recs),
        "totals": dict(num.most_common(30)),
        "fonts": dict(fonts.most_common(12)),
        "colours": dict(colours.most_common(12)),
        "outline_levels": dict(sorted(outl.items())),
        "errors": errors,
    }


def main() -> int:
    rows, meta = [], {}
    for (
        rid
    ) in (
        ROOTS
    ):  # every root gets its final rows; only REAL_ROOTS feed engines and graph
        ip = inv_dir(rid) / "root_inventory.json"
        if not ip.exists():
            continue
        inv = json.loads(ip.read_text("utf-8"))
        meta[rid] = inv
        rc = inv_dir(rid) / "probe" / "content_reclass.json"
        reclass = (
            dict(map(tuple, json.loads(rc.read_text("utf-8")))) if rc.exists() else {}
        )
        for r in inv["rows"]:
            r["root_id"] = rid
            r["epic_final"] = reclass.get(r["name"], r["epic"])
            r["epic_source"] = (
                "content"
                if r["name"] in reclass
                else ("name" if r["epic"] != "E0_OTHER" else "none")
            )
        (inv_dir(rid) / "root_inventory_final.json").write_text(
            json.dumps(inv["rows"], ensure_ascii=False, indent=0), "utf-8"
        )
        if rid not in REAL_ROOTS:
            del meta[rid]
            continue
        rows += inv["rows"]
    inv = meta.get("MI") or next(
        iter(meta.values()), {"generated": "n/a", "git_head": ""}
    )  # a fresh estate may have no real root yet
    epic_repo = {e[0]: e[1] for e in EPICS} | {OTHER_EPIC[0]: None}
    epics = list(epic_repo)
    ENG.mkdir(parents=True, exist_ok=True)
    GRAPH.mkdir(parents=True, exist_ok=True)
    index = []
    for letter, code, exts, cat in TYPES:
        d = ENG / f"{letter}_{code}.gg_Engine"
        (d / "adr").mkdir(parents=True, exist_ok=True)
        mine = [r for r in rows if r["type"] == code]
        by_epic = collections.Counter(r["epic_final"] for r in mine)
        hints = collections.Counter(r["decision_hint"] for r in mine)
        known = agg_known(code)
        caps = CAPS[code]
        manifest = {
            "schema": SCHEMA + "#engine",
            "engine": f"{code}.gg_Engine",
            "letter": letter,
            "extensions": list(exts),
            "bindings": {
                "public_catalog": {
                    "ref": PUBLIC_CATALOG,
                    "type": cat or f"PROPOSED:{code}",
                    "checks": CATALOG_CHECKS.get(
                        code,
                        f"PROPOSED K-{code}-01.. (extension PR to the hub; generic only)",
                    ),
                },
                "private_registry": {
                    "ref": PRIVATE_REGISTRY,
                    "ladder": LADDER.get(code, "none yet"),
                },
                "rule": "Bind, never copy: engine and K-check definitions stay with their owners (ADR-0001).",
            },
            "capabilities": {
                c: {"status": caps[c][0], "how": caps[c][1]} for c in CAPABILITIES
            },
            "lanes": [l for l, _ in LANES],
            "dag": [s for s, _, _ in DAG],
            "sipoc": sipoc(code),
            "outputs": OUTPUTS,
            "inventory": {
                "by_root": dict(collections.Counter(r["root_id"] for r in mine)),
                "files": len(mine),
                "bytes": sum(r["bytes"] for r in mine),
                "by_epic": dict(by_epic),
                "decision_hints": dict(hints),
            },
            "repo_rules": {
                repo: f"{repo} AGENTS.md / CLAUDE.md govern any file of this type landed there"
                for repo in OG5
            },
        }
        (d / "ENGINE.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True, width=140),
            "utf-8",
        )
        # queue: what this engine processes, in order (epic, decision, newest first)
        order = {
            k: i
            for i, k in enumerate(
                [
                    "KEEP_CANONICAL",
                    "ACTIVATE_ZIP",
                    "REWORK",
                    "PARK",
                    "SUPERSEDED",
                    "DUPLICATE",
                    "STALE_ARCHIVE",
                ]
            )
        }
        q = sorted(
            mine,
            key=lambda r: (
                (
                    epics.index(r["epic_final"])
                    if r["epic_final"] in epics
                    else len(epics)
                ),
                order.get(r["decision_hint"], 9),
                r["mtime"],
            ),
            reverse=False,
        )
        lines = [
            "root_id,epic_final,epic_source,decision_hint,staleness,git_tracked,office_lock_present,family_tip,bytes,mtime,name"
        ]
        lines += [
            ",".join(
                str(r[k])
                for k in [
                    "root_id",
                    "epic_final",
                    "epic_source",
                    "decision_hint",
                    "staleness",
                    "git_tracked",
                    "office_lock_present",
                    "family_tip",
                    "bytes",
                    "mtime",
                ]
            )
            + ',"'
            + r["name"].replace('"', "'")
            + '"'
            for r in q
        ]
        (d / "QUEUE.csv").write_text("\n".join(lines) + "\n", "utf-8")
        cap_rows = "\n".join(
            f"| {c} | {caps[c][0]} | {caps[c][1]} |" for c in CAPABILITIES
        )
        ke = known
        (d / "README.md").write_text(
            f"""# {letter}) {code}.gg_Engine

Extensions: {", ".join(exts)}. Files in the configured roots: **{len(mine)}** ({sum(r['bytes'] for r in mine) / 1e6:,.0f} MB).

Binds to: `{PUBLIC_CATALOG}` type **{cat or 'PROPOSED:' + code}** and `{PRIVATE_REGISTRY}` ({LADDER.get(code, 'no LADDER range yet')}).
This folder defines no engine or K-check of its own (ADR-0001). It records what this estate needs from those owners.

## By epic
{chr(10).join(f'- {e} -> {epic_repo[e] or "unassigned"}: {by_epic.get(e, 0)}' for e in epics)}

## Capabilities (now = runs today on this PC)
| Capability | Status | How |
|---|---|---|
{cap_rows}

## Known elements (E4, first pass)
- Totals: {json.dumps(ke.get('totals', {}), ensure_ascii=False)}
- Outline levels: {json.dumps(ke.get('outline_levels', {}))}
- Fonts: {json.dumps(ke.get('fonts', {}), ensure_ascii=False)}
- Colours: {json.dumps(ke.get('colours', {}))}
- Probe errors: {len(ke.get('errors', []))}{''.join(chr(10) + '  - ' + e for e in ke.get('errors', [])[:10])}

## Files here
- `ENGINE.yaml` manifest: bindings, capability matrix, lanes, DAG, SIPOC per lane, outputs, repo rules
- `QUEUE.csv` processing order: epic, then decision, then age
- `SKILL.md` how an agent runs this engine; `RULES.md` markdown rules; `adr/` decisions; `NOTES.md` hand notes (never regenerated)
""",
            "utf-8",
        )
        (d / "SKILL.md").write_text(
            f"""---
name: {code.lower()}-gg-engine
description: Process {code} files ({", ".join(exts)}) from the estate through the E0-E9 engine DAG. Use when asked to read, parse, outline, extract styles/text boxes/graphs from, patch, QA or route a {code} file.
---

1. Find the file in `../../inventory/root_inventory.csv` (type {code}). No row: run `DMAIC_V3/binary_engines/estate_inventory.py` first.
2. Read facts in `../../inventory/probe/{code}.jsonl`. Missing: `python -I DMAIC_V3/binary_engines/estate_probe.py --types {code}`.
3. Check `ENGINE.yaml` capabilities. Never do a `planned` capability by hand: record the gap in NOTES.md.
4. WRITE and PATCH make copies only (`<name>.gg-<step>{exts[0]}`). Never touch a file with `office_lock_present` or a pinned SSOT binary.
5. QA: cite catalogue IDs ({CATALOG_CHECKS.get(code, 'PROPOSED K-' + code)}) and {LADDER.get(code, 'no LADDER range')}; run the
   private registry's binary QA read-only (see the configuration). UNKNOWN is never PASS.
6. Route by `epic_final` to its OG5 repo; that repo's AGENTS.md/CLAUDE.md rules apply from then on.
""",
            "utf-8",
        )
        (d / "RULES.md").write_text(
            f"""# {code} markdown and handling rules

- R1 Originals are read-only. Outputs are copies with a `.gg-<step>` infix and a sha256 receipt.
- R2 A file with an Office lock (`~$`) is open: skip it this pass.
- R3 Files tracked by a git checkout move only with `git mv` on a branch, never a plain move (`GIT_MV_ON_BRANCH`).
- R4 Content of a private epic never lands in a public repo; it routes to its private repo or stays local (configuration: `private: true`).
- R5 Personal documents (`og5_repo=_personal`) go to `_personal/` (git-excluded) and are never probed beyond identity.
- R6 Definitions belong to the catalogue owners; this folder binds and reports gaps (ADR-0001).
- R7 Every count in a report names the inventory run it came from (generated timestamp + git HEAD).
""",
            "utf-8",
        )
        (d / "adr" / "ADR-0001-bind-not-copy.md").write_text(
            f"""# ADR-0001 Bind to the engine catalogue; do not copy it

Status: proposed (2026-11-12)

Context: generic engines and K-<TYPE>-NN checks already have an owner in `{PUBLIC_CATALOG}`; project bindings in
`{PRIVATE_REGISTRY}`. A second definition here would fork them.

Decision: {code}.gg_Engine stores bindings, a capability matrix and gaps only. A missing type or check is proposed upstream:
generic parts to the public catalogue, project-specific parts to the private registry.

Consequence: {"this type already exists in the catalogue" if cat else f"{code} is not in the catalogue yet; an extension PR is required before any K-{code} check counts"}.
""",
            "utf-8",
        )
        notes = d / "NOTES.md"
        if not notes.exists():
            notes.write_text(
                f"# {code} notes (hand-written, never regenerated)\n\n", "utf-8"
            )
        index.append(
            (
                letter,
                code,
                cat,
                len(mine),
                by_epic,
                sum(1 for c in CAPABILITIES if caps[c][0] == N),
            )
        )

    # ---------------- golden-thread graph (mycelium): nodes + edges
    nodes, edges = [], []
    add = lambda i, k, **a: nodes.append({"id": i, "kind": k, **a})  # noqa: E731
    for repo in OG5:
        add(f"repo:{repo}", "repo")
    for rid, (rpath, depth) in ROOTS.items():
        if rid in meta:
            add(
                f"root:{rid}",
                "root",
                path=str(rpath),
                depth=depth,
                git_head=meta[rid].get("git_head", ""),
            )
    for e in epics:
        add(f"epic:{e}", "epic")
        (
            edges.append(
                {"s": f"epic:{e}", "t": f"repo:{epic_repo[e]}", "rel": "converges_on"}
            )
            if epic_repo[e]
            else None
        )
    for l, desc in LANES:
        add(f"lane:{l}", "lane", desc=desc)
    for s, deps, lane in DAG:
        add(f"step:{s}", "step")
        edges.append({"s": f"step:{s}", "t": f"lane:{lane}", "rel": "in_lane"})
        edges += [{"s": f"step:{d}", "t": f"step:{s}", "rel": "precedes"} for d in deps]
    for letter, code, _, cat in TYPES:
        add(f"type:{code}", "type", letter=letter, catalog=cat)
        edges.append({"s": f"type:{code}", "t": "step:E0_DISCOVER", "rel": "enters"})
    for r in rows:
        fid = f"file:{r['root_id']}:{r['name']}"
        add(
            fid,
            "file",
            root=r["root_id"],
            type=r["type"],
            epic=r["epic_final"],
            hint=r["decision_hint"],
            bytes=r["bytes"],
        )
        edges += [
            {"s": fid, "t": f"root:{r['root_id']}", "rel": "lives_in"},
            {"s": fid, "t": f"type:{r['type']}", "rel": "is_a"},
            {"s": fid, "t": f"epic:{r['epic_final']}", "rel": "belongs_to"},
        ]
        if r.get("duplicate_of"):
            edges.append(
                {
                    "s": fid,
                    "t": f"file:{r['root_id']}:{r['duplicate_of']}",
                    "rel": "duplicate_of",
                }
            )
    fam = collections.defaultdict(list)
    for r in rows:
        fam[(r["root_id"], r["type"], r["family"])].append(r)
    for g in fam.values():
        g.sort(key=lambda r: r["mtime"])
        edges += [
            {
                "s": f"file:{x['root_id']}:{x['name']}",
                "t": f"file:{y['root_id']}:{y['name']}",
                "rel": "superseded_by",
            }
            for x, y in zip(g, g[1:])
        ]
    # same bytes in two roots = one artefact copied around (cross-root golden thread)
    by_sha = collections.defaultdict(set)
    for r in rows:
        if r["sha256"]:
            by_sha[r["sha256"]].add(r["root_id"] + ":" + r["name"])
    for group in by_sha.values():
        g = sorted(group)
        if len({x.split(":", 1)[0] for x in g}) > 1:
            edges += [
                {"s": f"file:{x}", "t": f"file:{g[0]}", "rel": "same_bytes_as"}
                for x in g[1:]
            ]
    for rid in meta:
        for z in json.loads(
            (inv_dir(rid) / "zip_reverse_kahn.json").read_text("utf-8")
        )["zips"]:
            edges += [
                {
                    "s": f"file:{rid}:{z['name']}",
                    "t": f"file:{rid}:{n}",
                    "rel": "zip_successor",
                }
                for n in z["successors"]
            ]
    (GRAPH / "estate_graph.json").write_text(
        json.dumps(
            {
                "schema": SCHEMA + "#graph",
                "generated_from": inv["generated"],
                "git_head": inv["git_head"],
                "nodes": nodes,
                "edges": edges,
            },
            ensure_ascii=False,
        ),
        "utf-8",
    )

    # ---------------- index
    head = (
        "| Engine | Catalogue | Files | "
        + " | ".join(e.split("_")[0] for e in epics)
        + " | Capabilities now |"
    )
    body = "\n".join(
        f"| [{l} {c}](engines/{l}_{c}.gg_Engine/README.md) | {cat or '**proposed**'} | {n} | "
        + " | ".join(str(be.get(e, 0)) for e in epics)
        + f" | {k}/{len(CAPABILITIES)} |"
        for l, c, cat, n, be, k in index
    )
    final = collections.Counter((r["type"], r["epic_final"]) for r in rows)
    other_left = sum(v for (t, e), v in final.items() if e == "E0_OTHER")
    roots_line = "; ".join(
        f"{rid} {ROOTS[rid][1]} ({sum(1 for r in rows if r['root_id'] == rid)} files, {m['generated']}, HEAD {(m.get('git_head') or 'n/a')[:10]})"
        for rid, m in meta.items()
    )
    (EST / "ENGINES_INDEX.md").write_text(
        f"# TYPE.gg_Engine index\n\nRoots: {roots_line}.\nEpics after the content pass; "
        f"E0_OTHER left: {other_left}.\n\n"
        f"{head}\n|---|---|---:|" + "---:|" * len(epics) + "---:|\n" + body + "\n\n"
        f"Graph: graph/estate_graph.json ({len(nodes)} nodes, {len(edges)} edges).\n",
        "utf-8",
    )
    print((EST / "ENGINES_INDEX.md").read_text("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
