"""The #1847 review-gate closure record must stay true to the gate code.

Every cited test has to exist in the gate test module, so a renamed or
deleted test cannot leave the record claiming evidence that is gone.
"""

import ast
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RECORD = (
    ROOT
    / "governance"
    / "qps_triage"
    / "review_gate"
    / "PR1847_RESIDUE_CLOSURE_v1.yaml"
)
DISPOSITIONS = {
    "FIXED_IN_CURRENT_HEAD",
    "ACCEPTED_NO_CHANGE_WITH_RATIONALE",
    "DEFERRED_WITH_TRACKED_ISSUE",
    "NON_ACTIONABLE_INFORMATION",
    "SUPERSEDED_BY_NEWER_EXACT_HEAD",
}
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def defined_test_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }


class ReviewGateClosureRecordTests(unittest.TestCase):
    def setUp(self):
        self.record = yaml.safe_load(RECORD.read_text(encoding="utf-8"))

    def test_record_identity(self):
        self.assertEqual(self.record["schema"], "qps-triage-review-gate-closure/1.0.0")
        self.assertEqual(self.record["source_pr"], 1847)
        self.assertIs(self.record["authority_transfer"], False)
        self.assertRegex(self.record["source_pr_merge_commit"], FULL_SHA)
        for key in ("gate_module", "gate_tests", "gate_workflow", "policy"):
            self.assertTrue((ROOT / self.record[key]).is_file(), key)

    def test_items_cite_existing_tests_and_full_shas(self):
        available = defined_test_names(ROOT / self.record["gate_tests"])
        ids = [item["id"] for item in self.record["items"]]
        self.assertEqual(len(ids), len(set(ids)))
        for item in self.record["items"]:
            with self.subTest(item=item["id"]):
                self.assertIn(item["disposition"], DISPOSITIONS)
                self.assertTrue(item["finding"].strip())
                self.assertTrue(item["evidence_tests"])
                missing = set(item["evidence_tests"]) - available
                self.assertFalse(missing, f"missing tests: {sorted(missing)}")
                for sha in item.get("evidence_commits", []):
                    self.assertRegex(sha, FULL_SHA)
                if item["disposition"] == "FIXED_IN_CURRENT_HEAD":
                    self.assertTrue(
                        item.get("evidence_commits") or item.get("evidence_this_pr")
                    )
                if item["disposition"] == "ACCEPTED_NO_CHANGE_WITH_RATIONALE":
                    self.assertTrue(item.get("rationale", "").strip())

    def test_closed_issues_are_not_also_standing_controls(self):
        closed = {
            number for item in self.record["items"] for number in item.get("closes", [])
        }
        standing = {
            entry["issue"] for entry in self.record["standing_controls_not_closed"]
        }
        self.assertEqual({1861, 1862, 1878, 1879}, closed)
        self.assertFalse(closed & standing)


if __name__ == "__main__":
    unittest.main()
