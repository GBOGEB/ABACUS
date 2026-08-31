from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from scripts import validate_ssot_style as style


class ValidateSsotStyleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = style.load_manifest(style.DEFAULT_MANIFEST)

    def test_manifest_is_valid(self) -> None:
        self.assertEqual(style.validate_manifest(self.manifest), [])

    def test_missing_required_html_gate_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["artifact_contract"]["html"].remove("playwright_navigation")

        errors = style.validate_manifest(manifest)

        self.assertTrue(any("missing required HTML QA gate" in error for error in errors))

    def test_federation_wave_requires_all_three_repos(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["federation_wave"]["repos"] = [
            repo for repo in manifest["federation_wave"]["repos"] if repo != "GBOGEB/cryoplant-project"
        ]

        errors = style.validate_manifest(manifest)

        self.assertTrue(any("missing federation repo" in error for error in errors))

    def test_federation_wave_rejects_wrong_id(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["federation_wave"]["id"] = "SSOT-STYLE-W03"

        errors = style.validate_manifest(manifest)

        self.assertIn("federation_wave id must be SSOT-STYLE-W04", errors)

    def test_federation_wave_rejects_missing_artifact_lane(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["federation_wave"]["artifact_lanes"] = [
            lane for lane in manifest["federation_wave"]["artifact_lanes"] if lane != "keb"
        ]

        errors = style.validate_manifest(manifest)

        self.assertIn("missing federation artifact lane(s): keb", errors)

    def test_federation_wave_rejects_missing_priority_method(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["federation_wave"]["methods"] = [
            method for method in manifest["federation_wave"]["methods"] if method != "BT_PRIORITY"
        ]

        errors = style.validate_manifest(manifest)

        self.assertIn("missing federation method(s): BT_PRIORITY", errors)

    def test_federation_wave_rejects_non_list_contract_fields(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["federation_wave"]["repos"] = "GBOGEB/ABACUS"
        manifest["federation_wave"]["artifact_lanes"] = {"html": True}
        manifest["federation_wave"]["methods"] = "DMAIC"

        errors = style.validate_manifest(manifest)

        self.assertIn("federation_wave.repos must be a list of strings", errors)
        self.assertIn("federation_wave.artifact_lanes must be a list of strings", errors)
        self.assertIn("federation_wave.methods must be a list of strings", errors)

    def test_federation_wave_blocks_credit_without_child_disposition(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["federation_wave"]["no_credit_without_child_disposition"] = False

        errors = style.validate_manifest(manifest)

        self.assertIn("federation wave must block credit without child disposition", errors)

    def test_handoff_check_policy_requires_repair_pr_links(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["federation_wave"]["handoff_check_policy"]["linked_repair_prs"]["GBOGEB/CODEX"] = 274

        errors = style.validate_manifest(manifest)

        self.assertIn("linked repair PR(s) missing for GBOGEB/CODEX: 298, 300", errors)

    def test_handoff_check_policy_blocks_known_failure_states(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        policy = manifest["federation_wave"]["handoff_check_policy"]
        policy["blocking_conclusions"].remove("timed_out")
        policy["manual_review_conclusions"] = []
        policy["pending_statuses"].remove("in_progress")

        errors = style.validate_manifest(manifest)

        self.assertIn("missing blocking conclusion(s): timed_out", errors)
        self.assertIn("missing manual-review conclusion(s): cancelled", errors)
        self.assertIn("missing pending status(es): in_progress", errors)

    def test_handoff_check_policy_requires_bidirectional_feedback(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["federation_wave"]["handoff_check_policy"]["repository_feedback"] = {
            "from_codex": "",
            "to_codex": "",
        }

        errors = style.validate_manifest(manifest)

        self.assertIn("repository_feedback.from_codex must be a non-empty string", errors)
        self.assertIn("repository_feedback.to_codex must be a non-empty string", errors)

    def test_awake_probe_score_counts_existing_paths(self) -> None:
        manifest = {
            "awake_probes": [
                {"id": "live", "kind": "html", "path": "live.html", "weight": 3},
                {"id": "missing", "kind": "graph", "path": "missing.yaml", "weight": 1},
            ]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "live.html").write_text("<html></html>", encoding="utf-8")

            report = style.score_awake_probes(manifest, root=root)

        self.assertEqual(report["awake_score"], 75.0)
        self.assertEqual(report["by_kind"]["html"], {"awake": 1, "total": 1})
        self.assertEqual(report["by_kind"]["graph"], {"awake": 0, "total": 1})

    def test_penetration_score_uses_content_signals(self) -> None:
        manifest = {
            "awake_probes": [
                {"id": "graph", "kind": "graph", "path": "graph.yaml", "weight": 1},
                {"id": "qa", "kind": "playwright", "path": "qa.py", "weight": 1},
            ]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "graph.yaml").write_text(
                "nodes:\n  - id: a\ndepends_on:\n  - b\nobjectives:\n  - test\n",
                encoding="utf-8",
            )
            (root / "qa.py").write_text(
                "from playwright.sync_api import sync_playwright\n"
                "page.on('console', print)\n"
                "page.evaluate('document.body.scrollWidth')\n",
                encoding="utf-8",
            )

            report = style.score_penetration(manifest, root=root)

        self.assertEqual(report["penetration_score"], 100.0)
        self.assertEqual(report["by_kind"]["graph"], {"depth": 4, "max_depth": 4})


    def test_handoff_policy_blocks_startup_failure_and_stale(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        policy = manifest["federation_wave"]["handoff_check_policy"]
        policy["blocking_conclusions"].remove("startup_failure")
        policy["blocking_conclusions"].remove("stale")
        errors = style.validate_manifest(manifest)
        self.assertIn("missing blocking conclusion(s): stale, startup_failure", errors)

    def test_handoff_policy_requires_structured_all_clear_controls(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["federation_wave"]["handoff_check_policy"]["all_clear_requirements"].remove(
            "repaired_sha_retested"
        )
        errors = style.validate_manifest(manifest)
        self.assertIn("missing all-clear requirement(s): repaired_sha_retested", errors)

    def test_handoff_policy_reports_malformed_object(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["federation_wave"]["handoff_check_policy"] = None
        errors = style.validate_manifest(manifest)
        self.assertIn("federation_wave.handoff_check_policy must be an object", errors)

    def test_handoff_policy_allows_additional_repair_links(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["federation_wave"]["handoff_check_policy"]["linked_repair_prs"]["GBOGEB/ABACUS"].append(999)
        self.assertEqual([], style.validate_manifest(manifest))


if __name__ == "__main__":
    unittest.main()
