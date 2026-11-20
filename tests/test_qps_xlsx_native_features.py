"""Generic regression fixtures for native-feature loss, not project binaries."""

from __future__ import annotations

import copy
import importlib.util
import io
import sys
import zipfile
from pathlib import Path

import tempfile
import unittest


def raises(error, *, match):
    return unittest.TestCase().assertRaisesRegex(error, match)


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.qps_xlsx_native_features import (
    compare_content,
    compare_features,
    digest,
    evaluate_repair,
    native_features,
    restore_supported_features,
    snapshot_xlsx,
)


def fixture_bytes(
    *, criterion="Open", hidden="hidden", calc="1", duplicate_name=False, scope="0"
):
    """Create a minimal generic OOXML test fixture with a real formula cache."""
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    entry = f'<definedName name="_xlnm._FilterDatabase" localSheetId="{scope}" hidden="1">Data!$A$1:$B$3</definedName>'
    content = {
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        "_rels/.rels": f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="{rel}/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": f'<workbook xmlns="{main}" xmlns:r="{rel}"><sheets><sheet name="Data" sheetId="1" r:id="rId1"/><sheet name="Support" sheetId="2" state="{hidden}" r:id="rId2"/></sheets><definedNames>{entry}{entry if duplicate_name else ""}</definedNames><calcPr forceFullCalc="{calc}"/></workbook>',
        "xl/_rels/workbook.xml.rels": f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="{rel}/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="{rel}/worksheet" Target="worksheets/sheet2.xml"/></Relationships>',
        "xl/worksheets/sheet1.xml": f'<worksheet xmlns="{main}"><cols><col min="3" max="3" hidden="1"/></cols><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Status</t></is></c></row><row r="2" hidden="1"><c r="A2" t="inlineStr"><is><t>Open</t></is></c></row><row r="3"><c r="A3" t="inlineStr"><is><t>Closed</t></is></c><c r="B3"><f>1+1</f><v>2</v></c></row></sheetData><autoFilter ref="A1:B3"><filterColumn colId="0"><filters><filter val="{criterion}"/></filters></filterColumn></autoFilter></worksheet>',
        "xl/worksheets/sheet2.xml": f'<worksheet xmlns="{main}"><sheetData/></worksheet>',
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as package:
        for key, value in content.items():
            package.writestr(key, value)
    return buffer.getvalue()


def check_snapshot_captures_meaning_and_explicit_false():
    result = snapshot_xlsx(fixture_bytes(calc="0"))
    assert result["explicit_calculation_settings"]["forceFullCalc"] is False
    assert result["sheets"][1]["visibility"] == "hidden"
    assert result["sheets"][0]["hidden_rows"] == [2]
    assert result["sheets"][0]["hidden_columns"] == [[3, 3]]
    assert result["defined_names"][0]["attributes"]["localSheetId"] == "0"
    assert result["cells"]["Data!B3"]["value"] == "2"
    assert compare_features(result, result) == []


def worksheet_target_fixture(target, external=False):
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(fixture_bytes())) as source, zipfile.ZipFile(
        output, "w"
    ) as destination:
        for name in source.namelist():
            data = source.read(name)
            if name == "xl/_rels/workbook.xml.rels":
                replacement = f'Target="{target}"'
                if external:
                    replacement += ' TargetMode="External"'
                data = data.replace(
                    b'Target="worksheets/sheet1.xml"', replacement.encode(), 1
                )
            destination.writestr(name, data)
    return output.getvalue()


def check_supported_worksheet_targets_share_native_identity(target):
    expected = snapshot_xlsx(fixture_bytes())
    observed = snapshot_xlsx(worksheet_target_fixture(target))
    assert native_features(observed) == native_features(expected)
    assert observed["cells"] == expected["cells"]


def check_worksheet_target_cannot_escape_or_be_external(target):
    with raises(ValueError, match="INVALID_WORKSHEET_MEMBER"):
        snapshot_xlsx(worksheet_target_fixture(target))


def check_external_worksheet_target_is_rejected():
    with raises(ValueError, match="EXTERNAL_WORKSHEET_RELATIONSHIP"):
        snapshot_xlsx(
            worksheet_target_fixture("xl/worksheets/sheet1.xml", external=True)
        )


