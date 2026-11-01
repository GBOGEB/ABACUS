"""W32 fail-closed source/semantic binding tests for all bridge input families."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qps_binary_bridge_w32", ROOT / "tools/qps_binary_bridge.py"
)
assert SPEC and SPEC.loader
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)


@pytest.mark.parametrize(
    "extension", [".docx", ".xlsx", ".pptx", ".pdf", ".html", ".htm"]
)
def test_mid_extraction_mutation_fails_closed(tmp_path, monkeypatch, extension):
    source = tmp_path / ("asset" + extension)
    source.write_bytes(b"original")

    def mutate(path):
        path.write_bytes(b"modified")
        return {"kind": extension, "extraction_quality": {"status": "STRUCTURED"}}

    monkeypatch.setitem(bridge.EXTRACTORS, extension, mutate)
    with pytest.raises(RuntimeError, match="binary source mutated during extraction"):
        bridge.normalize_source(
            source,
            authority="CHILD_SSOT",
            lifecycle_status="CURRENT",
            trace_links=[],
            supersedes=[],
            producer_commit="a" * 40,
        )


@pytest.mark.parametrize(
    "extension", [".docx", ".xlsx", ".pptx", ".pdf", ".html", ".htm"]
)
def test_unmodified_source_keeps_two_hashes_consistent(
    tmp_path, monkeypatch, extension
):
    source = tmp_path / ("asset" + extension)
    source.write_bytes(b"identical bytes")
    monkeypatch.setitem(
        bridge.EXTRACTORS,
        extension,
        lambda path: {"kind": extension, "text": path.read_bytes().decode("ascii")},
    )
    receipt = bridge.normalize_source(
        source,
        authority="CHILD_SSOT",
        lifecycle_status="CURRENT",
        trace_links=[],
        supersedes=[],
        producer_commit="b" * 40,
    )
    assert receipt["source_sha256"] == bridge.sha256_bytes(source.read_bytes())
    assert receipt["artifact_hashes"]["source_sha256"] == receipt["source_sha256"]
    assert receipt["semantic_sha256"] == bridge.canonical_sha256(
        receipt["hierarchy_node"]
    )
    assert receipt["artifact_hashes"]["semantic_sha256"] == receipt["semantic_sha256"]


def test_unsupported_family_fails_before_extraction(tmp_path):
    p = tmp_path / "unsupported.exe"
    p.write_bytes(b"data")
    with pytest.raises(ValueError, match="unsupported source family"):
        bridge.normalize_source(
            p,
            authority="DERIVED",
            lifecycle_status="CURRENT",
            trace_links=[],
            supersedes=[],
            producer_commit="c" * 40,
        )


def test_absent_source_fails_closed(tmp_path):
    p = tmp_path / "missing.html"
    with pytest.raises(FileNotFoundError):
        bridge.normalize_source(
            p,
            authority="DERIVED",
            lifecycle_status="CURRENT",
            trace_links=[],
            supersedes=[],
            producer_commit="d" * 40,
        )


def test_mid_extraction_deletion_fails_closed(tmp_path, monkeypatch):
    p = tmp_path / "deleted.html"
    p.write_text("before", encoding="utf-8")

    def delete(path):
        path.unlink()
        return {"kind": "html"}

    monkeypatch.setitem(bridge.EXTRACTORS, ".html", delete)
    with pytest.raises(FileNotFoundError):
        bridge.normalize_source(
            p,
            authority="DERIVED",
            lifecycle_status="CURRENT",
            trace_links=[],
            supersedes=[],
            producer_commit="e" * 40,
        )
