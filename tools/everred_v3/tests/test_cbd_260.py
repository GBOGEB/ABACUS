"""CBD-260 actual source cohort and adversarial native-job tests (no network)."""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cbd_260", ROOT / "scripts" / "cbd_260.py")
cbd = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cbd)
PATHS = sorted((ROOT / "data" / "cbd_260").glob("N0_*.json"))


class FakeNativeReader:
    def __init__(self, *, forged=False, no_step=False):
        self.forged = forged
        self.no_step = no_step
        self.calls = []

    def run_and_jobs(self, repo, run_id, sha):
        self.calls.append((repo, run_id, sha))
        # These are synthetic tests of code behavior, not native CI observations.
        name = self.entries[run_id]["workflow"]
        return ({
            "id": run_id,
            "head_sha": "f" * 40 if self.forged else sha,
            "name": name,
            "conclusion": "failure",
            "status": "completed",
            "run_attempt": 1,
            "created_at": "2026-10-16T12:00:00Z",
            "repository": {"full_name": repo},
        }, [{
            "id": run_id + 100000000000, "run_id": run_id,
            "name": "fixture failed job", "status": "completed",
            "conclusion": "failure",
            "steps": [] if self.no_step else [
                {"number": 5, "name": "secondary failure",
                 "conclusion": "failure"},
                {"number": 3, "name": "Install canonical dependencies",
                 "conclusion": "failure"},
                {"number": 1, "name": "Setup", "conclusion": "success"},
            ],
        }])


