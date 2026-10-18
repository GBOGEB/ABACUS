"""W40 disjoint CI proof/input mutation canaries; no network or dispatch.

Run in supported Python interpreters with:
    python -m unittest tests.test_w40_ci_proof_mutation -v
Source tests detect plausible mutant behavior, not just test-case quantity.
All output is engineering evidence, never approval or coverage acceptance.
"""

import copy
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from scripts import cbd_rerun_wave_planner as planner
from scripts import ci_matrix_proof_audit as matrix


SHA = "a" * 40
BASE = "b" * 40


def observation(run_id=7001, pr=2284, status="completed", conclusion="failure",
                attempt=1, root="runner-queue"):
    return {
        "pr": pr,
        "head_sha": SHA,
        "run_id": run_id,
        "attempt": attempt,
        "workflow": "MIP B0 Test Admission and Coverage Evidence",
        "status": status,
        "conclusion": conclusion,
        "url": "https://github.com/GBOGEB/ABACUS/actions/runs/" + str(run_id),
        "first_red": {
            "verified": True,
            "kind": "transient_runner",
            "root_signature": root,
            "job_id": run_id + 10000,
            "url": (
                "https://github.com/GBOGEB/ABACUS/actions/runs/"
                + str(run_id) + "/job/" + str(run_id + 10000)
            ),
        },
    }


def snapshot(*rows):
    return {
        "schema": planner.SCHEMA,
        "repository": planner.REPO,
        "base_sha": BASE,
        "current_pr_heads": {str(row["pr"]): row["head_sha"] for row in rows},
        "capacity": {
            "queued": 0, "in_progress": 0, "max_queued": 4,
            "max_in_progress": 2, "max_new_reruns": 1, "max_attempts": 2,
        },
        "authority": copy.deepcopy(planner.AUTHORITY),
        "observations": list(rows),
    }


def write_proofs(directory, versions):
    for version in versions:
        checks = dict(matrix.EXPECTED[version])
        checks["artifact_upload"] = "EXECUTED_PASS"
        payload = {
            "exact_sha": SHA, "python_version": version,
            "proof_role": "full-matrix",
            "checks": checks,
        }
        (directory / ("python-" + version + "-proof.json")).write_text(
            json.dumps(payload), encoding="utf-8"
        )


