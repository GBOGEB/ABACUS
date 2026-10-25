"""Changed-docs lint: pure renames are skipped, edited legacy Markdown is ratcheted."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_changed_docs.py"
SPEC = importlib.util.spec_from_file_location("validate_changed_docs_ratchet", SCRIPT)
docs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(docs)


def done(stdout="", code=0):
    return SimpleNamespace(returncode=code, stdout=stdout)


class RuleCountTest(unittest.TestCase):
    def test_counts_both_cli_output_formats(self):
        out = (
            "markdownlint-cli2 v0.18.1\n"
            "a.md:3:81 MD013/line-length Line length\n"
            "a.md:9 MD013/line-length Line length\n"
            "docs/b.md:1:1 error MD041/first-line-heading First line\n"
            "Summary: 3 error(s)\n"
        )
        counts = docs.markdown_rule_counts(out)
        self.assertEqual(counts["a.md"]["MD013"], 2)
        self.assertEqual(counts["docs/b.md"]["MD041"], 1)
        self.assertEqual(set(counts), {"a.md", "docs/b.md"})


class RenameOriginsTest(unittest.TestCase):
    def test_pure_renames_skip_and_edits_keep_their_base(self):
        status = (
            "R100\tReport.md\tdocs_versioned/generated_reports/Report.md\n"
            "R097\tINDEX.md\tdocs_versioned/handover/INDEX.md\n"
            "M\tREADME.md\n"
        )
        with (
            mock.patch.object(
                docs, "_github_diff_ranges", return_value=[["base1..HEAD"]]
            ),
            mock.patch.object(docs, "_run", return_value=done(status)),
        ):
            unchanged, origins = docs.rename_origins()
        self.assertEqual(unchanged, {"docs_versioned/generated_reports/Report.md"})
        self.assertEqual(
            origins,
            {
                "docs_versioned/handover/INDEX.md": ("base1", "INDEX.md"),
                "README.md": ("base1", "README.md"),
            },
        )

    def test_unresolved_ranges_validate_everything_in_full(self):
        with (
            mock.patch.object(
                docs, "_github_diff_ranges", return_value=[["a..b"], ["c..d"]]
            ),
            mock.patch.object(docs, "_run", return_value=done("", 128)),
        ):
            self.assertEqual(docs.rename_origins(), (set(), {}))


class RatchetTest(unittest.TestCase):
    def run_ratchet(self, head_out, base_out):
        def fake_run(args, check=True):
            # Base copies are linted by absolute path inside the scratch folder.
            is_base = any("changed-docs-base-" in a for a in args)
            prefix = (args[1].rsplit("/", 1)[0] + "/") if is_base else ""
            out = base_out if is_base else head_out
            return done("".join(prefix + line + "\n" for line in out.splitlines()))

        with (
            mock.patch.object(docs, "_git_blob", return_value=(0, "# Old\n".encode())),
            mock.patch.object(docs, "_run", side_effect=fake_run),
        ):
            return docs.ratchet_markdown(
                ["legacy.md"], {"legacy.md": ("base1", "legacy.md")}
            )

    def test_existing_debt_passes(self):
        lines = (
            "legacy.md:1:81 MD013/line-length x\nlegacy.md:2:81 MD013/line-length x\n"
        )
        self.assertEqual(self.run_ratchet(lines, lines), 0)

    def test_fewer_findings_pass(self):
        self.assertEqual(
            self.run_ratchet("", "legacy.md:1:81 MD013/line-length x\n"), 0
        )

    def test_new_findings_fail(self):
        head = "legacy.md:1:81 MD013/line-length x\nlegacy.md:4 MD034/no-bare-urls x\n"
        base = "legacy.md:1:81 MD013/line-length x\n"
        self.assertEqual(self.run_ratchet(head, base), 1)

    def test_unreadable_base_is_linted_in_full(self):
        with (
            mock.patch.object(docs, "run_optional", return_value=1) as full,
            mock.patch.object(docs, "_git_blob", return_value=(128, b"")),
        ):
            result = docs.ratchet_markdown(
                ["legacy.md"], {"legacy.md": ("base1", "legacy.md")}
            )
        self.assertEqual(result, 1)
        full.assert_called_once_with(
            "Markdown (base unreadable)", ["markdownlint-cli2"], ["legacy.md"]
        )

    def test_nothing_to_ratchet(self):
        self.assertEqual(docs.ratchet_markdown([], {}), 0)

    def test_git_blob_reads_the_base_revision(self):
        with mock.patch.object(docs, "_run", return_value=done("# Ä\n")) as run:
            self.assertEqual(docs._git_blob("base1", "a.md"), (0, "# Ä\n".encode()))
        run.assert_called_once_with(["git", "show", "base1:a.md"], check=False)


class MainTest(unittest.TestCase):
    def test_renames_skip_new_files_lint_in_full_edits_ratchet(self):
        paths = [Path("moved.md"), Path("new.md"), Path("legacy.md")]
        origins = {"legacy.md": ("base1", "legacy.md")}
        with (
            mock.patch.object(docs, "changed_files", return_value=paths),
            mock.patch.object(
                docs, "rename_origins", return_value=({"moved.md"}, origins)
            ),
            mock.patch.object(docs, "run_optional", return_value=0) as full,
            mock.patch.object(docs, "ratchet_markdown", return_value=1) as ratchet,
        ):
            self.assertEqual(docs.main(), 1)
        full.assert_any_call("Markdown", ["markdownlint-cli2"], ["new.md"])
        ratchet.assert_called_once_with(["legacy.md"], origins)


if __name__ == "__main__":
    unittest.main()
