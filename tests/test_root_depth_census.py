"""Synthetic read-only Git-tree depth and census guards."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "triage" / "root_depth_census.py"
SPEC = importlib.util.spec_from_file_location("root_depth_census", SCRIPT)
census = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(census)
SHA = "a" * 40


def entry(path, blob=None, size=1, *, kind="blob", mode=None):
    return {
        "path": path,
        "mode": mode or ("040000" if kind == "tree" else
                         "160000" if kind == "commit" else "100644"),
        "type": kind,
        "sha": blob or ("b" * 40),
        **({"size": size} if kind == "blob" else {}),
    }


def tree(entries, truncated=False):
    return {"sha": SHA, "truncated": truncated, "tree": entries}


class RootDepthCensusTest(unittest.TestCase):
    def test_tranche_reconciles_all_blobs(self):
        doc = tree([
            entry("tests/test_a.py", blob="1" * 40),
            entry("pkg/a.py", blob="2" * 40),
            entry(".github/workflows/ci.yml", blob="3" * 40),
            entry("config/settings.yaml", blob="4" * 40),
            entry("assets/report.pdf", blob="5" * 40),
            entry("README.md", blob="6" * 40),
        ])
        receipt = census.report(doc, SHA)
        self.assertEqual(receipt["totals"]["tracked_files"], 6)
        self.assertEqual(sum(receipt["tranches"].values()), 6)
        self.assertEqual(receipt["totals"]["tracked_yaml_files"], 2)
        self.assertEqual(receipt["totals"]["tracked_binary_extension_files"], 1)
        self.assertFalse(receipt["authority_transfer"])

    def test_gitlinks_not_conflated_with_nested_manifests(self):
        doc = tree([
            entry("subrepo", kind="commit"),
            entry("app/pyproject.toml", blob="2" * 40),
            entry("app/.gitignore", blob="3" * 40),
        ])
        receipt = census.report(doc, SHA)
        self.assertEqual(receipt["totals"]["gitlinks"], 1)
        self.assertEqual(receipt["gitlink_paths"], ["subrepo"])
        self.assertEqual(
            receipt["nested_project_manifest_candidates"],
            ["app/pyproject.toml"],
        )

    def test_duplicate_blob_bytes(self):
        doc = tree([
            entry("a.svg", "1" * 40, 1000),
            entry("copy/a.svg", "1" * 40, 1000),
            entry("other/b.svg", "1" * 40, 1000),
        ])
        value = census.report(doc, SHA)
        self.assertEqual(value["totals"]["duplicate_git_blob_groups"], 1)
        self.assertEqual(value["totals"]["repeated_tracked_blob_bytes"], 2000)

    def test_truncated_tree_must_fail(self):
        with self.assertRaisesRegex(ValueError, "truncated"):
            census.report(tree([entry("a.py")], truncated=True), SHA)

    def test_duplicate_path_must_fail(self):
        with self.assertRaisesRegex(ValueError, "duplicate path"):
            census.report(tree([entry("a.py"), entry("a.py")]), SHA)

    def test_empty_tree_must_fail(self):
        with self.assertRaisesRegex(ValueError, "tree objects absent"):
            census.report(tree([]), SHA)

    def test_unsafe_path_fails(self):
        for name in ("../secret.py", "/root.py", "a/../b.py", "a\\b.py"):
            with self.subTest(path=name):
                with self.assertRaisesRegex(ValueError, "unsafe"):
                    census.report(tree([entry(name)]), SHA)

    def test_unknown_local_binaries_are_not_zero(self):
        value = census.report(tree([entry("src/a.py")]), SHA)
        self.assertIsNone(value["untracked_ignored_local_artifacts"])
        self.assertIsNone(value["archive_members_scanned"])
        self.assertIsNone(value["coverage_instrumented_path_count"])

    def test_missing_blob_size_rejected(self):
        item = entry("src/a.py")
        del item["size"]
        with self.assertRaisesRegex(ValueError, "byte size"):
            census.report(tree([item]), SHA)

    def test_noncanonical_blob_mode_rejected(self):
        with self.assertRaisesRegex(ValueError, "blob mode"):
            census.report(tree([entry("a.py", mode="040000")]), SHA)


if __name__ == "__main__":
    unittest.main()
