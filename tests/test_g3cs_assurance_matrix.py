"""G3C-S W7: mutation, reverse, security, stress, and oracle calibration.

Synthetic controls measure the classifier's behaviour, not real-world FPR/FNR,
coverage uplift, root closure, or independently authenticated native receipts.
All inputs are deterministic; no third-party libraries, live tokens, or network.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import random
import runpy
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "MIP/G3CS_CONVERGENCE_V2/tools/serial_main_pair.py"
)
SPEC = importlib.util.spec_from_file_location("g3cs_assurance_subject", MODULE_PATH)
SUBJECT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUBJECT)
FIRST = "a" * 40
SECOND = "b" * 40
SHA_C = "c" * 64
SHA_D = "d" * 64
SHA_E = "e" * 64
SHA_F = "f" * 64


def coverage(source, numerator, denominator):
    return {
        "source_sha": source,
        "scope_sha256": SHA_D,
        "tool_sha256": SHA_E,
        "selection_sha256": SHA_F,
        "covered": numerator,
        "eligible": denominator,
    }


def observation(sha, after, parent=None, count=5):
    jobs = []
    for index in range(count):
        created = datetime(2026, 10, 18, 10, tzinfo=timezone.utc) + timedelta(
            seconds=index
        )
        job = {
            "source_sha": sha,
            "run_id": (100000 if sha == FIRST else 200000) + index,
            "attempt": 1,
            "job_id": (300000 if sha == FIRST else 400000) + index,
            "cohort_key": f"proof/linux/python/{index}",
            "environment_sha256": SHA_E,
            "status": "completed",
            "conclusion": "success",
            "created_at": created.isoformat().replace("+00:00", "Z"),
            "started_at": (created + timedelta(seconds=7))
            .isoformat()
            .replace("+00:00", "Z"),
            "completed_at": (created + timedelta(seconds=18))
            .isoformat()
            .replace("+00:00", "Z"),
        }
        jobs.append(job)
    return {
        "main_sha": sha,
        "parent_main_sha": parent,
        "captured_at": after,
        "coverage": {
            "statement": coverage(sha, 60 if sha == FIRST else 70, 100),
            "branch": coverage(sha, 30 if sha == FIRST else 35, 50),
            "diff": None,
        },
        "first_red_fingerprints": [SHA_C] if sha == FIRST else [SHA_D],
        "roots": (
            {SHA_C: "OPEN"}
            if sha == FIRST
            else {SHA_C: "CLOSURE_CLAIMED", SHA_D: "OPEN"}
        ),
        "jobs": jobs,
    }


def fixture(count=5):
    return {
        "schema": SUBJECT.INPUT_SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "clock": "SERIAL_MERGED_MAIN",
        "receipt_authentication": "NOT_INDEPENDENTLY_VERIFIED",
        "observations": [
            observation(FIRST, "2026-10-18T10:30:00Z", count=count),
            observation(SECOND, "2026-10-18T10:40:00Z", FIRST, count=count),
        ],
    }


def mutate_path(payload, address, value):
    node = payload
    for key in address[:-1]:
        node = node[key]
    node[address[-1]] = value


def adversarial_cases():
    """Distinct labelled invalid inputs; acceptance is a false negative."""
    a = ("observations", 0)
    b = ("observations", 1)
    out = [
        ("schema/unknown", ("schema",), "unexpected"),
        ("schema/null", ("schema",), None),
        ("repository/confused", ("repository",), "GBOGEB/CODEX"),
        ("repository/null", ("repository",), None),
        ("clock/parallel", ("clock",), "PARALLEL_PR_HEAD"),
        ("clock/null", ("clock",), None),
        ("auth/claimed", ("receipt_authentication",), "VERIFIED"),
        ("auth/boolean", ("receipt_authentication",), True),
        ("observations/null", ("observations",), None),
        ("observations/nonlist", ("observations",), {}),
        ("observations/missing", ("observations",), []),
        ("observations/bad_child", a, None),
        ("observations/second_bad", b, "evil"),
        ("lineage/forged_parent", b + ("parent_main_sha",), "f" * 40),
        ("lineage/same_head", b + ("main_sha",), FIRST),
        ("lineage/bad_sha", a + ("main_sha",), "z" * 40),
        ("lineage/nonstring_sha", a + ("main_sha",), 5),
        ("clock/naive_capture", a + ("captured_at",), "2026-10-18T10:30:00"),
        ("clock/backwards_capture", b + ("captured_at",), "2026-10-18T10:25:00Z"),
        ("clock/invalid_capture", b + ("captured_at",), "never"),
        ("clock/missing_capture", a + ("captured_at",), None),
        ("coverage/null_mapping", a + ("coverage",), None),
        ("coverage/nonobject_mapping", a + ("coverage",), []),
        ("coverage/invalid_branch_object", b + ("coverage", "branch"), 1),
        ("coverage/boolean_numerator", b + ("coverage", "statement", "covered"), True),
        ("coverage/float_numerator", b + ("coverage", "statement", "covered"), 70.1),
        ("coverage/negative_numerator", b + ("coverage", "statement", "covered"), -1),
        ("coverage/over_numerator", b + ("coverage", "statement", "covered"), 101),
        ("coverage/zero_denominator", b + ("coverage", "branch", "eligible"), 0),
        ("coverage/boolean_denominator", b + ("coverage", "branch", "eligible"), False),
        ("coverage/wrong_source", b + ("coverage", "branch", "source_sha"), FIRST),
        ("coverage/forged_tool", b + ("coverage", "branch", "tool_sha256"), "error"),
        ("coverage/missing_scope", b + ("coverage", "statement", "scope_sha256"), None),
        (
            "coverage/invalid_selection",
            b + ("coverage", "branch", "selection_sha256"),
            True,
        ),
        ("first_reds/null", a + ("first_red_fingerprints",), None),
        ("first_reds/nonlist", a + ("first_red_fingerprints",), {}),
        ("first_reds/malformed", a + ("first_red_fingerprints",), ["not-a-sha"]),
        ("first_reds/unhashable", a + ("first_red_fingerprints",), [{}]),
        ("first_reds/duplicated", a + ("first_red_fingerprints",), [SHA_C, SHA_C]),
        ("roots/null", a + ("roots",), None),
        ("roots/nonobject", a + ("roots",), []),
        ("roots/malformed_key", a + ("roots",), {17: "OPEN"}),
        ("roots/unhashable_state", a + ("roots",), {SHA_C: []}),
        ("roots/false_accepted", a + ("roots",), {SHA_C: "CLOSED"}),
        ("jobs/nonlist", a + ("jobs",), {}),
        ("jobs/null_child", a + ("jobs", 0), None),
        ("jobs/malformed_child", b + ("jobs", 1), []),
        ("jobs/forged_source", b + ("jobs", 0, "source_sha"), FIRST),
        ("jobs/bool_run_id", b + ("jobs", 0, "run_id"), True),
        ("jobs/negative_attempt", b + ("jobs", 0, "attempt"), 0),
        ("jobs/float_job_id", b + ("jobs", 0, "job_id"), 4.5),
        ("jobs/wrong_env", b + ("jobs", 0, "environment_sha256"), "bad"),
        ("jobs/list_cohort_key", b + ("jobs", 0, "cohort_key"), []),
        ("jobs/empty_cohort_key", b + ("jobs", 0, "cohort_key"), ""),
        ("jobs/unknown_status", b + ("jobs", 0, "status"), "done"),
        ("jobs/no_terminal_conclusion", b + ("jobs", 0, "conclusion"), None),
        ("jobs/fake_success", b + ("jobs", 0, "conclusion"), "pass"),
        ("jobs/no_start", b + ("jobs", 0, "started_at"), None),
        ("jobs/negative_queue", b + ("jobs", 0, "started_at"), "2026-10-18T09:00:00Z"),
        (
            "jobs/negative_runtime",
            b + ("jobs", 0, "completed_at"),
            "2026-10-18T09:00:00Z",
        ),
        ("jobs/late_created", b + ("jobs", 0, "created_at"), "2026-10-18T12:00:00Z"),
        ("jobs/duplicated_id", b + ("jobs", 0, "job_id"), 300000),
        ("jobs/reused_run", b + ("jobs", 0, "run_id"), 100000),
        (
            "jobs/duplicate_cohort",
            b + ("jobs", 1, "cohort_key"),
            "proof/linux/python/0",
        ),
        ("security/authority_transfer", ("authority_transfer",), True),
        ("security/security_waiver", ("security_waiver",), True),
        ("security/admission_claim", ("admission",), "PASS"),
        ("security/forged_root_credit", b + ("root_closure_credit",), 1),
        ("security/forged_approval", b + ("independent_review",), "APPROVED"),
        (
            "security/forged_coverage_credit",
            b + ("coverage", "statement", "governed_merge_credit"),
            1,
        ),
    ]
    return [
        (name, (lambda p, path=path, val=val: mutate_path(p, path, val)))
        for name, path, val in out
    ]


def valid_cases():
    """Distinct labelled legitimate inputs; rejection is a false positive."""
    actions = [
        ("zero_jobs", lambda p: [x.update(jobs=[]) for x in p["observations"]]),
        (
            "one_job",
            lambda p: [x.update(jobs=x["jobs"][:1]) for x in p["observations"]],
        ),
        (
            "four_jobs",
            lambda p: [x.update(jobs=x["jobs"][:4]) for x in p["observations"]],
        ),
        (
            "no_coverage",
            lambda p: [
                x.update(coverage={"statement": None, "branch": None, "diff": None})
                for x in p["observations"]
            ],
        ),
        (
            "zero_coverage",
            lambda p: [
                x["coverage"]["statement"].update(covered=0) for x in p["observations"]
            ],
        ),
        (
            "declining_coverage",
            lambda p: p["observations"][1]["coverage"]["statement"].update(covered=20),
        ),
        (
            "diff_coverage",
            lambda p: [
                x["coverage"].update(diff=coverage(x["main_sha"], 3, 10))
                for x in p["observations"]
            ],
        ),
        (
            "same_fingerprint",
            lambda p: p["observations"][1].update(first_red_fingerprints=[SHA_C]),
        ),
        (
            "no_reds",
            lambda p: [x.update(first_red_fingerprints=[]) for x in p["observations"]],
        ),
        ("no_roots", lambda p: [x.update(roots={}) for x in p["observations"]]),
        ("benign_metadata", lambda p: p.update(note="synthetic-input-only")),
        (
            "timezone_offset",
            lambda p: p["observations"][1].update(
                captured_at="2026-10-18T12:40:00+02:00"
            ),
        ),
        (
            "source_reported_claim",
            lambda p: p["observations"][1]["roots"].update({SHA_C: "CLOSURE_CLAIMED"}),
        ),
        (
            "unicode_cohort",
            lambda p: [
                x["jobs"][0].update(cohort_key="pressure/euro-a9")
                for x in p["observations"]
            ],
        ),
        (
            "python_html_cohort",
            lambda p: [
                x["jobs"][0].update(cohort_key="<script>alert(1)</script>")
                for x in p["observations"]
            ],
        ),
        (
            "reverse_job_order",
            lambda p: [x["jobs"].reverse() for x in p["observations"]],
        ),
    ]
    for status in ("queued", "pending", "waiting", "requested"):
        actions.append(
            (
                "nonterminal_" + status,
                lambda p, s=status: [
                    x["jobs"][0].update(
                        status=s, conclusion=None, started_at=None, completed_at=None
                    )
                    for x in p["observations"]
                ],
            )
        )
    actions.append(
        (
            "nonterminal_in_progress",
            lambda p: [
                x["jobs"][0].update(
                    status="in_progress", conclusion=None, completed_at=None
                )
                for x in p["observations"]
            ],
        )
    )
    for conclusion in ("skipped", "cancelled"):
        actions.append(
            (
                "terminal_" + conclusion,
                lambda p, c=conclusion: [
                    x["jobs"][0].update(
                        conclusion=c, started_at=None, completed_at=None
                    )
                    for x in p["observations"]
                ],
            )
        )
    return actions


def calibrate():
    """Synthetic confusion matrix. Positive=must reject a labelled invalid input."""
    counts = {"TP": 0, "FP": 0, "TN": 0, "FN": 0, "UNHANDLED": 0}
    examples = {k: [] for k in counts}
    for name, change in adversarial_cases():
        item = fixture()
        change(item)
        try:
            SUBJECT.compare(item)
        except ValueError:
            label = "TP"
        except Exception as exc:  # unhandled exceptions are protocol defects
            label = "UNHANDLED"
            name += ":" + type(exc).__name__
        else:
            label = "FN"
        counts[label] += 1
        examples[label].append(name)
    for name, change in valid_cases():
        item = fixture()
        change(item)
        try:
            SUBJECT.compare(item)
        except Exception as exc:
            label = "FP"
            name += ":" + type(exc).__name__
        else:
            label = "TN"
        counts[label] += 1
        examples[label].append(name)
    return counts, examples


class G3CSAssuranceMatrix(unittest.TestCase):
    def test_synthetic_confusion_matrix_no_escaped_invalids_or_rejected_valids(self):
        counts, examples = calibrate()
        self.assertEqual(
            counts["FN"], 0, "Invalid evidence accepted: " + repr(examples["FN"])
        )
        self.assertEqual(
            counts["FP"], 0, "Valid evidence rejected: " + repr(examples["FP"])
        )
        self.assertEqual(
            counts["UNHANDLED"],
            0,
            "Unclassified exception: " + repr(examples["UNHANDLED"]),
        )
        self.assertGreaterEqual(counts["TP"], 65)
        self.assertGreaterEqual(counts["TN"], 20)

    def test_reverse_coverage_delta(self):
        first = SUBJECT.compare(fixture())["coverage"]["statement"]["delta_pp"]
        payload = fixture()
        payload["observations"][0]["coverage"]["statement"]["covered"] = 70
        payload["observations"][1]["coverage"]["statement"]["covered"] = 60
        self.assertEqual(
            SUBJECT.compare(payload)["coverage"]["statement"]["delta_pp"], -first
        )

    def test_cross_clock_reversal_does_not_award_root_closure(self):
        p = fixture()
        p["observations"][0]["first_red_fingerprints"] = [SHA_D]
        p["observations"][1]["first_red_fingerprints"] = [SHA_C]
        out = SUBJECT.compare(p)
        self.assertEqual(out["first_reds"]["nonreproduced_candidates"], [SHA_D])
        self.assertEqual(out["first_reds"]["new"], [SHA_C])
        self.assertEqual(out["first_reds"]["closure_credit"], 0)
        self.assertIsNone(out["roots"]["verified_closed"])

    def test_job_permutation_metamorphic(self):
        p = fixture()
        original = SUBJECT.compare(p)
        rand = random.Random(7331)
        for observation in p["observations"]:
            rand.shuffle(observation["jobs"])
        self.assertEqual(SUBJECT.compare(p), original)

    def test_first_red_order_permutation_metamorphic(self):
        p = fixture()
        for observation in p["observations"]:
            observation["first_red_fingerprints"] = [SHA_C, SHA_D]
        before = SUBJECT.compare(p)
        for observation in p["observations"]:
            observation["first_red_fingerprints"].reverse()
        self.assertEqual(SUBJECT.compare(p), before)

    def test_input_immutability(self):
        p = fixture()
        baseline = copy.deepcopy(p)
        SUBJECT.compare(p)
        self.assertEqual(p, baseline)

    def test_delta_monotone_under_eligible_numerator_increase(self):
        p = fixture()
        values = []
        for n in range(0, 101, 5):
            p["observations"][1]["coverage"]["statement"]["covered"] = n
            values.append(SUBJECT.compare(p)["coverage"]["statement"]["delta_pp"])
        self.assertEqual(values, sorted(values))
        self.assertEqual(values[-1] - values[0], 100)

    def test_no_loss_of_unreported_coverage(self):
        p = fixture()
        p["observations"][1]["coverage"]["statement"] = None
        out = SUBJECT.compare(p)
        self.assertEqual(out["coverage"]["statement"]["status"], "UNKNOWN")
        self.assertIsNone(out["coverage"]["statement"]["delta_pp"])

    def test_scope_drift_blocks_positive_and_negative_delta(self):
        for numerator in (0, 100):
            p = fixture()
            p["observations"][1]["coverage"]["statement"].update(
                covered=numerator, scope_sha256=SHA_C
            )
            out = SUBJECT.compare(p)
            self.assertEqual(out["coverage"]["statement"]["status"], "NONCOMPARABLE")
            self.assertIsNone(out["coverage"]["statement"]["delta_pp"])

    def test_conclusion_is_not_workflow_admission(self):
        p = fixture()
        for x in p["observations"]:
            x["jobs"][0]["conclusion"] = "failure"
        out = SUBJECT.compare(p)
        self.assertEqual(out["admission"], "HOLD")
        self.assertEqual(
            out["evidence_level"], "SOURCE_REPORTED_NOT_INDEPENDENTLY_VERIFIED"
        )
        self.assertFalse(out["authority_transfer"])
        self.assertEqual(out["telemetry"]["matched_terminal_jobs"], 5)

    def test_source_reported_root_claim_is_never_formally_closed(self):
        p = fixture()
        p["observations"][1]["roots"][SHA_C] = "CLOSURE_CLAIMED"
        out = SUBJECT.compare(p)
        self.assertIsNone(out["roots"]["verified_closed"])
        self.assertEqual(out["first_reds"]["closure_credit"], 0)
        self.assertEqual(out["statistics"]["six_sigma"], None)

    def test_descriptive_p95_threshold_four_versus_five(self):
        p = fixture()
        for x in p["observations"]:
            x["jobs"] = x["jobs"][:4]
        self.assertIsNone(SUBJECT.compare(p)["telemetry"]["queue_p95_before_seconds"])
        for x in p["observations"]:
            x["jobs"].append(
                observation(x["main_sha"], x["captured_at"], count=5)["jobs"][-1]
            )
        self.assertEqual(SUBJECT.compare(p)["telemetry"]["queue_p95_before_seconds"], 7)

    def test_descriptive_p95_interpolation(self):
        self.assertIsNone(SUBJECT.percentile95([]))
        self.assertIsNone(SUBJECT.percentile95([1, 2, 3, 4]))
        self.assertEqual(SUBJECT.percentile95([1, 2, 3, 4, 10]), 8.8)
        self.assertEqual(SUBJECT.percentile95([10, 4, 3, 2, 1]), 8.8)

    def test_high_cardinality_stress_512_jobs_each_main(self):
        p = fixture(count=512)
        out = SUBJECT.compare(p)
        self.assertEqual(out["telemetry"]["matched_terminal_jobs"], 512)
        self.assertEqual(out["telemetry"]["execution_p95_before_seconds"], 11)
        self.assertEqual(out["coverage"]["statement"]["delta_pp"], 10)
        self.assertEqual(out["admission"], "HOLD")

    def test_stress_one_environment_drift_does_not_poison_other_cohorts(self):
        p = fixture(count=512)
        p["observations"][1]["jobs"][511]["environment_sha256"] = SHA_C
        out = SUBJECT.compare(p)["telemetry"]
        self.assertEqual(out["matched_terminal_jobs"], 511)
        self.assertEqual(out["environment_mismatched_jobs"], ["proof/linux/python/511"])

    def test_stress_determinism_under_seeded_permutation(self):
        p = fixture(count=128)
        before = SUBJECT.compare(p)
        seeded = random.Random(61888)
        for x in p["observations"]:
            seeded.shuffle(x["jobs"])
        self.assertEqual(before, SUBJECT.compare(p))

    def test_security_json_strings_remain_data(self):
        p = fixture()
        for x in p["observations"]:
            x["jobs"][0]["cohort_key"] = "<script>panic</script>&amp;"
            x["jobs"][0]["environment_sha256"] = SHA_C
        report = SUBJECT.compare(p)
        serialized = json.dumps(report, sort_keys=True, allow_nan=False)
        self.assertNotIn("<script>panic</script>", serialized)
        self.assertEqual(report["admission"], "HOLD")
        self.assertEqual(report["telemetry"]["environment_mismatched_jobs"], [])

    def test_cli_writes_claimed_source_report_without_authentication(self):
        with tempfile.TemporaryDirectory() as d:
            inp = Path(d) / "in.json"
            out = Path(d) / "nested/out.json"
            inp.write_text(json.dumps(fixture()), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--input",
                    str(inp),
                    "--output",
                    str(out),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(
                report["lineage"]["edge_type"],
                "MAIN_PARENT_CLAIM_NOT_INDEPENDENTLY_AUTHENTICATED",
            )
            self.assertEqual(report["admission"], "HOLD")

    def test_cli_invalid_source_no_receipt_written(self):
        with tempfile.TemporaryDirectory() as d:
            inp = Path(d) / "in.json"
            out = Path(d) / "out.json"
            p = fixture()
            p["receipt_authentication"] = "VERIFIED"
            inp.write_text(json.dumps(p), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--input",
                    str(inp),
                    "--output",
                    str(out),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(out.exists())

    def test_cli_main_entrypoint_direct_coverage_and_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            inp = Path(d) / "input.json"
            out = Path(d) / "artifacts/report.json"
            inp.write_text(json.dumps(fixture()), encoding="utf-8")
            with patch.object(
                sys,
                "argv",
                [str(MODULE_PATH), "--input", str(inp), "--output", str(out)],
            ):
                with redirect_stdout(StringIO()) as stream:
                    runpy.run_path(str(MODULE_PATH), run_name="__main__")
            self.assertIn("ADMISSION HOLD", stream.getvalue())
            self.assertEqual(json.loads(out.read_text())["admission"], "HOLD")

    def test_cli_malformed_json_no_receipt_written(self):
        with tempfile.TemporaryDirectory() as d:
            inp = Path(d) / "in.json"
            out = Path(d) / "out.json"
            inp.write_text("{not-valid-json", encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--input",
                    str(inp),
                    "--output",
                    str(out),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
