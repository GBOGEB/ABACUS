"""Source-bound XLSX feature preservation for the owned openpyxl engine.

Reading uses OOXML without executing formulas. Repair uses public openpyxl APIs
and a disposable serialization, then checks the serialized bytes independently.
An unsupported loss is a rejected repair, never an accepted workbook.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"s": MAIN}
BOOLS = {
    "hidden",
    "showButton",
    "hiddenButton",
    "and",
    "blank",
    "caseSensitive",
    "columnSort",
    "fullCalcOnLoad",
    "forceFullCalc",
    "iterate",
    "fullPrecision",
    "calcOnSave",
    "concurrentCalc",
}
CALC_KEYS = {
    "calcMode",
    "refMode",
    "fullCalcOnLoad",
    "forceFullCalc",
    "iterate",
    "iterateCount",
    "iterateDelta",
    "fullPrecision",
    "calcOnSave",
}


def digest(data: bytes) -> str:
    """Return the exact binary identity."""
    return hashlib.sha256(data).hexdigest()


def _attr(key: str, value: str) -> Any:
    if key in BOOLS and value in {"true", "false", "0", "1"}:
        return value in {"true", "1"}
    return value


def xml_node(element: ET.Element | None) -> dict[str, Any] | None:
    """Keep the complete behavior tree, excluding nonfunctional revision UIDs."""
    if element is None:
        return None
    return {
        "tag": element.tag,
        "attributes": {
            k: _attr(k, v) for k, v in element.attrib.items() if not k.endswith("}uid")
        },
        "text": (element.text or "").strip(),
        "children": [xml_node(child) for child in element],
    }


def _xml(data: bytes) -> ET.Element:
    # OOXML has no need for DTDs or entity definitions. Reject before parsing.
    if re.search(
        rb"<!\s*(?:DOCTYPE|ENTITY)\b", data.replace(b"\x00", b""), re.IGNORECASE
    ):
        raise ValueError("UNSUPPORTED_XML_DECLARATION")
    return ET.fromstring(data)


def _bytes(source: Path | bytes) -> bytes:
    return source if isinstance(source, bytes) else Path(source).read_bytes()


def snapshot_xlsx(
    source: Path | bytes, *, resolve_shared_string_values: bool = True
) -> dict[str, Any]:
    """Read native features and cell meanings without normalizing text.

    Repair snapshots resolve and validate shared-string references by default.
    A feature-only caller can retain raw indices when its existing cell reader
    owns value interpretation. Formula attributes are captured in either mode.
    """
    raw = _bytes(source)
    with zipfile.ZipFile(io.BytesIO(raw)) as package:
        infos = package.infolist()
        names = [item.filename for item in infos]
        if len(names) != len(set(names)):
            raise ValueError("DUPLICATE_ZIP_MEMBER")
        if len(infos) > 10000 or sum(x.file_size for x in infos) > 512 * 1024 * 1024:
            raise ValueError("XLSX_PACKAGE_LIMIT")
        if any(x.file_size > 128 * 1024 * 1024 for x in infos):
            raise ValueError("XLSX_PART_LIMIT")
        if package.testzip() is not None:
            raise ValueError("ZIP_CRC_FAILURE")
        workbook = _xml(package.read("xl/workbook.xml"))
        links = {
            item.attrib["Id"]: item.attrib
            for item in _xml(package.read("xl/_rels/workbook.xml.rels"))
        }
        shared = []
        if "xl/sharedStrings.xml" in names:
            shared = [
                "".join(x.text or "" for x in item.findall(".//s:t", NS))
                for item in _xml(package.read("xl/sharedStrings.xml")).findall(
                    "s:si", NS
                )
            ]
        sheets, cells = [], {}
        for sh in workbook.findall("s:sheets/s:sheet", NS):
            link = links[sh.attrib["{" + REL + "}id"]]
            if link.get("TargetMode") == "External":
                raise ValueError("EXTERNAL_WORKSHEET_RELATIONSHIP")
            target = link["Target"]
            if (
                not target
                or target.startswith("//")
                or any(char in target for char in ("\\", ":", "?", "#", "\0"))
            ):
                raise ValueError("INVALID_WORKSHEET_MEMBER")
            # Retain the bridge's package-rooted relative-target compatibility.
            # A target already beginning with xl/ must not acquire a second xl/.
            rooted = target.startswith(("/", "xl/"))
            member = posixpath.normpath(
                target.lstrip("/") if rooted else "xl/" + target
            )
            if not member.startswith("xl/") or ".." in member.split("/"):
                raise ValueError("INVALID_WORKSHEET_MEMBER")
            root = _xml(package.read(member))
            auto_filter = root.find("s:autoFilter", NS)
            sheets.append(
                {
                    "name": sh.attrib["name"],
                    "visibility": sh.attrib.get("state", "visible"),
                    "part": member,
                    "auto_filter": xml_node(auto_filter),
                    "auto_filter_xml": (
                        ET.tostring(auto_filter, encoding="unicode")
                        if auto_filter is not None
                        else None
                    ),
                    "hidden_rows": sorted(
                        int(row.attrib["r"])
                        for row in root.findall("s:sheetData/s:row", NS)
                        if row.attrib.get("hidden") in {"true", "1"}
                    ),
                    "hidden_columns": sorted(
                        [int(col.attrib["min"]), int(col.attrib["max"])]
                        for col in root.findall("s:cols/s:col", NS)
                        if col.attrib.get("hidden") in {"true", "1"}
                    ),
                }
            )
            for cell in root.findall("s:sheetData/s:row/s:c", NS):
                formula, value = cell.find("s:f", NS), cell.find("s:v", NS)
                kind = cell.attrib.get("t", "n")
                raw_value = None if value is None else value.text
                if (
                    kind == "s"
                    and raw_value is not None
                    and resolve_shared_string_values
                ):
                    index = int(raw_value)
                    if index < 0 or index >= len(shared):
                        raise ValueError("INVALID_SHARED_STRING_INDEX")
                    raw_value, kind = shared[index], "text"
                elif kind == "inlineStr":
                    raw_value = "".join(
                        x.text or "" for x in cell.findall("s:is//s:t", NS)
                    )
                    kind = "text"
                elif kind == "str" and formula is None:
                    kind = "text"
                if formula is None and raw_value is None:
                    continue
                cells[sh.attrib["name"] + "!" + cell.attrib["r"]] = {
                    "type": kind,
                    "value": raw_value,
                    "formula": formula.text if formula is not None else None,
                    "formula_attributes": (
                        dict(formula.attrib) if formula is not None else {}
                    ),
                }
        defined = []
        for entry in workbook.findall("s:definedNames/s:definedName", NS):
            attrs = {key: _attr(key, val) for key, val in entry.attrib.items()}
            scope = attrs.get("localSheetId")
            if scope is not None and (
                not str(scope).isdigit() or int(scope) >= len(sheets)
            ):
                raise ValueError("DEFINED_NAME_WITH_INVALID_SCOPE")
            defined.append({"attributes": attrs, "text": entry.text or ""})
        keys = [
            (x["attributes"].get("name"), x["attributes"].get("localSheetId"))
            for x in defined
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("DUPLICATE_SCOPED_DEFINED_NAME")
        calc = workbook.find("s:calcPr", NS)
        calc_attrs = {} if calc is None else calc.attrib
        return {
            "schema": "abacus-xlsx-native-snapshot/v1",
            "sha256": digest(raw),
            "sheets": sheets,
            "defined_names": sorted(
                defined,
                key=lambda x: (
                    x["attributes"].get("name", ""),
                    str(x["attributes"].get("localSheetId", "")),
                ),
            ),
            "explicit_calculation_settings": {
                k: _attr(k, v) for k, v in calc_attrs.items() if k in CALC_KEYS
            },
            "cells": cells,
        }


def native_features(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return native semantics only for the binary bridge's semantic identity."""
    return {
        "schema": "abacus-xlsx-native-features/v1",
        "sheets": [
            {k: v for k, v in sheet.items() if k not in {"part", "auto_filter_xml"}}
            for sheet in snapshot["sheets"]
        ],
        "defined_names": snapshot["defined_names"],
        "explicit_calculation_settings": snapshot["explicit_calculation_settings"],
        "formula_attributes": {
            locator: cell["formula_attributes"]
            for locator, cell in snapshot["cells"].items()
            if cell["formula_attributes"]
        },
    }


