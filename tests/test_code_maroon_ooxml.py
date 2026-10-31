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


def test_oversized_relationship_part_emits_high_not_silent_skip(tmp_path):
    external = (
        b'<Relationships><Relationship TargetMode="External" '
        b'Target="https://example.invalid"/></Relationships>'
    )
    payload = external + b" " * (M.MAX_REL_BYTES + 1 - len(external))
    path = make_zip(tmp_path / "oversize.docx", {"_rels/.rels": payload})
    receipt = M.scan_package(path)
    assert "OOXML_RELATIONSHIP_OVERSIZE" in rules(receipt)
    assert any(
        f["severity"] == "HIGH"
        for f in receipt["findings"]
        if f["rule_id"] == "OOXML_RELATIONSHIP_OVERSIZE"
    )
    assert receipt["entries"] == 1


def test_bounded_relationship_exact_limit_is_inspected(tmp_path):
    external = (
        b'<Relationships><Relationship TargetMode="External" '
        b'Target="https://example.invalid"/></Relationships>'
    )
    payload = external + b" " * (M.MAX_REL_BYTES - len(external))
    path = make_zip(tmp_path / "limit.docx", {"_rels/.rels": payload})
    receipt = M.scan_package(path)
    assert "OOXML_EXTERNAL_RELATIONSHIP" in rules(receipt)
    assert "OOXML_RELATIONSHIP_OVERSIZE" not in rules(receipt)


def test_cli_emits_a_real_receipt_and_blocks_invalid_package(
    tmp_path, monkeypatch, capsys
):
    import json
    import sys

    good = make_zip(tmp_path / "safe.docx", {"word/document.xml": b"<w/>"})
    bad = tmp_path / "broken.docx"
    bad.write_bytes(b"this is not a valid zip")
    out = tmp_path / "evidence" / "scan.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["ooxml_scan", str(good), str(bad), "--output", str(out), "--fail-on", "high"],
    )
    assert M.main() == 1
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["package_count"] == 2
    assert data["severity"]["HIGH"] >= 1
    assert data["merge_authorized"] is False
    assert json.loads(capsys.readouterr().out)["output"] == str(out)
    monkeypatch.setattr(
        sys,
        "argv",
        ["ooxml_scan", str(good), "--output", str(out), "--fail-on", "high"],
    )
    assert M.main() == 0


def test_cli_medium_findings_remain_blocking_only_when_selected(tmp_path, monkeypatch):
    import json
    import sys

    macro = make_zip(tmp_path / "macro.docm", {"word/vbaProject.bin": b"x"})
    out = tmp_path / "macro.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["ooxml_scan", str(macro), "--output", str(out), "--fail-on", "medium"],
    )
    assert M.main() == 1
    receipt = json.loads(out.read_text())
    assert receipt["severity"]["MEDIUM"] >= 1
    assert receipt["severity"]["HIGH"] == 0
    monkeypatch.setattr(
        sys,
        "argv",
        ["ooxml_scan", str(macro), "--output", str(out), "--fail-on", "high"],
    )
    assert M.main() == 0


def test_git_discovery_filters_tracked_ooxml_and_fails_on_git_error(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    good = make_zip(tmp_path / "tracked.docx", {"word/document.xml": b"<w/>"})
    (tmp_path / "notes.txt").write_text("not OOXML", encoding="utf-8")

    def listed(cmd, **kwargs):
        assert cmd == ["git", "ls-files", "-z"]
        assert kwargs["cwd"] == tmp_path
        return SimpleNamespace(returncode=0, stdout=b"tracked.docx\0notes.txt\0")

    monkeypatch.setattr(M.subprocess, "run", listed)
    assert M.discover_git(tmp_path) == [good]

    def failed(cmd, **kwargs):
        return SimpleNamespace(returncode=1, stdout=b"")

    monkeypatch.setattr(M.subprocess, "run", failed)
    import pytest

    with pytest.raises(RuntimeError, match="git ls-files failed"):
        M.discover_git(tmp_path)


def test_archive_metadata_limits_emit_high_findings(tmp_path, monkeypatch):
    path = make_zip(
        tmp_path / "limits.docx",
        {
            "word/document.xml": b"<x/>",
            "word/styles.xml": b"<y/>",
        },
    )
    monkeypatch.setattr(M, "MAX_ENTRIES", 1)
    monkeypatch.setattr(M, "MAX_TOTAL_UNCOMPRESSED", 1)
    receipt = M.scan_package(path)
    assert "OOXML_TOO_MANY_ENTRIES" in rules(receipt)
    assert "OOXML_UNCOMPRESSED_LIMIT" in rules(receipt)
    assert receipt["entries"] == 2
