"""Source-bound BD/LDAB import into EVERRED without causal/admission promotion."""

import datetime as dt
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from ingest_bd_ldab_join import to_event

from everred import InvalidEvidence, validate_event
from joined_census import join

SHA = "a" * 40
REPO = "GBOGEB/ABACUS"
RUN = 38565161511
JOB = 115855865882
URL = f"https://github.com/{REPO}/actions/runs/{RUN}"


def fixture():
    return {
        "schema": "bd.ldab.joined.census.v1",
        "scope": {
            "repository": REPO,
            "head_sha": SHA,
            "run_id": RUN,
            "job_id": JOB,
            "evidence_url": URL,
        },
        "metrics": {
            "full_bandit_unique": 2,
            "debug_receipts": 1,
            "comparable_delta": None,
        },
        "roots": [
            {"root_id": "BD-old-fingerprint"},
            {"root_id": "CI-unconfirmed"},
        ],
        "unlinked_debug_receipts": [{}],
        "merge_admission": "HOLD",
        "authority_transfer": False,
        "security_waiver": False,
    }


class BridgeBindingTests(unittest.TestCase):
    def test_valid_receipt_has_exact_source_binding_and_utc_ingestion_time(self):
        e = to_event(fixture())
        validate_event(e)
        self.assertEqual(e["sha"], SHA)
        self.assertEqual(
            e["evidence"]["source_binding"],
            {
                "repository": REPO,
                "source_sha": SHA,
                "run_id": RUN,
                "job_id": JOB,
                "run_url": URL,
            },
        )
        stamp = dt.datetime.fromisoformat(e["occurred_at"])
        self.assertIsNotNone(stamp.utcoffset())
        self.assertEqual(stamp.utcoffset(), dt.timedelta(0))
        self.assertEqual(e["evidence"]["ingested_at"], e["occurred_at"])

    def test_bridged_census_participates_in_exact_run_without_promoting_roots(self):
        e = to_event(fixture())
        report = join([e])
        self.assertEqual(report["run_group_count"], 1)
        self.assertEqual(report["source_bound_events"], 1)
        g = report["run_groups"][0]
        self.assertEqual((g["repo"], g["sha"], g["run_id"]), (REPO, SHA, RUN))
        self.assertEqual(g["job_ids"], [JOB])
        self.assertEqual(g["unverified_entries"], 1)
        self.assertEqual(len(g["bd_ldab"]), 1)
        self.assertEqual(g["bd_ldab"][0]["join_groups"], 2)
        self.assertEqual(g["bd_ldab"][0]["fingerprint_observations"], 2)
        self.assertEqual(g["bd_ldab"][0]["trust"], "MANUAL_UNVERIFIED")
        self.assertEqual(g["bd_ldab"][0]["root_causality"], "UNCONFIRMED")
        self.assertIsNone(g["confirmed_unique_roots"])
        self.assertIsNone(g["security_burndown"])
        self.assertIsNone(g["worker_sessions_verified"])
        self.assertEqual(report["global_merge_admission"], "HOLD")
        self.assertIs(report["security_waiver"], False)
        self.assertIs(report["authority_transfer"], False)

    def test_import_id_remains_stable_across_ingestion_timestamps(self):
        self.assertEqual(to_event(fixture())["id"], to_event(fixture())["id"])

    def test_join_rejects_imported_scope_mismatch(self):
        e = to_event(fixture())
        e["evidence"]["source_binding"]["source_sha"] = "b" * 40
        with self.assertRaisesRegex(InvalidEvidence, "source/census mismatch"):
            join([e])

    def test_import_cannot_be_treated_as_a_worker_or_a_code_review(self):
        g = join([to_event(fixture())])["run_groups"][0]
        self.assertEqual(g["verification"], [])
        self.assertEqual(g["runtime"], [])
        self.assertEqual(g["first_red_count"], 0)

    def test_missing_positive_run_and_job_ids_are_refused(self):
        for field in ("run_id", "job_id"):
            for value in (0, -1, False, None):
                with self.subTest(field=field, value=value):
                    obj = fixture()
                    obj["scope"][field] = value
                    with self.assertRaises(InvalidEvidence):
                        to_event(obj)

    def test_alias_root_ids_do_not_create_confirmed_causal_roots(self):
        obj = fixture()
        obj["roots"] = [{"root_id": "BD-candidate"}]
        g = join([to_event(obj)])["run_groups"][0]
        self.assertIsNone(g["confirmed_unique_roots"])
        self.assertEqual(g["bd_ldab"][0]["join_groups"], 1)


if __name__ == "__main__":
    unittest.main()
