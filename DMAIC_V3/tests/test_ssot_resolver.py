import json
from pathlib import Path

import pytest

from DMAIC_V3.core.integrity import sha256_bytes
from DMAIC_V3.core.ssot_resolver import (
    AuthorityResolutionError,
    duplicate_authorities,
    load_index,
    resolve_ssot,
    validate_index,
)


def write_manifest(root: Path, content: str = "manifest: true\n") -> str:
    (root / "ssot").mkdir(exist_ok=True)
    path = root / "ssot" / "manifest.yaml"
    path.write_text(content, encoding="utf-8")
    return sha256_bytes(path.read_bytes())


def write_index(root: Path, authorities, source="ssot/manifest.yaml", source_sha256=None):
    (root / "ssot").mkdir(exist_ok=True)
    if source_sha256 is None:
        source_sha256 = write_manifest(root)
    (root / "ssot" / "index.json").write_text(
        json.dumps({"source": source, "source_sha256": source_sha256, "authorities": authorities}),
        encoding="utf-8",
    )


def test_resolves_exactly_one_existing_authority(tmp_path):
    write_manifest(tmp_path)
    write_index(tmp_path, [{"logical_id": "A", "path": "ssot/a.yaml", "state": "AUTHORITATIVE"}])
    (tmp_path / "ssot" / "a.yaml").write_text("a: 1\n", encoding="utf-8")
    assert resolve_ssot(tmp_path, "A") == tmp_path / "ssot" / "a.yaml"


def test_duplicate_authority_fails_closed(tmp_path):
    entries = [
        {"logical_id": "A", "path": "ssot/a.yaml"},
        {"logical_id": "A", "path": "ssot/b.yaml"},
    ]
    write_index(tmp_path, entries)
    index = load_index(tmp_path)
    assert list(duplicate_authorities(index)) == ["A"]
    with pytest.raises(AuthorityResolutionError, match="competing"):
        validate_index(index)


def test_missing_logical_id_fails_closed(tmp_path):
    write_index(tmp_path, [])
    with pytest.raises(AuthorityResolutionError, match="found 0"):
        resolve_ssot(tmp_path, "MISSING")


def test_missing_authority_path_fails_closed(tmp_path):
    write_index(tmp_path, [{"logical_id": "A", "path": "ssot/missing.yaml"}])
    with pytest.raises(AuthorityResolutionError, match="does not exist"):
        resolve_ssot(tmp_path, "A")


def test_index_must_be_manifest_bound(tmp_path):
    write_index(tmp_path, [], source="other.yaml")
    with pytest.raises(AuthorityResolutionError, match="manifest"):
        load_index(tmp_path)


def test_index_must_match_current_manifest_digest(tmp_path):
    write_manifest(tmp_path, "manifest: old\n")
    write_index(tmp_path, [], source_sha256="0" * 64)
    with pytest.raises(AuthorityResolutionError, match="stale"):
        load_index(tmp_path)
