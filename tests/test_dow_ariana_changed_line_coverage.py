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
    assert summary["expected_tests"] == 2
    assert summary["results_complete"] is True
    assert summary["all_passed"] is True
    assert "Integration tests: 2/2 passed" in capsys.readouterr().out


def test_empty_bridge_results_cannot_claim_pipeline_success(tmp_path, monkeypatch):
    config = SimpleNamespace(
        version="test-version",
        paths=SimpleNamespace(workspace_root=tmp_path, output_root=tmp_path / "out"),
    )
    state = SimpleNamespace(state_dir=tmp_path / "state")
    integration = DOWArianaIntegration(config, state, _Bridge())
    monkeypatch.setattr(
        integration.test_bridge,
        "run_tests_parallel",
        lambda tests, max_workers=2: {},
    )
    result = integration.execute_dow_pipeline_with_ariana(1, 2)
    assert result["status"] == "completed"
    assert result["success"] is False
    summary = result["test_results"]
    assert summary["expected_tests"] == 2
    assert summary["total_tests"] == 0
    assert summary["passed"] == 0
    assert summary["results_complete"] is False
    assert summary["all_passed"] is False
    import json

    receipt = integration.dow_dir / "phase1_iteration2_result.json"
    assert json.loads(receipt.read_text())["success"] is False


def test_incomplete_bridge_results_rejected(tmp_path, monkeypatch):
    config = SimpleNamespace(
        version="test-version",
        paths=SimpleNamespace(workspace_root=tmp_path, output_root=tmp_path / "out"),
    )
    state = SimpleNamespace(state_dir=tmp_path / "state")
    integration = DOWArianaIntegration(config, state, _Bridge())

    def only_first(tests, max_workers=2):
        return {tests[0]["name"]: SimpleNamespace(success=True, duration_seconds=0.01)}

    monkeypatch.setattr(integration.test_bridge, "run_tests_parallel", only_first)
    summary = integration._run_integration_tests(3, 1)
    assert summary["expected_tests"] == 2
    assert summary["total_tests"] == 1
    assert summary["passed"] == 1
    assert summary["results_complete"] is False
    assert summary["all_passed"] is False


def test_unexpected_bridge_result_rejected(tmp_path, monkeypatch):
    config = SimpleNamespace(
        version="test-version",
        paths=SimpleNamespace(workspace_root=tmp_path, output_root=tmp_path / "out"),
    )
    state = SimpleNamespace(state_dir=tmp_path / "state")
    integration = DOWArianaIntegration(config, state, _Bridge())

    def extraneous(tests, max_workers=2):
        result = {
            test["name"]: SimpleNamespace(success=True, duration_seconds=0.01)
            for test in tests
        }
        result["not_requested"] = SimpleNamespace(success=True, duration_seconds=0.01)
        return result

    monkeypatch.setattr(integration.test_bridge, "run_tests_parallel", extraneous)
    summary = integration._run_integration_tests(3, 1)
    assert summary["expected_tests"] == 2
    assert summary["total_tests"] == 3
    assert summary["results_complete"] is False
    assert summary["all_passed"] is False
