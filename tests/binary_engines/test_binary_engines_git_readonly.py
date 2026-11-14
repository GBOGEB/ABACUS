"""git_readonly reads HEAD, tracked paths and bundle heads from disk, the way git reports them."""

from __future__ import annotations

import hashlib
import os
import shutil
import struct
import unittest

from tests.binary_engines import _env

SHA_A, SHA_B = "a" * 40, "b" * 40


def _index(version: int, paths: list[str]) -> bytes:
    """A minimal index file (gitformat-index) with one entry per path."""
    body, previous = b"", b""
    for path in paths:
        name = path.encode()
        entry = (
            b"\0" * 40
            + bytes.fromhex("e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")
            + struct.pack(">H", min(len(name), 0xFFF))
        )
        if version == 4:
            common = len(os.path.commonprefix([previous, name]))
            strip = len(previous) - common
            assert strip < 0x80  # one-byte varint is enough for these names
            entry += bytes([strip]) + name[common:] + b"\0"
        else:
            entry += name + b"\0"
            entry += b"\0" * ((8 - len(entry) % 8) % 8)
        body += entry
        previous = name
    data = b"DIRC" + struct.pack(">II", version, len(paths)) + body
    return data + hashlib.sha1(data, usedforsecurity=False).digest()


class Synthetic(unittest.TestCase):
    def setUp(self):
        self.gr = _env.engine("git_readonly")
        self.work = _env.HOME / "git_readonly_test"
        shutil.rmtree(self.work, ignore_errors=True)
        self.work.mkdir(parents=True)
        if self.gr.find_repo(self.work.parent) is not None:
            self.skipTest("the test folder lies inside a git work tree on this machine")

    def _repo(self, index: bytes | None = None) -> tuple:
        top = self.work / "repo"
        git = top / ".git"
        (git / "refs" / "heads").mkdir(parents=True)
        (top / "sub").mkdir()
        (git / "HEAD").write_text("ref: refs/heads/main\n", "utf-8")
        (git / "packed-refs").write_text(
            f"# pack-refs with: peeled\n{SHA_A} refs/heads/main\n^{SHA_B}\n", "utf-8"
        )
        if index is not None:
            (git / "index").write_bytes(index)
        return top, git

    def test_index_versions(self):
        paths = [
            "GG_A_DOCX/E1/note.docx",
            "GG_A_DOCX/E1/note2.docx",
            "readme.md",
            "sub/deep/file.txt",
        ]
        for version in (2, 3, 4):
            with self.subTest(version=version):
                shutil.rmtree(self.work / "repo", ignore_errors=True)
                top, _ = self._repo(_index(version, paths))
                self.assertEqual(self.gr.tracked_paths(top), set(paths))
                self.assertEqual(self.gr.tracked_paths(top / "sub"), {"deep/file.txt"})

    def test_unreadable_index_fails_closed(self):
        top, git = self._repo(b"DIRC" + struct.pack(">II", 9, 0) + b"\0" * 20)
        self.assertIsNone(self.gr.tracked_paths(top))
        (git / "index").write_bytes(
            _index(2, ["a"])[:-20] + b"link" + struct.pack(">I", 0) + b"\0" * 20
        )
        self.assertIsNone(
            self.gr.tracked_paths(top), "a split index keeps entries elsewhere"
        )

    def test_head_from_packed_and_loose_refs(self):
        top, git = self._repo()
        self.assertEqual(self.gr.head(top / "sub"), SHA_A)
        (git / "refs" / "heads" / "main").write_text(SHA_B + "\n", "utf-8")
        self.assertEqual(self.gr.head(top), SHA_B)
        (git / "HEAD").write_text(SHA_A + "\n", "utf-8")
        self.assertEqual(self.gr.head(top), SHA_A, "detached HEAD")

    def test_linked_worktree(self):
        top, git = self._repo(_index(2, ["shared.txt"]))
        wt_git = git / "worktrees" / "wt"
        wt_git.mkdir(parents=True)
        (wt_git / "HEAD").write_text("ref: refs/heads/main\n", "utf-8")
        (wt_git / "commondir").write_text("../..\n", "utf-8")
        (wt_git / "index").write_bytes(_index(2, ["only_in_wt.txt"]))
        wt = self.work / "wt"
        wt.mkdir()
        (wt / ".git").write_text(f"gitdir: {wt_git}\n", "utf-8")
        self.assertEqual(self.gr.head(wt), SHA_A)
        self.assertEqual(self.gr.tracked_paths(wt), {"only_in_wt.txt"})

    def test_outside_a_repository(self):
        self.assertEqual(self.gr.tracked_paths(self.work), set())
        self.assertEqual(self.gr.head(self.work), "")

    def test_bundle_heads(self):
        bundle = self.work / "x.bundle"
        header = f"# v3 git bundle\n@object-format=sha1\n-{SHA_B} old base\n{SHA_A} refs/heads/main\n{SHA_B} refs/tags/v1\n\n"
        bundle.write_bytes(header.encode() + b"PACK\x00\x00\x00\x02\xff\n\n")
        self.assertEqual(
            self.gr.bundle_heads(bundle),
            [f"{SHA_A} refs/heads/main", f"{SHA_B} refs/tags/v1"],
        )
        not_bundle = self.work / "y.bundle"
        not_bundle.write_bytes(b"PK\x03\x04 not a bundle")
        self.assertEqual(self.gr.bundle_heads(not_bundle), [])


class ThisCheckout(unittest.TestCase):
    def test_reads_the_repository_under_test(self):
        gr = _env.engine("git_readonly")
        if gr.find_repo(_env.REPO) is None:
            self.skipTest("not a git checkout")
        head = gr.head(_env.REPO)
        self.assertRegex(head, r"^([0-9a-f]{40}|[0-9a-f]{64})$")
        if os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("GITHUB_SHA"):
            self.assertEqual(head, os.environ["GITHUB_SHA"])
        tracked = gr.tracked_paths(_env.REPO)
        self.assertIn("pytest.ini", tracked)
        self.assertIn("DMAIC_V3/tools/dow_engine.py", tracked)
        self.assertIn("tools/dow_engine.py", gr.tracked_paths(_env.REPO / "DMAIC_V3"))


if __name__ == "__main__":
    unittest.main()
