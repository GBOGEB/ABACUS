"""W41 targeted native oracles for previously uncovered QPS bridge branches.

These are 12 additional distinct high-yield cases after W40's matched
N/N+1 native census. Source under test stays unchanged.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qps_binary_bridge_w41", ROOT / "tools/qps_binary_bridge.py"
)
assert SPEC is not None and SPEC.loader is not None
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def archive(path, entries):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as pack:
        for name, content in entries.items():
            pack.writestr(name, content)


def normalized(path):
    return bridge.normalize_source(
        path, authority="CHILD_SSOT", lifecycle_status="CURRENT",
        trace_links=[], supersedes=[], producer_commit="c" * 40,
    )["hierarchy_node"]


@pytest.mark.parametrize("bad", ("not-a-sha", "F" * 40, "a" * 39))
def test_producer_head_refuses_invalid_non_full_sha(monkeypatch, bad):
    monkeypatch.setattr(bridge.subprocess, "check_output", lambda *a, **kw: bad)
    with pytest.raises(RuntimeError, match="unable to resolve producer commit"):
        bridge.git_sha()


def test_docx_empty_paragraph_is_not_fabricated_as_semantic_block(tmp_path):
    path = tmp_path / "empty.docx"
    archive(path, {"word/document.xml": (
        f'<w:document xmlns:w="{W}"><w:body>'
        '<w:p><w:r><w:t> </w:t></w:r></w:p>'
        '<w:p><w:r><w:t>Visible</w:t></w:r></w:p>'
        '</w:body></w:document>'
    )})
    blocks = normalized(path)["blocks"]
    assert len(blocks) == 1
    assert blocks[0]["text"] == "Visible"


def spreadsheet_parts(shared_index=None, empty=False):
    common = {
        "xl/workbook.xml": (
            f'<workbook xmlns="{S}" xmlns:r="{R}"><sheets>'
            '<sheet name="First" sheetId="1" r:id="rId1"/>'
            '</sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            f'<Relationships xmlns="{REL}"><Relationship Id="rId1" '
            'Target="xl/worksheets/sheet1.xml"/></Relationships>'
        ),
    }
    if shared_index is not None:
        common["xl/sharedStrings.xml"] = (
            f'<sst xmlns="{S}"><si><t>First string</t></si></sst>'
        )
        cells = f'<c r="B1" t="s"><v>{shared_index}</v></c>'
    else:
        cells = '<c r="B1" t="inlineStr"><is><t>Retained</t></is></c>'
    if empty:
        cells = '<c r="A1"/>' + cells
    common["xl/worksheets/sheet1.xml"] = (
        f'<worksheet xmlns="{S}"><sheetData><row>{cells}</row>'
        '</sheetData></worksheet>'
    )
    return common


@pytest.mark.parametrize("index,expected", ((0, "First string"), (2, "2")))
def test_xlsx_shared_string_valid_and_out_of_range_are_disjoint(
    tmp_path, index, expected
):
    source = tmp_path / "shared.xlsx"
    archive(source, spreadsheet_parts(shared_index=index))
    cells = normalized(source)["sheets"][0]["cells"]
    assert cells == [{
        "anchor": "First!B1", "value": expected, "formula": None,
        "formula_type": None, "formula_shared_index": None,
    }]


def test_xlsx_no_value_no_formula_cell_is_not_fabricated(tmp_path):
    source = tmp_path / "empty-cell.xlsx"
    archive(source, spreadsheet_parts(empty=True))
    cells = normalized(source)["sheets"][0]["cells"]
    assert len(cells) == 1
    assert cells[0]["anchor"] == "First!B1"
    assert cells[0]["value"] == "Retained"


@pytest.mark.parametrize("count", (1, 2))
def test_actual_pypdf_reader_keeps_structured_empty_page_anchors(tmp_path, count):
    """Exercise genuinely parseable PDF, separate from W40 degraded fallback."""
    from pypdf import PdfWriter

    source = tmp_path / "valid.pdf"
    writer = PdfWriter()
    for _ in range(count):
        writer.add_blank_page(width=250, height=250)
    with source.open("wb") as handle:
        writer.write(handle)
    payload = normalized(source)
    assert payload["extraction_quality"]["status"] == "STRUCTURED"
    assert [p["anchor"] for p in payload["pages"]] == [
        f"page:{i}" for i in range(1, count + 1)
    ]
    assert all(page["text"] == "" for page in payload["pages"])


def test_html_whitespace_only_text_creates_no_phantom_node():
    parser = bridge.SemanticHTMLParser()
    parser.feed("<p> \n\t </p><div id='valid'>Visible</div>")
    assert parser.blocks == [{"anchor": "valid", "kind": "div", "text": "Visible"}]


def test_html_stray_end_tag_does_not_consume_visible_content():
    parser = bridge.SemanticHTMLParser()
    parser.feed("</unknown><p id='kept'>Visible</p>")
    assert parser.blocks == [{"anchor": "kept", "kind": "p", "text": "Visible"}]


def test_main_cli_emits_source_bound_output_without_authority_promotion(
    tmp_path, monkeypatch, capsys
):
    source = tmp_path / "source.html"
    source.write_text("<p>Derived trace</p>", encoding="utf-8")
    target = tmp_path / "outputs" / "bridge.json"
    monkeypatch.setattr(bridge, "git_sha", lambda: "b" * 40)
    monkeypatch.setattr(sys, "argv", [
        "qps_binary_bridge.py", str(source), "--output", str(target),
        "--authority", "DERIVED_REVIEW",
        "--lifecycle-status", "CURRENT", "--trace-link", "W41_TRACE",
        "--supersedes", "W40",
    ])
    assert bridge.main() == 0
    report = json.loads(target.read_text(encoding="utf-8"))
    assert report["producer_commit"] == "b" * 40
    assert report["sources"][0]["authority"] == "DERIVED_REVIEW"
    assert report["sources"][0]["trace_links"] == ["W41_TRACE"]
    assert report["sources"][0]["supersedes"] == ["W40"]
    assert report["sources"][0]["freshness_state"] == "CURRENT_AT_PARSE"
    assert str(target) in capsys.readouterr().out
