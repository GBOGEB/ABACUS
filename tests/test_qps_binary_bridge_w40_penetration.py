"""CODE PURPLE W40: native binary/semantic parser penetration, 42 distinct oracles.

The tests exercise real parsers and bytes (not mocked extractor outcomes).
Only self-contained synthetic fixtures; no test exclusions or remote writes.
"""
from __future__ import annotations

import html
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qps_binary_bridge_w40", ROOT / "tools/qps_binary_bridge.py"
)
assert SPEC is not None and SPEC.loader is not None
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _package(path: Path, family: str, token: str = "Baseline") -> str:
    """Materialize smallest executable OOXML fixture with real XML and ZIP bytes."""
    safe = html.escape(token, quote=False)
    if family == "docx":
        member = "word/document.xml"
        parts = {
            member: (
                f'<w:document xmlns:w="{W}"><w:body><w:p>'
                f'<w:r><w:t>{safe}</w:t></w:r></w:p></w:body></w:document>'
            )
        }
    elif family == "xlsx":
        member = "xl/workbook.xml"
        parts = {
            member: (
                f'<workbook xmlns="{S}" xmlns:r="{R}"><sheets>'
                '<sheet name="Main" sheetId="1" r:id="rId1"/>'
                '</sheets></workbook>'
            ),
            "xl/_rels/workbook.xml.rels": (
                f'<Relationships xmlns="{REL}"><Relationship Id="rId1" '
                'Type="worksheet" Target="worksheets/sheet1.xml"/>'
                '</Relationships>'
            ),
            "xl/worksheets/sheet1.xml": (
                f'<worksheet xmlns="{S}"><sheetData><row r="1">'
                f'<c r="A1" t="inlineStr"><is><t>{safe}</t></is></c>'
                '</row></sheetData></worksheet>'
            ),
        }
    elif family == "pptx":
        member = "ppt/slides/slide1.xml"
        parts = {
            member: (
                f'<p:sld xmlns:p="{P}" xmlns:a="{A}"><p:cSld>'
                f'<a:p><a:r><a:t>{safe}</a:t></a:r></a:p>'
                '</p:cSld></p:sld>'
            )
        }
    else:
        raise AssertionError("unknown family " + family)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for key, value in parts.items():
            z.writestr(key, value)
    return member


def _normalized(path: Path):
    return bridge.normalize_source(
        path, authority="DERIVED_CHILD", lifecycle_status="CURRENT",
        trace_links=["W40-REVERSE-ORACLE"], supersedes=["W32"],
        producer_commit="a" * 40,
    )


@pytest.mark.parametrize("family", ("docx", "xlsx", "pptx"))
@pytest.mark.parametrize(
    "attack,invalid", (
        ("not_a_zip", b"not a ZIP or Office source"),
        ("truncated_directory", b"PK\x03\x04truncated"),
        ("empty_xml", b""),
        ("unclosed_xml", b"<root>"),
        ("undefined_entity", b"<root>&w40_external_entity;</root>"),
        ("malformed_nesting", b"<root><child></root>"),
    ),
)
def test_ooxml_corrupted_container_or_xml_rejected(tmp_path, family, attack, invalid):
    """18 negative ZIP/XML oracles: never publish fabricated structured semantics."""
    source = tmp_path / ("fault." + family)
    member = _package(source, family)
    if attack in {"not_a_zip", "truncated_directory"}:
        source.write_bytes(invalid)
        expected = zipfile.BadZipFile
    else:
        with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr(member, invalid)
            if family == "xlsx":
                # Only the mandatory workbook root is corrupted, not its satellites.
                z.writestr(
                    "xl/_rels/workbook.xml.rels",
                    f'<Relationships xmlns="{REL}"/>',
                )
        expected = bridge.ET.ParseError
    with pytest.raises(expected):
        _normalized(source)


@pytest.mark.parametrize("family", ("docx", "xlsx", "pptx"))
@pytest.mark.parametrize("token", ("CAPEX", "OPEX", "helium-2K", "Ωmega & <stress>"))
def test_ooxml_single_semantic_token_flip_changes_both_digests(
    tmp_path, family, token
):
    """12 matched reverse controls: a real OOXML text mutation changes both hashes."""
    source = tmp_path / ("same-path." + family)
    _package(source, family, token)
    before = _normalized(source)
    before_semantics = json.dumps(before["hierarchy_node"], ensure_ascii=False)
    assert token in before_semantics
    _package(source, family, token + "::revised")
    after = _normalized(source)
    after_semantics = json.dumps(after["hierarchy_node"], ensure_ascii=False)
    assert token + "::revised" in after_semantics
    assert before["source_sha256"] != after["source_sha256"]
    assert before["semantic_sha256"] != after["semantic_sha256"]
    assert before["source_id"] == after["source_id"]
    assert before["authority"] == after["authority"] == "DERIVED_CHILD"
    assert before["trace_links"] == after["trace_links"]


@pytest.mark.parametrize(
    "suffix,markup,visible,hidden", (
        (".html", "<head>PRIVATE</head><main>Public</main>", "Public", "PRIVATE"),
        (".htm", "<script>EXFIL</script><p>Safe</p>", "Safe", "EXFIL"),
        (".html", "<style>HIDDEN</style><section>Section</section>",
         "Section", "HIDDEN"),
        (".htm", "<template>OPAQUE</template><article>Article</article>",
         "Article", "OPAQUE"),
        (".html", "<div id='root'>A<img src='x'>B</div>", "A B", "NOT-A-TOKEN"),
        (".htm", "<p id='entity'>A &amp; B</p>", "A & B", "NOT-A-TOKEN"),
    ),
)
def test_html_visibility_and_void_reverse_controls(
    tmp_path, suffix, markup, visible, hidden
):
    """6 source-real HTML/HTM visibility, script, entity and void-tag controls."""
    source = tmp_path / ("page" + suffix)
    source.write_text(markup, encoding="utf-8")
    receipt = _normalized(source)
    blocks = receipt["hierarchy_node"]["blocks"]
    assert any(visible in block["text"] for block in blocks)
    assert all(hidden not in block["text"] for block in blocks)
    assert receipt["extraction_quality"]["status"] == "STRUCTURED"
    assert receipt["source_sha256"] == bridge.sha256_bytes(source.read_bytes())


@pytest.mark.parametrize(
    "pages,literal", (
        (1, "QPS_HOT"),
        (1, "QPS_COLD"),
        (2, "AUX_LOOP"),
        (2, "LKT_HELIUM"),
        (3, "ALAT_COMPRESSION"),
        (4, "RECEIPT_W40"),
    ),
)
def test_pdf_uncompressed_fallback_is_explicitly_degraded(
    tmp_path, pages, literal
):
    """6 actual byte-stream fallback controls: distinguish degraded from structured."""
    source = tmp_path / "fallback.pdf"
    source.write_bytes(
        b"%PDF-1.4\n"
        + b"\n".join(b"1 0 obj << /Type /Page >> endobj" for _ in range(pages))
        + b"\nBT (" + literal.encode("ascii") + b") Tj ET\n%%EOF\n"
    )
    result = bridge._pdf_literal_fallback(source)
    assert result["extraction_quality"] == {
        "status": "FALLBACK", "parser": "pdf_literal_strings"
    }
    assert len(result["pages"]) == pages
    assert [p["number"] for p in result["pages"]] == list(range(1, pages + 1))
    assert result["pages"][0]["text"] == literal
    assert all(not p["text"] for p in result["pages"][1:])
    assert [p["anchor"] for p in result["pages"]] == [
        f"page:{i}" for i in range(1, pages + 1)
    ]
