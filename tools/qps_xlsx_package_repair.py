"""Restore source-native XLSX fields without reserializing candidate cell data.

This owned package engine complements the public-openpyxl trial. It never
calculates formulas or creates cached values. Only explicitly supported native
fields are transferred; every other package part/byte span stays candidate-owned.
The existing independent preservation reader must accept the final bytes before
the caller receives an output. Output remains a private qualification candidate.
"""

from __future__ import annotations

import argparse
import copy
import io
import json
import posixpath
import re
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from defusedxml.ElementTree import iterparse

try:
    from tools import qps_xlsx_native_features as native
except ModuleNotFoundError:
    import qps_xlsx_native_features as native

MAIN = native.MAIN
compare_content = native.compare_content
compare_features = native.compare_features
digest = native.digest
snapshot_xlsx = native.snapshot_xlsx

ENGINE_VERSION = "1.0.1"
PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
WORKBOOK_ORDER = (
    "fileVersion fileSharing workbookPr workbookProtection bookViews sheets "
    "functionGroups externalReferences definedNames calcPr oleSize "
    "customWorkbookViews pivotCaches smartTagPr smartTagTypes webPublishing "
    "fileRecoveryPr webPublishObjects extLst"
).split()
WORKSHEET_ORDER = (
    "sheetPr dimension sheetViews sheetFormatPr cols sheetData sheetCalcPr "
    "sheetProtection protectedRanges scenarios autoFilter sortState "
    "dataConsolidate customSheetViews mergeCells phoneticPr conditionalFormatting "
    "dataValidations hyperlinks printOptions pageMargins pageSetup headerFooter "
    "rowBreaks colBreaks customProperties cellWatches ignoredErrors smartTags "
    "drawing legacyDrawing legacyDrawingHF picture oleObjects controls "
    "webPublishItems tableParts extLst"
).split()


@dataclass
class Span:
    """Namespace-aware, byte-addressed element; never a serialization model."""

    name: str
    attributes: dict[str, str]
    namespaces: dict[str, str]
    start: int
    opening_end: int
    self_closing: bool
    closing_start: int = 0
    end: int = 0
    children: list[Span] = field(default_factory=list)


def _tag_end(data: bytes, start: int) -> int:
    quote = None
    for pos in range(start, len(data)):
        char = data[pos]
        if quote is not None:
            if char == quote:
                quote = None
        elif char in (34, 39):
            quote = char
        elif char == 62:
            return pos + 1
    raise ValueError("UNTERMINATED_XML_TAG")


def quoteattr(value: str) -> str:
    """Escape a namespace URI or fixed native attribute as XML text."""
    return (
        '"'
        + value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace("\r", "&#13;")
        .replace("\n", "&#10;")
        .replace("\t", "&#9;")
        + '"'
    )


def _tokens(data: bytes):
    """Locate markup only; defusedxml supplies every parsed name and attribute."""
    position = 0
    while True:
        start = data.find(b"<", position)
        if start < 0:
            return
        skip = next(
            (
                end
                for prefix, end in (
                    (b"<!--", b"-->"),
                    (b"<![CDATA[", b"]]>"),
                    (b"<?", b"?>"),
                )
                if data.startswith(prefix, start)
            ),
            None,
        )
        if skip is not None:
            stop = data.find(skip, start + 2)
            if stop < 0:
                raise ValueError("UNTERMINATED_XML_MARKUP")
            position = stop + len(skip)
            continue
        end = _tag_end(data, start)
        yield (
            "end" if data.startswith(b"</", start) else "start",
            start,
            end,
            data[end - 2 : end] == b"/>",
        )
        position = end


