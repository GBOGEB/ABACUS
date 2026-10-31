"""Source+fixture proof for lossless, fail-closed Pandoc export enumeration."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts/export_docs_manifest.py"
WORKFLOW = ROOT / ".github/workflows/export-docs.yml"
spec = importlib.util.spec_from_file_location("export_docs_manifest", MODULE)
assert spec is not None and spec.loader is not None
manifest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manifest)


class ExportManifestLosslessness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        subprocess.run(
            ["git", "init", "-q", str(self.repo)], check=True, capture_output=True
        )

    def stage(self, *paths):
        for rel in paths:
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# test\n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(self.repo), "add", "--", "docs"],
            check=True,
            capture_output=True,
        )

    @contextmanager
    def synthetic_git_index(self, *paths):
        """Exercise Git's NUL protocol for names unavailable on Windows/macOS.

        Separate tests exercise the real Git index and file validation.
        Path mocks here affect only the synthetic-index boundary, not production.
        """
        raw = ("\0".join(paths) + "\0").encode("utf-8")
        with (
            mock.patch.object(
                manifest.subprocess, "run", return_value=SimpleNamespace(stdout=raw)
            ),
            mock.patch.object(Path, "is_symlink", return_value=False),
            mock.patch.object(Path, "is_file", return_value=True),
        ):
            yield

    def test_empty_repository_fails_instead_of_publishing_empty_archive(self):
        with self.assertRaisesRegex(ValueError, "NO_TRACKED_MARKDOWN_SOURCES"):
            manifest.tracked_markdown(self.repo)

    def test_spaces_and_nested_identical_basenames_remain_distinct(self):
        self.stage("docs/one/a b.md", "docs/two/a b.md")
        self.assertEqual(
            manifest.tracked_markdown(self.repo), ["docs/one/a b.md", "docs/two/a b.md"]
        )

    def test_root_docs_markdown_is_included_not_only_double_star_glob(self):
        self.stage("docs/README.md", "docs/nested/b.md", "docs/nested/ignored.txt")
        self.assertEqual(
            manifest.tracked_markdown(self.repo), ["docs/README.md", "docs/nested/b.md"]
        )

    def test_source_newline_does_not_split_nul_manifest(self):
        with self.synthetic_git_index("docs/line\nname.md", "docs/ordinary.md"):
            out = self.repo / "tmp" / "paths0"
            report = manifest.write_manifest(self.repo, out)
        raw = out.read_bytes()
        self.assertTrue(raw.endswith(b"\0"))
        self.assertEqual(len(raw.split(b"\0")) - 1, 2)
        self.assertIn(b"docs/line\nname.md", raw)
        self.assertEqual(report["expected_artifact_count"], 4)

    def test_casefold_collision_is_rejected_before_export(self):
        with self.synthetic_git_index("docs/a/A.md", "docs/a/a.md"):
            with self.assertRaisesRegex(ValueError, "OUTPUT_PATH_COLLISION"):
                manifest.tracked_markdown(self.repo)

    def test_truncated_nul_protocol_rejected_before_path_processing(self):
        with mock.patch.object(
            manifest.subprocess,
            "run",
            return_value=SimpleNamespace(stdout=b"docs/a.md"),
        ):
            with self.assertRaisesRegex(ValueError, "TRUNCATED_NUL_GIT_MANIFEST"):
                manifest.tracked_markdown(self.repo)

    def test_missing_tracked_source_is_not_silently_dropped(self):
        self.stage("docs/a.md")
        (self.repo / "docs/a.md").unlink()
        with self.assertRaisesRegex(ValueError, "MISSING_OR_SYMLINKED_SOURCE"):
            manifest.tracked_markdown(self.repo)

    def test_symlinked_source_does_not_escape_export_root(self):
        self.stage("docs/a.md")
        (self.repo / "docs/a.md").unlink()
        (self.repo / "docs/a.md").symlink_to("../outside.md")
        with self.assertRaisesRegex(ValueError, "MISSING_OR_SYMLINKED_SOURCE"):
            manifest.tracked_markdown(self.repo)

    def test_non_docs_files_are_never_exported(self):
        self.stage("docs/doc.md", "elsewhere/no.md")
        self.assertEqual(manifest.tracked_markdown(self.repo), ["docs/doc.md"])

    def test_unstaged_file_is_not_treated_as_authoritative(self):
        self.stage("docs/one.md")
        extra = self.repo / "docs" / "untracked.md"
        extra.write_text("unknown", encoding="utf-8")
        self.assertEqual(manifest.tracked_markdown(self.repo), ["docs/one.md"])

    def test_workflow_consumes_nul_manifest_with_fail_closed_pandoc(self):
        src = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python scripts/export_docs_manifest.py", src)
        self.assertIn("while IFS= read -r -d '' f", src)
        self.assertIn('relative="${f#docs/}"', src)
        self.assertIn("out/${stem}.pdf", src)
        self.assertIn("out/${stem}.docx", src)
        self.assertIn('test "$count" -gt 0', src)
        self.assertNotIn("for f in $(git ls-files", src)
        self.assertIn("pandoc/latex:3.1", src)


if __name__ == "__main__":
    unittest.main()
