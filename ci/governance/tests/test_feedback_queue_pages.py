"""Read-only pagination, completeness and negative controls."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "feedback_queue_pages.py"
SPEC = importlib.util.spec_from_file_location("feedback_queue_pages", PATH)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)
SHA = "a" * 40


def record(n, head=SHA, event="workflow_run"):
    return {"id": n, "name": "PR Feedback Gate Evaluator", "event": event,
            "head_sha": head, "status": "queued", "created_at": "2026-10-15T08:29:00Z"}


def api(rows, total=None, mutate=None, expected_sha=None):
    calls = []
    def get(url):
        calls.append(url)
        if expected_sha is not None and "head_sha=" + expected_sha not in url:
            raise RuntimeError("head query missing")
        page = int(url.rsplit("page=", 1)[-1])
        part = rows[(page - 1) * 100:page * 100]
        data = {"total_count": len(rows) if total is None else total, "workflow_runs": part}
        return mutate(len(calls), data) if mutate else data
    return get, calls


class PaginationTests(unittest.TestCase):
    def test_200_rows_double_sweep_complete(self):
        get, calls = api([record(i) for i in range(1, 201)], expected_sha=SHA)
        r = mod.inspect(get, sha=SHA)
        self.assertEqual(r["state"], "CENSUS_CONSISTENT_NOT_ATOMIC")
        self.assertEqual(r["count"], 200)
        self.assertEqual(len(calls), 4)
        self.assertEqual(r["pages_per_pass"], 2)
        self.assertFalse(r["skip_authorized"])

    def test_101_rows_two_pages_each(self):
        get, calls = api([record(i) for i in range(1, 102)])
        r = mod.inspect(get)
        self.assertEqual(r["count"], 101)
        self.assertEqual(len(calls), 4)

    def test_0_population_two_passes(self):
        get, calls = api([])
        r = mod.inspect(get)
        self.assertEqual(r["count"], 0)
        self.assertEqual(len(calls), 2)

    def test_inconsistent_population_fails_closed(self):
        def change(n, d):
            if n == 2:
                d["total_count"] += 1
            return d
        get, _ = api([record(i) for i in range(1, 102)], mutate=change)
        r = mod.inspect(get)
        self.assertEqual(r["state"], "UNKNOWN")
        self.assertIsNone(r["runs"])

    def test_double_pass_drift_not_accepted(self):
        def change(n, d):
            if n >= 3:
                d["workflow_runs"] = [record(z["id"] + 500) for z in d["workflow_runs"]]
            return d
        get, _ = api([record(i) for i in range(1, 102)], mutate=change)
        r = mod.inspect(get)
        self.assertEqual(r["reason"], "DOUBLE_SWEEP_DRIFT")

    def test_duplicate_across_pages_unknown(self):
        def change(n, d):
            if n == 2:
                d["workflow_runs"][0] = record(1)
            return d
        get, _ = api([record(i) for i in range(1, 102)], mutate=change)
        r = mod.inspect(get)
        self.assertEqual(r["state"], "UNKNOWN")

    def test_status_change_unknown(self):
        rows = [record(1)]
        rows[0]["status"] = "completed"
        r = mod.inspect(api(rows)[0])
        self.assertEqual(r["state"], "UNKNOWN")

    def test_wrong_sha_unknown(self):
        r = mod.inspect(api([record(1, head="b" * 40)])[0], sha=SHA)
        self.assertEqual(r["state"], "UNKNOWN")

    def test_budget_limit_unknown(self):
        get, calls = api([record(1)], total=2001)
        r = mod.inspect(get)
        self.assertEqual(r["state"], "UNKNOWN")
        self.assertEqual(len(calls), 1)

    def test_invalid_limit_fails_validation(self):
        with self.assertRaises(ValueError):
            mod.inspect(api([])[0], max_pages=True)
        with self.assertRaises(ValueError):
            mod.inspect(api([])[0], max_pages=0)
        with self.assertRaises(ValueError):
            mod.inspect(api([])[0], max_pages=100)

    def test_invalid_repo_fails_validation(self):
        with self.assertRaises(ValueError):
            mod.inspect(api([])[0], repository="bad")

    def test_invalid_sha_fails_validation(self):
        with self.assertRaises(ValueError):
            mod.inspect(api([])[0], sha="123")

    def test_missing_total_unknown(self):
        get, _ = api([record(1)], mutate=lambda n, d: {"workflow_runs": d["workflow_runs"]})
        r = mod.inspect(get)
        self.assertEqual(r["state"], "UNKNOWN")

    def test_negative_total_unknown(self):
        r = mod.inspect(api([], total=-1)[0])
        self.assertEqual(r["state"], "UNKNOWN")

    def test_short_first_page_unknown(self):
        get, _ = api([record(1)], total=123)
        r = mod.inspect(get)
        self.assertEqual(r["state"], "UNKNOWN")

    def test_missing_workflow_rows_unknown(self):
        get, _ = api([record(1)], mutate=lambda n, d: {**d, "workflow_runs": None})
        r = mod.inspect(get)
        self.assertEqual(r["state"], "UNKNOWN")

    def test_boolean_run_id_unknown(self):
        d = record(1)
        d["id"] = True
        r = mod.inspect(api([d])[0])
        self.assertEqual(r["state"], "UNKNOWN")

    def test_missing_name_unknown(self):
        d = record(1)
        d["name"] = ""
        r = mod.inspect(api([d])[0])
        self.assertEqual(r["state"], "UNKNOWN")

    def test_missing_event_unknown(self):
        d = record(1)
        d["event"] = None
        r = mod.inspect(api([d])[0])
        self.assertEqual(r["state"], "UNKNOWN")

    def test_id_sort_deterministic(self):
        a = mod.inspect(api([record(3), record(1), record(2)])[0])
        b = mod.inspect(api([record(1), record(2), record(3)])[0])
        self.assertEqual(a["digest_sha256"], b["digest_sha256"])

    def test_request_failure_unknown(self):
        def get(_):
            raise RuntimeError("GitHub API unavailable")
        r = mod.inspect(get)
        self.assertEqual(r["state"], "UNKNOWN")
        self.assertFalse(r["authority_transfer"])


    def test_malformed_row_unknown(self):
        r = mod.inspect(api([None])[0])
        self.assertEqual(r["state"], "UNKNOWN")

    def test_reported_population_smaller_than_page_unknown(self):
        r = mod.inspect(api([record(1), record(2)], total=1)[0])
        self.assertEqual(r["state"], "UNKNOWN")

    def test_oversized_page_unknown(self):
        get, _ = api([record(1)], mutate=lambda n, d: {
            **d, "workflow_runs": [record(i) for i in range(1, 102)]})
        self.assertEqual(mod.inspect(get)["state"], "UNKNOWN")

    def test_empty_feedback_is_not_skip_authority(self):
        out = mod.inspect(api([])[0])
        self.assertFalse(out["skip_authorized"])
        self.assertEqual(out["open_pr_linkage"], "NOT_CHECKED")


if __name__ == "__main__":
    unittest.main()
