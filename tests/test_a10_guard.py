"""Unit tests for tools/a10_guard.py (A10.8 tender guard).

Uses a made-up term only; the real restricted terms are never written here.
"""

import hashlib
import importlib.util
import io
import os
import zipfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "a10_guard", os.path.join(ROOT, "tools", "a10_guard.py")
)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)

FAKE = "zebra quokka"


@pytest.fixture(autouse=True)
def fake_terms(monkeypatch):
    h = hashlib.sha256(("a10|" + FAKE).encode()).hexdigest()[:20]
    monkeypatch.setattr(guard, "TERM_HASHES", {h})


def test_clean_text_passes():
    assert guard.reason("docs/notes.md", b"nothing to see here") == ""


def test_term_in_text_blocks():
    why = guard.reason("docs/notes.md", b"some Zebra-Quokka text")
    assert why == "restricted term in content"


def test_folder_rule_is_case_insensitive():
    assert guard.reason("Tender_Library/a.md", None) == "tender folder"


def test_docx_is_unzipped_and_scanned():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", "<w:t>zebra</w:t><w:t>quokka</w:t>")
    assert guard.reason("docs/a.docx", buf.getvalue()) != ""


def test_closed_binary_fails_closed():
    assert "fail closed" in guard.reason("docs/a.xls", b"\x00\x01")


def test_broken_docx_fails_closed():
    assert "fail closed" in guard.reason("docs/a.docx", b"not a zip")


def test_blob_key_is_stable_and_short():
    assert guard.blob_key("abc") == guard.blob_key("abc")
    assert len(guard.blob_key("abc")) == 20


def test_utf16_with_bom_is_decoded_and_blocked():
    data = "some zebra quokka text".encode("utf-16")
    assert guard.reason("docs/notes.txt", data) == "restricted term in content"


def test_utf16_without_bom_fails_closed():
    data = "some zebra quokka text".encode("utf-16-le")
    assert "fail closed" in guard.reason("docs/notes.csv", data)


def test_invalid_utf8_fails_closed():
    assert "fail closed" in guard.reason("docs/notes.txt", b"caf\xe9 zebra")


def test_zero_width_and_fullwidth_tricks_are_blocked():
    data = "zeb​ra ｑｕｏｋｋａ".encode("utf-8")
    assert guard.reason("docs/notes.md", data) == "restricted term in content"


def test_clean_utf16_passes():
    assert guard.reason("docs/notes.txt", "hello".encode("utf-16")) == ""