def compare_features(
    source: dict[str, Any], candidate: dict[str, Any]
) -> list[dict[str, Any]]:
    """Strict source-native comparison. Missing explicit settings are failures."""
    changes: list[dict[str, Any]] = []

    def check(code: str, locator: str, before: Any, after: Any) -> None:
        if before != after:
            changes.append(
                {"code": code, "locator": locator, "source": before, "candidate": after}
            )

    check(
        "SHEET_SET_OR_ORDER_CHANGED",
        "workbook/sheets",
        [s["name"] for s in source["sheets"]],
        [s["name"] for s in candidate["sheets"]],
    )
    current = {s["name"]: s for s in candidate["sheets"]}
    for before in source["sheets"]:
        after = current.get(before["name"], {})
        for field in ("visibility", "auto_filter", "hidden_rows", "hidden_columns"):
            check(
                "NATIVE_" + field.upper() + "_CHANGED",
                before["name"] + "/" + field,
                before[field],
                after.get(field),
            )

    # Keep scope and hidden flag; do not collapse duplicate names by name alone.
    def keyed(items: list[dict[str, Any]]) -> dict[tuple[Any, Any], Any]:
        return {
            (x["attributes"].get("name"), x["attributes"].get("localSheetId")): x
            for x in items
        }

    prior_names, now_names = keyed(source["defined_names"]), keyed(
        candidate["defined_names"]
    )
    for key in sorted(set(prior_names) | set(now_names), key=str):
        check(
            "SCOPED_DEFINED_NAME_CHANGED",
            "definedNames/" + str(key),
            prior_names.get(key),
            now_names.get(key),
        )
    for key, value in source["explicit_calculation_settings"].items():
        check(
            "EXPLICIT_CALC_SETTING_CHANGED",
            "calcPr/" + key,
            value,
            candidate["explicit_calculation_settings"].get(key, "UNRECORDED"),
        )
    return changes


