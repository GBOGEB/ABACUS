"""Fail-closed disjoint CODE PURPLE resource/DAG stage controls."""
import copy
import hashlib
import json
import unittest
from pathlib import Path

import yaml

from runtime.execution import governed_recovery_wave as wave


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "runtime/execution/federated-execution-scheduler.yaml"
HEAD = "a" * 40


def fixture():
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


class RecoveryWaveTests(unittest.TestCase):
    def test_three_disjoint_technical_proposals_and_eight_lanes(self):
        result = wave.plan(HEAD, fixture())
        wave.verify(result)
        self.assertEqual(result["lane_count"], 8)
        self.assertEqual(result["edge_count"], 6)
        self.assertEqual(result["planned_worker_slots"], 3)
        self.assertEqual(
            set(result["selected_disjoint_proposals"]),
            {"PY39_RESOLVER", "SECURITY_DASHBOARD_403",
             "GOVERNANCE_CLASSIFICATION"},
        )
        self.assertEqual(result["observed_dispatches"], 0)
        self.assertFalse(result["mutation_enabled"])
        self.assertEqual(result["merge_admission"], "HOLD")
        self.assertEqual(result["verified_distinct_roots_closed"], 0)

    def test_owner_and_admission_never_run(self):
        result = wave.plan(HEAD, fixture())
        rows = {entry["id"]: entry for entry in result["lanes"]}
        for key in ("DOW_FORMAT_DEBT", "METRICS_PR_CREDENTIAL",
                    "EFFECTIVE_REPOSITORY_RULES"):
            self.assertEqual(rows[key]["state"], "OWNER_ACTION_REQUIRED")
        self.assertEqual(rows["ADMISSION"]["state"], "ADMISSION_HOLD")
        self.assertEqual(
            rows["EXACT_HEAD_QUALIFICATION"]["state"],
            "AWAIT_AUTHENTICATED_DEPENDENCY_RECEIPTS",
        )

    def test_reject_unknown_head_and_escalated_dispatch(self):
        with self.assertRaisesRegex(ValueError, "INVALID_EXACT_HEAD"):
            wave.plan("moving-branch", fixture())
        source = fixture()
        source["federated_execution_scheduler"]["governed_recovery_wave"][
            "worker_dispatch_authorized"
        ] = True
        with self.assertRaisesRegex(ValueError, "UNAUTHORIZED_SCHEDULER"):
            wave.plan(HEAD, source)

    def test_reject_cycle_and_missing_dependency(self):
        data = fixture()
        lanes = data["federated_execution_scheduler"]["governed_recovery_wave"]["lanes"]
        lanes[0]["needs"] = ["ADMISSION"]
        with self.assertRaisesRegex(ValueError, "DAG_CYCLE"):
            wave.plan(HEAD, data)
        lanes[0]["needs"] = ["NOT_A_LANE"]
        with self.assertRaisesRegex(ValueError, "UNKNOWN_DEPENDENCY"):
            wave.plan(HEAD, data)

    def test_reject_overlapping_technical_source_owner(self):
        data = fixture()
        lanes = data["federated_execution_scheduler"]["governed_recovery_wave"]["lanes"]
        lanes[1]["source_owner"] = "DMAIC_V3"
        with self.assertRaisesRegex(ValueError, "OVERLAPPING_SOURCE_OWNERS"):
            wave.plan(HEAD, data)

    def test_no_forced_positive_capacity_or_owner_authority(self):
        data = fixture()
        budget = data["federated_execution_scheduler"]["governed_recovery_wave"][
            "resources"
        ]
        budget["proposal_worker_slots"] = 100
        with self.assertRaisesRegex(ValueError, "INVALID_WORKER_CAPACITY"):
            wave.plan(HEAD, data)
        budget["proposal_worker_slots"] = 3
        budget["human_approval_slots"] = 1
        with self.assertRaisesRegex(ValueError, "UNVERIFIED_EXTERNAL_AUTHORITY"):
            wave.plan(HEAD, data)

    def test_tampered_or_rehashed_admission_rejected(self):
        original = wave.plan(HEAD, fixture())
        forged = copy.deepcopy(original)
        forged["observed_dispatches"] = 1
        with self.assertRaisesRegex(ValueError, "PROPOSAL_DIGEST_MISMATCH"):
            wave.verify(forged)
        raw = {k: v for k, v in forged.items() if k != "proposal_sha256"}
        forged["proposal_sha256"] = hashlib.sha256(
            (json.dumps(raw, sort_keys=True, indent=2) + "\n").encode("utf-8")
        ).hexdigest()
        with self.assertRaisesRegex(ValueError, "FALSE_DISPATCH_OR_ADMISSION"):
            wave.verify(forged)


if __name__ == "__main__":
    unittest.main()
