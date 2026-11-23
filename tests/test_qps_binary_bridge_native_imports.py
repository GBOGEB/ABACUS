"""Real native-reader fallback and fail-closed controls for the W42 successor."""

from __future__ import annotations

import builtins
import hashlib
import importlib.util
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qps_binary_bridge_native_imports", ROOT / "tools/qps_binary_bridge.py"
)
assert SPEC is not None and SPEC.loader is not None
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)


def workbook(path: Path) -> None:
    """Write generic OOXML directly, avoiding a serializer's feature defaults."""
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    package = "http://schemas.openxmlformats.org/package/2006/relationships"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{main}" xmlns:r="{rel}"><sheets>'
            '<sheet name="Review" sheetId="1" state="hidden" r:id="r1"/>'
            '</sheets><definedNames><definedName name="Target" localSheetId="0">'
            "Review!$A$1</definedName></definedNames></workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            f'<Relationships xmlns="{package}"><Relationship Id="r1" '
            'Target="worksheets/sheet1.xml"/></Relationships>',
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="{main}"><sheetData><row r="1"><c r="A1">'
            '<f ca="1">1+2</f><v>3</v></c></row></sheetData></worksheet>',
        )


def deny_package_import(monkeypatch, *, deny_fallback=False):
    """Remove one import route without replacing either native parser function."""
    original = builtins.__import__
    calls = []

    def restricted_import(name, *args, **kwargs):
        if name in {"tools.qps_xlsx_native_features", "qps_xlsx_native_features"}:
            calls.append(name)
            if name.startswith("tools.") or deny_fallback:
                raise ModuleNotFoundError("native reader intentionally unavailable")
        return original(name, *args, **kwargs)

    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    monkeypatch.setattr(builtins, "__import__", restricted_import)
    return calls


def test_standalone_native_reader_preserves_real_features(tmp_path, monkeypatch):
    source = tmp_path / "native.xlsx"
    workbook(source)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    expected = bridge.extract_xlsx(source)
    calls = deny_package_import(monkeypatch)
    actual = bridge.extract_xlsx(source)
    assert actual == expected
    assert actual["sheets"][0]["cells"][0]["formula"] == "1+2"
    assert actual["sheets"][0]["cells"][0]["value"] == "3"
    assert actual["native_features"]
    assert calls == ["tools.qps_xlsx_native_features", "qps_xlsx_native_features"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_absent_package_and_standalone_readers_cannot_mint_success(
    tmp_path, monkeypatch
):
    source = tmp_path / "native.xlsx"
    workbook(source)
    calls = deny_package_import(monkeypatch, deny_fallback=True)
    with pytest.raises(ModuleNotFoundError, match="intentionally unavailable"):
        bridge.extract_xlsx(source)
    assert calls == ["tools.qps_xlsx_native_features", "qps_xlsx_native_features"]


def test_standalone_reader_does_not_hide_malformed_package(tmp_path, monkeypatch):
    source = tmp_path / "malformed.xlsx"
    source.write_bytes(b"not an OOXML package")
    deny_package_import(monkeypatch)
    with pytest.raises(zipfile.BadZipFile):
        bridge.extract_xlsx(source)
