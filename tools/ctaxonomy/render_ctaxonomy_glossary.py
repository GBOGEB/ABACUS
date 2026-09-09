#!/usr/bin/env python3
"""Render a deterministic, non-authoritative CTaxonomy glossary projection.

Input is a child-compatible semantic-support YAML. The renderer never changes IDs,
definitions or engineering state.
"""
from __future__ import annotations
import argparse
import html
from pathlib import Path
import yaml


def render(data: dict) -> str:
    terms = data.get("terms", {})
    aliases = data.get("aliases", {})
    alias_map: dict[str, list[str]] = {}
    for alias, record in aliases.items():
        alias_map.setdefault(record.get("resolves_to", ""), []).append(alias)
    rows = []
    for term_id in sorted(terms):
        term = terms[term_id]
        friendly = term.get("canonical_term", term_id)
        definition = term.get("definition", "")
        alias_text = ", ".join(sorted(alias_map.get(term_id, [])))
        rows.append(
            "<tr>"
            f"<td><code>{html.escape(term_id)}</code></td>"
            f"<td>{html.escape(str(friendly))}</td>"
            f"<td>{html.escape(str(definition))}</td>"
            f"<td>{html.escape(alias_text)}</td>"
            "</tr>"
        )
    return """<!doctype html><html><head><meta charset='utf-8'><title>CTaxonomy Glossary</title></head><body>
<h1>CTaxonomy Glossary</h1>
<p>Projection only. Canonical taxonomy identity and engineering authority remain in the child SSOT.</p>
<table><thead><tr><th>ID</th><th>Term</th><th>Definition</th><th>Aliases</th></tr></thead><tbody>
""" + "\n".join(rows) + "\n</tbody></table></body></html>\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("registry", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = yaml.safe_load(args.registry.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(data), encoding="utf-8")
    print(f"CTAXONOMY_RENDER=PASS terms={len(data.get('terms', {}))}")
    print("engineering_credit_delta=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
