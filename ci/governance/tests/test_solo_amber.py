"""Negative controls for solo-maintainer exception evidence."""

import importlib.util
import pathlib
import unittest
from copy import deepcopy

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "solo_amber.py"
SPEC = importlib.util.spec_from_file_location("solo_amber", SOURCE)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
SHA = "a" * 40
URL = "https://github.com/GBOGEB/ABACUS/"


def fixture():
    return {
        "schema": M.SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "pr_number": 1990,
        "head_sha": SHA,
        "decision": {
            "intent": "REQUEST_AMBER",
            "actor": "GBOGEB",
            "acknowledge_solo_not_independent": True,
            "reason": "Explicitly accept bounded formatting debt for one wave.",
            "recorded_at_utc": "2026-10-15T09:00:00Z",
        },
        "checks": [
            {
                "name": "format-check",
                "state": "failure",
                "category": "formatting",
                "head_sha": SHA,
                "run_url": URL + "actions/runs/100",
                "exception": {
                    "issue_url": URL + "issues/100",
                    "root_id": "BD-FORMAT-001",
                    "owner": "GBO",
                    "reason": "Known formatter differences in old test files.",
                    "impact": "Does not alter production runtime behavior.",
                    "mitigation": "Native formatting repair PR with exact-head CI.",
                    "risk": "low",
                    "expires_at_utc": "2026-10-17T09:00:00Z",
                },
            }
        ],
        "pulses": [],
    }


class SoloAmberTests(unittest.TestCase):
    def test_single_low_risk_carry_requests_amber_not_merge(self):
        r = M.assess(fixture())
        self.assertEqual(r["decision"], "AMBER_REQUESTED")
        self.assertFalse(r["merge_admitted"])
        self.assertEqual(r["carried_count"], 1)

    def test_critical_security_hard_block(self):
        x = fixture()
        x["checks"][0]["category"] = "security"
        self.assertEqual(M.assess(x)["decision"], "RED_HOLD")

    def test_confidentiality_hard_block(self):
        x = fixture()
        x["checks"][0]["category"] = "confidentiality"
        self.assertEqual(M.assess(x)["decision"], "RED_HOLD")

    def test_governance_hard_block(self):
        x = fixture()
        x["checks"][0]["category"] = "governance"
        self.assertEqual(M.assess(x)["decision"], "RED_HOLD")

    def test_missing_exception_holds(self):
        x = fixture()
        del x["checks"][0]["exception"]
        self.assertEqual(M.assess(x)["decision"], "UNKNOWN_HOLD")

    def test_unclassified_check_holds(self):
        x = fixture()
        x["checks"][0]["category"] = "misc"
        self.assertEqual(M.assess(x)["decision"], "UNKNOWN_HOLD")

    def test_expired_exception_holds(self):
        x = fixture()
        x["checks"][0]["exception"]["expires_at_utc"] = "2026-10-15T09:00:00Z"
        self.assertEqual(M.assess(x)["decision"], "UNKNOWN_HOLD")

    def test_different_sha_fails(self):
        x = fixture()
        x["checks"][0]["head_sha"] = "b" * 40
        with self.assertRaises(ValueError):
            M.assess(x)

    def test_missing_root_fails(self):
        x = fixture()
        x["checks"][0]["exception"]["root_id"] = ""
        with self.assertRaises(ValueError):
            M.assess(x)

    def test_missing_rationale_fails(self):
        x = fixture()
        x["decision"]["reason"] = "OK"
        with self.assertRaises(ValueError):
            M.assess(x)

    def test_solo_acknowledgement_required(self):
        x = fixture()
        x["decision"]["acknowledge_solo_not_independent"] = False
        with self.assertRaises(ValueError):
            M.assess(x)

    def test_high_risk_rejected(self):
        x = fixture()
        x["checks"][0]["exception"]["risk"] = "high"
        with self.assertRaises(ValueError):
            M.assess(x)

    def test_duplicate_check_rejected(self):
        x = fixture()
        x["checks"].append(deepcopy(x["checks"][0]))
        with self.assertRaises(ValueError):
            M.assess(x)

    def test_green_still_not_merge_admission(self):
        x = fixture()
        x["checks"][0]["state"] = "success"
        x["checks"][0]["exception"] = None
        r = M.assess(x)
        self.assertEqual(r["decision"], "GREEN_EVIDENCE_ONLY")
        self.assertFalse(r["merge_admitted"])

    def test_comparable_pulse_and_unknown_are_distinct(self):
        x = fixture()
        x["pulses"] = [
            {
                "wave_id": "W1",
                "head_sha": SHA,
                "coverage": {"status": "UNKNOWN"},
                "tests": {"passed": 8, "failed": 0, "skipped": 0},
                "root_counts": {"open": 2},
                "first_reds": [],
            },
            {
                "wave_id": "W2",
                "head_sha": SHA,
                "coverage": {"status": "COMPARABLE", "delta_pp": 0.25},
                "tests": {"passed": 10, "failed": 0, "skipped": 0},
                "root_counts": {"open": 1},
                "first_reds": [],
            },
        ]
        r = M.assess(x)
        self.assertIsNone(r["pulses"][0]["coverage_delta_pp"])
        self.assertEqual(r["pulses"][1]["coverage_delta_pp"], 0.25)

    def test_duplicate_pulse_rejected(self):
        x = fixture()
        p = {
            "wave_id": "W1",
            "head_sha": SHA,
            "tests": {"passed": 1, "failed": 0, "skipped": 0},
        }
        x["pulses"] = [p, deepcopy(p)]
        with self.assertRaises(ValueError):
            M.assess(x)


if __name__ == "__main__":
    unittest.main()