def _index(data: bytes) -> Span:
    if re.search(rb"<!\s*(?:DOCTYPE|ENTITY)\b", data.replace(b"\0", b""), re.I):
        raise ValueError("UNSUPPORTED_XML_DECLARATION")
    data.decode("utf-8-sig")
    encoding = re.search(rb"<\?xml\b[^?]*encoding\s*=\s*['\"]([^'\"]+)", data)
    if encoding and encoding[1].lower() not in {b"utf-8", b"utf8", b"us-ascii"}:
        raise ValueError("UNSUPPORTED_XML_ENCODING")
    stack: list[Span] = []
    roots: list[Span] = []
    pending: dict[str, str] = {}
    tokens = iter(_tokens(data))
    for event, value in iterparse(
        io.BytesIO(data),
        events=("start-ns", "start", "end"),
        forbid_dtd=True,
        forbid_entities=True,
        forbid_external=True,
    ):
        if event == "start-ns":
            prefix, uri = value
            pending[prefix or ""] = uri or ""
        elif event == "start":
            kind, position, opening_end, self_closing = next(tokens)
            if kind != "start":
                raise ValueError("XML_SPAN_ALIGNMENT_FAILURE")
            namespaces = dict(stack[-1].namespaces) if stack else {}
            namespaces.update(pending)
            pending.clear()

            def expanded(name):
                return name[1:].replace("}", "|", 1) if name.startswith("{") else name

            node = Span(
                expanded(value.tag),
                {expanded(k): v for k, v in value.attrib.items()},
                namespaces,
                position,
                opening_end,
                self_closing,
            )
            (stack[-1].children if stack else roots).append(node)
            stack.append(node)
        else:
            node = stack.pop()
            if node.self_closing:
                node.closing_start, node.end = node.opening_end - 2, node.opening_end
            else:
                kind, position, closing_end, _self_closing = next(tokens)
                if kind != "end":
                    raise ValueError("XML_SPAN_ALIGNMENT_FAILURE")
                node.closing_start, node.end = position, closing_end
    if next(tokens, None) is not None:
        raise ValueError("XML_SPAN_ALIGNMENT_FAILURE")
    if len(roots) != 1:
        raise ValueError("INVALID_XML_ROOT")
    return roots[0]


def _child(node: Span, local: str) -> Span | None:
    found = [n for n in node.children if n.name == MAIN + "|" + local]
    if len(found) > 1:
        raise ValueError("DUPLICATE_NATIVE_ELEMENT:" + local)
    return found[0] if found else None


def _fragment(data: bytes, node: Span | None) -> bytes:
    """Copy lexical content and make inherited namespace bindings explicit."""
    if node is None:
        return b""
    opening = data[node.start : node.opening_end]
    existing = {
        (match[1] or b"").decode()
        for match in re.finditer(rb"\sxmlns(?::([\w.-]+))?\s*=", opening)
    }
    declarations = b"".join(
        (" xmlns" + (":" + prefix if prefix else "") + "=" + quoteattr(uri)).encode()
        for prefix, uri in sorted(node.namespaces.items())
        if prefix not in existing and prefix != "xml"
    )
    boundary = node.opening_end - (2 if node.self_closing else 1)
    fragment = data[node.start : boundary] + declarations + data[boundary : node.end]
    _index(fragment)
    return fragment


def _replace_child(data: bytes, local: str, replacement: bytes, order) -> bytes:
    root = _index(data)
    old = _child(root, local)
    if old:
        return data[: old.start] + replacement + data[old.end :]
    if not replacement:
        return data
    if root.self_closing:
        raise ValueError("UNSUPPORTED_SELF_CLOSING_CONTAINER")
    position = root.closing_start
    rank = order.index(local)
    for node in root.children:
        name = node.name.removeprefix(MAIN + "|")
        if name in order and order.index(name) > rank:
            position = node.start
            break
    return data[:position] + replacement + data[position:]


