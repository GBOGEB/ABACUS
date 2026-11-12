"""Public-repository synthetic contract tests; no project-source fixtures."""
import unittest

from qplant.m2_source_guard import (
    FlowAtom, PowerMode, reconcile_user_mass, require_flow_anchor_config,
    pvps_running_motor_screen, reproduce_offer_power,
    validate_bidder_qeq, ts_source_alignment,
)


def flow(port, amount, *, candidate="CASE_ALPHA", config="CONFIG_X",
         mode="MODE_1", boundary="QRB_USER_INTERFACE",
         evidence="CURRENT_BIDDER_EXPECTED"):
    return FlowAtom(candidate, config, mode, boundary, port, amount, evidence, "SYNTHETIC_FIXTURE")


class TestM2PublicContract(unittest.TestCase):
    def test_exact_mass_conservation(self):
        r = reconcile_user_mass(flow("A", "12.00"), flow("B", "9.50"), flow("W", "2.50"))
        self.assertAlmostEqual(r.residual_g_s, 0.0)
        self.assertEqual(r.disposition, "ROUNDING_CONSISTENT_NOT_INDEPENDENTLY_VALIDATED")
        self.assertFalse(r.authority_transfer)

    def test_printed_rounding_budget(self):
        r = reconcile_user_mass(flow("A", "12.00"), flow("B", "9.50"), flow("W", "2.49"))
        self.assertAlmostEqual(r.residual_g_s, 0.01)
        self.assertAlmostEqual(r.display_rounding_budget_g_s, .015)
        self.assertEqual(r.disposition, "ROUNDING_CONSISTENT_NOT_INDEPENDENTLY_VALIDATED")

    def test_missing_input_deferred(self):
        r = reconcile_user_mass(flow("A", "12.00"), flow("B", None), flow("W", "2.50"))
        self.assertEqual(r.disposition, "OPEN_INPUT")
        self.assertIsNone(r.residual_g_s)

    def test_source_alignment_diagnostic(self):
        r = ts_source_alignment(9.9, 10.0, "SYNTHETIC_1", "SYNTHETIC_2")
        self.assertAlmostEqual(r["delta_g_s"], -.1)
        self.assertIn("NOT_INDEPENDENT", r["state"])

    def test_electrical_allowance_in_numerator(self):
        r = reproduce_offer_power(PowerMode("MODE_1", 40, 5, 1, 1, 1, 30, 20, 2.0, 55.65))
        self.assertAlmostEqual(r["direct_kW"], 48)
        self.assertAlmostEqual(r["CWS_kW"], 5)
        self.assertAlmostEqual(r["contract_reproduction_kW"], 55.65)
        self.assertEqual(r["Qeq_unchanged_kW"], 2.0)

    # Five adversarial controls: invalid inference must raise.
    def test_adversary_1_unrelated_stream(self):
        with self.assertRaisesRegex(ValueError, "STREAM_ID_MISMATCH"):
            reconcile_user_mass(flow("A", "12.00"), flow("HP_TOTAL", "9.5"), flow("W", "2.5"))

    def test_adversary_2_installed_not_active(self):
        with self.assertRaisesRegex(ValueError, "RUNNING_COUNT_NOT_SOURCE_BOUND"):
            pvps_running_motor_screen(3, None, 4)

    def test_adversary_3_denominator_change(self):
        with self.assertRaisesRegex(ValueError, "BIDDER_DENOMINATOR_SOURCE_SEMANTICS_MISMATCH"):
            validate_bidder_qeq(2.0, 2.1)

    def test_adversary_4_generation_mismatch(self):
        with self.assertRaisesRegex(ValueError, "CONFIGURATION_GENERATION_MISMATCH"):
            require_flow_anchor_config("CONFIG_X", "CONFIG_Y")

    def test_adversary_5_no_guarantee_promotion(self):
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_GUARANTEE_PROMOTION"):
            reconcile_user_mass(flow("A", "12.00", evidence="DERIVED_DIAGNOSTIC"),
                                flow("B", "9.5", evidence="BIDDER_NONBINDING"),
                                flow("W", "2.5", evidence="BIDDER_NONBINDING"),
                                require_guarantee=True)
