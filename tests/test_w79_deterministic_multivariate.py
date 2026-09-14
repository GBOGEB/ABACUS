#!/usr/bin/env python3
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import w79_deterministic_multivariate as w79  # noqa: E402


def synthetic_rows() -> list[dict]:
    rows: list[dict] = []
    for index in range(15):
        semantic = {
            "consumer_hits": 5 + 3 * index,
            "consumer_files_with_hits": 1 + index // 2,
            "semantic_entities": 4 + 2 * (index % 5),
            "semantic_references": 2 + 3 * (index % 3),
            "lineage_paths": 3 + 2 * (index % 4),
            "graph_nodes": 5 + 2 * index,
            "graph_edges": 2 + 4 * index,
        }
        work = {
            "scanned_text_files": 100 + 10 * index,
            "scanned_text_bytes": 10000 + 500 * index * index,
            "consumer_candidate_checks": 1000 + 100 * index,
            **semantic,
        }
        rows.append(
            {
                "source_sha": f"{index + 1:040x}",
                "matrix_label": f"s{index + 1:02d}",
                "execution_state": "PASS",
                "semantic_parity_with_w72": True,
                "work_vector": work,
                "semantic_work_vector": semantic,
            }
        )
    return rows


class W79Tests(unittest.TestCase):
    def evaluate(self, rows: list[dict]) -> dict:
        return w79.evaluate(
            rows,
            w78_run_id="34777543492",
            w78_head_sha="9d55b8ba73a05efaa3e519acacacd1dffb3c787c",
            w78_artifact_id="10323323552",
            w78_artifact_digest=(
                "sha256:6e0a868916c1730fdc8eefc1f24ffea06185ca56ef1a8caffdaeb325eed445ae"
            ),
        )

    def test_diagnostic_analysis_is_deterministic_and_non_authoritative(self) -> None:
        first = self.evaluate(synthetic_rows())
        second = self.evaluate(synthetic_rows())
        self.assertEqual(first["status"], "DIAGNOSTIC_PCA_PA_COMPLETE")
        self.assertEqual(first["receipt_sha256"], second["receipt_sha256"])
        self.assertEqual(first["source_panel"]["target_count"], 15)
        self.assertGreaterEqual(
            first["primary_semantic_work_panel"]["parallel_analysis"][
                "retained_component_count"
            ],
            1,
        )
        self.assertFalse(first["global_allocation_authority"])
        self.assertFalse(first["child_engineering_promotion_authority"])
        self.assertFalse(first["engineering_compliance_release_authority"])
        self.assertEqual(
            first["bt_status"], "WITHHELD_NO_OBSERVED_PAIRWISE_OUTCOME_EVIDENCE"
        )
        self.assertEqual(first["qps_credit_delta"], 0)

    def test_duplicate_source_sha_fails_closed(self) -> None:
        rows = synthetic_rows()
        rows[1]["source_sha"] = rows[0]["source_sha"]
        with self.assertRaisesRegex(ValueError, "15 unique"):
            self.evaluate(rows)

    def test_non_pass_input_fails_closed(self) -> None:
        rows = synthetic_rows()
        rows[0]["execution_state"] = "NOT_EXECUTED"
        with self.assertRaisesRegex(ValueError, "non-PASS"):
            self.evaluate(rows)

    def test_semantic_parity_failure_fails_closed(self) -> None:
        rows = synthetic_rows()
        rows[0]["semantic_parity_with_w72"] = False
        with self.assertRaisesRegex(ValueError, "semantic parity"):
            self.evaluate(rows)

    def test_mutation_changes_bound_input_identity(self) -> None:
        rows = synthetic_rows()
        baseline = self.evaluate(rows)
        changed = copy.deepcopy(rows)
        changed[4]["semantic_work_vector"]["consumer_hits"] += 1
        changed[4]["work_vector"]["consumer_hits"] += 1
        mutated = self.evaluate(changed)
        self.assertNotEqual(
            baseline["source_panel"]["input_sha256"],
            mutated["source_panel"]["input_sha256"],
        )
        self.assertNotEqual(baseline["receipt_sha256"], mutated["receipt_sha256"])


if __name__ == "__main__":
    unittest.main()
