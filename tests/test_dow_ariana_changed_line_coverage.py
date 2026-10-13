"""Canonical-suite coverage proof for the DOW/Ariana changed output line."""
from types import SimpleNamespace

from DMAIC_V3.core.dow_ariana_integration import DOWArianaIntegration


class _Bridge:
    def run_tests_parallel(self, tests, max_workers=2):
        return {
            test["name"]: SimpleNamespace(success=True, duration_seconds=0.01)
            for test in tests
        }


def test_integration_summary_uses_real_total_tests(tmp_path, capsys):
    config = SimpleNamespace(
        version="test-version",
        paths=SimpleNamespace(workspace_root=tmp_path, output_root=tmp_path / "out"),
    )
    state = SimpleNamespace(state_dir=tmp_path / "state")
    integration = DOWArianaIntegration(config, state, _Bridge())
    summary = integration._run_integration_tests(1, 2)
    assert summary["total_tests"] == 2
    assert summary["passed"] == 2
    assert "Integration tests: 2/2 passed" in capsys.readouterr().out