def compare_content(
    before: dict[str, Any], after: dict[str, Any]
) -> list[dict[str, Any]]:
    """Reject changed cells, formulas or caches during a native-only repair."""
    differences = []
    for locator in sorted(set(before["cells"]) | set(after["cells"])):
        old, new = before["cells"].get(locator), after["cells"].get(locator)
        if old == new:
            continue
        if (
            old
            and new
            and old["formula"] is not None
            and old["formula"] == new["formula"]
        ):
            if old["formula_attributes"] != new["formula_attributes"]:
                differences.append(
                    {
                        "code": "FORMULA_ATTRIBUTES_CHANGED",
                        "locator": locator,
                        "before": old["formula_attributes"],
                        "after": new["formula_attributes"],
                    }
                )
            if (old["value"], old["type"]) != (new["value"], new["type"]):
                differences.append(
                    {
                        "code": "FORMULA_CACHE_OR_RESULT_TYPE_CHANGED",
                        "locator": locator,
                        "before": {k: old[k] for k in ("value", "type")},
                        "after": {k: new[k] for k in ("value", "type")},
                    }
                )
        else:
            differences.append(
                {
                    "code": "CELL_CONTENT_OR_FORMULA_CHANGED",
                    "locator": locator,
                    "before": old,
                    "after": new,
                }
            )
    return differences


