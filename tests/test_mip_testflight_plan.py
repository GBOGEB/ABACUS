"""Adversarial/positive unit proof for deterministic read-only testflight planning."""
import copy
import unittest

from tools.mip_testflight_plan import compile_plan

HEAD = "a" * 40
PREVIOUS = "b" * 40
BASE = "c" * 40
DIGEST = "d" * 64


def fixture():
    return {
        "schema": "abacus.mip.testflight-input.v1",
        "repository": "GBOGEB/ABACUS",
        "source_sha": HEAD,
        "previous_sha": PREVIOUS,
        "base_sha": BASE,
        "changed_paths": ["tools/foo.py", "tests/test_foo.py"],
        "max_parallel": 2,
        "tasks": [
            {"id": "LINT", "kind": "static", "required": True, "priority": "P0", "needs": [], "paths": ["tools/foo.py"]},
            {"id": "A10", "kind": "a10", "required": True, "priority": "P0", "needs": []},
            {"id": "NEG", "kind": "negative", "required": True, "priority": "P1", "needs": ["LINT"], "paths": ["tests/test_foo.py"]},
            {"id": "UNIT", "kind": "unit", "required": True, "priority": "P1", "needs": ["NEG"], "axes": ["linux39", "win312"]},
            {"id": "COVERAGE", "kind": "coverage", "required": True, "priority": "P2", "needs": ["UNIT"]},
            {"id": "REX", "kind": "rex", "required": True, "priority": "P0", "needs": ["COVERAGE"], "mode": "CONTROLLED_MUTATION"},
        ],
    }


def job(task, source, result="success", axis="default", ident=1, checkout=None):
    return {"task_id": task, "axis": axis, "source_sha": source,
            "checkout_sha": checkout or source, "run_id": 100 + ident,
            "run_attempt": 1, "job_id": 10000 + ident,
            "status": "completed", "conclusion": result}


def case_block(sha, cases, digest=DIGEST, complete=True):
    return {"source_sha": sha, "selection_digest": digest,
            "environment_digest": DIGEST, "definition_digest": DIGEST,
            "complete": complete, "cases": cases}


