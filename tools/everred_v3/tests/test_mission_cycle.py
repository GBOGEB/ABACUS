"""Mission-cycle readiness and unlock-yield negative controls (no native claims)."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mission_cycle import STAGES, project
from unlock_yield import evaluate

BEFORE, AFTER = "a" * 40, "b" * 40
ROOT, REPO = "BD-ER-FORMAT-20261014", "GBOGEB/ABACUS"


def graph(confirmed=True):
    return {
        "schema": "abacus.everred.blocking-dag.v1",
        "source_sha": AFTER,
        "nodes": [
            {
                "id": ROOT,
                "type": "root",
                "causal_status": "CONFIRMED" if confirmed else "CANDIDATE",
            },
            {"id": "ci-A", "type": "gate", "mandatory": True},
            {"id": "ci-B", "type": "gate", "mandatory": True},
        ],
        "edges": [
            {"from": ROOT, "to": "ci-A", "causally_supported": True},
            {"from": ROOT, "to": "ci-B", "causally_supported": True},
        ],
    }


def proof(gate, source, run, result):
    return {
        "repository": REPO,
        "source_sha": source,
        "gate_id": gate,
        "config_digest": "c" * 64,
        "run_id": run,
        "job_id": run + 1,
        "result": result,
        "evidence_url": f"https://github.com/{REPO}/actions/runs/{run}/job/{run + 1}",
    }


def measurement():
    return {
        "schema": "abacus.everred.unlock-yield.v1",
        "repository": REPO,
        "root_id": ROOT,
        "before_sha": BEFORE,
        "after_sha": AFTER,
        "config_digest": "c" * 64,
        "blocking_dag": graph(),
        "complete_denominator": True,
        "security_waiver": False,
        "authority_transfer": False,
        "dependencies": [
            {
                "gate_id": "ci-A",
                "before": proof("ci-A", BEFORE, 10, "BLOCKED"),
                "after": proof("ci-A", AFTER, 20, "READY"),
            },
            {
                "gate_id": "ci-B",
                "before": proof("ci-B", BEFORE, 30, "BLOCKED"),
                "after": proof("ci-B", AFTER, 40, "BLOCKED"),
            },
        ],
    }


def queue():
    return {
        "families": [
            {
                "id": ROOT,
                "severity": "P1",
                "justification": "Native job reds",
                "remediation": "Verify exact head",
                "dov": "Native terminal proof",
            },
            {
                "id": "BD-SECURITY-001",
                "severity": "P0",
                "justification": "Mandatory security gate",
                "remediation": "Obtain authorized reviewer",
                "dov": "Native security proof",
            },
        ]
    }


class MissionCycleTests(unittest.TestCase):
    def test_unknown_without_native_proof(self):
        result = evaluate(measurement())
        self.assertIsNone(result["yield_pct"])
        self.assertEqual(result["denominator"], 2)
        self.assertEqual(result["admission"], "HOLD")

    def test_synthetic_trusted_verifier_yield_50_percent(self):
        # Synthetic callback is testing the mathematical contract, NOT a live run.
        result = evaluate(measurement(), native_verifier=lambda receipt: True)
        self.assertEqual(result["yield_pct"], 50.0)
        self.assertEqual(result["numerator"], 1)
        self.assertEqual(result["denominator"], 2)
        self.assertFalse(result["causal_effect"])

    def test_unknown_without_native_verifier(self):
        self.assertIsNone(evaluate()["yield_pct"])
        self.assertEqual(evaluate()["status"], "UNKNOWN")

    def test_incomplete_denominator_fails_closed(self):
        val = measurement()
        val["dependencies"].pop()
        with self.assertRaisesRegex(ValueError, "eligible dependencies"):
            evaluate(val)

    def test_wrong_source_and_config_fail(self):
        val = measurement()
        val["dependencies"][0]["after"]["source_sha"] = BEFORE
        with self.assertRaisesRegex(ValueError, "source"):
            evaluate(val)
        val = measurement()
        val["dependencies"][0]["after"]["config_digest"] = "d" * 64
        with self.assertRaisesRegex(ValueError, "unbound"):
            evaluate(val)

    def test_untrusted_verifier_fails_closed(self):
        self.assertIsNone(
            evaluate(measurement(), native_verifier=lambda receipt: False)["yield_pct"]
        )

    def test_unconfirmed_root_and_authority_fail(self):
        val = measurement()
        val["blocking_dag"] = graph(False)
        with self.assertRaises(ValueError):
            evaluate(val)
        val = measurement()
        val["security_waiver"] = True
        with self.assertRaisesRegex(ValueError, "authority"):
            evaluate(val)

    def test_p0_priority_overrides_analytics(self):
        decision = project(queue())
        self.assertEqual(len(STAGES), 6)
        self.assertEqual(decision["stages"][0], "Mission")
        self.assertEqual(
            decision["cards"]["BD-SECURITY-001"]["priority_policy"],
            "P0_HARD_GATE_FIRST",
        )
        self.assertIsNone(decision["cards"][ROOT]["bt_rank"])
        self.assertIsNone(decision["cards"][ROOT]["unlock_yield_pct"])
        self.assertFalse(decision["merge_authorized"])

    def test_confirmed_reverse_pressure_not_admission(self):
        decision = project(queue(), blocking_dag=graph())
        self.assertEqual(decision["cards"][ROOT]["reverse_pressure"], 2)
        self.assertEqual(decision["cards"][ROOT]["admission"], "HOLD")


if __name__ == "__main__":
    unittest.main()