class CBD260Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = cbd.read_n0(PATHS)
        cls.reader = FakeNativeReader()
        cls.reader.entries = cls.snapshot["unique_failed_runs"]

    def mutate(self, mutator):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "N0_01.json"
            doc = json.loads(PATHS[0].read_text(encoding="utf-8"))
            mutator(doc)
            path.write_text(json.dumps(doc), encoding="utf-8")
            return cbd.read_n0([path, *PATHS[1:]])

    def test_real_pr_and_failure_denominators(self):
        p = cbd.project(self.snapshot)
        m = p["metrics"]
        self.assertEqual(75, m["prs_observed"])
        self.assertEqual(74, m["prs_open_in_captured_readbacks"])
        self.assertEqual(1, m["prs_closed_in_captured_readbacks"])
        self.assertFalse(m["snapshot_atomic"])
        self.assertEqual(260, m["failed_workflow_associations"])
        self.assertEqual(253, m["distinct_failed_run_ids"])
        self.assertEqual(7, m["duplicated_pr_failure_associations"])
        self.assertEqual(19, m["workflow_name_buckets"])
        self.assertEqual(1581, m["passed_associations"])
        self.assertEqual(36, m["cancelled_associations"])
        self.assertEqual(4, m["nonterminal_associations"])
        self.assertEqual(1881, m["workflow_associations"])

    def test_pareto_is_descriptive_not_causality(self):
        p = cbd.project(self.snapshot)
        plan = cbd.wave_plan(p)
        self.assertEqual(170, plan["top4_workflow_associations"])
        self.assertEqual(214, plan["top6_workflow_associations"])
        self.assertEqual("HOLD", p["safety"]["merge_admission"])
        self.assertIsNone(p["metrics"]["independently_confirmed_causal_roots"])
        self.assertIsNone(plan["independent_root_closure_forecast"])

    def test_distinct_heads_and_repeated_run_aliases_not_double_roots(self):
        m = cbd.project(self.snapshot)["metrics"]
        self.assertEqual(74, m["distinct_pr_source_shas"])
        self.assertEqual(
            253, len(set(self.snapshot["unique_failed_runs"])))
        self.assertEqual(7, len(self.snapshot["duplicate_associations"]))

    def test_negative_forged_root_id_rejected(self):
        with self.assertRaisesRegex(ValueError, "forged"):
            self.mutate(lambda d: d["rows"][0]["failed_runs"][0].update(
                root_id="BD-FAKE-CLOSED"))

    def test_negative_unsupported_admission_rejected(self):
        with self.assertRaisesRegex(ValueError, "authority"):
            self.mutate(lambda d: d.update(merge_admission="PASS"))

    def test_negative_security_waiver_rejected(self):
        with self.assertRaisesRegex(ValueError, "authority"):
            self.mutate(lambda d: d.update(security_waiver=True))

    def test_negative_missing_failure_occurrence_rejected(self):
        with self.assertRaisesRegex(ValueError, "denominator"):
            self.mutate(lambda d: d["rows"][0]["failed_runs"].pop())

    def test_negative_forged_state_rejected(self):
        with self.assertRaisesRegex(ValueError, "head/state"):
            self.mutate(lambda d: d["rows"][0].update(state="merged_and_admitted"))

    def test_negative_invalid_head_rejected(self):
        with self.assertRaisesRegex(ValueError, "head"):
            self.mutate(lambda d: d["rows"][0].update(head_sha="short"))

    def test_negative_duplicate_pr_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate PR"):
            self.mutate(lambda d: d["rows"].append(copy.deepcopy(d["rows"][0])))

    def test_negative_empty_scope_rejected(self):
        with self.assertRaisesRegex(ValueError, "scope"):
            self.mutate(lambda d: d.update(scope="ALL_ATTEMPTS_VERIFIED"))

    def test_negative_fake_first_red_rejected(self):
        with self.assertRaisesRegex(ValueError, "forged"):
            self.mutate(lambda d: d["rows"][0]["failed_runs"][0].update(
                first_red_job=123))

    def test_negative_cross_repo_identity_rejected(self):
        with self.assertRaisesRegex(ValueError, "repo/main"):
            self.mutate(lambda d: d.update(repository="GBOGEB/CODEX"))

    def test_253_native_job_scouts_return_bound_metadata(self):
        r = FakeNativeReader()
        r.entries = self.snapshot["unique_failed_runs"]
        native = cbd.enrich_native(self.snapshot, r, workers=4)
        p = cbd.project(self.snapshot, native)
        self.assertEqual(253, len(native))
        self.assertEqual(253, p["metrics"]["job_readbacks_accepted"])
        self.assertEqual(0, p["metrics"]["job_readbacks_withheld"])
        self.assertIsNone(p["metrics"]["open_causal_roots"])
        self.assertIsNone(p["metrics"]["authenticated_crew_launches"])
        one = next(iter(native.values()))
        self.assertEqual(
            "Install canonical dependencies",
            one["failed_jobs"][0]["first_failed_step"]["name"])
        self.assertFalse(one["full_log_read"])

    def test_forged_native_source_is_withheld(self):
        r = FakeNativeReader(forged=True)
        r.entries = self.snapshot["unique_failed_runs"]
        native = cbd.enrich_native(self.snapshot, r, workers=2)
        self.assertEqual(
            253, cbd.project(self.snapshot, native)["metrics"][
                "job_readbacks_withheld"])

    def test_job_without_step_remains_unknown(self):
        r = FakeNativeReader(no_step=True)
        r.entries = self.snapshot["unique_failed_runs"]
        native = cbd.enrich_native(self.snapshot, r, workers=1)
        one = next(iter(native.values()))
        self.assertIsNone(
            one["failed_jobs"][0]["first_failed_step"])
        self.assertIsNone(one["first_red_causal_root"])

    def test_worker_limit_is_bounded(self):
        with self.assertRaisesRegex(ValueError, "worker"):
            cbd.enrich_native(self.snapshot, self.reader, workers=9)
        with self.assertRaisesRegex(ValueError, "run bound"):
            cbd.enrich_native(self.snapshot, self.reader, limit=100)

    def test_deterministic_outputs_and_digest_parity(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = cbd.build(PATHS, tmp)
            a = {p.name: p.read_bytes() for p in Path(tmp).iterdir()}
            second = cbd.build(PATHS, tmp)
            b = {p.name: p.read_bytes() for p in Path(tmp).iterdir()}
            self.assertEqual(first, second)
            self.assertEqual(a, b)
            digests = json.loads((Path(tmp) / "sha256.json").read_text())
            for name, digest in digests.items():
                self.assertEqual(digest, hashlib.sha256(a[name]).hexdigest())
            self.assertNotIn("native_jobs.json", digests)

    def test_html_escapes_untrusted_workflow_labels(self):
        p = cbd.project(self.snapshot)
        p["families"][0]["workflow"] = "<script>alert(1)</script>"
        content = cbd.render_html(p)
        self.assertNotIn("<script>alert(1)</script>", content)
        self.assertIn("&lt;script&gt;", content)
        self.assertIn("Read-only" .lower(), content.lower())

    def test_wave_scheduler_separates_source_and_readonly(self):
        plan = cbd.wave_plan(cbd.project(self.snapshot))
        self.assertEqual(4, plan["bounded_parallelism"][
            "read_only_scout_workers_max"])
        self.assertEqual(0, plan["bounded_parallelism"][
            "source_mutation_workers_max_before_owner_lease"])
        self.assertEqual("HOLD", plan["p"][-1]["state"])
        self.assertIsNone(plan["bounded_parallelism"][
            "authenticated_crew_launches"])


if __name__ == "__main__":
    unittest.main()