def restore_supported_features(workbook: Any, source: dict[str, Any]) -> dict[str, Any]:
    """Restore a loaded owned-engine workbook using public openpyxl APIs only.

    No save or acceptance is performed here. The serializer must be checked with
    evaluate_repair; openpyxl does not evaluate filters or spreadsheet formulas.
    """
    from openpyxl.worksheet.filters import AutoFilter
    from openpyxl.workbook.defined_name import DefinedName
    from openpyxl.workbook.properties import CalcProperties

    expected = [s["name"] for s in source["sheets"]]
    if workbook.sheetnames != expected:
        raise ValueError("SHEET_SET_OR_ORDER_CHANGED")
    if not any(s["visibility"] == "visible" for s in source["sheets"]):
        raise ValueError("NO_VISIBLE_WORKSHEET")
    prepared = []
    for sheet in source["sheets"]:
        if sheet["auto_filter_xml"] is None:
            prepared.append(AutoFilter())
            continue
        node = _xml(sheet["auto_filter_xml"].encode("utf-8"))
        for child in node.iter():
            for key in list(child.attrib):
                if key.endswith("}uid"):
                    del child.attrib[key]
            if child.tag.rsplit("}", 1)[-1] == "extLst":
                raise ValueError("UNSUPPORTED_FILTER_EXTENSION")
        model = AutoFilter.from_tree(node)
        # Public optional attributes default differently from absent source XML.
        source_columns = node.findall("s:filterColumn", NS)
        for column, original in zip(model.filterColumn, source_columns):
            if "hiddenButton" not in original.attrib:
                column.hiddenButton = None
            if "showButton" not in original.attrib:
                column.showButton = None
        serialized_filter = model.to_tree()
        for child in serialized_filter.iter():
            if not child.tag.startswith("{"):
                child.tag = "{" + MAIN + "}" + child.tag
        if xml_node(serialized_filter) != sheet["auto_filter"]:
            raise ValueError("UNSUPPORTED_FILTER_ROUNDTRIP")
        prepared.append(model)
    # Filter support is validated before changing the disposable model. Any
    # later failure is still fail-closed: no workbook is emitted or accepted.
    for sheet, auto_filter in zip(source["sheets"], prepared):
        ws = workbook[sheet["name"]]
        ws.sheet_state = sheet["visibility"]
        ws.auto_filter = auto_filter
    if workbook.calculation is None:
        workbook.calculation = CalcProperties()
    for key, value in source["explicit_calculation_settings"].items():
        setattr(workbook.calculation, key, value)
    orphan_names = 0
    print_names = 0
    for entry in source["defined_names"]:
        attrs = entry["attributes"]
        name = attrs.get("name")
        if name not in {
            "_xlnm._FilterDatabase",
            "_xlnm.Print_Area",
            "_xlnm.Print_Titles",
        }:
            continue
        sheet = source["sheets"][int(attrs["localSheetId"])]
        ws = workbook[sheet["name"]]
        if name in {"_xlnm.Print_Area", "_xlnm.Print_Titles"}:
            definition = DefinedName(name=name, attr_text=entry["text"])
            destinations = list(definition.destinations)
            if not destinations or any(title != ws.title for title, _ in destinations):
                raise ValueError("UNSUPPORTED_PRINT_NAME_SCOPE")
            if name == "_xlnm.Print_Area":
                ws.print_area = [address for _, address in destinations]
            else:
                for _, address in destinations:
                    if re.fullmatch(r"\$?\d+:\$?\d+", address):
                        ws.print_title_rows = address
                    elif re.fullmatch(r"\$?[A-Z]+:\$?[A-Z]+", address):
                        ws.print_title_cols = address
                    else:
                        raise ValueError("UNSUPPORTED_PRINT_TITLE_RANGE")
            print_names += 1
            continue
        # openpyxl writes its own scoped name for an AutoFilter. Adding a second
        # one would duplicate the same scoped key. Preserve source orphan names.
        if sheet["auto_filter"] is None:
            ws.defined_names.add(
                DefinedName(
                    name=attrs["name"],
                    localSheetId=int(attrs["localSheetId"]),
                    hidden=attrs.get("hidden", False),
                    attr_text=entry["text"],
                )
            )
            orphan_names += 1
    return {
        "auto_filters": sum(s["auto_filter"] is not None for s in source["sheets"]),
        "active_filter_columns": sum(len(f.filterColumn) for f in prepared),
        "hidden_sheets": sum(s["visibility"] != "visible" for s in source["sheets"]),
        "orphan_filter_names": orphan_names,
        "print_names": print_names,
        "explicit_calculation_settings": source["explicit_calculation_settings"],
        "state": "IN_MEMORY_ONLY_REQUIRES_SERIALIZED_GATE",
    }


