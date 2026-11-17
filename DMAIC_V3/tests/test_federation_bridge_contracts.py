"""Fail-closed bridge contract smoke without external services."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from dmaic.tuple_metadata import validate_tuple_metadata  # noqa: E402


class FederationBridgeContracts(unittest.TestCase):
    def test_required_six_bridge_targets_exist(self):
        paths = (
            "src/dmaic/tuple_metadata.py",
            "scripts/validate_tuple_metadata.py",
            "DMAIC_V3/tests/test_tuple_metadata_validation.py",
            "DMAIC_V3/core/temporal_metadata_engine.py",
            "DMAIC_V3/phases/phase6_knowledge.py",
            "DMAIC_V3/core/handover_bridge.py",
            "local_mcp/agent_orchestrator_v3.0.py",
            "scripts/generate_docs_html.py",
            "scripts/export_docs.py",
            ".github/workflows/smoke-test.yml",
            ".github/workflows/export-docs.yml",
            "docs/progress_tracker.html",
        )
        missing = [path for path in paths if not (ROOT / path).is_file()]
        self.assertEqual(missing, [], f"Declared bridge targets absent: {missing}")

    def test_valid_tuple_accepts_lineage(self):
        rows = [
            {
                "tuple_id": "a",
                "source": "source.json",
                "validation_log": "ok",
                "downstream_consumer": "handover.json",
                "status": "validated",
                "feeds_into": ["b"],
            },
            {
                "tuple_id": "b",
                "source": "handover.json",
                "validation_log": "ok",
                "downstream_consumer": "tracker.html",
                "status": "in_progress",
                "consumed_from": ["a"],
            },
        ]
        self.assertEqual(validate_tuple_metadata(rows), [])

    def test_unknown_tuple_reference_rejected(self):
        rows = [
            {
                "tuple_id": "a",
                "source": "source.json",
                "validation_log": "ok",
                "downstream_consumer": "handover.json",
                "status": "validated",
                "feeds_into": ["missing"],
            }
        ]
        self.assertTrue(
            any("unknown tuple_id" in error for error in validate_tuple_metadata(rows))
        )

    def test_invalid_status_and_missing_required_keys_rejected(self):
        errors = validate_tuple_metadata([{"tuple_id": "a", "status": "green"}])
        self.assertTrue(any("invalid status" in error for error in errors))
        self.assertTrue(any("missing required field" in error for error in errors))

    def test_pr_bridge_workflow_is_event_triggered_and_fails_closed(self):
        workflow = (
            ROOT / ".github/workflows/federation-bridge-contract.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("pull_request:", workflow)
        self.assertIn("test_federation_bridge_contracts.py", workflow)
        self.assertIn("test_tuple_metadata_validation.py", workflow)
        self.assertNotIn("continue-on-error: true", workflow)


if __name__ == "__main__":
    unittest.main()
