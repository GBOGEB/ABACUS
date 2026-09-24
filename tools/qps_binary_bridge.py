#!/usr/bin/env python3
"""Normalize governed QPS binary/static inputs into a provenance-bound bridge.

Supported families:
- DOCX (OOXML)
- XLSX (OOXML)
- PPTX (OOXML)
- PDF (pypdf)
- HTML (standard-library parser)

The bridge is derived analysis only. It preserves source identity and semantic
content fingerprints without changing child/source authority.
"""

from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from typing import Any
import xml.etree.ElementTree as ET
import zipfile



SCHEMA = "abacus-binary-bridge/v1"
PARSER_VERSION = "1.0.0"
PRODUCER_REPOSITORY = "GBOGEB/ABACUS"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/"
    "relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
}


def sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 hex digest for bytes."""
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(value: object) -> str:
    """Hash a deterministic JSON representation."""
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256_bytes(payload)


def git_sha() -> str:
    """Resolve the exact producer commit from the ABACUS worktree."""
    value = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        text=True,
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise RuntimeError("unable to resolve producer commit")
    return value


def _inline_text(
    node: ET.Element,
    xpath: str,
    namespaces: dict[str, str],
) -> str:
    """Join formatting runs without inventing whitespace between them."""
    parts = [
        item.text or ""
        for item in node.findall(xpath, namespaces)
        if item.text
    ]
    return " ".join("".join(parts).split())


def _paragraph_text(
    node: ET.Element,
    paragraph_xpath: str,
    text_xpath: str,
    namespaces: dict[str, str],
) -> str:
    """Separate structural paragraphs while preserving inline run text."""
    paragraphs = [
        _inline_text(paragraph, text_xpath, namespaces)
        for paragraph in node.findall(paragraph_xpath, namespaces)
    ]
    return " ".join(part for part in paragraphs if part)


def _zip_xml(archive: zipfile.ZipFile, member: str) -> ET.Element:
    return ET.fromstring(archive.read(member))


def extract_docx(path: Path) -> dict[str, Any]:
    """Extract paragraphs, heading anchors, and table rows from DOCX."""
    with zipfile.ZipFile(path) as archive:
        root = _zip_xml(archive, "word/document.xml")

    blocks: list[dict[str, Any]] = []
    index = 0
    for child in root.findall(".//w:body/*", NS):
        local = child.tag.rsplit("}", 1)[-1]
        if local == "p":
            text = _inline_text(child, ".//w:t", NS)
            if not text:
                continue
            style = child.find("./w:pPr/w:pStyle", NS)
            style_id = (
                style.attrib.get(f"{{{NS['w']}}}val")
                if style is not None
                else None
            )
            index += 1
            blocks.append(
                {
                    "anchor": f"paragraph:{index}",
                    "kind": "paragraph",
                    "style": style_id,
                    "text": text,
                }
            )
        elif local == "tbl":
            rows: list[list[str]] = []
            for row in child.findall("./w:tr", NS):
                rows.append(
                    [
                        _paragraph_text(cell, ".//w:p", ".//w:t", NS)
                        for cell in row.findall("./w:tc", NS)
                    ]
                )
            index += 1
            blocks.append(
                {
                    "anchor": f"table:{index}",
                    "kind": "table",
                    "rows": rows,
                }
            )

    return {
        "kind": "docx",
        "blocks": blocks,
        "extraction_quality": {
            "status": "STRUCTURED",
            "parser": "ooxml_xml",
        },
    }


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    member = "xl/sharedStrings.xml"
    if member not in archive.namelist():
        return []
    root = _zip_xml(archive, member)
    return [
        _inline_text(item, ".//s:t", NS)
        for item in root.findall("./s:si", NS)
    ]


def _xlsx_sheet_map(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = _zip_xml(archive, "xl/workbook.xml")
    rels = _zip_xml(archive, "xl/_rels/workbook.xml.rels")
    targets = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall("./rel:Relationship", NS)
    }

    sheets: list[tuple[str, str]] = []
    for sheet in workbook.findall("./s:sheets/s:sheet", NS):
        name = sheet.attrib["name"]
        rel_id = sheet.attrib[f"{{{NS['r']}}}id"]
        target = targets[rel_id].lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        sheets.append((name, target))
    return sheets


def extract_xlsx(path: Path) -> dict[str, Any]:
    """Extract sheet/cell values and formulas from XLSX."""
    with zipfile.ZipFile(path) as archive:
        shared = _xlsx_shared_strings(archive)
        sheets_out: list[dict[str, Any]] = []
        for name, member in _xlsx_sheet_map(archive):
            root = _zip_xml(archive, member)
            cells: list[dict[str, Any]] = []
            for cell in root.findall(".//s:c", NS):
                ref = cell.attrib.get("r", "")
                cell_type = cell.attrib.get("t")
                value_node = cell.find("./s:v", NS)
                inline = cell.find("./s:is", NS)
                formula_node = cell.find("./s:f", NS)

                value: Any = None
                if inline is not None:
                    value = _inline_text(inline, ".//s:t", NS)
                elif value_node is not None:
                    raw = value_node.text or ""
                    if cell_type == "s" and raw.isdigit():
                        idx = int(raw)
                        value = shared[idx] if idx < len(shared) else raw
                    else:
                        value = raw

                if value is None and formula_node is None:
                    continue
                cells.append(
                    {
                        "anchor": f"{name}!{ref}",
                        "value": value,
                        "formula": (
                            formula_node.text
                            if formula_node is not None
                            else None
                        ),
                        "formula_type": (
                            formula_node.attrib.get("t")
                            if formula_node is not None
                            else None
                        ),
                        "formula_shared_index": (
                            formula_node.attrib.get("si")
                            if formula_node is not None
                            else None
                        ),
                    }
                )
            sheets_out.append(
                {
                    "anchor": f"sheet:{name}",
                    "name": name,
                    "cells": cells,
                }
            )
    return {
        "kind": "xlsx",
        "sheets": sheets_out,
        "extraction_quality": {
            "status": "STRUCTURED",
            "parser": "ooxml_xml",
        },
    }


def _slide_number(member: str) -> int:
    match = re.search(r"slide(\d+)\.xml$", member)
    return int(match.group(1)) if match else 0


def extract_pptx(path: Path) -> dict[str, Any]:
    """Extract ordered slide text from PPTX."""
    with zipfile.ZipFile(path) as archive:
        members = sorted(
            (
                name
                for name in archive.namelist()
                if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
            ),
            key=_slide_number,
        )
        slides = []
        for member in members:
            number = _slide_number(member)
            root = _zip_xml(archive, member)
            text = _paragraph_text(root, ".//a:p", ".//a:t", NS)
            slides.append(
                {
                    "anchor": f"slide:{number}",
                    "number": number,
                    "text": text,
                }
            )
    return {
        "kind": "pptx",
        "slides": slides,
        "extraction_quality": {
            "status": "STRUCTURED",
            "parser": "ooxml_xml",
        },
    }


def _pdf_literal_fallback(path: Path) -> dict[str, Any]:
    """Extract uncompressed PDF literal strings when pypdf is unavailable."""
    raw = path.read_bytes().decode("latin-1", errors="ignore")
    page_count = max(
        1,
        len(re.findall(r"/Type\s*/Page(?!s)", raw)),
    )
    literals = [
        bytes(value, "latin-1").decode(
            "unicode_escape",
            errors="ignore",
        )
        for value in re.findall(r"\(([^()]*)\)\s*Tj", raw)
    ]
    text = " ".join(" ".join(literals).split())
    pages = [
        {
            "anchor": f"page:{number}",
            "number": number,
            "text": text if number == 1 else "",
        }
        for number in range(1, page_count + 1)
    ]
    return {
        "kind": "pdf",
        "pages": pages,
        "extraction_quality": {
            "status": "FALLBACK",
            "parser": "pdf_literal_strings",
        },
    }


def extract_pdf(path: Path) -> dict[str, Any]:
    """Extract page text with stable page anchors from PDF."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return _pdf_literal_fallback(path)

    try:
        reader = PdfReader(str(path))
        pages = []
        for number, page in enumerate(reader.pages, start=1):
            text = " ".join((page.extract_text() or "").split())
            pages.append(
                {
                    "anchor": f"page:{number}",
                    "number": number,
                    "text": text,
                }
            )
        return {
            "kind": "pdf",
            "pages": pages,
            "extraction_quality": {
                "status": "STRUCTURED",
                "parser": "pypdf",
            },
        }
    except Exception:
        return _pdf_literal_fallback(path)


