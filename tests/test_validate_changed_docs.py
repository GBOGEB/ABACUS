from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import validate_changed_docs as docs


def _completed(args: list[str], returncode: int = 0, stdout: str = ""):
    return subprocess.CompletedProcess(args=args, returncode=returncode, stdout=stdout)


class ValidateChangedDocsTests(unittest.TestCase):
    def test_pr_diff_ranges_prefer_base_sha(self) -> None:
        env = {
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_BASE_REF": "main",
            "GITHUB_BASE_SHA": "a" * 40,
            "GITHUB_EVENT_BEFORE": "b" * 40,
            "GITHUB_SHA": "c" * 40,
        }

        def fake_run(args, *, check=True):
            if args[:3] == ["git", "cat-file", "-e"]:
                return _completed(args)
            if args[:2] == ["git", "fetch"]:
                return _completed(args)
            raise AssertionError(args)

        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            docs, "_run", side_effect=fake_run
        ):
            self.assertEqual(
                docs._github_diff_ranges()[:3],
                [
                    [f"{'a' * 40}..{'c' * 40}"],
                    [f"{'b' * 40}..{'c' * 40}"],
                    ["origin/main..HEAD"],
                ],
            )

    def test_missing_base_sha_is_fetched_before_use(self) -> None:
        missing_sha = "d" * 40
        env = {"GITHUB_BASE_SHA": missing_sha, "GITHUB_SHA": "e" * 40}
        seen = {"cat_file": 0, "fetch": []}

        def fake_run(args, *, check=True):
            if args[:3] == ["git", "cat-file", "-e"] and args[3].startswith(
                missing_sha
            ):
                seen["cat_file"] += 1
                return _completed(
                    args, returncode=1 if seen["cat_file"] == 1 else 0
                )
            if args[:2] == ["git", "fetch"]:
                seen["fetch"].append(args[-1])
                return _completed(args)
            if args[:3] == ["git", "cat-file", "-e"]:
                return _completed(args, returncode=1)
            raise AssertionError(args)

        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            docs, "_run", side_effect=fake_run
        ):
            self.assertEqual(
                docs._github_diff_ranges()[0],
                [f"{missing_sha}..{'e' * 40}"],
            )
            self.assertEqual(seen["fetch"], [missing_sha])

    def test_changed_files_tries_next_range_after_diff_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            doc_path = root / "docs" / "ok.md"
            doc_path.parent.mkdir()
            doc_path.write_text("# OK\n", encoding="utf-8")

            def fake_run(args, *, check=True):
                if args[-1] == "bad...HEAD":
                    return _completed(
                        args, returncode=128, stdout="fatal: no merge base\n"
                    )
                return _completed(args, stdout="docs/ok.md\n")

            with mock.patch.object(docs, "REPO_ROOT", root), mock.patch.object(
                docs,
                "_github_diff_ranges",
                return_value=[["bad...HEAD"], ["good..HEAD"]],
            ), mock.patch.object(docs, "_run", side_effect=fake_run):
                self.assertEqual(docs.changed_files(), [Path("docs/ok.md")])


if __name__ == "__main__":
    unittest.main()