def _sheet_states(data: bytes, states: dict[str, str]) -> bytes:
    root = _index(data)
    sheets = _child(root, "sheets")
    if sheets is None:
        raise ValueError("MISSING_WORKSHEETS")
    edits = []
    for node in sheets.children:
        if node.name != MAIN + "|sheet":
            raise ValueError("UNSUPPORTED_SHEET_ELEMENT")
        state = states[node.attributes["name"]]
        if node.attributes.get("state", "visible") == state:
            continue
        opening = data[node.start : node.opening_end]
        attribute = re.compile(rb"\sstate\s*=\s*(?:\"[^\"]*\"|'[^']*')")
        replacement = (" state=" + quoteattr(state)).encode()
        if attribute.search(opening):
            revised = attribute.sub(lambda _match: replacement, opening, count=1)
        else:
            boundary = len(opening) - (2 if node.self_closing else 1)
            revised = opening[:boundary] + replacement + opening[boundary:]
        edits.append((node.start, node.opening_end, revised))
    for start, end, revised in reversed(edits):
        data = data[:start] + revised + data[end:]
    return data


def _parts(raw: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(raw)) as package:
        return {name: package.read(name) for name in package.namelist()}


def _external_reference_bindings(parts: dict[str, bytes]) -> list[dict]:
    """Bind external formula indexes to ordered workbook relationship targets.

    Unchanged externalLink part bytes alone do not preserve [1], [2], ...:
    their positions are defined by workbook/externalReferences. Reject an
    unsupported or ambiguous binding before transplanting source names.
    """
    references = _child(_index(parts["xl/workbook.xml"]), "externalReferences")
    if references is None:
        return []
    rels = _index(parts["xl/_rels/workbook.xml.rels"])
    if rels.name != PACKAGE_REL + "|Relationships":
        raise ValueError("UNSUPPORTED_EXTERNAL_REFERENCE_BINDING")
    relationships = {}
    for node in rels.children:
        identifier = node.attributes.get("Id")
        if (
            node.name != PACKAGE_REL + "|Relationship"
            or not identifier
            or identifier in relationships
        ):
            raise ValueError("AMBIGUOUS_WORKBOOK_RELATIONSHIP")
        relationships[identifier] = node.attributes
    bindings = []
    for reference in references.children:
        identifier = reference.attributes.get(native.REL + "|id")
        relationship = relationships.get(identifier)
        if reference.name != MAIN + "|externalReference" or not relationship:
            raise ValueError("UNSUPPORTED_EXTERNAL_REFERENCE_BINDING")
        target = relationship.get("Target", "")
        resolved = posixpath.normpath(
            target.lstrip("/") if target.startswith("/") else "xl/" + target
        )
        if (
            relationship.get("Type") != native.REL + "/externalLink"
            or relationship.get("TargetMode", "Internal") != "Internal"
            or any(char in target for char in ("\\", ":", "?", "#", "%"))
            or not resolved.startswith("xl/externalLinks/")
            or resolved not in parts
        ):
            raise ValueError("UNSUPPORTED_EXTERNAL_REFERENCE_BINDING")
        bindings.append(
            {
                "reference_attributes": reference.attributes,
                "relationship_attributes": relationship,
                "resolved_part": resolved,
            }
        )
    return bindings


def _repack(candidate: bytes, parts: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(candidate)) as source, zipfile.ZipFile(
        output, "w"
    ) as target:
        target.comment = source.comment
        for item in source.infolist():
            target.writestr(copy.copy(item), parts[item.filename])
    return output.getvalue()


def _without_native_fields(data: bytes, *, workbook: bool) -> bytes:
    """Mask only the authorized fields for the final byte-footprint assertion."""
    root = _index(data)
    edits = []
    for local in (("definedNames", "calcPr") if workbook else ("autoFilter",)):
        node = _child(root, local)
        if node is not None:
            edits.append((node.start, node.end, b""))
    if workbook:
        sheets = _child(root, "sheets")
        if sheets is None:
            raise ValueError("MISSING_WORKSHEETS")
        for node in sheets.children:
            opening = data[node.start : node.opening_end]
            revised = re.sub(rb"\sstate\s*=\s*(?:\"[^\"]*\"|'[^']*')", b"", opening)
            edits.append((node.start, node.opening_end, revised))
    for start, end, replacement in sorted(edits, reverse=True):
        data = data[:start] + replacement + data[end:]
    return data


