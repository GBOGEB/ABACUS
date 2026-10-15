import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from everred import InvalidEvidence
from joined_census import join
from native_ingest import events_from_run

SHA = "e9f34b22967064c779891a4d2ac40541f370e812"
REPO = "GBOGEB/ABACUS"


class JoinTests(unittest.TestCase):
    def run_events(self):
        r = {
            "id": 4,
            "head_sha": SHA,
            "repository": {"full_name": REPO},
            "status": "completed",
            "name": "suite",
            "conclusion": "failure",
            "created_at": "2026-10-14T08:00:00Z",
        }
        j = [
            {
                "id": 8,
                "run_id": 4,
                "status": "completed",
                "conclusion": "failure",
                "name": "tests",
                "completed_at": "2026-10-14T08:01:00Z",
                "steps": [{"number": 1, "name": "pytest", "conclusion": "failure"}],
            }
        ]
        return events_from_run(r, j, REPO, SHA)

    def test_join_same_exact_scope(self):
        x = join(self.run_events())
        self.assertEqual(x["run_group_count"], 1)
        self.assertEqual(x["run_groups"][0]["first_red_count"], 1)
        self.assertIsNone(x["run_groups"][0]["confirmed_unique_roots"])

    def test_reject_mismatched_embedded_sha(self):
        ev = self.run_events()
        ev[1]["evidence"]["source_binding"]["source_sha"] = "0" * 40
        with self.assertRaises(InvalidEvidence):
            join(ev)

    def test_separates_new_run(self):
        ev = self.run_events()
        more = self.run_events()
        for e in more:
            e["id"] = "other" + e["id"]
            e["evidence"]["source_binding"]["run_id"] = 6
        self.assertEqual(join(ev + more)["run_group_count"], 2)


if __name__ == "__main__":
    unittest.main()
