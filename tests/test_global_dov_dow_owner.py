"""DOW owner routing cannot substitute fixtures or CI for native proof."""
import json
import unittest
from pathlib import Path

CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "docs" / "ci" / "GLOBAL_DOV_DOW_OWNER_V1.json"
)


class DOWGlobalDoVOwnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_exact_diagnostic_owner(self):
        self.assertEqual("GBOGEB/ABACUS", self.data["owner_repository"])
        self.assertEqual("GBOGEB/cryoplant-project",
                         self.data["engineering_owner"])

    def test_no_native_proof_from_fixture(self):
        gates = self.data["hard_gates"]
        self.assertEqual("SYNTHETIC_ONLY", gates["fixture_status"])
        self.assertEqual("UNKNOWN", gates["native_four_hop"])
        self.assertEqual("UNKNOWN", gates["independent_replay"])

    def test_qps_and_security_not_waived(self):
        gates = self.data["hard_gates"]
        self.assertEqual("DEFER", gates["qps_acceptance"])
        self.assertFalse(gates["security_waived"])
        self.assertFalse(gates["required_checks_relaxed"])
        self.assertFalse(gates["authority_transfer"])
        self.assertEqual(0, gates["root_closure_claims"])

    def test_five_evidence_obligations_remain_open(self):
        data = self.data["owned_evidence"]
        self.assertEqual(5, len(data))
        self.assertTrue(all(
            row["current"] in ("UNVERIFIED", "DEFER") for row in data
        ))

    def test_no_historical_purge(self):
        self.assertTrue(self.data["handover"]["do_not_delete_history"])
        self.assertEqual("READ_ONLY_CENSUS_AND_SCHEDULING",
                         self.data["handover"]["mission_control_role"])


if __name__ == "__main__":
    unittest.main()
