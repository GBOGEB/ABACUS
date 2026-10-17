"""Contract tests mutate a historical fixture in memory; synthetic cases are not live CI."""
import copy
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "bseries", ROOT / "scripts" / "b_series_temporal_metrics.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BSeriesTemporalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(
            (ROOT / "docs/ci/B_SERIES_NATIVE_PULSES_20261017.json").read_text()
        )

    def test_native_sample_rollup(self):
        m = MODULE.build(self.fixture)
        self.assertEqual(m["three_pulse_metrics"]["sampled_run_success"], [3, 3])
        self.assertEqual(m["three_pulse_metrics"]["b1_raw_counts"], [139] * 3)
        self.assertEqual(m["execution_composite"]["index_series"], [100.0] * 3)
        self.assertEqual(m["merge_admission"], "HOLD")
        self.assertIsNone(m["authenticated_crew_launches"])
        self.assertIsNone(m["three_pulse_metrics"]["test_count_growth_rate"])
        self.assertIsNone(m["three_pulse_metrics"]["b1_comparable_velocity"])
        self.assertIsNone(m["forecast"]["point_estimate"])

    def test_weight_normalization(self):
        self.assertAlmostEqual(sum(MODULE.WEIGHTS.values()), 1.0)

    def test_missing_composite_never_reweights(self):
        self.assertIsNone(
            MODULE._composite({"b0": 1, "b1": 1, "dab": None, "fanin": 1})
        )

    def test_missing_denominator_not_zero(self):
        self.assertIsNone(MODULE._fraction(0, None))
        self.assertIsNone(MODULE._fraction(0, 0))

    def test_reject_source_sha_drift(self):
        d = copy.deepcopy(self.fixture)
        d["observations"][1]["source_sha"] = "branch-name"
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(d)

    def test_reject_duplicated_runs(self):
        d = copy.deepcopy(self.fixture)
        d["observations"][1]["run_id"] = d["observations"][0]["run_id"]
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(d)

    def test_reject_invalid_clock_order(self):
        d = copy.deepcopy(self.fixture)
        d["observations"][2]["observation_at"] = "2026-10-17T08:00:00Z"
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(d)

    def test_reject_claimed_crew_dispatch(self):
        d = copy.deepcopy(self.fixture)
        d["observations"][0]["authenticated_crew_launch"] = 1
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(d)

    def test_reject_claimed_root_closure(self):
        d = copy.deepcopy(self.fixture)
        d["observations"][0]["root_closure_count"] = 0
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(d)

    def test_reject_out_of_range_fraction(self):
        d = copy.deepcopy(self.fixture)
        d["observations"][1]["job_success"] = 14
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(d)

    def test_reject_malformed_schema(self):
        d = copy.deepcopy(self.fixture)
        d["schema"] = "anything"
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(d)

    def test_reject_boolean_count(self):
        d = copy.deepcopy(self.fixture)
        d["observations"][0]["b1_unguarded"] = True
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(d)

    def test_allow_qualified_b1_flat_velocity_only(self):
        d = copy.deepcopy(self.fixture)
        for row in d["observations"]:
            row["b1_config_fingerprint"] = "digest-v1"
        out = MODULE.build(d)
        self.assertEqual(out["three_pulse_metrics"]["b1_comparable_velocity"], 0.0)
        self.assertEqual(out["forecast"]["point_estimate"], 139)

    def test_report_contains_provenance(self):
        s = MODULE.render_markdown(MODULE.build(self.fixture))
        self.assertIn("39024853388", s)
        self.assertIn("39029208988", s)
        self.assertIn("not an admission", s.casefold())


    def test_cli_roundtrip_creates_machine_and_markdown_receipts(self):
        import tempfile
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            source = root / "input.json"
            target = root / "out" / "result.json"
            report = root / "out" / "result.md"
            source.write_text(json.dumps(self.fixture), encoding="utf-8")
            args = ["bseries", "--input", str(source), "--json-out",
                    str(target), "--markdown-out", str(report)]
            with mock.patch("sys.argv", args):
                self.assertEqual(MODULE.main(), 0)
            result = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(result["merge_admission"], "HOLD")
            self.assertEqual(len(result["pulses"]), 3)
            self.assertIn("Not an admission", report.read_text(encoding="utf-8"))

    def test_cli_repeat_is_byte_identical(self):
        import tempfile
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            source = root / "in.json"
            target = root / "out.json"
            report = root / "out.md"
            source.write_text(json.dumps(self.fixture), encoding="utf-8")
            argv = ["bseries", "--input", str(source), "--json-out",
                    str(target), "--markdown-out", str(report)]
            with mock.patch("sys.argv", argv):
                MODULE.main()
                json_one = target.read_bytes()
                md_one = report.read_bytes()
                MODULE.main()
                self.assertEqual(target.read_bytes(), json_one)
                self.assertEqual(report.read_bytes(), md_one)

    def test_reject_non_object_document(self):
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build([])

    def test_reject_unknown_workflow_scope(self):
        doc = copy.deepcopy(self.fixture)
        doc["scope"] = "GBOGEB/CODEX/.github/workflows/other.yml"
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(doc)

    def test_reject_authority_transfer(self):
        doc = copy.deepcopy(self.fixture)
        doc["authority_transfer"] = True
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(doc)

    def test_reject_undeclared_sampling_design(self):
        doc = copy.deepcopy(self.fixture)
        doc["sampling"] = "FLEET_WIDE"
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(doc)

    def test_reject_missing_observation_rows(self):
        doc = copy.deepcopy(self.fixture)
        doc["observations"] = []
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(doc)

    def test_reject_non_object_observation(self):
        doc = copy.deepcopy(self.fixture)
        doc["observations"][0] = None
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(doc)

    def test_reject_invalid_run_attempt(self):
        doc = copy.deepcopy(self.fixture)
        doc["observations"][0]["run_attempt"] = 0
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(doc)

    def test_reject_boolean_job_id(self):
        doc = copy.deepcopy(self.fixture)
        doc["observations"][0]["b1_job_id"] = True
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(doc)

    def test_reject_negative_test_count(self):
        doc = copy.deepcopy(self.fixture)
        doc["observations"][0]["b0_tests_failed"] = -1
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(doc)

    def test_reject_proposals_over_total(self):
        doc = copy.deepcopy(self.fixture)
        doc["observations"][0]["dab_proposal_jobs_success"] = 9
        doc["observations"][0]["dab_proposal_jobs_total"] = 8
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(doc)

    def test_reject_non_boolean_fanin(self):
        doc = copy.deepcopy(self.fixture)
        doc["observations"][0]["fanin_success"] = 1
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(doc)

    def test_reject_nonfinite_or_zero_duration(self):
        for bad in (0, float("nan"), float("inf"), -0.1, True):
            with self.subTest(bad=bad):
                doc = copy.deepcopy(self.fixture)
                doc["observations"][0]["b0_test_duration_seconds"] = bad
                with self.assertRaises(MODULE.EvidenceError):
                    MODULE.build(doc)

    def test_reject_b1_scanner_schema_drift(self):
        doc = copy.deepcopy(self.fixture)
        doc["observations"][0]["b1_schema"] = "unknown"
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(doc)

    def test_reject_invalid_observation_clock(self):
        for bad in (None, "bad-clock", "2026-10-17T08:00:00"):
            with self.subTest(bad=bad):
                doc = copy.deepcopy(self.fixture)
                doc["observations"][0]["observation_at"] = bad
                with self.assertRaises(MODULE.EvidenceError):
                    MODULE.build(doc)

    def test_reject_duplicate_timestamp_even_with_distinct_runs(self):
        doc = copy.deepcopy(self.fixture)
        doc["observations"][1]["observation_at"] = doc["observations"][0]["observation_at"]
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.build(doc)


if __name__ == "__main__":
    unittest.main()
