from __future__ import annotations

import json

from cicd_github_orchestrator import CICDGitHubOrchestrator


def test_git_tool_configuration_and_verification(tmp_path):
    vscode = tmp_path / ".vscode"
    vscode.mkdir()
    (vscode / "settings.json").write_text(json.dumps({
        "gitlens.plusFeatures.enabled": True,
        "gitlens.graph.layout": "editor",
        "gitlens.ai.experimental.provider": "openai",
    }), encoding="utf-8")
    (vscode / "extensions.json").write_text("{}", encoding="utf-8")
    gitkraken = tmp_path / ".gitkraken"
    gitkraken.mkdir()
    (gitkraken / "config.json").write_text(json.dumps({
        "authentication": {"gitlens": {"enabled": True, "pro_token": "test-token"}}
    }), encoding="utf-8")
    orchestrator = CICDGitHubOrchestrator(tmp_path)
    verification = orchestrator.verify_git_tools()
    assert verification["gitlens"] == {
        "configured": True, "graph_enabled": True, "ai_enabled": True,
    }
    assert verification["gitkraken"] == {
        "configured": True, "pro_token_set": True,
    }
    assert verification["vscode_extensions"]["extensions_json_exists"] is True


def test_invalid_configs_fall_back_to_disabled(tmp_path):
    vscode = tmp_path / ".vscode"
    vscode.mkdir()
    (vscode / "settings.json").write_text("{not-json", encoding="utf-8")
    gitkraken = tmp_path / ".gitkraken"
    gitkraken.mkdir()
    (gitkraken / "config.json").write_text("{not-json", encoding="utf-8")
    orchestrator = CICDGitHubOrchestrator(tmp_path)
    assert orchestrator.gitlens_config == {"enabled": False}
    assert orchestrator.gitkraken_config == {"enabled": False}


def test_collect_and_save_metrics_counts_behavior(tmp_path):
    (tmp_path / "pkg").mkdir()
    content = '__version__ = "1.0"\nprint("hello")\n'
    (tmp_path / "pkg" / "a.py").write_text(content, encoding="utf-8")
    (tmp_path / "pkg" / "b.py").write_text(content, encoding="utf-8")
    (tmp_path / "pkg" / "legacy.py").write_text(
        "from DMAIC_V3.core import something\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text("# sample\n", encoding="utf-8")
    orchestrator = CICDGitHubOrchestrator(tmp_path)
    metrics = orchestrator.collect_metrics("pre")
    assert metrics.python_files == 3
    assert metrics.total_files >= 4
    assert metrics.duplicate_files == 1
    assert metrics.version_headers == 2
    assert metrics.import_issues == 1
    assert metrics.directory_structure["pkg"] == 3
    orchestrator.save_metrics(metrics, "pre")
    saved = list(orchestrator.output_dir.glob("metrics_pre_*.json"))
    assert len(saved) == 1
    payload = json.loads(saved[0].read_text(encoding="utf-8"))
    assert payload["python_files"] == 3
    assert payload["duplicate_files"] == 1
