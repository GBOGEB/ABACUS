import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        with tempfile.TemporaryDirectory() as d:
            e = envelope(
                [
                    item(
                        1885,
                        "Dashboard health check failure",
                        "Broken internal links | 53",
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
                self.assertEqual(
                    hashlib.sha256((p / name).read_bytes()).hexdigest(), digest
                )

    def test_latest_dashboard_bot_comment_ignores_forged_updates(self):
        def comment(login, broken, marker):
            return {
                "user": {"login": login},
                "id": marker,
                "created_at": f"2026-10-14T{marker:02d}:00:00Z",
                "body": (
                    "## 🚨 Dashboard Health Check Failed\\n"
                    "| Missing dashboards | 0 |\\n"
                    f"| Broken internal links | {broken} |\\n"
                ),
            }

        rows = [
            comment("github-actions[bot]", 53, 1),
            comment("arbitrary-contributor", 0, 2),
            comment("github-actions[bot]", 5, 3),
            {"user": {"login": "github-actions[bot]"}, "body": "unrelated"},
        ]
        with patch.object(mod, "github_get", return_value=(rows, "")):
            latest = mod.latest_dashboard_bot_comment(1885, "test-token")
        self.assertEqual(latest["id"], 3)
        self.assertIn("Broken internal links | 5", latest["body"])

    def test_recent_bot_count_supersedes_stale_issue_body(self):
        original = item(
            1885, "Dashboard health check failure",
            "Broken internal links | 53",
        )
        original["latest_dashboard_comment"] = {
            "id": 321,
            "body": (
                "## 🚨 Dashboard Health Check Failed\\n"
                "| Missing dashboards | 0 |\\n"
                "| Broken internal links | 5 |\\n"
            ),
        }
        evidence, _ = mod.build(envelope([original]))
        row = evidence["issues"][0]
        self.assertEqual(row["root_candidate"], "DASHBOARD_LINK_COUNTS:5:0")
        self.assertEqual(row["source_class"], "DASHBOARD_BOT_COMMENT")
        self.assertEqual(row["latest_dashboard_comment_id"], 321)

    def test_malformed_dashboard_comment_fails_closed(self):
        issue = item(1885, "Dashboard health check failure")
        issue["latest_dashboard_comment"] = "untrusted string"
        with self.assertRaises(ValueError):
            mod.build(envelope([issue]))

    def test_github_transport_auth_and_fail_closed(self):
        class Response:
            status = 200

            def read(self):
                return b'{"ok": true}'

            def getheader(self, key, default=""):
                return "" if key == "Link" else default

        class Connection:
            def __init__(self):
                self.response = Response()
                self.closed = False
                self.request_args = None

            def request(self, *args, **kwargs):
                self.request_args = (args, kwargs)

            def getresponse(self):
                return self.response

            def close(self):
                self.closed = True

        connection = Connection()
        with patch.object(mod.http.client, "HTTPSConnection") as factory:
            factory.return_value = connection
            result, link = mod.github_get(
                "/repos/GBOGEB/ABACUS/issues?state=open", "test-token"
            )
            self.assertEqual(result, {"ok": True})
            self.assertEqual(link, "")
            factory.assert_called_once_with("api.github.com", timeout=25)
            self.assertEqual(connection.request_args[0][0], "GET")
            self.assertTrue(connection.closed)

        with self.assertRaises(ValueError):
            mod.github_get("/repos/other/repository/issues", "test-token")
        with self.assertRaises(ValueError):
            mod.github_get("/repos/GBOGEB/ABACUS/issues", "")

        connection = Connection()
        connection.response.status = 403
        with patch.object(
            mod.http.client, "HTTPSConnection", return_value=connection
        ):
            with self.assertRaisesRegex(ValueError, "GitHub API HTTP 403"):
                mod.github_get("/repos/GBOGEB/ABACUS/issues", "test-token")
            self.assertTrue(connection.closed)

    def test_paginated_issue_census_filters_pull_requests(self):
        first = [item(1885, "Dashboard health check failure")]
        first.append(
            dict(
                item(100, "PR excluded"),
                pull_request={"url": "https://github.com/GBOGEB/ABACUS/pull/100"},
            )
        )
        second = [item(1929, "BD LDAB census")]
        next_url = (
            '<https://api.github.com/repos/GBOGEB/ABACUS/issues'
            '?state=open&per_page=100&page=2>; rel="next"'
        )
        with patch.object(
            mod, "github_get",
            side_effect=[(first, next_url), (second, "")],
        ) as api:
            issues = mod.list_open_issues("test-token")
        self.assertEqual([issue["number"] for issue in issues], [1885, 1929])
        self.assertEqual(api.call_count, 2)

    def test_live_census_uses_latest_dashboard_bot_comment(self):
        incident = item(
            1885, "Dashboard health check failure",
            "Broken internal links | 53",
        )
        ordinary = item(1929, "BD LDAB census")
        bot_body = (
            "## 🚨 Dashboard Health Check Failed\\n"
            "| Missing dashboards | 0 |\\n"
            "| Broken internal links | 5 |\\n"
        )
        latest = {
            "user": {"login": "github-actions[bot]"},
            "body": bot_body,
            "id": 777,
            "created_at": "2026-10-14T16:00:00Z",
        }

        def get(path, token):
            self.assertEqual(token, "test-token")
            if path.endswith("/branches/main"):
                return {"commit": {"sha": SHA}, "protected": True}, ""
            if "/actions/runs?" in path:
                return {"workflow_runs": [{"head_sha": SHA, "conclusion": "success"}],
                        "total_count": 1}, ""
            if path.endswith("/comments?per_page=100"):
                return [latest], ""
            self.fail(f"unexpected GitHub API route: {path}")
            raise AssertionError(f"unexpected GitHub API route: {path}")

        with patch.object(mod, "list_open_issues", return_value=[incident, ordinary]):
            with patch.object(mod, "github_get", side_effect=get):
                snapshot = mod.collect_live("test-token")
        evidence, _ = mod.build(snapshot)
        rows = {row["number"]: row for row in evidence["issues"]}
        self.assertEqual(snapshot["main_sha"], SHA)
        self.assertTrue(snapshot["protected"])
        self.assertEqual(rows[1885]["root_candidate"], "DASHBOARD_LINK_COUNTS:5:0")
        self.assertEqual(rows[1885]["latest_dashboard_comment_id"], 777)
        self.assertEqual(rows[1929]["source_class"], "ISSUE_BODY")
        self.assertEqual(evidence["current_main_workflows"]["status_counts"],
                         {"success": 1})

    def test_dashboard_comment_malformed_api_fails_closed(self):
        with patch.object(mod, "github_get", return_value=({}, "")):
            with self.assertRaisesRegex(ValueError, "non-list"):
                mod.latest_dashboard_bot_comment(1885, "test-token")

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
