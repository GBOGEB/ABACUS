"""Lane A wave 13: DMAIC_V3.core.integrity behaviour."""

import hashlib

import pytest

from DMAIC_V3.core import integrity


def _fake_git(calls):
    def fake(cmd, cwd=None, text=None):
        calls.append((tuple(cmd), cwd))
        if cmd[-1] == "HEAD":
            return "c0ffee\n"
        return "7ree\n"

    return fake


def test_canonical_json_bytes_sorted_compact_and_unicode():
    data = integrity.canonical_json_bytes({"b": 1, "a": "\u00e9"})
    assert data == '{"a":"\u00e9","b":1}'.encode("utf-8")


def test_canonical_json_bytes_default_str_and_rejects_nan():
    assert integrity.canonical_json_bytes({"p": object}).startswith(b'{"p":"<class')
    with pytest.raises(ValueError):
        integrity.canonical_json_bytes(float("nan"))


def test_sha_helpers_agree_with_hashlib(tmp_path):
    expected = hashlib.sha256(b"abc").hexdigest()
    assert integrity.sha256_bytes(b"abc") == expected
    assert integrity.sha256_text("abc") == expected
    assert integrity.sha256_json([1]) == hashlib.sha256(b"[1]").hexdigest()
    target = tmp_path / "f.bin"
    target.write_bytes(b"abc" * 5)
    assert integrity.sha256_file(target, chunk_size=4) == (
        hashlib.sha256(b"abc" * 5).hexdigest()
    )
    empty = tmp_path / "e.bin"
    empty.write_bytes(b"")
    assert integrity.sha256_file(empty) == hashlib.sha256(b"").hexdigest()


def test_git_identity_uses_rev_parse(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("subprocess.check_output", _fake_git(calls))
    ident = integrity.git_identity(str(tmp_path))
    assert ident == integrity.GitIdentity(commit_sha="c0ffee", tree_sha="7ree")
    assert calls[0][0] == ("git", "rev-parse", "HEAD")
    assert calls[1][0] == ("git", "rev-parse", "HEAD^{tree}")
    assert calls[0][1] == tmp_path


@pytest.mark.parametrize(
    "kind,payload,expected",
    [
        ("json", {"x": 1}, integrity.sha256_json({"x": 1})),
        ("text", "hi", integrity.sha256_text("hi")),
        ("bytes", b"hi", integrity.sha256_bytes(b"hi")),
    ],
)
def test_payload_receipt_kinds(monkeypatch, tmp_path, kind, payload, expected):
    monkeypatch.setattr("subprocess.check_output", _fake_git([]))
    receipt = integrity.payload_receipt(tmp_path, payload, payload_kind=kind)
    assert receipt.payload_sha256 == expected
    assert receipt.payload_kind == kind
    as_dict = receipt.to_dict()
    assert as_dict["git"] == {"commit_sha": "c0ffee", "tree_sha": "7ree"}
    assert receipt.receipt_sha256 == integrity.sha256_json(as_dict)


@pytest.mark.parametrize(
    "kind,payload,exc",
    [
        ("text", b"no", TypeError),
        ("bytes", "no", TypeError),
        ("xml", "x", ValueError),
    ],
)
def test_payload_receipt_rejects_bad_input(monkeypatch, tmp_path, kind, payload, exc):
    monkeypatch.setattr("subprocess.check_output", _fake_git([]))
    with pytest.raises(exc):
        integrity.payload_receipt(tmp_path, payload, payload_kind=kind)


def test_assert_expected_sha():
    integrity.assert_expected_sha("a", "a")
    with pytest.raises(ValueError, match="digest mismatch: expected b, got a"):
        integrity.assert_expected_sha("a", "b", label="digest")