def repair_native_package(
    source: bytes,
    candidate: bytes,
    *,
    expected_source_sha: str,
    expected_candidate_sha: str,
) -> tuple[bytes, dict]:
    """Return bytes only after exact feature/content and package-footprint gates.

    This supported path restores AutoFilters, scoped names, sheet states and
    calculation properties. Hidden-row/column differences fail closed. It never
    restores a lost cell, formula attribute or cache from another evidence layer.
    """
    if digest(source) != expected_source_sha:
        raise ValueError("SOURCE_HASH_MISMATCH")
    if digest(candidate) != expected_candidate_sha:
        raise ValueError("CANDIDATE_HASH_MISMATCH")
    original, before = snapshot_xlsx(source), snapshot_xlsx(candidate)
    if [s["name"] for s in original["sheets"]] != [s["name"] for s in before["sheets"]]:
        raise ValueError("SHEET_SET_OR_ORDER_CHANGED")
    if not any(s["visibility"] == "visible" for s in original["sheets"]):
        raise ValueError("NO_VISIBLE_WORKSHEET")
    source_parts, candidate_parts = _parts(source), _parts(candidate)
    if any(name.startswith("_xmlsignatures/") for name in candidate_parts):
        raise ValueError("SIGNED_PACKAGE_REQUIRES_SIGNER")
    for parts in (source_parts, candidate_parts):
        if any(".." in name.split("/") or name.startswith("/") for name in parts):
            raise ValueError("INVALID_PACKAGE_MEMBER")

    def external(parts):
        return {
            name: digest(value)
            for name, value in parts.items()
            if name.startswith("xl/externalLinks/")
        }

    if external(source_parts) != external(candidate_parts):
        raise ValueError("UNSUPPORTED_EXTERNAL_LINK_CHANGE")
    external_bindings = _external_reference_bindings(source_parts)
    if external_bindings != _external_reference_bindings(candidate_parts):
        raise ValueError("UNSUPPORTED_EXTERNAL_REFERENCE_BINDING_CHANGE")
    parts = dict(candidate_parts)
    workbook = parts["xl/workbook.xml"]
    source_workbook = source_parts["xl/workbook.xml"]
    source_root = _index(source_workbook)
    for local in ("definedNames", "calcPr"):
        workbook = _replace_child(
            workbook,
            local,
            _fragment(source_workbook, _child(source_root, local)),
            WORKBOOK_ORDER,
        )
    workbook = _sheet_states(
        workbook, {s["name"]: s["visibility"] for s in original["sheets"]}
    )
    parts["xl/workbook.xml"] = workbook
    allowed = {"xl/workbook.xml"}
    preserved_sheet_data = []
    for old, current in zip(original["sheets"], before["sheets"]):
        for key in ("hidden_rows", "hidden_columns"):
            if old[key] != current[key]:
                raise ValueError("UNSUPPORTED_" + key.upper() + "_CHANGE")
        source_xml = source_parts[old["part"]]
        candidate_xml = candidate_parts[current["part"]]
        source_filter = _child(_index(source_xml), "autoFilter")
        if source_filter:
            stack = [source_filter]
            while stack:
                node = stack.pop()
                if node.name == MAIN + "|extLst" or not node.name.startswith(
                    MAIN + "|"
                ):
                    raise ValueError("UNSUPPORTED_FILTER_EXTENSION")
                stack.extend(node.children)
        revised = _replace_child(
            candidate_xml,
            "autoFilter",
            _fragment(source_xml, source_filter),
            WORKSHEET_ORDER,
        )
        # Check complete lexical sheetData, including rich text and all cell metadata.
        old_data, new_data = _child(_index(candidate_xml), "sheetData"), _child(
            _index(revised), "sheetData"
        )
        if old_data is None or new_data is None:
            raise ValueError("MISSING_SHEET_DATA")
        old_bytes = candidate_xml[old_data.start : old_data.end]
        new_bytes = revised[new_data.start : new_data.end]
        if old_bytes != new_bytes:
            raise ValueError("SHEET_DATA_BYTES_CHANGED")
        preserved_sheet_data.append({"sheet": old["name"], "sha256": digest(new_bytes)})
        parts[current["part"]] = revised
        allowed.add(current["part"])
    final = _repack(candidate, parts)
    after = snapshot_xlsx(final)
    native_losses = compare_features(original, after)
    content_losses = compare_content(before, after)
    final_parts = _parts(final)
    changed = sorted(
        name for name in candidate_parts if candidate_parts[name] != final_parts[name]
    )
    if set(candidate_parts) != set(final_parts) or not set(changed).issubset(allowed):
        raise ValueError("PACKAGE_FOOTPRINT_CHANGED")
    for name in changed:
        if _without_native_fields(
            candidate_parts[name], workbook=name == "xl/workbook.xml"
        ) != _without_native_fields(
            final_parts[name], workbook=name == "xl/workbook.xml"
        ):
            raise ValueError("UNAUTHORIZED_XML_BYTES_CHANGED:" + name)
    if native_losses or content_losses:
        raise ValueError(
            "REJECTED_SERIALIZED_LOSS:"
            + json.dumps({"native": native_losses, "content": content_losses})
        )
    receipt = {
        "schema": "abacus-xlsx-package-preservation/v1",
        "engine": {"name": "abacus-qps-xlsx-package-repair", "version": ENGINE_VERSION},
        "source_sha256": digest(source),
        "candidate_sha256": digest(candidate),
        "output_sha256": digest(final),
        "before_feature_losses": compare_features(original, before),
        "remaining_native_losses": native_losses,
        "content_losses": content_losses,
        "changed_package_parts": changed,
        "unchanged_package_parts": len(parts) - len(changed),
        "sheet_data_byte_preservation": preserved_sheet_data,
        "external_reference_binding_policy": (
            "ORDERED_REFERENCE_RELATIONSHIPS_AND_EXTERNAL_PART_BYTES_IDENTICAL"
        ),
        "external_reference_count": len(external_bindings),
        "formula_cache_policy": "PRESERVED_FROM_CANDIDATE_WITHOUT_CALCULATION",
        "state": "PRESERVATION_PASS_NATIVE_RUNTIME_UNQUALIFIED",
        "native_excel_qualification": "NOT_PERFORMED",
        "engineering_acceptance": "NOT_CONFERRED",
    }
    return final, receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--expected-source-sha", required=True)
    parser.add_argument("--expected-candidate-sha", required=True)
    parser.add_argument("--trial-output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    paths = [args.source, args.candidate, args.trial_output, args.receipt]
    resolved = [path.resolve() for path in paths]
    if len(set(resolved[2:])) != 2 or any(
        path in resolved[:2] for path in resolved[2:]
    ):
        raise ValueError("OUTPUT_MUST_NOT_OVERWRITE_INPUT_OR_RECEIPT")
    if args.trial_output.exists() or args.receipt.exists():
        raise FileExistsError("OUTPUT_ALREADY_EXISTS")
    source, candidate = args.source.read_bytes(), args.candidate.read_bytes()
    final, receipt = repair_native_package(
        source,
        candidate,
        expected_source_sha=args.expected_source_sha,
        expected_candidate_sha=args.expected_candidate_sha,
    )
    if args.source.read_bytes() != source or args.candidate.read_bytes() != candidate:
        raise ValueError("INPUT_MUTATED_DURING_REPAIR")
    args.trial_output.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.trial_output.open("xb") as stream:
        stream.write(final)
    receipt["output_workbook_written"] = True
    receipt["source_mutation"] = False
    receipt["candidate_mutation"] = False
    with args.receipt.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(
        json.dumps(
            {"state": receipt["state"], "output_sha256": receipt["output_sha256"]}
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