def check_feature_only_read_does_not_weaken_repair_shared_string_guard():
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(fixture_bytes())) as source, zipfile.ZipFile(
        output, "w"
    ) as destination:
        for name in source.namelist():
            data = source.read(name)
            if name == "xl/worksheets/sheet1.xml":
                data = data.replace(
                    b'<c r="A2" t="inlineStr"><is><t>Open</t></is></c>',
                    b'<c r="A2" t="s"><v>999</v></c>',
                ).replace(b"<f>1+1</f>", b'<f aca="1">1+1</f>')
            destination.writestr(name, data)
    raw = output.getvalue()
    with raises(ValueError, match="INVALID_SHARED_STRING_INDEX"):
        snapshot_xlsx(raw)
    observed = snapshot_xlsx(raw, resolve_shared_string_values=False)
    assert observed["cells"]["Data!A2"]["value"] == "999"
    assert observed["cells"]["Data!A2"]["type"] == "s"
    assert native_features(observed)["formula_attributes"]["Data!B3"] == {"aca": "1"}


def check_sort_custom_list_keeps_string_identity():
    def make(value):
        result = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(fixture_bytes())) as source, zipfile.ZipFile(
            result, "w"
        ) as target:
            for name in source.namelist():
                data = source.read(name)
                if name == "xl/worksheets/sheet1.xml":
                    data = data.replace(
                        b"</autoFilter>",
                        f'<sortState ref="A2:B3"><sortCondition ref="A2:A3" customList="{value}"/></sortState></autoFilter>'.encode(),
                    )
                target.writestr(name, data)
        return snapshot_xlsx(result.getvalue())

    before, after = make("1"), make("true")
    assert native_features(before) != native_features(after)
    assert compare_features(before, after)


def check_feature_guard_detects_same_count_changes(kind):
    source = snapshot_xlsx(fixture_bytes())
    other = copy.deepcopy(source)
    if kind == "criterion":
        other = snapshot_xlsx(fixture_bytes(criterion="Closed"))
    elif kind == "visibility":
        other["sheets"][1]["visibility"] = "visible"
    elif kind == "rows":
        other["sheets"][0]["hidden_rows"] = [3]
    elif kind == "columns":
        other["sheets"][0]["hidden_columns"] = [[4, 4]]
    elif kind == "calc":
        other["explicit_calculation_settings"] = {}
    elif kind == "name_range":
        other["defined_names"][0]["text"] = "Data!$A$1:$B$2"
    elif kind == "name_scope":
        other["defined_names"][0]["attributes"]["localSheetId"] = "1"
    else:
        other["sheets"].reverse()
    assert compare_features(source, other)


def check_duplicate_scope_is_not_silently_collapsed():
    with raises(ValueError, match="DUPLICATE_SCOPED_DEFINED_NAME"):
        snapshot_xlsx(fixture_bytes(duplicate_name=True))


def check_invalid_scope_is_rejected(scope):
    with raises(ValueError, match="DEFINED_NAME_WITH_INVALID_SCOPE"):
        snapshot_xlsx(fixture_bytes(scope=scope))


def check_dtd_is_rejected_before_xml_parse():
    raw = fixture_bytes()
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw)) as source, zipfile.ZipFile(
        output, "w"
    ) as target:
        for name in source.namelist():
            data = source.read(name)
            if name == "xl/workbook.xml":
                data = b'<!DOCTYPE workbook [<!ENTITY demo "x">]>' + data
            target.writestr(name, data)
    with raises(ValueError, match="UNSUPPORTED_XML_DECLARATION"):
        snapshot_xlsx(output.getvalue())


def check_cache_loss_is_rejected_without_changing_formula_text():
    before = snapshot_xlsx(fixture_bytes())
    after = copy.deepcopy(before)
    after["cells"]["Data!B3"]["value"] = None
    assert (
        compare_content(before, after)[0]["code"]
        == "FORMULA_CACHE_OR_RESULT_TYPE_CHANGED"
    )