class MatrixMutantSensitivity(unittest.TestCase):
    def test_three_interpreter_baseline_and_fifteen_false_green_mutants(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            versions = ("3.10", "3.11", "3.12")
            write_proofs(path, versions)
            baseline = matrix.audit(path, "full", "3.10", SHA)
            self.assertEqual(baseline["status"], "PASS", baseline["errors"])
            killed = 0
            for version in versions:
                target = path / ("python-" + version + "-proof.json")
                original = json.loads(target.read_text(encoding="utf-8"))
                for key in matrix.EXPECTED[version]:
                    with self.subTest(version=version, changed_proof=key):
                        mutant = copy.deepcopy(original)
                        mutant["checks"][key] = "EXECUTED_PASS_MUTANT"
                        target.write_text(json.dumps(mutant), encoding="utf-8")
                        result = matrix.audit(path, "full", "3.10", SHA)
                        self.assertEqual(result["status"], "FAIL")
                        self.assertTrue(
                            any(e.startswith(version + ":" + key + ":")
                                for e in result["errors"]),
                            result["errors"],
                        )
                        killed += 1
                        target.write_text(json.dumps(original), encoding="utf-8")
            self.assertEqual(killed, 15)
            self.assertEqual(matrix.audit(path, "full", "3.10", SHA)["status"], "PASS")

    def test_sentinel_and_sampled_interpreter_proof_roles(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            checks = dict(matrix.EXPECTED["3.12"])
            checks["artifact_upload"] = "OPTIONAL_NO_PAYLOAD"
            target = path / "python-3.12-proof.json"
            target.write_text(json.dumps({
                "exact_sha": SHA, "python_version": "3.12",
                "proof_role": "sentinel", "checks": checks,
            }), encoding="utf-8")
            self.assertEqual(matrix.audit(path, "sentinel", "3.10", SHA)["status"], "PASS")
            self.assertEqual(matrix.audit(path, "sampled", "3.10", SHA)["status"], "FAIL")
            for secondary in ("3.12", "3.9", "", "not-python"):
                with self.subTest(secondary=secondary):
                    with self.assertRaises(ValueError):
                        matrix.expected_versions("sampled", secondary)

    def test_manifest_fault_injection_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "python-3.12-proof.json"
            variants = (
                "[1, 2]", "not-json",
                json.dumps({"checks": None}),
                json.dumps({"checks": "green"}),
                json.dumps({"checks": []}),
                json.dumps({"checks": False}),
            )
            for payload in variants:
                with self.subTest(payload=payload):
                    target.write_text(payload, encoding="utf-8")
                    result = matrix.audit(Path(d), "sentinel", "3.10", SHA)
                    self.assertEqual(result["status"], "FAIL")
                    self.assertTrue(result["errors"])


class PlannerBoundaryMutantSensitivity(unittest.TestCase):
    def test_queue_boundary_truth_table(self):
        row = observation()
        exercised = 0
        for max_queue in (0, 1, 4):
            for count in (0, 1, 2, 4, 5):
                for active in (0, 1, 2):
                    with self.subTest(cap=max_queue, queued=count, active=active):
                        x = snapshot(copy.deepcopy(row))
                        x["capacity"].update(
                            max_queued=max_queue, queued=count, in_progress=active,
                        )
                        expected_hold = count >= max_queue or active >= 2
                        out = planner.plan(x)
                        self.assertEqual(out["backpressure"], expected_hold)
                        self.assertEqual(out["proposed_reruns"], 0 if expected_hold else 1)
                        self.assertEqual(out["proposals"][0]["action"],
                                         "BACKPRESSURE_HOLD" if expected_hold
                                         else "RERUN_FAILED_JOBS")
                        self.assertFalse(out["proposals"][0]["executed"])
                        exercised += 1
        self.assertEqual(exercised, 45)

    def test_greater_than_mutant_is_killed_at_equal_queue_cap(self):
        actual_source = inspect.getsource(planner.plan)
        needle = 'cap["queued"] >= cap["max_queued"]'
        self.assertEqual(actual_source.count(needle), 1)
        # Static source oracle plus a manually evaluated wrong comparator.
        # Do not exec/eval mutated source inside CI or create Bandit B102 debt.
        x = snapshot(observation())
        x["capacity"]["queued"] = x["capacity"]["max_queued"]
        reference = planner.plan(x)
        wrong_gt_predicate = (
            x["capacity"]["queued"] > x["capacity"]["max_queued"]
            or x["capacity"]["in_progress"] >= x["capacity"]["max_in_progress"]
        )
        self.assertFalse(wrong_gt_predicate)
        self.assertTrue(reference["backpressure"])
        self.assertEqual(reference["proposed_reruns"], 0)

    def test_duplicate_root_and_budget_are_non_dispatching(self):
        x = snapshot(observation(run_id=7001, pr=2284),
                     observation(run_id=7002, pr=2285))
        proposed = planner.plan(x)
        self.assertEqual(proposed["proposed_reruns"], 1)
        self.assertEqual([r["action"] for r in proposed["proposals"]],
                         ["RERUN_FAILED_JOBS", "WAIT_SHARED_ROOT_CANARY"])
        self.assertTrue(all(r["merge_authorized"] is False for r in proposed["proposals"]))
        self.assertTrue(all(r["executed"] is False for r in proposed["proposals"]))
        x["capacity"]["max_new_reruns"] = 0
        self.assertEqual(planner.plan(x)["proposed_reruns"], 0)

    def test_malformed_mutation_matrix_fails_closed(self):
        base = snapshot(observation())
        mutation_cases = (
            ("source_sha_type", ("current_pr_heads", "2284"), True),
            ("pr_key", ("current_pr_heads",), {"02284": SHA}),
            ("attempt_bool", ("observations", 0, "attempt"), True),
            ("run_zero", ("observations", 0, "run_id"), 0),
            ("invalid_state", ("observations", 0, "status"), "green"),
            ("invalid_conclusion", ("observations", 0, "conclusion"), "green"),
            ("foreign_url", ("observations", 0, "url"), "https://example.invalid/7001"),
            ("fake_gate", ("authority", "merge_admission"), "PASS"),
            ("float_queue", ("capacity", "queued"), 1.5),
            ("negative_cap", ("capacity", "max_queued"), -1),
            ("unknown_root", ("observations", 0, "first_red", "kind"), "untrusted"),
            ("fake_job_url", ("observations", 0, "first_red", "url"), "https://elsewhere"),
        )
        for label, path, value in mutation_cases:
            with self.subTest(label=label):
                x = copy.deepcopy(base)
                node = x
                for key in path[:-1]:
                    node = node[key]
                node[path[-1]] = value
                with self.assertRaises(ValueError):
                    planner.plan(x)

    def test_immutable_attempt_identity_and_deterministic_replay(self):
        x = snapshot(observation())
        previous = copy.deepcopy(x)
        self.assertEqual(planner.compare(previous, x), [])
        self.assertEqual(planner.plan(x), planner.plan(copy.deepcopy(x)))
        later = copy.deepcopy(x)
        later["observations"][0]["attempt"] = 2
        self.assertEqual(planner.compare(x, later)[0]["event"], "NEW_ATTEMPT")
        for key, replacement in (
            ("workflow", "Security Scan"), ("head_sha", "b" * 40),
            ("pr", 2285),
        ):
            with self.subTest(changed=key):
                wrong = copy.deepcopy(x)
                wrong["observations"][0][key] = replacement
                if key == "pr":
                    wrong["current_pr_heads"] = {"2285": SHA}
                if key == "head_sha":
                    wrong["current_pr_heads"]["2284"] = replacement
                with self.assertRaises(ValueError):
                    planner.compare(x, wrong)



class W43ProvenanceMutationGuards(unittest.TestCase):
    def test_duplicate_manifest_keys_do_not_become_green(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "python-3.12-proof.json"
            checks = dict(matrix.EXPECTED["3.12"])
            checks["artifact_upload"] = "EXECUTED_PASS"
            valid = json.dumps({
                "exact_sha": SHA, "python_version": "3.12",
                "proof_role": "sentinel", "checks": checks,
            })
            top_level_duplicate = (
                '{"exact_sha":"' + SHA + '","exact_sha":"' + SHA
                + '","python_version":"3.12","proof_role":"sentinel",'
                + '"checks":' + json.dumps(checks) + '}'
            )
            nested_duplicate = valid.replace(
                '"artifact_upload": "EXECUTED_PASS"',
                '"artifact_upload": "EXECUTED_PASS", '
                '"artifact_upload": "EXECUTED_PASS"',
            )
            self.assertEqual(len(valid.split('"artifact_upload"')), 2)
            self.assertNotEqual(top_level_duplicate, valid)
            self.assertNotEqual(nested_duplicate, valid)
            target.write_text(valid, encoding="utf-8")
            self.assertEqual(
                matrix.audit(Path(directory), "sentinel", "3.10", SHA)["status"],
                "PASS",
            )
            for payload in (top_level_duplicate, nested_duplicate):
                with self.subTest(payload=payload[:30]):
                    target.write_text(payload, encoding="utf-8")
                    result = matrix.audit(Path(directory), "sentinel", "3.10", SHA)
                    self.assertEqual(result["status"], "FAIL")
                    self.assertIn(
                        "3.12:INVALID_SUMMARY:ValueError", result["errors"],
                    )

    def test_verified_first_red_cannot_be_rewritten_at_same_attempt(self):
        prior = snapshot(observation())
        for change in ("root_signature", "kind", "removed"):
            with self.subTest(change=change):
                candidate = copy.deepcopy(prior)
                if change == "removed":
                    candidate["observations"][0]["first_red"] = None
                elif change == "kind":
                    candidate["observations"][0]["first_red"]["kind"] = "security"
                else:
                    candidate["observations"][0]["first_red"]["root_signature"] = "new-root"
                with self.assertRaisesRegex(
                    ValueError, "verified first-red cannot be replaced",
                ):
                    planner.compare(prior, candidate)
                # The same changed evidence on an independently numbered
                # native run attempt is retained as a new observation.
                candidate["observations"][0]["attempt"] = 2
                event = planner.compare(prior, candidate)
                self.assertEqual(event[0]["event"], "NEW_ATTEMPT")

    def test_first_red_discovery_on_same_attempt_is_separate_from_rewrite(self):
        prior = snapshot(observation())
        prior["observations"][0]["first_red"] = None
        updated = snapshot(observation())
        change = planner.compare(prior, updated)
        self.assertEqual(change[0]["event"], "FIRST_RED_UPDATED")
        self.assertEqual(change[0]["allowed_downstream_action"], "RECHECK_ONLY")

    def test_multi_root_rerun_budget_monotonicity(self):
        rows = [observation(7001, 2284, root="root-A"),
                observation(7002, 2285, root="root-B"),
                observation(7003, 2286, root="root-C")]
        x = snapshot(*rows)
        for budget in (0, 1, 2, 3, 4):
            with self.subTest(budget=budget):
                x["capacity"]["max_new_reruns"] = budget
                result = planner.plan(x)
                self.assertEqual(result["proposed_reruns"], min(budget, 3))
                self.assertTrue(all(not row["executed"]
                                    for row in result["proposals"]))
                self.assertTrue(all(not row["merge_authorized"]
                                    for row in result["proposals"]))



if __name__ == "__main__":
    unittest.main()