class PlanningProof(unittest.TestCase):
    def test_dag_and_nonmutating_control(self):
        r = compile_plan(fixture())
        self.assertEqual([w["task_ids"] for w in r["waves"]],
                         [["LINT", "A10"], ["NEG"], ["UNIT"], ["COVERAGE"]])
        self.assertEqual(r["dispatch"], "NOT_PERFORMED_READ_ONLY_PLAN")
        self.assertEqual(r["admission"], "HOLD")
        self.assertIsNone(r["accepted_root_closures"])
        self.assertIsNone(r["crew_launch_authenticated"])
        self.assertFalse(r["merge_authorized"])
        self.assertEqual(r["withheld_task_ids"], ["REX"])
        self.assertEqual(r["tasks"][0]["id"], "LINT")
        self.assertEqual(r["tasks"][0]["decision"], "EXACT_HEAD_RETEST_OR_EVIDENCE_REQUIRED")

    def test_deterministic(self):
        self.assertEqual(compile_plan(fixture()), compile_plan(fixture()))

    def test_emits_proposed_estimates_but_not_native_proof(self):
        p = fixture()
        for t in p["tasks"]:
            t["estimate_seconds"] = 7
        r = compile_plan(p)
        self.assertEqual(r["waves"][0]["predicted_wall_seconds"], 7)
        self.assertEqual(r["waves"][0]["timing_class"], "UNVALIDATED_ESTIMATE_NOT_NATIVE_DURATION")
        self.assertIsNone(r["spc_control_limit"])

    def test_explicit_previous_green_now_red(self):
        p = fixture()
        p["previous_jobs"] = [job("LINT", PREVIOUS, ident=1)]
        p["current_jobs"] = [job("LINT", HEAD, "failure", ident=2)]
        r = compile_plan(p)
        t = next(x for x in r["tasks"] if x["id"] == "LINT")
        self.assertEqual(t["transition"], "PREVIOUS_GREEN_NOW_RED_JOB")
        self.assertEqual(t["decision"], "FIRST_RED_TRIAGE")

    def test_previous_red_now_green_is_not_closure(self):
        p = fixture()
        p["previous_jobs"] = [job("LINT", PREVIOUS, "failure", ident=1)]
        p["current_jobs"] = [job("LINT", HEAD, ident=2)]
        r = compile_plan(p)
        t = next(x for x in r["tasks"] if x["id"] == "LINT")
        self.assertEqual(t["transition"], "PREVIOUS_RED_NOW_GREEN_JOB")
        self.assertIsNone(r["accepted_root_closures"])

    def test_prior_green_without_current_retests(self):
        p = fixture()
        p["previous_jobs"] = [job("LINT", PREVIOUS, ident=1)]
        r = compile_plan(p)
        t = next(x for x in r["tasks"] if x["id"] == "LINT")
        self.assertEqual(t["decision"], "EXACT_HEAD_RETEST_OR_EVIDENCE_REQUIRED")

    def test_no_partial_matrix_green(self):
        p = fixture()
        p["current_jobs"] = [job("UNIT", HEAD, axis="linux39")]
        r = compile_plan(p)
        t = next(x for x in r["tasks"] if x["id"] == "UNIT")
        self.assertEqual(t["current"], "MISSING_REQUIRED_MATRIX_AXIS")

    def test_pending_not_failure_or_green(self):
        p = fixture()
        current = job("LINT", HEAD)
        current.update(status="in_progress", conclusion=None)
        p["current_jobs"] = [current]
        r = compile_plan(p)
        t = next(x for x in r["tasks"] if x["id"] == "LINT")
        self.assertEqual(t["current"], "PENDING_NATIVE_JOBS")

    def test_missing_checkout_not_accepted(self):
        p = fixture()
        current = job("LINT", HEAD)
        current["checkout_sha"] = None
        p["current_jobs"] = [current]
        r = compile_plan(p)
        t = next(x for x in r["tasks"] if x["id"] == "LINT")
        self.assertEqual(t["current"], "UNVERIFIED_CHECKOUT_IDENTITY")

    def test_wrong_checkout_not_accepted(self):
        p = fixture()
        p["current_jobs"] = [job("LINT", HEAD, checkout=PREVIOUS)]
        r = compile_plan(p)
        t = next(x for x in r["tasks"] if x["id"] == "LINT")
        self.assertEqual(t["current"], "UNVERIFIED_CHECKOUT_IDENTITY")

    def test_case_regression_and_clearance(self):
        p = fixture()
        p["previous_cases"] = case_block(PREVIOUS, [
            {"id": "suite::green", "outcome": "PASS"},
            {"id": "suite::red", "outcome": "FAIL"}])
        p["current_cases"] = case_block(HEAD, [
            {"id": "suite::green", "outcome": "FAIL"},
            {"id": "suite::red", "outcome": "PASS"}])
        r = compile_plan(p)["test_case_comparison"]
        self.assertTrue(r["comparable"])
        self.assertEqual([x["kind"] for x in r["events"]],
                         ["PREVIOUS_GREEN_NOW_RED", "RED_CLEARED_TEST_ONLY"])

    def test_unsafe_new_test_not_inferred_old_regression(self):
        p = fixture()
        p["previous_cases"] = case_block(PREVIOUS, [{"id": "suite::old", "outcome": "PASS"}])
        p["current_cases"] = case_block(HEAD, [{"id": "suite::new", "outcome": "FAIL"}])
        r = compile_plan(p)["test_case_comparison"]
        self.assertEqual([x["kind"] for x in r["events"]],
                         ["NEW_TEST_RED", "TEST_DISAPPEARED"])

    def test_skip_debt_retained(self):
        p = fixture()
        p["previous_cases"] = case_block(PREVIOUS, [{"id": "s::x", "outcome": "PASS"}])
        p["current_cases"] = case_block(HEAD, [{"id": "s::x", "outcome": "SKIP"}])
        self.assertEqual(compile_plan(p)["test_case_comparison"]["events"][0]["kind"],
                         "PASS_TO_SKIP_TEST_OBLIGATION_LOSS")

    def test_incomparable_test_selection_is_not_green_to_red(self):
        p = fixture()
        p["previous_cases"] = case_block(PREVIOUS, [{"id": "s::x", "outcome": "PASS"}])
        p["current_cases"] = case_block(HEAD, [{"id": "s::x", "outcome": "ERROR"}], digest="e" * 64)
        c = compile_plan(p)["test_case_comparison"]
        self.assertFalse(c["comparable"])
        self.assertEqual(c["events"][0]["kind"], "RED_UNMATCHED_COHORT")

    def test_unverified_case_collection_unknown(self):
        p = fixture()
        p["previous_cases"] = case_block(PREVIOUS, [{"id": "s::x", "outcome": "PASS"}], complete=False)
        p["current_cases"] = case_block(HEAD, [{"id": "s::x", "outcome": "FAIL"}])
        self.assertEqual(compile_plan(p)["test_case_comparison"]["state"], "UNKNOWN")

    def test_rex_withheld_always(self):
        r = compile_plan(fixture())
        rex = next(x for x in r["tasks"] if x["id"] == "REX")
        self.assertEqual(rex["decision"], "WITHHELD_REQUIRES_SEPARATE_AUTHORITY")
        self.assertNotIn("REX", [x for wave in r["waves"] for x in wave["task_ids"]])

    def test_descendant_of_withheld_authority_is_not_scheduled(self):
        p = fixture()
        p["tasks"].append({"id": "AFTER_REX", "kind": "artifact", "required": True,
                           "priority": "P0", "needs": ["REX"]})
        r = compile_plan(p)
        self.assertEqual(r["withheld_task_ids"], ["AFTER_REX", "REX"])
        self.assertEqual(next(t for t in r["tasks"] if t["id"] == "AFTER_REX")["decision"],
                         "BLOCKED_BEHIND_WITHHELD_AUTHORITY")

    def test_measured_native_queue_and_runtime(self):
        p = fixture()
        x = job("LINT", HEAD)
        x.update(created_at="2026-10-16T08:00:00Z", started_at="2026-10-16T08:04:00Z",
                 completed_at="2026-10-16T08:04:13Z")
        p["current_jobs"] = [x]
        r = compile_plan(p)
        self.assertEqual(r["queue_seconds_p50"], 240)
        self.assertEqual(r["runtime_seconds_p95"], 13)
        self.assertIsNone(r["independent_stable_cycles"])

    def test_no_native_queue_as_zero_when_unknown(self):
        r = compile_plan(fixture())
        self.assertIsNone(r["queue_seconds_p50"])
        self.assertIsNone(r["runtime_seconds_p95"])

    def test_reject_negative_native_clock(self):
        p = fixture()
        x = job("LINT", HEAD)
        x.update(created_at="2026-10-16T08:04:00Z", started_at="2026-10-16T08:00:00Z")
        p["current_jobs"] = [x]
        with self.assertRaises(ValueError):
            compile_plan(p)

    def test_reject_nonterminal_completed_clock(self):
        p = fixture()
        x = job("LINT", HEAD)
        x.update(status="queued", conclusion=None, completed_at="2026-10-16T08:04:00Z")
        p["current_jobs"] = [x]
        with self.assertRaises(ValueError):
            compile_plan(p)

    def test_successful_native_job_does_not_clear_wrong_artifact_sha(self):
        p = fixture()
        p["previous_jobs"] = [job("LINT", PREVIOUS, "failure", ident=1)]
        n = job("LINT", HEAD, ident=2)
        n["receipt_source_sha"] = BASE
        p["current_jobs"] = [n]
        t = next(x for x in compile_plan(p)["tasks"] if x["id"] == "LINT")
        self.assertEqual(t["transition"], "PREVIOUS_RED_NOW_GREEN_JOB")
        self.assertEqual(t["artifact_receipt_identity"], "MISMATCH_REJECT_ARTIFACT_SOURCE")
        self.assertEqual(t["decision"], "REPAIR_SOURCE_RECEIPT_IDENTITY")

    def test_unreported_receipt_stays_unknown(self):
        p = fixture()
        p["current_jobs"] = [job("LINT", HEAD)]
        t = next(x for x in compile_plan(p)["tasks"] if x["id"] == "LINT")
        self.assertEqual(t["artifact_receipt_identity"], "UNKNOWN")

    def test_matching_receipt_cannot_claim_byte_verified(self):
        p = fixture()
        n = job("LINT", HEAD)
        n["receipt_source_sha"] = HEAD
        p["current_jobs"] = [n]
        t = next(x for x in compile_plan(p)["tasks"] if x["id"] == "LINT")
        self.assertEqual(t["artifact_receipt_identity"], "DECLARED_MATCH_BYTES_UNVERIFIED")

    def test_reject_duplicate_tasks(self):
        p = fixture()
        p["tasks"].append(copy.deepcopy(p["tasks"][0]))
        with self.assertRaises(ValueError):
            compile_plan(p)

    def test_reject_cycle(self):
        p = fixture()
        p["tasks"][0]["needs"] = ["REX"]
        with self.assertRaises(ValueError):
            compile_plan(p)

    def test_reject_missing_dependency(self):
        p = fixture()
        p["tasks"][2]["needs"] = ["GHOST"]
        with self.assertRaises(ValueError):
            compile_plan(p)

    def test_reject_path_traversal(self):
        p = fixture()
        p["tasks"][0]["paths"] = ["../bad"]
        with self.assertRaises(ValueError):
            compile_plan(p)

    def test_reject_windows_absolute(self):
        p = fixture()
        p["changed_paths"] = ["C:\\secret\\file"]
        with self.assertRaises(ValueError):
            compile_plan(p)

    def test_reject_foreign_repo(self):
        p = fixture()
        p["repository"] = "GBOGEB/CODEX"
        with self.assertRaises(ValueError):
            compile_plan(p)

    def test_reject_wrong_job_sha(self):
        p = fixture()
        p["current_jobs"] = [job("LINT", PREVIOUS)]
        with self.assertRaises(ValueError):
            compile_plan(p)

    def test_reject_duplicate_native_job(self):
        p = fixture()
        p["current_jobs"] = [job("LINT", HEAD), job("NEG", HEAD)]
        with self.assertRaises(ValueError):
            compile_plan(p)

    def test_reject_bool_job_id(self):
        p = fixture()
        x = job("LINT", HEAD)
        x["job_id"] = True
        p["current_jobs"] = [x]
        with self.assertRaises(ValueError):
            compile_plan(p)

    def test_reject_false_green_conclusion(self):
        p = fixture()
        x = job("LINT", HEAD)
        x.update(status="in_progress", conclusion="success")
        p["current_jobs"] = [x]
        with self.assertRaises(ValueError):
            compile_plan(p)

    def test_reject_empty_complete_collection(self):
        p = fixture()
        p["previous_cases"] = case_block(PREVIOUS, [])
        p["current_cases"] = case_block(HEAD, [{"id": "s::x", "outcome": "PASS"}])
        with self.assertRaises(ValueError):
            compile_plan(p)

    def test_reject_duplicate_test_id(self):
        p = fixture()
        p["previous_cases"] = case_block(PREVIOUS, [{"id": "s::x", "outcome": "PASS"},
                                                  {"id": "s::x", "outcome": "PASS"}])
        p["current_cases"] = case_block(HEAD, [{"id": "s::x", "outcome": "PASS"}])
        with self.assertRaises(ValueError):
            compile_plan(p)

    def test_reject_nonfinite_test_duration(self):
        p = fixture()
        p["previous_cases"] = case_block(PREVIOUS, [{"id": "s::x", "outcome": "PASS",
                                                     "duration_seconds": float("nan")}])
        p["current_cases"] = case_block(HEAD, [{"id": "s::x", "outcome": "PASS"}])
        with self.assertRaises(ValueError):
            compile_plan(p)

    def test_reject_excess_parallelism(self):
        p = fixture()
        p["max_parallel"] = 17
        with self.assertRaises(ValueError):
            compile_plan(p)

    def test_reject_unprotected_rex_mode(self):
        p = fixture()
        p["tasks"][-1]["mode"] = "LOCAL_TEST"
        with self.assertRaises(ValueError):
            compile_plan(p)

    def test_reject_remote_mutation_as_observation(self):
        p = fixture()
        p["tasks"][0]["mode"] = "REMOTE_OBSERVE"
        with self.assertRaises(ValueError):
            compile_plan(p)


if __name__ == "__main__":
    unittest.main()