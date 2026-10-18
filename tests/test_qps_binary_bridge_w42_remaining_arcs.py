"""W42 fixed-source remaining-arc testflight for the QPS semantic bridge.

Four disjoint native controls targeting *only* the five unexercised opportunities
in the W41 artifact: statements 371-372 and branch arcs [172,143],
[462,-457], [463,462]. No exclusions or production source edits.
"""
from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qps_binary_bridge_w42", ROOT / "tools/qps_binary_bridge.py"
)
assert SPEC is not None and SPEC.loader is not None
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def test_missing_optional_pdf_reader_takes_explicit_degraded_path(
    tmp_path, monkeypatch
):
    """Cover the genuine ImportError branch, not the separate malformed-PDF path."""
    source = tmp_path / "reader-unavailable.pdf"
    source.write_bytes(
        b"%PDF-1.4\n1 0 obj << /Type /Page >> endobj\n"
        b"BT (W42 reader missing) Tj ET\n%%EOF\n"
    )
    original_import = builtins.__import__

    def deny_optional_reader(name, *args, **kwargs):
        if name == "pypdf":
            raise ImportError("W42 fault injection: optional reader unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", deny_optional_reader)
    result = bridge.extract_pdf(source)
    assert result["extraction_quality"] == {
        "status": "FALLBACK", "parser": "pdf_literal_strings",
    }
    assert result["pages"] == [
        {"anchor": "page:1", "number": 1, "text": "W42 reader missing"},
    ]


def test_docx_section_properties_do_not_emit_false_content(tmp_path):
    """Exercise a valid body child that is neither a paragraph nor a table."""
    source = tmp_path / "with-section.docx"
    document = (
        f'<w:document xmlns:w="{W}"><w:body>'
        "<w:p><w:r><w:t>Visible</w:t></w:r></w:p>"
        "<w:sectPr/><w:sectPr/></w:body></w:document>"
    )
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("word/document.xml", document)
    result = bridge.extract_docx(source)
    assert result["blocks"] == [
        {"anchor": "paragraph:1", "kind": "paragraph",
         "style": None, "text": "Visible"},
    ]


def test_html_no_capture_ancestor_drops_orphan_text_without_phantom_node():
    """Exercise the unconsumed full-loop outcome of handle_data."""
    parser = bridge.SemanticHTMLParser()
    parser.feed("<span>Outside capture</span>")
    assert parser.blocks == []
    assert parser._stack == []


def test_html_non_capture_inner_run_returns_to_visible_parent():
    """Exercise false-then-true CAPTURE_TAGS path for legitimate nested formatting."""
    parser = bridge.SemanticHTMLParser()
    parser.feed(
        "<p id='visible'><em>First</em> and <strong>Second</strong></p>"
    )
    assert parser.blocks == [
        {"anchor": "visible", "kind": "p", "text": "First and Second"},
    ]
    assert parser._stack == []
