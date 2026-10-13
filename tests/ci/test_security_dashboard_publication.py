"""Regression tests for aggregate-only public dashboard publication."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

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
        alerts = [{
            "tool": {"name": "Bandit"},
            "rule": {"id": "B101", "severity": "warning"},
            "number": 99,
            "html_url": source_url,
            "most_recent_instance": {
                "location": {"path": source_path, "start_line": 9},
                "message": {"text": source_message},
            },
        }]
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
        try:
            with TemporaryDirectory() as tmp, \
                 patch.object(dashboard, "TOKEN", "dummy"), \
                 patch.object(dashboard, "fetch_alerts", return_value=[alert]):
                os.chdir(tmp)
                dashboard.main()
                self.assertTrue(Path(".github/security/dashboard.md").is_file())
                self.assertFalse(Path(".github/security/alerts.yaml").exists())
        finally:
            os.chdir(cwd)

    def test_scheduled_workflow_never_stages_raw_yaml(self) -> None:
        workflow = (ROOT / ".github/workflows/security-dashboard.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("git add -- .github/security/dashboard.md", workflow)
        self.assertNotIn("git add .github/security/dashboard.md .github/security/alerts.yaml",
                         workflow)
