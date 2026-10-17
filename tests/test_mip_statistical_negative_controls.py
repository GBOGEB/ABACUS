"""Negative controls for MIP statistical observation admission."""

import importlib.util
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "scripts/mip_statistical_readiness.py"
SPEC = importlib.util.spec_from_file_location("mip_statistical_readiness_extra", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def observation():
    return {
        "schema": "mip.stat.observation.v1",
        "repository": "GBOGEB/ABACUS",
        "family": "coverage",
        "metric": "covered_statements",
        "metric_version": "1",
        "exact_sha": "a" * 40,
        "run_id": 123,
        "job_id": 456,
        "observed_at": "2026-10-15T07:00:00Z",
        "evidence_url": "https://github.com/GBOGEB/ABACUS/actions/runs/123",
        "collection_quality": "NATIVE",
        "status": "PASS",
        "numerator": 3,
        "denominator": 4,
    }


class AdditionalReceiptNegativeControls(unittest.TestCase):
    def test_invalid_identity_and_schema_fail_closed(self):
        mutations = [
            ("schema", "untrusted"),
            ("repository", "other/repo"),
            ("family", "nonexistent"),
            ("exact_sha", "z" * 40),
            ("exact_sha", "a" * 39),
            ("run_id", 0),
            ("job_id", -1),
            ("run_id", True),
            ("job_id", "456"),
        ]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                record = observation()
                record[field] = value
                with self.assertRaises(ValueError):
                    MODULE.check(record)

    def test_invalid_counts_fail_closed(self):
        mutations = [
            (None, 4),
            (3, None),
            (-1, 4),
            (5, 4),
            (0, 0),
            (True, 4),
            (3, 4.0),
        ]
        for numerator, denominator in mutations:
            with self.subTest(numerator=numerator, denominator=denominator):
                record = observation()
                record["numerator"] = numerator
                record["denominator"] = denominator
                with self.assertRaises(ValueError):
                    MODULE.check(record)

    def test_missing_metadata_and_bad_timestamp_fail_closed(self):
        for field in ("metric", "metric_version", "evidence_url", "collection_quality"):
            with self.subTest(field=field):
                record = observation()
                record[field] = ""
                with self.assertRaises(ValueError):
                    MODULE.check(record)
        for timestamp in ("2026-10-15T07:00:00+00:00", "not-a-timeZ"):
            with self.subTest(timestamp=timestamp):
                record = observation()
                record["observed_at"] = timestamp
                with self.assertRaises(ValueError):
                    MODULE.check(record)

    def test_unknown_and_unverified_numeric_receipts_fail_closed(self):
        for status, quality in (
            ("UNKNOWN", "NATIVE"),
            ("PASS", "UNVERIFIED"),
            ("PASS", "INCOMPLETE"),
        ):
            with self.subTest(status=status, quality=quality):
                record = observation()
                record["status"] = status
                record["collection_quality"] = quality
                with self.assertRaises(ValueError):
                    MODULE.check(record)

    def test_invalid_thresholds_fail_closed(self):
        for minimum, holdout in ((4, 5), (20, 1)):
            with self.subTest(minimum=minimum, holdout=holdout):
                with self.assertRaises(ValueError):
                    MODULE.evaluate([], minimum=minimum, holdout=holdout)

    def test_accepted_receipt_does_not_grant_merge_authority(self):
        result = MODULE.evaluate([observation()])
        self.assertEqual("HOLD", result["merge_admission"])
        self.assertFalse(result["authority_transfer"])
        self.assertEqual(1, result["series"][0]["native_marked_records"])
        self.assertFalse(result["series"][0]["PROCESS_STABLE"])


class NativeSnapshotAndTelemetryControls(unittest.TestCase):
    def receipt(self):
        r = observation()
        r.update(
            family="ci_reliability",
            metric="workflow_failure_rate",
            numerator=0,
            denominator=1,
        )
        return r

    def snapshot(self, r):
        return {
            "schema": "mip.github.snapshot.v1",
            "runs": [
                {
                    "id": r["run_id"],
                    "head_sha": r["exact_sha"],
                    "html_url": r["evidence_url"],
                    "repository": {"full_name": r["repository"]},
                    "run_attempt": 1,
                    "status": "completed",
                    "conclusion": "success",
                    "updated_at": r["observed_at"],
                    "path": ".github/workflows/test.yml",
                }
            ],
            "jobs": [
                {
                    "id": r["job_id"],
                    "run_id": r["run_id"],
                    "head_sha": r["exact_sha"],
                    "run_attempt": 1,
                    "status": "completed",
                    "completed_at": r["observed_at"],
                }
            ],
        }

    def test_native_label_alone_cannot_pass_m1(self):
        x = MODULE.evaluate([self.receipt()])["series"][0]
        self.assertTrue(x["STRUCTURE_VALID"])
        self.assertFalse(x["MEASUREMENT_VALID"])
        self.assertEqual("HOLD", x["M1_DECISION"])
        self.assertIsNone(x["independent_runs"])
        self.assertEqual(1, x["distinct_runs"])

    def test_matching_snapshot_only_validates_selected_receipts(self):
        r = self.receipt()
        x = MODULE.evaluate([r], native_evidence=self.snapshot(r))["series"][0]
        self.assertTrue(x["MEASUREMENT_VALID"])
        self.assertEqual(1, x["native_snapshot_matches"])
        self.assertEqual("SELECTED_RECEIPTS_ONLY", x["measurement_scope"])
        self.assertEqual("UNKNOWN", x["comparability"])
        self.assertEqual("HOLD", x["PROCESS_SERIES_DECISION"])
        for gate in (
            "STABILITY_ASSESSABLE",
            "PROCESS_STABLE",
            "CAPABILITY_ASSESSABLE",
            "BACKTEST_ELIGIBLE",
        ):
            self.assertFalse(x[gate])

    def test_false_native_provenance_never_matches(self):
        r = self.receipt()
        for collection, field, value in (
            ("runs", "head_sha", "b" * 40),
            ("jobs", "head_sha", "b" * 40),
            ("jobs", "run_id", 999),
            ("jobs", "run_attempt", 2),
            ("jobs", "run_attempt", True),
            ("runs", "run_attempt", True),
            ("runs", "run_attempt", 0),
            ("runs", "status", "in_progress"),
            ("jobs", "status", "queued"),
            ("runs", "conclusion", "failure"),
            ("runs", "html_url", "https://example.com"),
            ("runs", "repository", None),
            ("runs", "repository", {"full_name": "other/repo"}),
            ("runs", "updated_at", "2026-10-16T07:00:00Z"),
            ("jobs", "completed_at", "2026-10-16T07:00:00Z"),
            ("jobs", "completed_at", None),
            ("jobs", "completed_at", "bad"),
            ("jobs", "completed_at", "badZ"),
            ("runs", "path", None),
            ("runs", "path", "other.yml"),
        ):
            with self.subTest(collection=collection, field=field, value=value):
                evidence = self.snapshot(r)
                evidence[collection][0][field] = value
                self.assertFalse(MODULE.match_native(r, evidence))

    def test_failed_workflow_uses_workflow_not_anchor_job_conclusion(self):
        r = self.receipt()
        r.update(status="FAIL", numerator=1)
        evidence = self.snapshot(r)
        evidence["runs"][0]["conclusion"] = "failure"
        evidence["jobs"][0]["conclusion"] = "success"
        self.assertTrue(MODULE.match_native(r, evidence))

    def test_missing_or_wrong_metric_evidence_stays_unmatched(self):
        r = self.receipt()
        for key in ("runs", "jobs"):
            evidence = self.snapshot(r)
            evidence[key] = []
            self.assertFalse(MODULE.match_native(r, evidence))
        self.assertFalse(
            MODULE.match_native(observation(), self.snapshot(observation()))
        )
        r["status"] = "UNKNOWN"
        self.assertFalse(MODULE.match_native(r, self.snapshot(r)))

    def test_malformed_snapshot_rejected(self):
        r = self.receipt()
        for evidence in (
            [],
            {},
            {"schema": "mip.github.snapshot.v1", "runs": {}, "jobs": []},
        ):
            with self.subTest(evidence=evidence), self.assertRaises(ValueError):
                MODULE.match_native(r, evidence)
        for key in ("runs", "jobs"):
            for value in ([None], [{"id": True}], [{"id": 1}, {"id": 1}]):
                evidence = self.snapshot(r)
                evidence[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    MODULE.match_native(r, evidence)

    def test_same_repository_wrong_run_url_rejected(self):
        r = self.receipt()
        for suffix in ("124", "123?other=1", "123/jobs/456"):
            r["evidence_url"] = (
                "https://github.com/GBOGEB/ABACUS/actions/runs/" + suffix
            )
            with self.subTest(suffix=suffix), self.assertRaisesRegex(
                ValueError, "run identity"
            ):
                MODULE.check(r)

    def test_binary_workflow_count_must_match_outcome(self):
        for status, n, d in (("PASS", 1, 1), ("FAIL", 0, 1), ("FAIL", 1, 2)):
            r = self.receipt()
            r.update(status=status, numerator=n, denominator=d)
            with self.subTest(status=status, n=n, d=d), self.assertRaisesRegex(
                ValueError, "outcome/count"
            ):
                MODULE.check(r)

    def test_conflicting_sha_and_job_rebinding_rejected(self):
        a = self.receipt()
        b = dict(a, exact_sha="b" * 40)
        with self.assertRaisesRegex(ValueError, "conflicting native"):
            MODULE.evaluate([a, b])
        b = dict(
            a,
            run_id=124,
            evidence_url="https://github.com/GBOGEB/ABACUS/actions/runs/124",
        )
        with self.assertRaisesRegex(ValueError, "conflicting native"):
            MODULE.evaluate([a, b])

    def test_unknown_counts_and_families_are_explicit(self):
        r = self.receipt()
        r.update(status="UNKNOWN", numerator=None, denominator=None)
        result = MODULE.evaluate([r])
        self.assertEqual(
            {"PASS": 0, "FAIL": 0, "UNKNOWN": 1}, result["series"][0]["status_counts"]
        )
        self.assertEqual(6, list(result["family_states"].values()).count("UNKNOWN"))
        self.assertEqual(0, result["series"][0]["native_snapshot_matches"])

    def test_invalid_schema_quality_and_status_rejected(self):
        for value in (
            None,
            [],
            dict(self.receipt(), collection_quality="FAKE"),
            dict(self.receipt(), status="bad"),
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                MODULE.check(value)

    def test_long_varying_history_only_emits_diagnostic_statistics(self):
        rows = []
        for i in range(1, 31):
            r = self.receipt()
            r.update(
                run_id=i,
                job_id=i + 1000,
                evidence_url=f"https://github.com/GBOGEB/ABACUS/actions/runs/{i}",
                observed_at=f"2026-10-{i:02d}T07:00:00Z",
                numerator=i % 2,
                status="FAIL" if i % 2 else "PASS",
            )
            rows.append(r)
        x = MODULE.evaluate(rows)["series"][0]
        self.assertIsNotNone(x["lag1_autocorrelation"])
        self.assertFalse(x["STABILITY_ASSESSABLE"])
        self.assertFalse(x["BACKTEST_ELIGIBLE"])
        self.assertEqual(1, x["distinct_source_shas"])
        self.assertEqual(30, x["distinct_runs"])

    def test_cli_hashes_inputs_and_keeps_missing_evidence_explicit(self):
        import hashlib
        import json
        import subprocess
        import sys
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "rows.jsonl"
            evidence = Path(td) / "snapshot.json"
            output = Path(td) / "nested" / "out.json"
            r = self.receipt()
            source.write_text(json.dumps(r) + "\n\n", encoding="utf-8")
            evidence.write_text(json.dumps(self.snapshot(r)), encoding="utf-8")
            for extra in ([], ["--native-evidence", str(evidence)]):
                subprocess.run(
                    [
                        sys.executable,
                        str(SOURCE),
                        "--input",
                        str(source),
                        "--output",
                        str(output),
                    ]
                    + extra,
                    check=True,
                )
                result = json.loads(output.read_text())
                self.assertEqual(
                    hashlib.sha256(source.read_bytes()).hexdigest(),
                    result["input_sha256"],
                )
                expected = (
                    hashlib.sha256(evidence.read_bytes()).hexdigest() if extra else None
                )
                self.assertEqual(expected, result["native_evidence_sha256"])
                self.assertEqual(bool(extra), result["series"][0]["MEASUREMENT_VALID"])

    def test_cli_entrypoint_in_process(self):
        import json
        import runpy
        import sys
        import tempfile
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "rows.jsonl"
            output = Path(td) / "out.json"
            evidence = Path(td) / "snapshot.json"
            r = self.receipt()
            source.write_text(json.dumps(r) + "\n\n", encoding="utf-8")
            evidence.write_text(json.dumps(self.snapshot(r)), encoding="utf-8")
            for extra in ([], ["--native-evidence", str(evidence)]):
                with patch.object(
                    sys,
                    "argv",
                    [str(SOURCE), "--input", str(source), "--output", str(output)]
                    + extra,
                ):
                    runpy.run_path(str(SOURCE), run_name="__main__")
                self.assertEqual(
                    "HOLD", json.loads(output.read_text())["merge_admission"]
                )

    def test_multiple_metric_families_remain_disjoint(self):
        result = MODULE.evaluate([self.receipt(), observation()])
        self.assertEqual(
            ["ci_reliability", "coverage"], [x["family"] for x in result["series"]]
        )
        self.assertEqual(5, len(result["missing_families"]))
        self.assertTrue(all(x["independent_runs"] is None for x in result["series"]))


if __name__ == "__main__":
    unittest.main()
