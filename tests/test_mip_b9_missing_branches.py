"""B9 focused coverage for MIP statistical CLI and fail-closed malformed inputs."""

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stat = load("mip_stat_b9", "scripts/mip_statistical_readiness.py")
native = load("mip_native_b9", "scripts/mip_native_metric_ingest.py")
unknown = load("mip_unknown_b9", "scripts/code_purple_mip_unknown_rollup.py")


def stat_row():
    return {
        "schema": "mip.stat.observation.v1",
        "repository": "GBOGEB/ABACUS",
        "family": "ci_reliability",
        "metric": "workflow_failure_rate",
        "metric_version": "1.0",
        "exact_sha": "a" * 40,
        "run_id": 100,
        "job_id": 101,
        "observed_at": "2026-10-14T20:00:00Z",
        "evidence_url": "https://github.com/GBOGEB/ABACUS/actions/runs/100",
        "collection_quality": "NATIVE",
        "status": "PASS",
        "numerator": 0,
        "denominator": 1,
    }


def native_row(**changes):
    r = dict(
        stat_row(), family="coverage", metric="statement_coverage", verified_native=True
    )
    r.update(changes)
    return r


def native_payload(rows):
    return {"schema": "mip.native.metric.receipts.v1", "receipts": rows}


class B9MissingBranches(unittest.TestCase):
    def test_stat_schema_and_provenance_rejections(self):
        row = stat_row
        bad = (
            {"schema": "other"},
            {"repository": "other"},
            {"metric": ""},
            {"evidence_url": "https://invalid"},
            {"collection_quality": "FAKE"},
            {"exact_sha": "bad"},
            {"run_id": "1"},
            {"job_id": 0},
            {"observed_at": "no"},
            {"status": "BROKEN"},
            {"numerator": None, "denominator": 1},
            {"numerator": -1},
            {"numerator": 2},
            {"denominator": 0},
            {"status": "UNKNOWN"},
            {"collection_quality": "UNVERIFIED"},
        )
        for change in bad:
            with self.subTest(change=change):
                with self.assertRaises((ValueError, TypeError)):
                    stat.check(dict(row(), **change))

    def test_malformed_thresholds_and_rows(self):
        with self.assertRaises(ValueError):
            stat.evaluate([], minimum=4)
        with self.assertRaises(ValueError):
            stat.evaluate([], holdout=1)
        with self.assertRaises(ValueError):
            stat.evaluate([None])

    def test_native_ingestion_rejects_unknown_schema_and_rows(self):
        for data in (
            None,
            {},
            {"schema": "incorrect", "receipts": []},
            {"schema": "mip.native.metric.receipts.v1", "receipts": {}},
            {"schema": "mip.native.metric.receipts.v1", "receipts": [None]},
            {
                "schema": "mip.native.metric.receipts.v1",
                "receipts": [{"family": "other", "metric": "wrong"}],
            },
        ):
            with self.subTest(data=data), self.assertRaises(ValueError):
                native.convert(data)

    def test_native_ingestion_rejects_partial_counts(self):
        row, payload = native_row, native_payload
        for change in (
            {"numerator": None},
            {"denominator": None},
            {"numerator": -1},
            {"numerator": 5},
            {"numerator": True},
            {"denominator": 0},
            {"verified_native": False},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                native.convert(payload([row(**change)]))

    def test_unknown_rollup_rejects_invalid_contracts(self):
        data = json.loads((ROOT / "MIP/code_purple_unknown_backlog.json").read_text())
        changes = (("schema", "invalid"), ("items", []))
        for key, value in changes:
            with self.subTest(key=key), self.assertRaises(ValueError):
                unknown.rollup(dict(data, **{key: value}), "2026-10-14")
        for change in (
            {"dmaic_phase": "BAD"},
            {"owner": ""},
            {"acceptance_target": ""},
            {"age": None},
            {"evidence_state": "BAD"},
        ):
            cloned = copy.deepcopy(data)
            cloned["items"][0].update(change)
            with (
                self.subTest(change=change),
                self.assertRaises((ValueError, TypeError)),
            ):
                unknown.rollup(cloned, "2026-10-14")

    def test_stat_cli_writes_readiness_file(self):
        from tests.test_mip_statistical_readiness import row

        with tempfile.TemporaryDirectory() as td:
            input_file = Path(td) / "in.jsonl"
            output_file = Path(td) / "out" / "readiness.json"
            input_file.write_text(json.dumps(row()) + "\n")
            with patch.object(
                sys,
                "argv",
                ["stat", "--input", str(input_file), "--output", str(output_file)],
            ):
                stat.main()
            result = json.loads(output_file.read_text())
            self.assertEqual("HOLD", result["merge_admission"])

    def test_ingest_cli_writes_native_jsonl(self):
        payload, row = native_payload, native_row
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "native.json"
            output = Path(td) / "out" / "receipts.jsonl"
            source.write_text(json.dumps(payload([row()])))
            with patch.object(
                sys, "argv", ["ingest", "--input", str(source), "--output", str(output)]
            ):
                native.main()
            self.assertEqual(1, len(output.read_text().splitlines()))


if __name__ == "__main__":
    unittest.main()
