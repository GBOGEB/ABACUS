import unittest

from mission_control_lite.rex import build_index, fingerprint, wave_delta


class TestRexWave(unittest.TestCase):
    def setUp(self):
        self.event = {
            "event_id": "e1",
            "repository": "GBOGEB/ABACUS",
            "source_sha": "a" * 40,
            "run_id": 12,
            "job_id": 34,
            "topic_id": "PYTHON.SQLITE.WINDOWS.FILE_LOCK",
            "fingerprint": fingerprint(
                "GBOGEB/ABACUS",
                "pytest",
                "WinError32",
                "mission_control_lite/core.py",
                "sqlite lock",
            ),
            "manifestation": "WinError 32",
            "root_candidate_id": "r1",
        }
        self.root = {
            "root_id": "r1",
            "rex_id": "rex1",
            "hypothesis": "sqlite context does not close handle",
        }
        self.rex = {
            "rex_id": "rex1",
            "repair": "contextlib.closing",
            "verification": "native Windows Python 3.11/3.12",
        }

    def test_index_links_without_promoting_authority(self):
        result = build_index([self.event], [self.root], [self.rex])
        self.assertEqual(result["event_count"], 1)
        self.assertEqual(result["events"][0]["rex"]["rex_id"], "rex1")
        self.assertFalse(result["events"][0]["root_confirmed"])
        self.assertEqual(result["verified_root_closures"], 0)

    def test_multiple_manifestations_one_root(self):
        second = dict(self.event, event_id="e2", run_id=13)
        result = build_index([self.event, second], [self.root], [self.rex])
        self.assertEqual(result["event_count"], 2)
        self.assertEqual(result["root_candidates"], 1)

    def test_missing_rex_fails_closed(self):
        with self.assertRaises(ValueError):
            build_index([self.event], [self.root], [])

    def test_duplicate_event_fails_closed(self):
        with self.assertRaises(ValueError):
            build_index([self.event, self.event], [self.root], [self.rex])

    def test_missing_native_provenance_fails_closed(self):
        bad = dict(self.event, job_id=None)
        with self.assertRaises(ValueError):
            build_index([bad], [self.root], [self.rex])

    def test_comparable_wave_delta(self):
        base = {
            "repository": "GBOGEB/ABACUS",
            "scanner_config_sha256": "f" * 64,
            "coverage_scope": "changed",
            "fingerprints": ["a", "b"],
            "covered_lines": 60,
            "total_lines": 100,
            "covered_branches": 8,
            "total_branches": 10,
        }
        now = dict(base, fingerprints=["b", "c"], covered_lines=85, covered_branches=9)
        result = wave_delta(base, now)
        self.assertEqual(result["opened"], ["c"])
        self.assertEqual(result["resolved_candidates"], ["a"])
        self.assertEqual(result["persistent"], ["b"])
        self.assertAlmostEqual(result["line_coverage_delta_pp"], 25)
        self.assertEqual(result["root_closure_credit"], 0)

    def test_incomparable_scope_fails_closed(self):
        base = {
            "repository": "A",
            "scanner_config_sha256": "x",
            "coverage_scope": "changed",
            "fingerprints": [],
        }
        with self.assertRaises(ValueError):
            wave_delta(base, dict(base, scanner_config_sha256="y"))

    def test_fingerprint_stable_and_symptom_sensitive(self):
        first = fingerprint("A", "pytest", "E32", "core.py", "locked")
        self.assertEqual(first, fingerprint("A", "pytest", "E32", "core.py", "locked"))
        self.assertNotEqual(
            first, fingerprint("A", "pytest", "E32", "core.py", "different")
        )

    def test_fingerprint_rejects_empty_and_non_string(self):
        for bad in ("", None, 12):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                fingerprint("A", "pytest", "E32", "core.py", bad)

    def test_index_rejects_duplicate_roots(self):
        with self.assertRaises(ValueError):
            build_index([self.event], [self.root, self.root], [self.rex])

    def test_index_rejects_duplicate_rex(self):
        with self.assertRaises(ValueError):
            build_index([self.event], [self.root], [self.rex, self.rex])

    def test_index_rejects_unknown_root(self):
        bad = dict(self.event, root_candidate_id="missing")
        with self.assertRaises(ValueError):
            build_index([bad], [self.root], [self.rex])

    def test_index_rejects_non_list_inputs(self):
        with self.assertRaises(ValueError):
            build_index(None, [], [])

    def test_wave_rejects_duplicate_fingerprints(self):
        base = {
            "repository": "A",
            "scanner_config_sha256": "x",
            "coverage_scope": "changed",
            "fingerprints": ["a", "a"],
        }
        with self.assertRaises(ValueError):
            wave_delta(base, dict(base))

    def test_wave_rejects_impossible_coverage(self):
        base = {
            "repository": "A",
            "scanner_config_sha256": "x",
            "coverage_scope": "changed",
            "fingerprints": [],
            "covered_lines": 11,
            "total_lines": 10,
        }
        with self.assertRaises(ValueError):
            wave_delta(base, dict(base))

    def test_wave_rejects_invalid_branch_denominator(self):
        base = {
            "repository": "A",
            "scanner_config_sha256": "x",
            "coverage_scope": "changed",
            "fingerprints": [],
            "covered_branches": 0,
            "total_branches": 0,
        }
        with self.assertRaises(ValueError):
            wave_delta(base, dict(base))

    def test_wave_rejects_missing_census(self):
        base = {
            "repository": "A",
            "scanner_config_sha256": "x",
            "coverage_scope": "changed",
        }
        with self.assertRaises(ValueError):
            wave_delta(base, dict(base))

    def test_index_without_root_keeps_observation_only(self):
        event = dict(self.event)
        event.pop("root_candidate_id")
        result = build_index([event], [], [])
        self.assertIsNone(result["events"][0]["root_candidate"])
        self.assertIsNone(result["events"][0]["rex"])
        self.assertEqual(result["verified_root_closures"], 0)

    def test_index_rejects_missing_required_fields(self):
        for field in (
            "repository",
            "source_sha",
            "run_id",
            "job_id",
            "topic_id",
            "fingerprint",
            "manifestation",
        ):
            with self.subTest(field=field):
                event = dict(self.event)
                event.pop(field)
                with self.assertRaises(ValueError):
                    build_index([event], [self.root], [self.rex])

    def test_wave_branch_coverage_delta(self):
        base = {
            "repository": "A",
            "scanner_config_sha256": "x",
            "coverage_scope": "changed",
            "fingerprints": [],
            "covered_branches": 3,
            "total_branches": 10,
        }
        after = dict(base, covered_branches=8)
        result = wave_delta(base, after)
        self.assertAlmostEqual(result["branch_coverage_delta_pp"], 50)
        self.assertIsNone(result["line_coverage_delta_pp"])

    def test_wave_rejects_negative_coverage(self):
        base = {
            "repository": "A",
            "scanner_config_sha256": "x",
            "coverage_scope": "changed",
            "fingerprints": [],
            "covered_lines": -1,
            "total_lines": 10,
        }
        with self.assertRaises(ValueError):
            wave_delta(base, dict(base))

    def test_wave_rejects_noninteger_coverage(self):
        base = {
            "repository": "A",
            "scanner_config_sha256": "x",
            "coverage_scope": "changed",
            "fingerprints": [],
            "covered_lines": 2.5,
            "total_lines": 10,
        }
        with self.assertRaises(ValueError):
            wave_delta(base, dict(base))

    def test_duplicate_root_and_rex_fail_closed(self):
        with self.assertRaises(ValueError):
            build_index([self.event], [self.root, self.root], [self.rex])
        with self.assertRaises(ValueError):
            build_index([self.event], [self.root], [self.rex, self.rex])

    def test_unknown_root_and_incomplete_event_fail_closed(self):
        with self.assertRaises(ValueError):
            build_index(
                [dict(self.event, root_candidate_id="missing")], [self.root], [self.rex]
            )
        for field in (
            "repository",
            "source_sha",
            "run_id",
            "job_id",
            "topic_id",
            "fingerprint",
            "manifestation",
        ):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    build_index(
                        [dict(self.event, **{field: None})], [self.root], [self.rex]
                    )

    def test_wave_duplicate_and_invalid_counts_fail_closed(self):
        base = {
            "repository": "A",
            "scanner_config_sha256": "x",
            "coverage_scope": "changed",
            "fingerprints": ["one"],
            "covered_lines": 1,
            "total_lines": 2,
        }
        for bad in (
            dict(base, fingerprints=["one", "one"]),
            dict(base, covered_lines=3),
            dict(base, total_lines=0),
            dict(base, covered_lines=-1),
            dict(base, covered_lines="1"),
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    wave_delta(base, bad)

    def test_wave_branch_coverage_and_new_roots_not_closure(self):
        base = {
            "repository": "A",
            "scanner_config_sha256": "x",
            "coverage_scope": "changed",
            "fingerprints": ["persistent"],
            "covered_lines": 1,
            "total_lines": 2,
            "covered_branches": 1,
            "total_branches": 4,
        }
        new = dict(base, fingerprints=["persistent", "new"], covered_branches=3)
        result = wave_delta(base, new)
        self.assertAlmostEqual(result["branch_coverage_delta_pp"], 50)
        self.assertEqual(result["opened"], ["new"])
        self.assertEqual(result["root_closure_credit"], 0)
        self.assertEqual(result["merge_admission"], "HOLD")

    def test_unknown_coverage_not_zero(self):
        base = {
            "repository": "A",
            "scanner_config_sha256": "x",
            "coverage_scope": "changed",
            "fingerprints": [],
        }
        result = wave_delta(base, dict(base))
        self.assertIsNone(result["line_coverage_delta_pp"])
        self.assertIsNone(result["branch_coverage_delta_pp"])


if __name__ == "__main__":
    unittest.main()
