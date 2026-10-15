"""Native metric ingestion safety and UNKNOWN preservation."""

import importlib.util
import unittest
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "scripts/mip_native_metric_ingest.py"
spec = importlib.util.spec_from_file_location("mip_ingest", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def payload(rows):
    return {"schema": "mip.native.metric.receipts.v1", "receipts": rows}


def row(family="coverage", metric="statement_coverage", **changes):
    v = {
        "family": family,
        "metric": metric,
        "repository": "GBOGEB/ABACUS",
        "exact_sha": "a" * 40,
        "run_id": 1,
        "job_id": 2,
        "observed_at": "2026-10-14T20:00:00Z",
        "status": "PASS",
        "evidence_url": "https://github.com/GBOGEB/ABACUS/actions/runs/1",
        "numerator": 2,
        "denominator": 4,
        "verified_native": True,
    }
    v.update(changes)
    return v


class NativeIngestTests(unittest.TestCase):
    def test_verified_coverage(self):
        result = mod.convert(payload([row()]))
        self.assertEqual((2, 4), (result[0]["numerator"], result[0]["denominator"]))
        self.assertEqual("NATIVE", result[0]["collection_quality"])

    def test_unknown_preserved(self):
        result = mod.convert(
            payload([row(numerator=None, denominator=None, verified_native=False)])
        )
        self.assertEqual("UNKNOWN", result[0]["status"])
        self.assertIsNone(result[0]["numerator"])

    def test_fake_native_rejected(self):
        with self.assertRaises(ValueError):
            mod.convert(payload([row(verified_native=False)]))

    def test_proposals_not_credited(self):
        self.assertEqual([], mod.convert(payload([row(proposal_only=True)])))

    def test_bd_needs_fingerprint(self):
        with self.assertRaises(ValueError):
            mod.convert(payload([row("bd_burndown", "root_transitions")]))

    def test_valid_attributed_session(self):
        result = mod.convert(
            payload(
                [
                    row(
                        "debug_ldab",
                        "attributed_session_rate",
                        root_fingerprint="b" * 64,
                    )
                ]
            )
        )
        self.assertEqual("NATIVE", result[0]["collection_quality"])

    def test_denominator_rejected(self):
        with self.assertRaises(ValueError):
            mod.convert(payload([row(denominator=0)]))


if __name__ == "__main__":
    unittest.main()
