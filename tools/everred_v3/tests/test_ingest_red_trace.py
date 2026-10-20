"""EVERRED consumer controls for GOGREEN red-trace ingestion (offline)."""
import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import everred  # noqa: E402

spec = importlib.util.spec_from_file_location("ingest_red_trace", ROOT / "scripts" / "ingest_red_trace.py")
irt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(irt)

A, B, C = "a" * 40, "b" * 40, "c" * 40


def report():
    def brk(name, pinned):
        return {"name": name, "path": f".github/workflows/{name}.yml", "class": "GREEN_TO_RED", "current": "RED",
                "pinned_historical_ids": ["35171901674"] if pinned else [],
                "break": {"last_green_sha": A, "first_red_sha": B, "first_red_run": 9, "first_red_at": "2026-10-17T11:25:35Z",
                          "red_streak_runs": 2, "suspect_commit_count": 3,
                          "failing": [{"job": "j", "steps": ["s"]}]},
                "latest": {"sha": B, "at": "2026-10-17T11:25:35Z"}, "stale": False}
    return {"schema": "gogreen.red_trace.v1", "repository": "GBOGEB/pipeline-automation-hub", "digest_sha256": "d" * 64,
            "authority": {"merge_authorized": False},
            "workflows": [brk("w1", True), brk("w2", False),
                          {"name": "rec", "path": "r.yml", "class": "RED_TO_GREEN", "current": "GREEN",
                           "red_episodes": [{"first_red_sha": A, "recovery_sha": C, "recovery_run": 7,
                                             "recovered_at": "2026-10-18T00:00:00Z", "red_hours": 4.0}]},
                          {"name": "old", "path": "o.yml", "class": "EVERRED", "current": "RED", "stale": True,
                           "latest_age_days": 30.4, "latest": {"sha": C, "at": "2026-09-19T06:03:38Z"},
                           "first_red": {"sha": C, "run_id": 5, "at": "2026-09-19T06:03:38Z"}}]}


class IngestRedTrace(unittest.TestCase):
    def test_mapping_and_shared_root_counted_once(self):
        ev = irt.events_from_report(report())
        kinds = [e["kind"] for e in ev]
        self.assertEqual(kinds.count("occurrence"), 3)
        roots = [e for e in ev if e["kind"] == "root_candidate"]
        self.assertEqual(len(roots), 2)
        shared = [r for r in roots if r["sha"] == B][0]
        self.assertEqual(shared["evidence"]["applicable_consumers"], ["w1", "w2"])
        self.assertEqual(shared["evidence"]["cause"], "UNKNOWN", "mixed pinned/unpinned must not claim pinned cause")
        self.assertEqual([e for e in ev if e["kind"] == "verification"][0]["sha"], C)
        self.assertEqual(kinds.count("note"), 1)

    def test_pinned_cause_only_when_all_consumers_pinned(self):
        r = report()
        r["workflows"][1]["pinned_historical_ids"] = ["1" * 9]
        root = [e for e in irt.events_from_report(r) if e["kind"] == "root_candidate" and e["sha"] == B][0]
        self.assertEqual(root["evidence"]["cause"], "PINNED_HISTORICAL_EVIDENCE")

    def test_never_confirms_closes_or_admits(self):
        self.assertFalse({e["kind"] for e in irt.events_from_report(report())} &
                         {"root_confirmed", "closure", "admission"})

    def test_all_events_pass_everred_validation_and_chain(self):
        with tempfile.TemporaryDirectory() as d:
            led = pathlib.Path(d) / "ledger.jsonl"
            src = pathlib.Path(d) / "r.json"
            src.write_text(json.dumps(report()))
            irt.main(["--input", str(src), "--ledger", str(led), "--apply"])
            n = len(everred.read_ledger(led))
            irt.main(["--input", str(src), "--ledger", str(led), "--apply"])  # idempotent
            self.assertEqual(len(everred.read_ledger(led)), n)
            snap = everred.snapshot(everred.read_ledger(led))
            self.assertEqual(snap["root_count"], 2)

    def test_rejects_wrong_schema_and_authority(self):
        for mutate in (lambda r: r.update(schema="x"), lambda r: r["authority"].update(merge_authorized=True)):
            r = copy.deepcopy(report())
            mutate(r)
            with self.assertRaises(everred.InvalidEvidence):
                irt.events_from_report(r)


if __name__ == "__main__":
    unittest.main()
