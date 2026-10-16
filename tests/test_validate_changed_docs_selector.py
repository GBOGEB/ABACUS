"""Adversarial regressions for changed-doc source selection."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import validate_changed_docs as mod


class ChangedDocsSelectionTests(unittest.TestCase):
    def _fixture(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        subprocess.run(["git", "init", "-q", str(root)], check=True)

        def git(*args):
            return subprocess.run(
                ["git", "-C", str(root), *args],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    "GIT_AUTHOR_NAME": "test",
                    "GIT_AUTHOR_EMAIL": "test@example.invalid",
                    "GIT_COMMITTER_NAME": "test",
                    "GIT_COMMITTER_EMAIL": "test@example.invalid",
                },
            ).stdout.strip()

        (root / "baseline.yml").write_text("base: true\n")
        git("add", ".")
        git("commit", "-qm", "common")
        ancestor = git("rev-parse", "HEAD")
        (root / "base-only.yml").write_text("unrelated: true\n")
        git("add", ".")
        git("commit", "-qm", "base advanced")
        base = git("rev-parse", "HEAD")
        git("checkout", "-qb", "feature", ancestor)
        (root / "feature.yml").write_text("changed: true\n")
        git("add", ".")
        git("commit", "-qm", "feature")
        head = git("rev-parse", "HEAD")
        return tmp, root, git, ancestor, base, head

    def _select(self, root, base, head):
        with patch.object(mod, "REPO_ROOT", root), patch.dict(
            os.environ,
            {
                "GITHUB_EVENT_NAME": "pull_request",
                "GITHUB_BASE_SHA": base,
                "GITHUB_SHA": head,
                "GITHUB_BASE_REF": "main",
            },
            clear=False,
        ):
            # Production resolves git merge-base against HEAD, so the fixture
            # must execute in the same checked-out revision as the event.
            return [str(p) for p in mod.changed_files()]

    def test_normal_pr_head(self):
        tmp, root, git, ancestor, base, head = self._fixture()
        try:
            git("checkout", "-q", head)
            self.assertEqual(self._select(root, base, head), ["feature.yml"])
        finally:
            tmp.cleanup()

    def test_synthetic_merge_excludes_unrelated_base_changes(self):
        tmp, root, git, ancestor, base, head = self._fixture()
        try:
            git("checkout", "-qB", "integration", base)
            git("merge", "-q", "--no-ff", "feature", "-m", "synthetic")
            merged = git("rev-parse", "HEAD")
            # Synthetic merge contains the base-only change; selection must not.
            self.assertEqual(self._select(root, base, merged), ["feature.yml"])
        finally:
            tmp.cleanup()

    def test_missing_merge_base_fails_closed(self):
        tmp, root, git, ancestor, base, head = self._fixture()
        try:
            git("checkout", "-q", "--orphan", "unrelated")
            git("rm", "-q", "-rf", ".")
            (root / "orphan.yml").write_text("isolated: true\n")
            git("add", ".")
            git("commit", "-qm", "unrelated root")
            with self.assertRaisesRegex(RuntimeError, "Cannot resolve PR merge base"):
                self._select(root, base, git("rev-parse", "HEAD"))
        finally:
            tmp.cleanup()

    def test_shallow_missing_base_fails_closed(self):
        tmp, root, git, ancestor, base, head = self._fixture()
        try:
            git("checkout", "-q", head)
            with self.assertRaisesRegex(RuntimeError, "Cannot resolve PR base SHA"):
                self._select(root, "a" * 40, head)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
