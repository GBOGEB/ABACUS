from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
import zipfile



ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "qps_binary_bridge.py"
SPEC = importlib.util.spec_from_file_location("qps_binary_bridge", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)


def write_zip(path: Path, members: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, value in members.items():
            archive.writestr(name, value)


def test_docx_bridge_extracts_text_and_minimum_tuple(tmp_path: Path) -> None:
    source = tmp_path / "sample.docx"
    write_zip(
        source,
        {
            "word/document.xml": """<?xml version="1.0"?>
<w:document
 xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
 <w:body>
  <w:p>
   <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
   <w:r><w:t>QPS System</w:t></w:r>
  </w:p>
  <w:tbl>
   <w:tr>
    <w:tc><w:p><w:r><w:t>RTM-001</w:t></w:r></w:p></w:tc>
    <w:tc><w:p><w:r><w:t>Requirement</w:t></w:r></w:p></w:tc>
   </w:tr>
  </w:tbl>
 </w:body>
</w:document>""",
        },
    )

    item = bridge.normalize_source(
        source,
        authority="SCK_CEN_CONTRACT",
        lifecycle_status="CURRENT",
        trace_links=["RTM-001"],
        supersedes=[],
        producer_commit="a" * 40,
    )

    assert item["hierarchy_node"]["kind"] == "docx"
    assert item["hierarchy_node"]["blocks"][0]["text"] == "QPS System"
    assert item["hierarchy_node"]["blocks"][0]["style"] == "Heading1"
    assert item["hierarchy_node"]["blocks"][1]["rows"] == [
        ["RTM-001", "Requirement"]
    ]
    assert item["source_sha256"]
    assert item["semantic_sha256"]
    assert item["authority"] == "SCK_CEN_CONTRACT"
    assert item["trace_links"] == ["RTM-001"]
    assert item["producer_repository"] == "GBOGEB/ABACUS"


def test_docx_bridge_preserves_text_across_formatting_runs(tmp_path: Path) -> None:
    source = tmp_path / "formatted.docx"
    write_zip(
        source,
        {
            "word/document.xml": """<?xml version="1.0"?>
<w:document
 xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
 <w:body><w:p>
  <w:r><w:t>Q</w:t></w:r><w:r><w:t>PS</w:t></w:r>
 </w:p></w:body>
</w:document>""",
        },
    )

    item = bridge.normalize_source(
        source,
        authority="CHILD_SSOT",
        lifecycle_status="CURRENT",
        trace_links=[],
        supersedes=[],
        producer_commit="a" * 40,
    )

    assert item["hierarchy_node"]["blocks"][0]["text"] == "QPS"


def test_docx_bridge_preserves_explicit_tabs_and_breaks(tmp_path: Path) -> None:
    source = tmp_path / "breaks.docx"
    write_zip(
        source,
        {
            "word/document.xml": """<?xml version="1.0"?>
<w:document
 xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
 <w:body><w:p>
  <w:r><w:t>A</w:t><w:tab/><w:t>B</w:t><w:br/><w:t>C</w:t></w:r>
 </w:p></w:body>
</w:document>""",
        },
    )

    item = bridge.normalize_source(
        source,
        authority="CHILD_SSOT",
        lifecycle_status="CURRENT",
        trace_links=[],
        supersedes=[],
        producer_commit="a" * 40,
    )

    assert item["hierarchy_node"]["blocks"][0]["text"] == "A B C"


def test_xlsx_bridge_extracts_sheet_cells_and_formula(tmp_path: Path) -> None:
    source = tmp_path / "sample.xlsx"
    write_zip(
        source,
        {
            "xl/workbook.xml": """<?xml version="1.0"?>
<workbook
 xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
 <sheets>
  <sheet name="RTM" sheetId="1" r:id="rId1"/>
 </sheets>
</workbook>""",
            "xl/_rels/workbook.xml.rels": """<?xml version="1.0"?>
<Relationships
 xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship
  Id="rId1"
  Type="worksheet"
  Target="worksheets/sheet1.xml"/>
</Relationships>""",
            "xl/worksheets/sheet1.xml": """<?xml version="1.0"?>
<worksheet
 xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
 <sheetData>
  <row r="1">
   <c r="A1" t="inlineStr"><is><t>RTM-001</t></is></c>
   <c r="B1"><f>1+1</f><v>2</v></c>
  </row>
 </sheetData>
</worksheet>""",
        },
    )

    item = bridge.normalize_source(
        source,
        authority="RTM_PROJECTION",
        lifecycle_status="CURRENT",
        trace_links=[],
        supersedes=[],
        producer_commit="b" * 40,
    )

    sheet = item["hierarchy_node"]["sheets"][0]
    assert sheet["name"] == "RTM"
    assert sheet["cells"][0]["anchor"] == "RTM!A1"
    assert sheet["cells"][0]["value"] == "RTM-001"
    assert sheet["cells"][1]["formula"] == "1+1"


def test_xlsx_bridge_retains_shared_formula_identity(tmp_path: Path) -> None:
    source = tmp_path / "shared-formula.xlsx"
    write_zip(
        source,
        {
            "xl/workbook.xml": """<?xml version="1.0"?>
<workbook
 xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
 <sheets><sheet name="Calc" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
            "xl/_rels/workbook.xml.rels": """<?xml version="1.0"?>
<Relationships
 xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
            "xl/worksheets/sheet1.xml": """<?xml version="1.0"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
 <sheetData><row r="1">
  <c r="A1"><f t="shared" si="3">B1+1</f><v>2</v></c>
  <c r="A2"><f t="shared" si="3"/><v>3</v></c>
 </row></sheetData>
</worksheet>""",
        },
    )

    item = bridge.normalize_source(
        source,
        authority="RTM_PROJECTION",
        lifecycle_status="CURRENT",
        trace_links=[],
        supersedes=[],
        producer_commit="b" * 40,
    )
    cells = item["hierarchy_node"]["sheets"][0]["cells"]

    assert cells[0]["formula"] == "B1+1"
    assert cells[0]["formula_type"] == "shared"
    assert cells[0]["formula_shared_index"] == "3"
    assert cells[1]["formula"] is None
    assert cells[1]["formula_type"] == "shared"
    assert cells[1]["formula_shared_index"] == "3"


def test_pptx_html_and_pdf_have_stable_family_anchors(
    tmp_path: Path,
) -> None:
    pptx = tmp_path / "sample.pptx"
    write_zip(
        pptx,
        {
            "ppt/slides/slide1.xml": """<?xml version="1.0"?>
<p:sld
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
 <p:cSld><p:spTree><p:sp><p:txBody>
  <a:p><a:r><a:t>Interface A</a:t></a:r></a:p>
 </p:txBody></p:sp></p:spTree></p:cSld>
</p:sld>""",
        },
    )
    html = tmp_path / "sample.html"
    html.write_text(
        "<h1 id='scope'>Scope</h1><p>Battery limit A</p>",
        encoding="utf-8",
    )
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Page >> endobj\n"
        b"2 0 obj << /Length 31 >> stream\n"
        b"BT (QPS PDF sample) Tj ET\n"
        b"endstream endobj\n%%EOF\n"
    )

    pptx_item = bridge.normalize_source(
        pptx,
        authority="DERIVED_INPUT",
        lifecycle_status="CURRENT",
        trace_links=[],
        supersedes=[],
        producer_commit="c" * 40,
    )
    html_item = bridge.normalize_source(
        html,
        authority="DERIVED_INPUT",
        lifecycle_status="CURRENT",
        trace_links=[],
        supersedes=[],
        producer_commit="c" * 40,
    )
    pdf_item = bridge.normalize_source(
        pdf,
        authority="CONTRACT",
        lifecycle_status="CURRENT",
        trace_links=[],
        supersedes=[],
        producer_commit="c" * 40,
    )

    assert pptx_item["hierarchy_node"]["slides"][0] == {
        "anchor": "slide:1",
        "number": 1,
        "text": "Interface A",
    }
    assert html_item["hierarchy_node"]["blocks"][0]["anchor"] == "scope"
    assert html_item["hierarchy_node"]["blocks"][1]["text"] == "Battery limit A"
    assert pdf_item["hierarchy_node"]["pages"][0]["anchor"] == "page:1"
    assert "QPS PDF sample" in pdf_item["hierarchy_node"]["pages"][0]["text"]


