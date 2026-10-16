from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "code_maroon" / "ooxml_scan.py"
SPEC = importlib.util.spec_from_file_location("code_maroon_ooxml", MODULE)
M = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(M)


def make_zip(path: Path, members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return path


def rules(receipt):
    return {item["rule_id"] for item in receipt["findings"]}


def test_safe_minimal_ooxml_package(tmp_path):
    path = make_zip(
        tmp_path / "safe.docx",
        {
            "[Content_Types].xml": b"<Types/>",
            "_rels/.rels": b"<Relationships/>",
            "word/document.xml": b"<w:document/>",
        },
    )
    receipt = M.scan_package(path)
    assert receipt["entries"] == 3
    assert receipt["findings"] == []
    assert len(receipt["sha256"]) == 64


def test_path_traversal_is_high_severity(tmp_path):
    path = make_zip(
        tmp_path / "bad.docx",
        {
            "../escape.bin": b"x",
            "[Content_Types].xml": b"<Types/>",
        },
    )
    receipt = M.scan_package(path)
    assert "OOXML_PATH_TRAVERSAL" in rules(receipt)
    assert any(
        item["severity"] == "HIGH"
        for item in receipt["findings"]
        if item["rule_id"] == "OOXML_PATH_TRAVERSAL"
    )


def test_macro_embedding_and_external_relationships_are_review_findings(tmp_path):
    path = make_zip(
        tmp_path / "review.docm",
        {
            "word/vbaProject.bin": b"macro",
            "word/embeddings/oleObject1.bin": b"ole",
            "word/externalLinks/externalLink1.xml": b"<x/>",
            "word/_rels/document.xml.rels": (
                b'<Relationships><Relationship TargetMode="External" '
                b'Target="https://example.invalid"/></Relationships>'
            ),
        },
    )
    receipt = M.scan_package(path)
    assert rules(receipt) >= {
        "OOXML_VBA_MACRO",
        "OOXML_EMBEDDED_OBJECT",
        "OOXML_EXTERNAL_LINK_PART",
        "OOXML_EXTERNAL_RELATIONSHIP",
    }
    assert not any(item["severity"] == "HIGH" for item in receipt["findings"])


def test_malformed_ooxml_fails_closed(tmp_path):
    path = tmp_path / "broken.xlsx"
    path.write_bytes(b"not-a-zip")
    receipt = M.scan_package(path)
    assert rules(receipt) == {"OOXML_INVALID_PACKAGE"}
    assert receipt["findings"][0]["severity"] == "HIGH"
