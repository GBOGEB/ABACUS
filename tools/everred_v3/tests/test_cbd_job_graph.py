"""Pure deterministic CBD job/step graph tests: fixture data are NOT native proof."""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_cbd_260 import PATHS, cbd

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cbd_job_graph", ROOT / "scripts" / "cbd_job_graph.py"
)
graph = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(graph)


class CBDJobGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = cbd.read_n0(PATHS)
        cls.native = {}
        for rid, entry in cls.snapshot["unique_failed_runs"].items():
            cls.native[str(rid)] = {
                "status": "JOB_METADATA_BOUND",
                "head_sha": entry["sha"],
                "workflow": entry["workflow"],
                "trust": graph.TRUST,
                "run_attempt": 1,
                "failed_jobs": [{
                    "job_id": rid + 100000000000,
                    "job_name": "Full Red Proof Summary" if rid % 2
                    else "Independent subject step",
                    "first_failed_step": {"number": 5, "name": "Seeded error"},
                    "step_causality": "UNATTRIBUTED",
                }],
                "failed_job_count": 1,
                "full_log_read": False,
                "first_red_causal_root": None,
            }

    def mutated(self, change):
        native = copy.deepcopy(self.native)
        change(native)
        return graph.analyze(self.snapshot, native)

    def test_real_N0_denominator_bounded_fixture(self):
        dag = graph.analyze(self.snapshot, self.native)
        m = dag["metrics"]
        self.assertEqual(253, m["runs_requested"])
        self.assertEqual(253, m["runs_bound"])
        self.assertEqual(253, m["failed_job_observations"])
        self.assertEqual(253, m["jobs_with_failed_step"])
        self.assertEqual(0, m["runs_withheld"] if "runs_withheld" in m else 0)
        self.assertIsNone(m["confirmed_roots_open"])
        self.assertIsNone(m["diff_coverage"])
        self.assertEqual("HOLD", dag["safety"]["merge_admission"])

    def test_shared_run_id_not_double_counted(self):
        dag = graph.analyze(self.snapshot, self.native)
        edges = dag["graph"]["edges"]
        self.assertEqual(
            260,
            len([e for e in edges if e["type"] == "PR_HAS_RUN_ASSOCIATION"]),
        )
        self.assertEqual(253, dag["metrics"]["failed_job_observations"])

    def test_source_sha_mismatch_rejected(self):
        rid = next(iter(self.native))
        with self.assertRaisesRegex(ValueError, "source or trust"):
            self.mutated(lambda d: d[rid].update(head_sha="f" * 40))

    def test_forged_root_confirmation_rejected(self):
        rid = next(iter(self.native))
        with self.assertRaisesRegex(ValueError, "root confirmation"):
            self.mutated(lambda d: d[rid].update(first_red_causal_root="ROOT-1"))

    def test_forged_full_log_claim_rejected(self):
        rid = next(iter(self.native))
        with self.assertRaisesRegex(ValueError, "full-log claim"):
            self.mutated(lambda d: d[rid].update(full_log_read=True))

    def test_duplicate_job_id_rejected(self):
        rid = next(iter(self.native))
        def change(d):
            d[rid]["failed_jobs"].append(copy.deepcopy(d[rid]["failed_jobs"][0]))
            d[rid]["failed_job_count"] = 2
        with self.assertRaisesRegex(ValueError, "duplicate job"):
            self.mutated(change)

    def test_missing_and_foreign_run_ids_rejected(self):
        rid = next(iter(self.native))
        for mutation in (
            lambda d: d.pop(rid),
            lambda d: d.update({"999999999": d[rid]}),
        ):
            with self.subTest(change=str(mutation)):
                with self.assertRaisesRegex(ValueError, "run ID census"):
                    self.mutated(mutation)

    def test_failed_step_missing_is_unknown_not_pass(self):
        rid = next(iter(self.native))
        dag = self.mutated(
            lambda d: d[rid]["failed_jobs"][0].update(first_failed_step=None)
        )
        self.assertEqual(1, dag["metrics"]["jobs_without_failed_step"])
        self.assertTrue(any(
            x["first_failed_step"] == "UNKNOWN_FIRST_FAILED_STEP"
            for x in dag["candidate_signatures"]
        ))
        self.assertIsNone(dag["metrics"]["confirmed_roots_closed"])

    def test_withheld_readback_preserves_unknown(self):
        rid = next(iter(self.native))
        def withhold(d):
            d[rid].update(
                status="READBACK_WITHHELD",
                failed_jobs=None,
                failed_job_count=None,
                first_red_causal_root=None,
                full_log_read=False,
            )
        dag = self.mutated(withhold)
        self.assertEqual(1, dag["metrics"]["runs_withheld"])
        self.assertEqual(252, dag["metrics"]["runs_bound"])
        self.assertEqual(252, dag["metrics"]["failed_job_observations"])
        self.assertIsNone(dag["metrics"]["confirmed_roots_open"])

    def test_withheld_cannot_carry_failure_count(self):
        rid = next(iter(self.native))
        with self.assertRaisesRegex(ValueError, "withheld readback"):
            self.mutated(lambda d: d[rid].update(
                status="READBACK_WITHHELD", failed_jobs=None
            ))

    def test_measured_zero_and_unknown_have_separate_types(self):
        dag = graph.analyze(self.snapshot, self.native)
        self.assertEqual(0, dag["metrics"]["runs_withheld"])
        self.assertEqual(0, dag["metrics"]["jobs_without_failed_step"])
        self.assertEqual(0, dag["metrics"]["bound_runs_without_failure_job"])
        self.assertIsNone(dag["metrics"]["confirmed_roots_closed"])
        self.assertIsNone(dag["metrics"]["main_coverage"])

    def test_malformed_attempt_and_step_rejected(self):
        rid = next(iter(self.native))
        with self.assertRaisesRegex(ValueError, "run attempt"):
            self.mutated(lambda d: d[rid].update(run_attempt=0))
        with self.assertRaisesRegex(ValueError, "first failed step"):
            self.mutated(lambda d: d[rid]["failed_jobs"][0].update(
                first_failed_step={"number": False, "name": ""}
            ))

    def test_causal_step_forgery_rejected(self):
        rid = next(iter(self.native))
        with self.assertRaisesRegex(ValueError, "forged causal"):
            self.mutated(lambda d: d[rid]["failed_jobs"][0].update(
                step_causality="ROOT_CONFIRMED"
            ))

    def test_top_frequency_is_descriptive_only(self):
        dag = graph.analyze(self.snapshot, self.native)
        ranks = dag["candidate_signatures"]
        self.assertEqual(1, ranks[0]["priority_rank_by_observation_frequency"])
        self.assertEqual(253, sum(x["manifestations"] for x in ranks))
        self.assertTrue(any(
            x["treatment"] == "DOWNSTREAM_SUSPECT" for x in ranks
        ))
        self.assertTrue(all(x["causal_root_id"] is None for x in ranks))

    def test_render_html_escapes_untrusted_labels(self):
        dag = graph.analyze(self.snapshot, self.native)
        dag["candidate_signatures"][0]["job"] = "<script>bad()</script>"
        rendered = graph.render_html(dag)
        self.assertNotIn("<script>bad()</script>", rendered)
        self.assertIn("&lt;script&gt;bad()", rendered)

    def test_deterministic_receipts_and_sha256(self):
        dag = graph.analyze(self.snapshot, self.native)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            graph.write(dag, path)
            first = {p.name: p.read_bytes() for p in path.iterdir()}
            graph.write(dag, path)
            second = {p.name: p.read_bytes() for p in path.iterdir()}
            self.assertEqual(first, second)
            digests = json.loads(first["sha256.json"])
            for name, hexdigest in digests.items():
                self.assertEqual(hashlib.sha256(first[name]).hexdigest(), hexdigest)

    def test_cli_against_local_synthetic_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            native = directory / "synthetic.json"
            native.write_text(json.dumps(self.native), encoding="utf-8")
            destination = directory / "output"
            with mock.patch.dict("sys.modules", {"cbd_260": cbd}):
                with mock.patch("builtins.print"):
                    graph.main([
                        *(str(p) for p in PATHS),
                        "--native-jobs", str(native),
                        "--output-dir", str(destination),
                    ])
            dag = json.loads((destination / "candidate_dag.json").read_text())
            self.assertEqual(253, dag["metrics"]["runs_bound"])
            self.assertTrue((destination / "candidate_index.html").exists())


if __name__ == "__main__":
    unittest.main()