def test_semantic_hash_ignores_filename_for_identical_content(
    tmp_path: Path,
) -> None:
    left = tmp_path / "left.html"
    right = tmp_path / "right.html"
    content = "<h2>Definitions</h2><p>QPS = Cryogenic System</p>"
    left.write_text(content, encoding="utf-8")
    right.write_text(content, encoding="utf-8")

    kwargs = {
        "authority": "CHILD_SSOT",
        "lifecycle_status": "CURRENT",
        "trace_links": [],
        "supersedes": [],
        "producer_commit": "d" * 40,
    }
    first = bridge.normalize_source(left, **kwargs)
    second = bridge.normalize_source(right, **kwargs)

    assert first["source_sha256"] == second["source_sha256"]
    assert first["semantic_sha256"] == second["semantic_sha256"]


def test_html_bridge_captures_visible_generic_container_text(
    tmp_path: Path,
) -> None:
    source = tmp_path / "containers.html"
    source.write_text(
        "<html><body><div id='callout'>Direct callout"
        "<p>Nested paragraph</p>Tail text</div></body></html>",
        encoding="utf-8",
    )

    item = bridge.normalize_source(
        source,
        authority="DERIVED_INPUT",
        lifecycle_status="CURRENT",
        trace_links=[],
        supersedes=[],
        producer_commit="d" * 40,
    )
    blocks = item["hierarchy_node"]["blocks"]

    assert {block["text"] for block in blocks} == {
        "Direct callout Tail text",
        "Nested paragraph",
    }
    assert next(block for block in blocks if block["kind"] == "div")[
        "anchor"
    ] == "callout"


