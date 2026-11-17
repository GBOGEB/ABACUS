"""Source-reported G3C-S serial-main comparator regression and denial cases."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

FILE = (
    Path(__file__).resolve().parents[1]
    / "MIP/G3CS_CONVERGENCE_V2/tools/serial_main_pair.py"
)
SPEC = importlib.util.spec_from_file_location("g3cs_paired_main", FILE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
A, B, C = "a" * 40, "b" * 40, "c" * 64
D, E, F = "d" * 64, "e" * 64, "f" * 64


def cov(sha, numerator, eligible=100, *, scope=D, tool=E, selection=F):
    return {
        "source_sha": sha,
        "scope_sha256": scope,
        "tool_sha256": tool,
        "selection_sha256": selection,
        "covered": numerator,
        "eligible": eligible,
    }


def row(sha, timestamp, parent=None, *, count=5):
    jobs = []
    for i in range(count):
        created = f"2026-10-18T10:{i:02d}:00Z"
        started = f"2026-10-18T10:{i:02d}:05Z"
        finished = f"2026-10-18T10:{i:02d}:12Z"
        jobs.append(
            {
                "source_sha": sha,
                "run_id": (100 if sha == A else 200) + i,
                "attempt": 1,
                "job_id": (1000 if sha == A else 2000) + i,
                "cohort_key": f"linux-py3.{i}/suite",
                "environment_sha256": E,
                "status": "completed",
                "conclusion": "success",
                "created_at": created,
                "started_at": started,
                "completed_at": finished,
            }
        )
    return {
        "main_sha": sha,
        "parent_main_sha": parent,
        "captured_at": timestamp,
        "coverage": {
            "statement": cov(sha, 60 if sha == A else 70),
            "branch": cov(sha, 30 if sha == A else 32, 50),
            "diff": None,
        },
        "first_red_fingerprints": [C] if sha == A else [D],
        "roots": {C: "OPEN"} if sha == A else {C: "CLOSURE_CLAIMED", D: "OPEN"},
        "jobs": jobs,
    }


def fixture():
    return {
        "schema": MODULE.INPUT_SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "clock": "SERIAL_MERGED_MAIN",
        "receipt_authentication": "NOT_INDEPENDENTLY_VERIFIED",
        "observations": [
            row(A, "2026-10-18T12:30:00+02:00"),
            row(B, "2026-10-18T10:40:00Z", A),
        ],
    }


class G3CSSerialMainTests(unittest.TestCase):
    def deny(self, edit, error):
        payload = fixture()
        edit(payload)
        with self.assertRaisesRegex(ValueError, error):
            MODULE.compare(payload)

    def test_comparable_statement_and_branch_deltas(self):
        out = MODULE.compare(fixture())
        self.assertEqual(out["coverage"]["statement"]["numerator_delta"], 10)
        self.assertEqual(out["coverage"]["statement"]["delta_pp"], 10.0)
        self.assertEqual(out["coverage"]["branch"]["delta_pp"], 4.0)
        self.assertEqual(out["coverage"]["diff"]["status"], "UNKNOWN")

    def test_noncomparable_tool_and_population(self):
        p = fixture()
        p["observations"][1]["coverage"]["statement"]["tool_sha256"] = C
        p["observations"][1]["coverage"]["branch"]["eligible"] = 51
        out = MODULE.compare(p)
        self.assertEqual(out["coverage"]["statement"]["status"], "NONCOMPARABLE")
        self.assertEqual(out["coverage"]["branch"]["status"], "NONCOMPARABLE")
        self.assertIsNone(out["coverage"]["statement"]["delta_pp"])

    def test_first_red_disappearance_not_root_closure(self):
        out = MODULE.compare(fixture())
        self.assertEqual(out["first_reds"]["nonreproduced_candidates"], [C])
        self.assertEqual(out["first_reds"]["new"], [D])
        self.assertEqual(out["first_reds"]["closure_credit"], 0)
        self.assertIsNone(out["roots"]["verified_closed"])
        self.assertEqual(out["admission"], "HOLD")

    def test_five_matched_jobs_have_descriptive_p95(self):
        result = MODULE.compare(fixture())["telemetry"]
        self.assertEqual(result["matched_terminal_jobs"], 5)
        self.assertEqual(result["queue_p95_before_seconds"], 5)
        self.assertEqual(result["execution_p95_after_seconds"], 7)
        self.assertEqual(
            result["provenance"], "SOURCE_REPORTED_NOT_NATIVE_AUTHENTICATED"
        )

    def test_fewer_than_five_matched_jobs_have_unknown_p95(self):
        p = fixture()
        for item in p["observations"]:
            item["jobs"] = item["jobs"][:2]
        result = MODULE.compare(p)["telemetry"]
        self.assertEqual(result["matched_terminal_jobs"], 2)
        self.assertIsNone(result["queue_p95_before_seconds"])

    def test_unsupported_authority_promotion_rejected(self):
        self.deny(
            lambda p: p.update(receipt_authentication="INDEPENDENTLY_VERIFIED"),
            "unproven native attestation",
        )

    def test_parallel_or_other_repository_rejected(self):
        self.deny(lambda p: p.update(clock="PARALLEL_PR_HEAD"), "non-main")
        self.deny(lambda p: p.update(repository="GBOGEB/CODEX"), "non-main")

    def test_noncontiguous_main_chain_rejected(self):
        self.deny(
            lambda p: p["observations"][1].update(parent_main_sha="f" * 40),
            "not contiguous",
        )

    def test_nonmonotonic_or_naive_capture_time_rejected(self):
        self.deny(
            lambda p: p["observations"][1].update(captured_at="2026-10-18T09:00:00Z"),
            "nonmonotonic",
        )
        self.deny(
            lambda p: p["observations"][0].update(captured_at="2026-10-18T10:00:00"),
            "offset-aware",
        )

    def test_coverage_source_and_integer_denominator_guards(self):
        self.deny(
            lambda p: p["observations"][1]["coverage"]["statement"].update(
                source_sha=A
            ),
            "not source-bound",
        )
        self.deny(
            lambda p: p["observations"][1]["coverage"]["branch"].update(covered=52),
            "numerator/denominator",
        )
        self.deny(
            lambda p: p["observations"][1]["coverage"]["branch"].update(eligible=True),
            "numerator/denominator",
        )

    def test_forged_duplicate_fingerprint_and_job_identity_rejected(self):
        self.deny(
            lambda p: p["observations"][0]["first_red_fingerprints"].append(C),
            "duplicated first-red",
        )
        self.deny(
            lambda p: p["observations"][1]["jobs"][0].update(run_id=100, job_id=1000),
            "reused native job identity",
        )
        self.deny(
            lambda p: p["observations"][1]["jobs"][0].update(job_id=1000),
            "reused native job identity",
        )
        self.deny(
            lambda p: p["observations"][1]["jobs"][0].update(run_id=100),
            "cross-main native run ID reused",
        )

    def test_nonterminal_completion_or_negative_clock_rejected(self):
        self.deny(
            lambda p: p["observations"][1]["jobs"][0].update(
                status="queued", conclusion=None
            ),
            "falsely complete",
        )
        self.deny(
            lambda p: p["observations"][1]["jobs"][0].update(
                started_at="2026-10-18T09:00:00Z"
            ),
            "negative queue",
        )
        self.deny(
            lambda p: p["observations"][1]["jobs"][0].update(
                completed_at="2026-10-18T09:00:00Z"
            ),
            "negative execution",
        )

    def test_skipped_and_cancelled_jobs_do_not_fake_latency(self):
        p = fixture()
        for row in p["observations"]:
            job = row["jobs"][0]
            job.update(conclusion="skipped", started_at=None, completed_at=None)
        timing = MODULE.compare(p)["telemetry"]
        self.assertEqual(timing["matched_terminal_jobs"], 4)
        self.assertIsNone(timing["execution_p95_before_seconds"])

    def test_stale_capture_and_false_queued_clock_rejected(self):
        self.deny(
            lambda p: p["observations"][0].update(captured_at="2026-10-18T10:00:00Z"),
            "observation precedes",
        )
        self.deny(
            lambda p: p["observations"][1]["jobs"][0].update(
                status="queued", conclusion=None, completed_at=None
            ),
            "queued job has start",
        )

    def test_waiting_and_requested_are_nonterminal_without_fake_p95(self):
        for state in ("pending", "waiting", "requested"):
            p = fixture()
            for row in p["observations"]:
                row["jobs"][0].update(
                    status=state, conclusion=None, started_at=None, completed_at=None
                )
            out = MODULE.compare(p)
            self.assertEqual(out["telemetry"]["matched_terminal_jobs"], 4)
            self.assertIsNone(out["telemetry"]["queue_p95_before_seconds"])

    def test_environment_drift_blocks_latency_comparison(self):
        p = fixture()
        p["observations"][1]["jobs"][0]["environment_sha256"] = C
        out = MODULE.compare(p)["telemetry"]
        self.assertEqual(len(out["environment_mismatched_jobs"]), 1)
        self.assertEqual(out["matched_terminal_jobs"], 4)
        self.assertIsNone(out["queue_p95_before_seconds"])
        self.deny(
            lambda p: p["observations"][1]["jobs"][0].pop("environment_sha256"),
            "missing job environment fingerprint",
        )

    def test_nonmatching_job_keys_cannot_fake_latency(self):
        p = fixture()
        for job in p["observations"][1]["jobs"]:
            job["cohort_key"] = "windows" + job["cohort_key"]
        result = MODULE.compare(p)["telemetry"]
        self.assertEqual(result["matched_terminal_jobs"], 0)
        self.assertIsNone(result["execution_p95_before_seconds"])

    def test_output_does_not_claim_statistical_convergence(self):
        out = MODULE.compare(fixture())
        self.assertEqual(out["statistics"]["regime"], "DESCRIPTIVE_PAIR_ONLY")
        self.assertIsNone(out["statistics"]["six_sigma"])
        self.assertFalse(out["authority_transfer"])

    def test_deterministic_json_output(self):
        one = json.dumps(MODULE.compare(fixture()), sort_keys=True)
        two = json.dumps(MODULE.compare(copy.deepcopy(fixture())), sort_keys=True)
        self.assertEqual(one, two)


if __name__ == "__main__":
    unittest.main()