def check_wrong_source_or_candidate_hash_is_rejected(tmp_path, which):
    source, candidate = tmp_path / "source.xlsx", tmp_path / "candidate.xlsx"
    raw = fixture_bytes()
    source.write_bytes(raw)
    candidate.write_bytes(raw)
    with raises(ValueError, match=which.upper() + "_HASH_MISMATCH"):
        evaluate_repair(
            source,
            candidate,
            expected_source_sha="0" * 64 if which == "source" else digest(raw),
            expected_candidate_sha="0" * 64 if which == "candidate" else digest(raw),
        )
    assert source.read_bytes() == candidate.read_bytes() == raw


def check_owned_engine_serialized_output_rejects_formula_cache_loss(tmp_path):
    __import__("openpyxl")
    source, candidate = tmp_path / "source.xlsx", tmp_path / "candidate.xlsx"
    raw = fixture_bytes()
    source.write_bytes(raw)
    candidate.write_bytes(raw)
    result = evaluate_repair(
        source,
        candidate,
        expected_source_sha=digest(raw),
        expected_candidate_sha=digest(raw),
    )
    assert result["state"] == "REJECTED_SERIALIZED_LOSS"
    assert result["output_workbook_written"] is False
    assert result["restored"]["active_filter_columns"] == 1
    assert any(
        row["code"] == "FORMULA_CACHE_OR_RESULT_TYPE_CHANGED"
        for row in result["content_losses"]
    )
    assert source.read_bytes() == candidate.read_bytes() == raw
    assert set(p.name for p in tmp_path.iterdir()) == {"source.xlsx", "candidate.xlsx"}


def check_sheet_order_rejected_before_model_mutation():
    openpyxl = __import__("openpyxl")
    wb = openpyxl.Workbook()
    before = wb.sheetnames[:]
    with raises(ValueError, match="SHEET_SET_OR_ORDER_CHANGED"):
        restore_supported_features(wb, snapshot_xlsx(fixture_bytes()))
    assert wb.sheetnames == before


def check_bridge_semantic_identity_includes_same_count_filter_change(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "bridge_native_test", ROOT / "tools/qps_binary_bridge.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    a, b = tmp_path / "a.xlsx", tmp_path / "b.xlsx"
    a.write_bytes(fixture_bytes(criterion="Open"))
    b.write_bytes(fixture_bytes(criterion="Closed"))
    first, second = module.extract_xlsx(a), module.extract_xlsx(b)
    assert first["sheets"] == second["sheets"]
    assert first["native_features"] != second["native_features"]
    assert module.canonical_sha256(first) != module.canonical_sha256(second)


class NativeFeatureTests(unittest.TestCase):
    pass


def _run(function, *args):
    def method(self):
        if "tmp_path" in function.__code__.co_varnames[: function.__code__.co_argcount]:
            with tempfile.TemporaryDirectory() as directory:
                function(Path(directory), *args)
        else:
            function(*args)

    return method


for _name, _function in list(globals().items()):
    if not _name.startswith("check_"):
        continue
    _parameters = {
        "check_feature_guard_detects_same_count_changes": [
            "criterion",
            "visibility",
            "rows",
            "columns",
            "calc",
            "name_range",
            "name_scope",
            "sheet_order",
        ],
        "check_invalid_scope_is_rejected": ["-1", "9", "not-an-index"],
        "check_wrong_source_or_candidate_hash_is_rejected": ["source", "candidate"],
        "check_supported_worksheet_targets_share_native_identity": [
            "worksheets/sheet1.xml",
            "xl/worksheets/sheet1.xml",
            "/xl/worksheets/sheet1.xml",
        ],
        "check_worksheet_target_cannot_escape_or_be_external": [
            "../../outside.xml",
            "xl/../../outside.xml",
            "/outside.xml",
            "//remote/xl/worksheets/sheet1.xml",
            "https://example.invalid/sheet1.xml",
            "..\\outside.xml",
            "worksheets/sheet1.xml#fragment",
            "worksheets/sheet1.xml?query=1",
            "",
        ],
    }.get(_name, [None])
    for _index, _argument in enumerate(_parameters):
        setattr(
            NativeFeatureTests,
            _name.replace("check_", "test_", 1)
            + (str(_index) if len(_parameters) > 1 else ""),
            _run(_function, *(() if _argument is None else (_argument,))),
        )


if __name__ == "__main__":
    unittest.main()
