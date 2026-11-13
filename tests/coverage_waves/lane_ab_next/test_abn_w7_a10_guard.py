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
        z = "-z" in args
        args = tuple(a for a in args if a != "-z")
        for key, value in outputs.items():
            if args[: len(key)] == key:
                return value.replace(b"\n", b"\0") if z else value
        return b""

    def fake_read_blobs(tree, items):
        for _ in items:
            yield outputs.get(("cat-file", "-p"), b"")

    monkeypatch.setattr(guard, "git", fake_git)
    monkeypatch.setattr(guard, "git_ok", lambda *a: ok)
    monkeypatch.setattr(guard, "read_blobs", fake_read_blobs)
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
        c[0] == "diff" and "--name-only" in c and "abcdef1...HEAD" in c for c in calls
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


# --- #2698: merge-aware --staged and the streamed cat-file batch -------------


def test_main_staged_merge_diffs_against_merge_head(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(guard.sys, "argv", ["a10_guard.py", "--staged"])
    calls = _install_git(
        monkeypatch,
        {
            ("diff", "--cached"): b"docs/pr.md\n",
            ("ls-files", "-s"): b"100644 blobpr 0\tdocs/pr.md\n",
            ("cat-file", "-p"): b"plain words",
        },
        ok=True,
    )
    guard.main()
    diff = [c for c in calls if c[0] == "diff"]
    assert diff and diff[0][-1] == "MERGE_HEAD"
    assert "OK (1 files checked)" in capsys.readouterr().out


def test_main_staged_without_merge_checks_all_staged(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(guard.sys, "argv", ["a10_guard.py", "--staged"])
    calls = _install_git(
        monkeypatch,
        {
            ("diff", "--cached"): b"docs/a.md\n",
            ("ls-files", "-s"): b"100644 blobA 0\tdocs/a.md\n",
            ("cat-file", "-p"): b"plain words",
        },
        ok=False,
    )
    guard.main()
    diff = [c for c in calls if c[0] == "diff"]
    assert diff and "MERGE_HEAD" not in diff[0]
    assert "OK (1 files checked)" in capsys.readouterr().out


def test_git_z_and_index_ids(monkeypatch):
    out = {
        "ls-files": b"100644 aaa 0\tsp ace.md\x00100644 bbb 2\tb.md\x00",
        "ls-tree": b"100644 blob ccc\tc.md\x00",
    }
    seen = []

    def fake_git(*args):
        seen.append(args)
        return out[args[0]]

    monkeypatch.setattr(guard, "git", fake_git)
    assert guard.index_ids("ls-files", "-s") == {"sp ace.md": "aaa", "b.md": "bbb"}
    assert guard.index_ids("ls-tree", "-r", "HEAD") == {"c.md": "ccc"}
    assert seen[0] == ("ls-files", "-z", "-s")
    assert seen[1] == ("ls-tree", "-z", "-r", "HEAD")


def _tar(files):
    import tarfile

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def test_chunks_split_on_count_and_length():
    items = [(f"p{i}", "x") for i in range(5)]
    assert [len(c) for c in guard.chunks(items, max_items=2)] == [2, 2, 1]
    long = [("a" * 10, "x"), ("b" * 10, "y")]
    assert [len(c) for c in guard.chunks(long, max_chars=15)] == [1, 1]
    assert list(guard.chunks([])) == []


def test_read_blobs_uses_raw_archive_members(monkeypatch):
    archive = _tar({"a.md": b"hello\n", "b.md": b"bee"})
    calls = []

    def fake_git(*args):
        calls.append(args)
        if "archive" in args:
            # No repository attributes and no eol conversion: members are the raw blobs.
            assert args[:7] == (
                "--attr-source=" + guard.EMPTY_TREE,
                "-c",
                "core.autocrlf=false",
                "--literal-pathspecs",
                "archive",
                "--format=tar",
                "T",
            )
            return archive
        return b"exact blob"

    monkeypatch.setattr(guard, "git", fake_git)
    items = [
        ("a.md", "1"),
        ("b.md", "2"),
        ("c.md", "3"),
    ]  # c.md missing from the archive
    assert list(guard.read_blobs("T", items)) == [b"hello\n", b"bee", b"exact blob"]
    assert [c for c in calls if c[0] == "cat-file"] == [("cat-file", "-p", "3")]


def test_read_merge_heads(monkeypatch, tmp_path):
    head_file = tmp_path / "MERGE_HEAD"
    head_file.write_text("aaa\nbbb\n\n", encoding="ascii")
    monkeypatch.setattr(guard, "git_ok", lambda *a: True)
    monkeypatch.setattr(guard, "git", lambda *a: str(head_file).encode() + b"\n")
    assert guard.read_merge_heads() == ["aaa", "bbb"]
    monkeypatch.setattr(guard, "git", lambda *a: str(tmp_path / "missing").encode())
    assert guard.read_merge_heads() == ["MERGE_HEAD"]
    monkeypatch.setattr(guard, "git_ok", lambda *a: False)
    assert guard.read_merge_heads() == []


def test_main_staged_octopus_skips_files_from_any_parent(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(guard.sys, "argv", ["a10_guard.py", "--staged"])
    calls = _install_git(
        monkeypatch,
        {("ls-files", "-s"): b"100644 b1 0\tpr.md\n", ("cat-file", "-p"): b"ok"},
    )
    differs = {
        "A": b"pr.md\0offers_itt/from_b.md\0",  # from_b.md is unchanged from parent B
        "B": b"pr.md\0offers_itt/from_a.md\0",  # from_a.md is unchanged from parent A
    }
    inner = guard.git

    def fake_git(*args):
        if args[0] == "diff":
            calls.append(args)
            return differs[args[-1]]
        return inner(*args)

    monkeypatch.setattr(guard, "git", fake_git)
    monkeypatch.setattr(guard, "read_merge_heads", lambda: ["A", "B"])
    guard.main()
    assert "OK (1 files checked)" in capsys.readouterr().out
    assert [c[-1] for c in calls if c[0] == "diff"] == ["A", "B"]


def test_read_blobs_falls_back_when_archive_fails(monkeypatch):
    monkeypatch.setattr(
        guard, "git", lambda *a: b"" if "archive" in a else b"blob " + a[-1].encode()
    )
    assert list(guard.read_blobs("T", [("a.md", "aaa")])) == [b"blob aaa"]
    assert list(guard.read_blobs("T", [])) == []
