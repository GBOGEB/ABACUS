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
                # A PR head that is not a synthetic merge has no 2nd parent.
                return _completed(args, returncode=int(args[3].startswith("HEAD^2")))
            if args[:3] == ["git", "merge-base", "a" * 40]:
                return _completed(args, stdout="f" * 40 + "\n")
            if args[:2] == ["git", "fetch"]:
                return _completed(args)
            raise AssertionError(args)

        with (
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch.object(docs, "_run", side_effect=fake_run),
        ):
            self.assertEqual(
                docs._github_diff_ranges()[:3],
                [[f"{'f' * 40}..HEAD"]],
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
                return _completed(args, returncode=1 if seen["cat_file"] == 1 else 0)
            if args[:2] == ["git", "fetch"]:
                seen["fetch"].append(args[-1])
                return _completed(args)
            if args[:3] == ["git", "cat-file", "-e"]:
                return _completed(args, returncode=1)
            raise AssertionError(args)

        with (
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch.object(docs, "_run", side_effect=fake_run),
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

            with (
                mock.patch.object(docs, "REPO_ROOT", root),
                mock.patch.object(
                    docs,
                    "_github_diff_ranges",
                    return_value=[["bad...HEAD"], ["good..HEAD"]],
                ),
                mock.patch.object(docs, "_run", side_effect=fake_run),
            ):
                self.assertEqual(docs.changed_files(), [Path("docs/ok.md")])

    def test_yaml_duplicate_nested_key_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / "workflow.yml"
            path.write_text(
                "on: pull_request\njobs:\n  build:\n    runs-on: ubuntu\n"
                "    runs-on: windows\n",
                encoding="utf-8",
            )
            with mock.patch.object(docs, "REPO_ROOT", root):
                self.assertEqual(docs.validate_yaml_structure(["workflow.yml"]), 1)

    def test_yaml_anchors_and_on_literal_are_valid(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / "workflow.yml"
            path.write_text(
                "on: pull_request\npaths: &paths\n  - '**/*.yml'\n"
                "pull_request:\n  paths: *paths\n",
                encoding="utf-8",
            )
            with mock.patch.object(docs, "REPO_ROOT", root):
                self.assertEqual(docs.validate_yaml_structure(["workflow.yml"]), 0)

    def test_yaml_invalid_syntax_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "broken.yaml").write_text("config: [unclosed\n", encoding="utf-8")
            with mock.patch.object(docs, "REPO_ROOT", root):
                self.assertEqual(docs.validate_yaml_structure(["broken.yaml"]), 1)

    def test_workflow_multidocument_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            workflow = root / ".github" / "workflows" / "x.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text("name: one\n---\nname: two\n", encoding="utf-8")
            with mock.patch.object(docs, "REPO_ROOT", root):
                self.assertEqual(
                    docs.validate_yaml_structure([".github/workflows/x.yml"]), 1
                )

    def test_yaml_security_semgrep_config_contract(self) -> None:
        config_file = (
            Path(__file__).resolve().parents[1]
            / ".github"
            / "security"
            / "semgrep-yaml-workflows.yml"
        )
        import yaml

        parsed = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        ids = {rule["id"] for rule in parsed["rules"]}
        self.assertEqual(
            ids,
            {
                "abacus.github-actions-broad-write-all",
                "abacus.github-actions-untrusted-pr-target",
                "abacus.github-actions-unpinned-action-tag",
            },
        )
        for rule in parsed["rules"]:
            self.assertEqual(rule["languages"], ["yaml"])
            self.assertIn("pattern-regex", rule)
            self.assertEqual(len(rule["paths"]["include"]), 2)
        import re

        rules = {rule["id"]: rule["pattern-regex"] for rule in parsed["rules"]}
        samples = {
            "abacus.github-actions-broad-write-all": "permissions: write-all",
            "abacus.github-actions-untrusted-pr-target": "  pull_request_target:",
            "abacus.github-actions-unpinned-action-tag": (
                "  - uses: actions/checkout@v7"
            ),
        }
        for rule_id, sample in samples.items():
            with self.subTest(rule=rule_id):
                self.assertIsNotNone(re.search(rules[rule_id], sample))
                self.assertIsNone(re.search(rules[rule_id], "permissions: read"))


if __name__ == "__main__":
    unittest.main()
