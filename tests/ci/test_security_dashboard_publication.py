"""Regression tests for aggregate-only public dashboard publication."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".github/scripts/security_dashboard.py"
spec = importlib.util.spec_from_file_location("security_dashboard_under_test", SCRIPT)
assert spec is not None and spec.loader is not None
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)


class SecurityDashboardPublicationTests(TestCase):
    def test_public_dashboard_excludes_individual_alert_details(self) -> None:
        source_path = "sensitive_internal_component/fixture.py"
        source_message = "a source-only finding must not be published"
        source_url = "https://example.invalid/security/secret-case"
        alerts = [
            {
                "tool": {"name": "Bandit"},
                "rule": {"id": "B101", "severity": "warning"},
                "number": 99,
                "html_url": source_url,
                "most_recent_instance": {
                    "location": {"path": source_path, "start_line": 9},
                    "message": {"text": source_message},
                },
            }
        ]
        summary = dashboard.render_markdown(dashboard.build_telemetry(alerts))
        self.assertIn("1 open alerts", summary)
        self.assertIn("Bandit", summary)
        self.assertNotIn(source_path, summary)
        self.assertNotIn(source_url, summary)
        self.assertNotIn(source_message, summary)
        self.assertNotIn("99](", summary)

    def test_runtime_does_not_persist_raw_alert_snapshot(self) -> None:
        alert = {
            "tool": {"name": "Bandit"},
            "rule": {"id": "B101", "severity": "warning"},
            "number": 1,
            "most_recent_instance": {
                "location": {"path": "private/fixture.py", "start_line": 1},
                "message": {"text": "source evidence"},
            },
        }
        cwd = Path.cwd()
        with (
            TemporaryDirectory() as tmp,
            patch.object(dashboard, "TOKEN", "dummy"),
            patch.object(dashboard, "fetch_alerts", return_value=[alert]),
        ):
            try:
                os.chdir(tmp)
                dashboard.main()
                self.assertTrue(Path(".github/security/dashboard.md").is_file())
                self.assertFalse(Path(".github/security/alerts.yaml").exists())
            finally:
                # On Windows, restore CWD before TemporaryDirectory cleanup.
                os.chdir(cwd)

    def test_scheduled_workflow_publishes_without_main_writes(self) -> None:
        workflow = (ROOT / ".github/workflows/security-dashboard.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("contents: read", workflow)
        self.assertIn("security-events: read", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("actions/upload-artifact@v7", workflow)
        self.assertIn("if-no-files-found: error", workflow)
        self.assertIn("sha256sum dashboard.md", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("git push", workflow)
        self.assertNotIn("git add", workflow)
        self.assertNotIn(".github/security/alerts.yaml", workflow)

    def test_cross_host_pagination_is_rejected_before_token_send(self) -> None:
        response = Mock(status=200)
        response.read.return_value = b'[{"number": 1}]'
        response.getheader.return_value = (
            "<https://different.example.invalid/repos/GBOGEB/ABACUS/"
            'code-scanning/alerts?page=2>; rel="next"'
        )
        connection = Mock()
        connection.getresponse.return_value = response
        with patch.object(
            dashboard, "HTTPSConnection", return_value=connection
        ) as factory:
            with self.assertRaisesRegex(ValueError, "Unsafe GitHub"):
                dashboard.gh_get(
                    "/repos/GBOGEB/ABACUS/code-scanning/alerts?per_page=100"
                )
        factory.assert_called_once_with("api.github.com", timeout=20)
        connection.close.assert_called_once()

    def test_api_error_fails_closed_instead_of_reporting_zero(self) -> None:
        response = Mock(status=403)
        connection = Mock()
        connection.getresponse.return_value = response
        with patch.object(dashboard, "HTTPSConnection", return_value=connection):
            with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
                dashboard.gh_get(
                    "/repos/GBOGEB/ABACUS/code-scanning/alerts?per_page=100"
                )
        connection.close.assert_called_once()

    def test_safe_same_host_pagination_is_complete(self) -> None:
        first = Mock(status=200)
        first.read.return_value = b'[{"number": 1}]'
        first.getheader.return_value = (
            "<https://api.github.com/repos/GBOGEB/ABACUS/"
            'code-scanning/alerts?page=2>; rel="next"'
        )
        second = Mock(status=200)
        second.read.return_value = b'[{"number": 2}]'
        second.getheader.return_value = ""
        first_conn = Mock()
        first_conn.getresponse.return_value = first
        second_conn = Mock()
        second_conn.getresponse.return_value = second
        with patch.object(
            dashboard,
            "HTTPSConnection",
            side_effect=[first_conn, second_conn],
        ):
            result = dashboard.gh_get(
                "/repos/GBOGEB/ABACUS/code-scanning/alerts?per_page=100"
            )
        self.assertEqual([x["number"] for x in result], [1, 2])
        first_conn.close.assert_called_once()
        second_conn.close.assert_called_once()

    def test_canonical_repository_id_pagination_is_accepted(self) -> None:
        first = Mock(status=200)
        first.read.return_value = b'[{"number": 1}]'
        first.getheader.return_value = (
            "<https://api.github.com/repositories/1054507184/"
            'code-scanning/alerts?page=2>; rel="next"'
        )
        second = Mock(status=200)
        second.read.return_value = b'[{"number": 2}]'
        second.getheader.return_value = ""
        connections = [Mock(), Mock()]
        connections[0].getresponse.return_value = first
        connections[1].getresponse.return_value = second
        with patch.object(
            dashboard, "HTTPSConnection", side_effect=connections
        ) as factory:
            records = dashboard.gh_get(
                "/repos/GBOGEB/ABACUS/code-scanning/alerts?per_page=100"
            )
        self.assertEqual([item["number"] for item in records], [1, 2])
        self.assertEqual(factory.call_count, 2)
        for conn in connections:
            conn.close.assert_called_once()

    def test_other_repository_id_is_rejected(self) -> None:
        first = Mock(status=200)
        first.read.return_value = b'[{"number": 1}]'
        first.getheader.return_value = (
            "<https://api.github.com/repositories/1054507185/"
            'code-scanning/alerts?page=2>; rel="next"'
        )
        connection = Mock()
        connection.getresponse.return_value = first
        with patch.object(
            dashboard, "HTTPSConnection", return_value=connection
        ) as factory:
            with self.assertRaisesRegex(ValueError, "Unsafe GitHub"):
                dashboard.gh_get(
                    "/repos/GBOGEB/ABACUS/code-scanning/alerts?per_page=100"
                )
        factory.assert_called_once_with("api.github.com", timeout=20)
        connection.close.assert_called_once()