def test_html_bridge_does_not_retain_void_elements() -> None:
    parser = bridge.SemanticHTMLParser()
    parser.feed(
        "<html><head><meta charset='utf-8'></head><body>"
        "<div>A<br><img src='x'>B<input value='x'></div>"
        "</body></html>"
    )

    assert parser._stack == []
    assert parser.blocks == [
        {"anchor": "div:1", "kind": "div", "text": "A B"}
    ]


def test_git_sha_is_resolved_from_abacus_root(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def fake_check_output(*args, **kwargs):
        observed.update(kwargs)
        return "f" * 40 + "\n"

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    assert bridge.git_sha() == "f" * 40
    assert observed["cwd"] == ROOT


def test_bridge_payload_is_json_serializable(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "sample.html"
    source.write_text("<p>Offer request</p>", encoding="utf-8")
    monkeypatch.setattr(bridge, "git_sha", lambda: "e" * 40)

    result = bridge.build_bridge(
        [source],
        authority="OFFER_REQUEST",
        lifecycle_status="CURRENT",
        trace_links=["OFFER-01"],
    )

    payload = json.dumps(result, sort_keys=True)
    assert result["schema"] == "abacus-binary-bridge/v1"
    assert result["parser_version"] == "1.1.0"
    assert result["sources"][0]["trace_links"] == ["OFFER-01"]
    assert result["bridge_semantic_sha256"] in payload


def test_current_qps_html_sample_emits_provenance_tuple() -> None:
    source = (
        ROOT
        / "docs"
        / "qps_offer_rtm_evaluation"
        / "current"
        / "DELIVERABLES_INDEX.html"
    )
    assert source.is_file()

    item = bridge.normalize_source(
        source,
        authority="QPS_DERIVED_VIEW",
        lifecycle_status="CURRENT",
        trace_links=["QPS_OFFER_RTM_DELIVERABLES_INDEX"],
        supersedes=[],
        producer_commit="f" * 40,
    )

    assert item["source_id"] == "DELIVERABLES_INDEX.html"
    assert item["source_sha256"]
    assert item["semantic_sha256"]
    assert item["hierarchy_node"]["kind"] == "html"
    assert item["hierarchy_node"]["blocks"]
    assert item["freshness_state"] == "CURRENT_AT_PARSE"
