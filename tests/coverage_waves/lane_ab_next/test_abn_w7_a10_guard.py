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

    def fake_read_blobs(blob_ids):
        for bid in blob_ids:
            yield bid, outputs.get(("cat-file", "-p"), b"")

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


class _FakeProc:
    def __init__(self, stdout, stdin=None):
        self.stdin = stdin if stdin is not None else io.BytesIO()
        self.stdout = io.BytesIO(stdout)
        self.waited = False

    def wait(self):
        self.waited = True
        return 0


def test_read_blobs_streams_batch_output(monkeypatch):
    payload = b"aaa blob 5\nhello\nbbb missing\nccc blob 0\n\n"
    proc = _FakeProc(payload)
    monkeypatch.setattr(guard.subprocess, "Popen", lambda *a, **k: proc)
    got = list(guard.read_blobs(["aaa", "bbb", "ccc"]))
    assert got == [("aaa", b"hello"), ("bbb", None), ("ccc", b"")]
    assert proc.waited and proc.stdin.closed


def test_read_blobs_empty_spawns_nothing(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("no process expected")

    monkeypatch.setattr(guard.subprocess, "Popen", boom)
    assert list(guard.read_blobs([])) == []


def test_read_blobs_survives_broken_stdin(monkeypatch):
    class Broken:
        def write(self, data):
            raise BrokenPipeError

        def close(self):
            raise OSError

    proc = _FakeProc(b"aaa missing\n", stdin=Broken())
    monkeypatch.setattr(guard.subprocess, "Popen", lambda *a, **k: proc)
    assert list(guard.read_blobs(["aaa"])) == [("aaa", None)]
