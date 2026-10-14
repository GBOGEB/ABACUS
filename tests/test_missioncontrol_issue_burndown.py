import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "missioncontrol_issue_burndown.py"
)
spec = importlib.util.spec_from_file_location("mc_burndown", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SHA = "a" * 40


def item(n, title, body=""):
    return {
        "number": n,
        "title": title,
        "body": body,
        "state": "open",
        "html_url": f"https://github.com/GBOGEB/ABACUS/issues/{n}",
    }


def envelope(issues):
    return {
        "repository": "GBOGEB/ABACUS",
        "main_sha": SHA,
        "protected": False,
        "issues": issues,
        "runs": [{"head_sha": SHA, "conclusion": "failure"}],
    }


class TestMissionBurndown(unittest.TestCase):
    def test_cohorts_not_closed_or_approved(self):
        e, plan = mod.build(
            envelope(
                [
                    item(
                        1885,
                        "Dashboard health check failure",
                        "Broken internal links | 53",
                    ),
                    item(
                        1870,
                        "Dashboard health check failure",
                        "Broken internal links | 52",
                    ),
                    item(
                        1853,
                        "Dashboard health check failure",
                        "Broken internal links | 52",
                    ),
                    item(1861, "P1 Codex gate first red"),
                    item(1878, "Gate: synchronize"),
                    item(1929, "BD LDAB census"),
                    item(635, "Local Windows builder"),
                ]
            )
        )
        self.assertEqual(e["counts"]["open_issues"], 7)
        self.assertEqual(e["counts"]["dashboard_incidents"], 3)
        self.assertEqual(e["counts"]["proven_fixes"], 0)
        self.assertEqual(e["counts"]["worker_packets_launched"], 0)
        self.assertEqual(
            e["dashboard_cohorts_by_count_only"]["DASHBOARD_LINK_COUNTS:52:UNKNOWN"],
            [1853, 1870],
        )
        self.assertEqual(e["current_main_workflows"]["status_counts"], {"failure": 1})
        self.assertTrue(all(not p["dispatch_authorized"] for p in plan["packets"]))
        self.assertEqual(
            len({p["owner_lock"] for p in plan["packets"]}), len(plan["packets"])
        )
        self.assertFalse(plan["mutation_enabled"])

    def test_untrusted_incomplete_observation_rejected(self):
        cases = [
            dict(envelope([]), main_sha="short"),
            dict(envelope([]), protected=None),
            dict(envelope([]), repository="GBOGEB/CODEX"),
            dict(envelope([]), issues=[item(1, "ok"), item(1, "duplicate")]),
            dict(
                envelope([]),
                issues=[dict(item(1, "ok"), html_url="https://evil.example/1")],
            ),
            dict(envelope([]), issues=None),
        ]
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    mod.build(case)

    def test_determinism_and_sha_manifest(self):
        with tempfile.Te               "Broken internal links | 53",
                    ),
                    item(1861, "P1 issue"),
                ]
            )
            p = Path(d)
            mod.emit(e, p)
            before = {x.name: x.read_bytes() for x in p.iterdir()}
            mod.emit(e, p)
            self.assertEqual(before, {x.name: x.read_bytes() for x in p.iterdir()})
            m = json.loads((p / "manifest.json").read_text())
            for name, digest in m["sha256"].items():
                self.assertEqual(mod.sha256((p / name).read_text()), digest)

    def test_pagination_host_guard(self):
        self.assertEqual(
            mod.next_link(
                '<https://api.github.com/repos/x/y/issues?page=2>; rel="next"'
            ),
            "/repos/x/y/issues?page=2",
        )
        with self.assertRaises(ValueError):
            mod.next_link('<https://evil.example/issues?page=2>; rel="next"')


if __name__ == "__main__":
    unittest.main()