def evaluate_repair(
    source: Path,
    candidate: Path,
    *,
    expected_source_sha: str,
    expected_candidate_sha: str,
) -> dict[str, Any]:
    """Try the owned engine in memory and reject any remaining serialized loss.

    Returns a receipt only, never a workbook. Private source values remain in the
    caller-owned receipt. No source path is written and no caches are fabricated.
    """
    from openpyxl import load_workbook
    import openpyxl

    source_raw, candidate_raw = source.read_bytes(), candidate.read_bytes()
    if digest(source_raw) != expected_source_sha:
        raise ValueError("SOURCE_HASH_MISMATCH")
    if digest(candidate_raw) != expected_candidate_sha:
        raise ValueError("CANDIDATE_HASH_MISMATCH")
    original, before = snapshot_xlsx(source_raw), snapshot_xlsx(candidate_raw)
    if [s["name"] for s in original["sheets"]] != [s["name"] for s in before["sheets"]]:
        raise ValueError("SHEET_SET_OR_ORDER_CHANGED")
    wb = load_workbook(
        io.BytesIO(candidate_raw), data_only=False, keep_links=True, rich_text=True
    )
    restored = restore_supported_features(wb, original)
    buffer = io.BytesIO()
    wb.save(buffer)
    wb.close()
    serialized = buffer.getvalue()
    after = snapshot_xlsx(serialized)
    feature_losses = compare_features(original, after)
    content_losses = compare_content(before, after)
    if source.read_bytes() != source_raw or candidate.read_bytes() != candidate_raw:
        raise ValueError("INPUT_MUTATED_DURING_REPAIR_EVALUATION")
    return {
        "schema": "abacus-xlsx-preservation-evaluation/v1",
        "engine": {"name": "openpyxl", "version": openpyxl.__version__},
        "source_sha256": digest(source_raw),
        "candidate_sha256": digest(candidate_raw),
        "serialized_trial_sha256": digest(serialized),
        "before_feature_losses": compare_features(original, before),
        "restored": restored,
        "remaining_native_losses": feature_losses,
        "content_losses": content_losses,
        "state": (
            "REJECTED_SERIALIZED_LOSS"
            if feature_losses or content_losses
            else "PRESERVATION_PASS_NATIVE_RUNTIME_UNQUALIFIED"
        ),
        "formula_evaluation": "NOT_PERFORMED_OPENPYXL_IS_NOT_A_CALCULATION_ENGINE",
        "output_workbook_written": False,
        "source_mutation": False,
        "candidate_mutation": False,
    }


def main() -> int:
    """Write a private evaluation receipt; never write a repaired workbook."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--expected-source-sha", required=True)
    parser.add_argument("--expected-candidate-sha", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.receipt.resolve() in {args.source.resolve(), args.candidate.resolve()}:
        raise ValueError("RECEIPT_MUST_NOT_OVERWRITE_INPUT")
    receipt = evaluate_repair(
        args.source,
        args.candidate,
        expected_source_sha=args.expected_source_sha,
        expected_candidate_sha=args.expected_candidate_sha,
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.receipt.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"state": receipt["state"], "receipt": str(args.receipt)}))
    return 3 if receipt["state"] == "REJECTED_SERIALIZED_LOSS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