class SemanticHTMLParser(HTMLParser):
    """Collect stable text blocks with heading and element anchors."""

    CAPTURE_TAGS = {
        "body",
        "main",
        "article",
        "section",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "li",
        "td",
        "th",
    }
    IGNORED_TAGS = {"head", "script", "style", "template"}

    def __init__(self) -> None:
        super().__init__()
        self.blocks: list[dict[str, Any]] = []
        self._stack: list[dict[str, Any]] = []
        self._index = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self._stack.append(
            {
                "tag": tag,
                "attrs": {key: value or "" for key, value in attrs},
                "parts": [],
            }
        )

    def handle_data(self, data: str) -> None:
        if not data.strip():
            return
        if any(frame["tag"] in self.IGNORED_TAGS for frame in self._stack):
            return
        for frame in reversed(self._stack):
            if frame["tag"] in self.CAPTURE_TAGS:
                frame["parts"].append(data)
                return

    def handle_endtag(self, tag: str) -> None:
        matching = next(
            (
                index
                for index in range(len(self._stack) - 1, -1, -1)
                if self._stack[index]["tag"] == tag
            ),
            None,
        )
        if matching is None:
            return
        frame = self._stack.pop(matching)
        if tag not in self.CAPTURE_TAGS:
            return
        text = " ".join(" ".join(frame["parts"]).split())
        if text:
            self._index += 1
            explicit = frame["attrs"].get("id")
            anchor = explicit or f"{tag}:{self._index}"
            self.blocks.append(
                {
                    "anchor": anchor,
                    "kind": tag,
                    "text": text,
                }
            )


