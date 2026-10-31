"""Gap tests for tools/a10_guard.py: git wrappers, decoding edges and main()."""

import io
import types
import zipfile

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

guard = load("tools/a10_guard.py", name="abn_w7_a10_guard")


def test_git_returns_stdout(monkeypatch):
    seen = {}

    def fake_run(cmd, capture_output):
        seen["cmd"] = cmd
        return types.SimpleNamespace(stdout=b"out", returncode=0)

    monkeypatch.setattr(guard.subprocess, "run", fake_run)
    assert guard.git("ls-files") == b"out"
    assert seen["cmd"] == ["git", "ls-files"]


def test_git_ok_reflects_returncode(monkeypatch):
    codes = iter([0, 1])
    monkeypatch.setattr(
        guard.subprocess,
        "run",
        lambda cmd, capture_output: types.SimpleNamespace(returncode=next(codes)),
    )
    assert guard.git_ok("cat-file", "-e", "x") is True
    assert guard.git_ok("cat-file", "-e", "x") is False


def test_decode_text_bom_with_invalid_payload_fails_closed():
    # UTF-16 BOM followed by an odd trailing byte cannot be decoded.
    assert guard.decode_text(b"\xff\xfeA\x00B") is None


def test_doc_text_zip_skips_non_xml_and_rejects_bad_xml():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("media/image.png", b"\x89PNG")
        z.writestr("word/document.xml", b"<w>hello</w>")
    assert "hello" in guard.doc_text(".docx", buf.getvalue())

    bad = io.BytesIO()
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("word/document.xml", b"\xff\xfe\x00bad\x00")
        z.writestr("word/x.xml", b"abc\x00def")
    assert guard.doc_text(".docx", bad.getvalue()) is None


def test_reason_without_data_and_clean_name_is_empty():
    assert guard.reason("docs/readme.md", None) == ""


def _install_git(monkeypatch, outputs, ok=True):
    calls = []

    def fake_git(*args):
        calls.append(args)
        for key, value in outputs.items():
            if args[: len(key)] == key:
                return value
        return b""

    monkeypatch.setattr(guard, "git", fake_git)
    monkeypatch.setattr(guard, "git_ok", lambda *a: ok)
    return calls


def test_main_head_mode_ok(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(guard.sys, "argv", ["a10_guard.py", "--head"])
    _install_git(
        monkeypatch,
        {
            ("ls-files",): b"docs/a.md\ntools/a10_guard.py\n.githooks/pre\n",
            ("ls-tree",): b"100644 blob abc123\tdocs/a.md\n",
            ("cat-file", "-p"): b"plain words",
        },
    )
    guard.main()
    assert "a10_guard: OK (3 files checked)" in capsys.readouterr().out


def test_main_unusable_base_falls_back_and_blocks(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(guard.sys, "argv", ["a10_guard.py", "--diff", "0000000000"])
    _install_git(
        monkeypatch,
        {
            ("ls-files",): b"offers_itt/x.md\nnotracked_tender.txt\n",
            ("ls-tree",): b"100644 blob abc\toffers_itt/x.md\n",
            ("cat-file", "-p"): b"text",
        },
    )
    with pytest.raises(SystemExit) as exc:
        guard.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "not usable" in out
    assert "BLOCK  offers_itt/x.md   (tender folder)" in out
    assert "2 file(s) look like tender material" in out


def test_main_diff_mode_with_valid_base(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(guard.sys, "argv", ["a10_guard.py", "--diff", "abcdef1"])
    calls = _install_git(
        monkeypatch,
        {
            ("diff", "--name-only"): b"docs/b.md\n",
            ("ls-tree",): b"",
        },
    )
    guard.main()
    assert any(
        c[:2] == ("diff", "--name-only") and "abcdef1...HEAD" in c for c in calls
    )
    assert "OK (1 files checked)" in capsys.readouterr().out


def test_main_staged_mode_respects_allow_file(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    allowed_blob = guard.blob_key("blob1")
    allowed_path = guard.path_key("cost_estimate_v2.md")
    (tmp_path / guard.ALLOW_FILE).write_text(
        "# reviewed\n\n" + allowed_blob + "\n" + allowed_path + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(guard.sys, "argv", ["a10_guard.py", "--staged"])
    _install_git(
        monkeypatch,
        {
            ("diff", "--cached"): b"tender_a.md\ncost_estimate_v2.md\n",
            ("ls-files", "-s"): b"100644 blob1 0\ttender_a.md\n",
        },
    )
    guard.main()
    assert "OK (2 files checked)" in capsys.readouterr().out
