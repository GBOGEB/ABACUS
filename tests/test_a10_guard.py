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


def test_pdf_streams_are_inflated_and_bad_streams_skipped():
    import zlib

    good = zlib.compress(b"BT (zebra quokka) Tj ET")
    pdf = (
        b"%PDF-1.4\nstream\nnot zlib\nendstream\n"
        + b"stream\n"
        + good
        + b"\nendstream\n"
    )
    assert guard.reason("docs/a.pdf", pdf) == "restricted term in content"
    assert guard.reason("docs/b.pdf", b"%PDF-1.4\nplain") == ""


def test_too_large_fails_closed(monkeypatch):
    monkeypatch.setattr(guard, "MAX_BYTES", 4)
    assert "too large" in guard.reason("docs/a.md", b"12345")


def test_unscanned_extension_passes():
    assert guard.reason("img/logo.png", b"\x89PNG zebra quokka") == ""


def test_tender_like_name():
    assert guard.reason("docs/Bidder_list.md", None) == "tender-like name"


def test_path_key_is_stable():
    assert guard.path_key("a/b.md") == guard.path_key("a/b.md")


# --- end-to-end: main() against a throwaway git repository -------------------


def _git(repo, *args):
    import subprocess  # nosec B404

    subprocess.run(  # nosec B603 B607
        ["git", "-C", str(repo), *args], check=True, capture_output=True
    )


@pytest.fixture
def repo(tmp_path, monkeypatch):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "config", "commit.gpgsign", "false")
    (tmp_path / "README.md").write_text("clean\n")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-qm", "base")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _run(monkeypatch, *argv):
    monkeypatch.setattr(guard.sys, "argv", ["a10_guard.py", *argv])
    try:
        guard.main()
    except SystemExit as exc:
        return exc.code
    return 0


def test_main_staged_clean_and_blocked(repo, monkeypatch, capsys):
    (repo / "ok.md").write_text("fine\n")
    _git(repo, "add", "ok.md")
    assert _run(monkeypatch, "--staged") == 0
    (repo / "bad.md").write_text("zebra quokka\n")
    _git(repo, "add", "bad.md")
    assert _run(monkeypatch, "--staged") == 1
    assert "BLOCK  bad.md" in capsys.readouterr().out


def test_main_allow_list_exempts_reviewed_version_only(repo, monkeypatch):
    (repo / "bad.md").write_text("zebra quokka\n")
    _git(repo, "add", "bad.md")
    import subprocess  # nosec B404

    blob = subprocess.run(  # nosec B603 B607
        ["git", "rev-parse", ":bad.md"], capture_output=True, text=True
    ).stdout.strip()
    (repo / guard.ALLOW_FILE).write_text("# baseline\n" + guard.blob_key(blob) + "\n")
    assert _run(monkeypatch, "--staged") == 0
    (repo / "bad.md").write_text("zebra quokka edited\n")
    _git(repo, "add", "bad.md")
    assert _run(monkeypatch, "--staged") == 1


def test_main_head_and_diff_modes(repo, monkeypatch, capsys):
    import subprocess  # nosec B404

    base = subprocess.run(  # nosec B603 B607
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    (repo / "Tender_Library").mkdir()
    (repo / "Tender_Library" / "x.md").write_text("x\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "add")
    assert _run(monkeypatch, "--head") == 1
    assert _run(monkeypatch, "--diff", base) == 1
    assert _run(monkeypatch, "--diff", "0" * 40) == 1
    assert "not usable" in capsys.readouterr().out
    assert _run(monkeypatch, "--diff", "f" * 40) == 1
