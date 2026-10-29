"""Lane A wave 1: DMAIC_V3.core.ssot_resolver and federation_zero_delta."""

import hashlib
import json

import pytest

from DMAIC_V3.core import federation_zero_delta as fzd
from DMAIC_V3.core import ssot_resolver as sr

MANIFEST = b"authorities:\n  - spine\n"


def _write_root(tmp_path, authorities, source=None, sha=None, manifest=MANIFEST):
    ssot = tmp_path / "ssot"
    ssot.mkdir()
    (ssot / "manifest.yaml").write_bytes(manifest)
    index = {
        "source": "ssot/manifest.yaml" if source is None else source,
        "source_sha256": hashlib.sha256(manifest).hexdigest() if sha is None else sha,
        "authorities": authorities,
    }
    (ssot / "index.json").write_text(json.dumps(index), encoding="utf-8")
    return tmp_path


def test_manifest_sha256_matches_bytes(tmp_path):
    root = _write_root(tmp_path, [])
    assert sr.manifest_sha256(root) == hashlib.sha256(MANIFEST).hexdigest()


def test_manifest_sha256_missing_manifest(tmp_path):
    with pytest.raises(sr.AuthorityResolutionError, match="does not exist"):
        sr.manifest_sha256(tmp_path)


def test_load_index_rejects_wrong_source(tmp_path):
    root = _write_root(tmp_path, [], source="other.yaml")
    with pytest.raises(sr.AuthorityResolutionError, match="not bound"):
        sr.load_index(root)


def test_load_index_rejects_missing_sha(tmp_path):
    root = _write_root(tmp_path, [], sha="")
    with pytest.raises(sr.AuthorityResolutionError, match="missing"):
        sr.load_index(root)


def test_load_index_rejects_stale_sha(tmp_path):
    root = _write_root(tmp_path, [], sha="0" * 64)
    with pytest.raises(sr.AuthorityResolutionError, match="stale"):
        sr.load_index(root)


def test_load_index_rejects_non_list_authorities(tmp_path):
    root = _write_root(tmp_path, {"spine": "x"})
    with pytest.raises(sr.AuthorityResolutionError, match="must be a list"):
        sr.load_index(root)


def test_duplicate_authorities_groups_only_duplicates():
    index = {
        "authorities": [
            {"logical_id": "a", "path": "1"},
            {"logical_id": "b", "path": "2"},
            {"logical_id": "a", "path": "3"},
        ]
    }
    dupes = sr.duplicate_authorities(index)
    assert list(dupes) == ["a"]
    assert [e["path"] for e in dupes["a"]] == ["1", "3"]
    assert sr.duplicate_authorities({}) == {}


def test_duplicate_authorities_requires_logical_id():
    with pytest.raises(sr.AuthorityResolutionError, match="missing logical_id"):
        sr.duplicate_authorities({"authorities": [{"path": "x"}]})


def test_validate_index_reports_competitors_sorted():
    index = {
        "authorities": [
            {"logical_id": "z"},
            {"logical_id": "z"},
            {"logical_id": "b"},
            {"logical_id": "b"},
        ]
    }
    with pytest.raises(
        sr.AuthorityResolutionError, match="competing SSOT authorities: b, z"
    ):
        sr.validate_index(index)
    sr.validate_index({"authorities": [{"logical_id": "only"}]})


def test_resolve_ssot_returns_existing_path(tmp_path):
    root = _write_root(tmp_path, [{"logical_id": "spine", "path": "data/spine.json"}])
    (root / "data").mkdir()
    (root / "data" / "spine.json").write_text("{}", encoding="utf-8")
    assert sr.resolve_ssot(root, "spine") == root / "data" / "spine.json"


def test_resolve_ssot_unknown_id(tmp_path):
    root = _write_root(tmp_path, [{"logical_id": "spine", "path": "x"}])
    with pytest.raises(sr.AuthorityResolutionError, match="found 0"):
        sr.resolve_ssot(root, "nope")


def test_resolve_ssot_missing_authority_file(tmp_path):
    root = _write_root(tmp_path, [{"logical_id": "spine", "path": "gone.json"}])
    with pytest.raises(sr.AuthorityResolutionError, match="does not exist: gone.json"):
        sr.resolve_ssot(root, "spine")


def test_resolve_ssot_rejects_competing_authorities(tmp_path):
    root = _write_root(
        tmp_path,
        [{"logical_id": "s", "path": "a"}, {"logical_id": "s", "path": "b"}],
    )
    with pytest.raises(sr.AuthorityResolutionError, match="competing"):
        sr.resolve_ssot(root, "s")


@pytest.fixture
def spine_root(tmp_path):
    root = _write_root(tmp_path, [{"logical_id": "spine", "path": "d/spine.bin"}])
    (root / "d").mkdir()
    (root / "d" / "spine.bin").write_bytes(b"\x00payload\xff")
    return root


def test_identity_transport_copies_bytes():
    data = b"abc"
    out = fzd.identity_transport(data)
    assert out == data
    assert isinstance(out, bytes)


def test_roundtrip_ssot_zero_delta_receipt(spine_root):
    receipt = fzd.roundtrip_ssot(spine_root, "spine")
    digest = hashlib.sha256(b"\x00payload\xff").hexdigest()
    assert receipt.zero_delta is True
    assert receipt.authority_path == "d/spine.bin"
    assert receipt.payload_sha256 == receipt.returned_payload_sha256 == digest
    assert receipt.boundary == "identity_transport"
    as_dict = receipt.to_dict()
    assert as_dict["authority"] == "AUTHORITATIVE_REFERENCE_ONLY"
    assert as_dict["logical_id"] == "spine"


def test_roundtrip_ssot_rejects_non_bytes_transport(spine_root):
    with pytest.raises(TypeError, match="must return bytes"):
        fzd.roundtrip_ssot(spine_root, "spine", transport=bytearray)


def test_roundtrip_ssot_detects_mutation(spine_root):
    with pytest.raises(RuntimeError, match="SHA256 mismatch"):
        fzd.roundtrip_ssot(spine_root, "spine", transport=lambda p: p + b"!")


class _NamelessTransport:
    def __call__(self, payload):
        return bytes(payload)


def test_roundtrip_ssot_callable_without_name(spine_root):
    receipt = fzd.roundtrip_ssot(spine_root, "spine", transport=_NamelessTransport())
    assert receipt.boundary == "callable_transport"