def extract_html(path: Path) -> dict[str, Any]:
    """Extract heading/body/table-cell text from static HTML."""
    parser = SemanticHTMLParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return {
        "kind": "html",
        "blocks": parser.blocks,
        "extraction_quality": {
            "status": "STRUCTURED",
            "parser": "html_parser",
        },
    }


EXTRACTORS = {
    ".docx": extract_docx,
    ".xlsx": extract_xlsx,
    ".pptx": extract_pptx,
    ".pdf": extract_pdf,
    ".html": extract_html,
    ".htm": extract_html,
}


def normalize_source(
    path: Path,
    *,
    authority: str,
    lifecycle_status: str,
    trace_links: list[str],
    supersedes: list[str],
    producer_commit: str,
) -> dict[str, Any]:
    """Create one minimum bridge tuple plus normalized semantic content."""
    suffix = path.suffix.lower()
    if suffix not in EXTRACTORS:
        raise ValueError(f"unsupported source family: {suffix}")
    if not path.is_file():
        raise FileNotFoundError(path)

    raw = path.read_bytes()
    normalized = EXTRACTORS[suffix](path)
    semantic_sha = canonical_sha256(normalized)

    return {
        "source_id": path.name,
        "source_path": path.as_posix(),
        "source_sha256": sha256_bytes(raw),
        "semantic_sha256": semantic_sha,
        "authority": authority,
        "lifecycle_status": lifecycle_status,
        "hierarchy_node": normalized,
        "extraction_quality": normalized.get(
            "extraction_quality",
            {"status": "UNKNOWN", "parser": "unknown"},
        ),
        "trace_links": trace_links,
        "producer_repository": PRODUCER_REPOSITORY,
        "producer_commit": producer_commit,
        "parser_or_builder_version": (
            f"qps_binary_bridge/{PARSER_VERSION}"
        ),
        "artifact_hashes": {
            "source_sha256": sha256_bytes(raw),
            "semantic_sha256": semantic_sha,
        },
        "freshness_state": "CURRENT_AT_PARSE",
        "supersedes": supersedes,
    }


def build_bridge(
    paths: list[Path],
    *,
    authority: str,
    lifecycle_status: str,
    trace_links: list[str] | None = None,
    supersedes: list[str] | None = None,
) -> dict[str, Any]:
    """Build a deterministic multi-source bridge package."""
    producer_commit = git_sha()
    sources = [
        normalize_source(
            path,
            authority=authority,
            lifecycle_status=lifecycle_status,
            trace_links=trace_links or [],
            supersedes=supersedes or [],
            producer_commit=producer_commit,
        )
        for path in paths
    ]
    return {
        "schema": SCHEMA,
        "producer_repository": PRODUCER_REPOSITORY,
        "producer_commit": producer_commit,
        "parser_version": PARSER_VERSION,
        "authority_rule": (
            "normalized output is derived; source/child authority is unchanged"
        ),
        "sources": sources,
        "bridge_semantic_sha256": canonical_sha256(
            [
                {
                    "source_id": item["source_id"],
                    "semantic_sha256": item["semantic_sha256"],
                }
                for item in sources
            ]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authority", required=True)
    parser.add_argument("--lifecycle-status", default="CURRENT")
    parser.add_argument("--trace-link", action="append", default=[])
    parser.add_argument("--supersedes", action="append", default=[])
    args = parser.parse_args()

    bridge = build_bridge(
        args.sources,
        authority=args.authority,
        lifecycle_status=args.lifecycle_status,
        trace_links=args.trace_link,
        supersedes=args.supersedes,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(bridge, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
