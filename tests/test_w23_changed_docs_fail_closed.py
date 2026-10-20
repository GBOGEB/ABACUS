"""Regression guards for W23 changed-document diff provenance."""
from __future__ import annotations

import subprocess
import unittest
from unittest import mock

from scripts import validate_changed_docs as docs


def _result(args, returncode=0, stdout=""):
    return subprocess.CompletedProcess(args, returncode, stdout)


class ChangedDocumentDiffFailClosedTests(unittest.TestCase):
    def test_all_diff_ranges_fail_closed(self):
        ranges = [["missing-base..HEAD"], ["another-missing-base..HEAD"]]
        calls = []

        def fail_git_diff(args, *, check=True):
            calls.append(args[-1])
            return _result(args, returncode=128, stdout="fatal: bad revision")

        with mock.patch.object(docs, "_github_diff_ranges", return_value=ranges):
            with mock.patch.object(docs, "_run", side_effect=fail_git_diff):
                with self.assertRaisesRegex(RuntimeError, "Unable to determine changed files"):
                    docs.changed_files()
        self.assertEqual(calls, ["missing-base..HEAD", "another-missing-base..HEAD"])

    def test_successful_empty_diff_is_distinct_from_unresolved_diff(self):
        with mock.patch.object(docs, "_github_diff_ranges", return_value=[["valid-base..HEAD"]]):
            with mock.patch.object(docs, "_run", return_value=_result([], stdout="")):
                self.assertEqual(docs.changed_files(), [])

    def test_main_cannot_publish_green_when_diff_selection_fails(self):
        with mock.patch.object(docs, "changed_files", side_effect=RuntimeError("no source range")):
            with mock.patch.object(docs, "run_optional") as lint:
                with mock.patch.object(docs, "validate_yaml_structure") as structure:
                    with mock.patch.object(docs, "validate_json") as json_validator:
                        self.assertEqual(docs.main(), 1)
                        lint.assert_not_called()
                        structure.assert_not_called()
                        json_validator.assert_not_called()


if __name__ == "__main__":
    unittest.main()
