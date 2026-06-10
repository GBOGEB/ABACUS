from pathlib import Path
import json

from build_federation_dashboard import build_federation_dashboard


def test_build_federation_dashboard_consumes_json_and_generates_html(tmp_path: Path) -> None:
    metrics_dir = tmp_path / "metrics" / "federation"
    metrics_dir.mkdir(parents=True)

    rollup_path = metrics_dir / "federation_rollup.json"
    rollup_path.write_text(
        json.dumps(
            {
                "forward_pca": "100%",
                "backward_pca": "100%",
                "geti": "0.97",
                "pci": "0.96",
                "expansion_factor": "1.2",
                "federation_status": {
                    "ABACUS": "active",
                    "ARTSTYLE": "active",
                    "QPLANT": "active",
                    "CODEX": "active",
                },
                "wave_progress": {f"W{i:03d}": "done" for i in range(11)},
            }
        ),
        encoding="utf-8",
    )

    scree_path = metrics_dir / "federation_scree.json"
    scree_path.write_text(
        json.dumps(
            {
                "components": [
                    {"pc": "PC1", "variance": "40%", "rank": 1, "cumulative_variance": "40%"},
                    {"pc": "PC2", "variance": "25%", "rank": 2, "cumulative_variance": "65%"},
                    {"pc": "PC3", "variance": "15%", "rank": 3, "cumulative_variance": "80%"},
                    {"pc": "PC4", "variance": "12%", "rank": 4, "cumulative_variance": "92%"},
                    {"pc": "PC5", "variance": "8%", "rank": 5, "cumulative_variance": "100%"},
                ]
            }
        ),
        encoding="utf-8",
    )

    bottleneck_path = tmp_path / "bottleneck_report.json"
    bottleneck_path.write_text(
        json.dumps(
            {
                "dominant_repo": "ABACUS",
                "dominant_wave": "W005",
                "dominant_bottleneck": "Telemetry publication",
                "recommended_next_action": "Stabilize dashboard publication",
            }
        ),
        encoding="utf-8",
    )

    runtime_registry_path = metrics_dir / "runtime_registry.json"
    runtime_registry_path.write_text(
        json.dumps(
            {
                "repositories": {
                    "ABACUS": {"runtime_evidence": "verified", "truth_matrix": "pass", "renderability": "ready"},
                    "ARTSTYLE": {"runtime_evidence": "verified", "truth_matrix": "pass", "renderability": "ready"},
                    "QPLANT": {"runtime_evidence": "verified", "truth_matrix": "pass", "renderability": "ready"},
                    "CODEX": {"runtime_evidence": "verified", "truth_matrix": "pass", "renderability": "ready"},
                }
            }
        ),
        encoding="utf-8",
    )

    runtime_registry_report_path = tmp_path / "reports" / "runtime_registry_report.json"
    runtime_registry_report_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_registry_report_path.write_text(
        json.dumps(
            {
                "repositories": {
                    "ABACUS": {"runtime_coverage": "95%"},
                    "ARTSTYLE": {"runtime_coverage": "93%"},
                    "QPLANT": {"runtime_coverage": "94%"},
                    "CODEX": {"runtime_coverage": "96%"},
                }
            }
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "docs" / "dashboard.html"
    status_output_path = tmp_path / "reports" / "dashboard_status.json"

    generated = build_federation_dashboard(
        rollup_path=rollup_path,
        scree_path=scree_path,
        runtime_registry_path=runtime_registry_path,
        runtime_registry_report_path=runtime_registry_report_path,
        bottleneck_path=bottleneck_path,
        output_path=output_path,
        status_output_path=status_output_path,
    )

    assert generated == output_path
    assert output_path.exists()
    assert status_output_path.exists()

    html = output_path.read_text(encoding="utf-8")
    for expected in [
        "Program Overview",
        "Federation Status",
        "Scree Analysis",
        "Bottleneck Report",
        "Wave Progress Board",
        "Runtime Evidence",
        "Federation Truth Matrix",
        "Renderability",
        "Runtime Coverage Gauges",
        "CI Gate Rollup",
        "First Failed Gate",
        "dashboard-gates.json",
        "Forward PCA",
        "ABACUS",
        "PC1",
        "dominant_repo",
        "W010",
        "95%",
    ]:
        assert expected in html

    status = json.loads(status_output_path.read_text(encoding="utf-8"))
    assert status["dashboard_generated"] is True
    assert status["github_pages_compatible"] is True
    assert status["json_consumed"] is True
    assert status["runtime_registry_consumed"] is True


def test_build_federation_dashboard_runtime_registry_missing_sets_status_false(tmp_path: Path) -> None:
    metrics_dir = tmp_path / "metrics" / "federation"
    metrics_dir.mkdir(parents=True)
    rollup_path = metrics_dir / "federation_rollup.json"
    rollup_path.write_text("{}", encoding="utf-8")
    scree_path = metrics_dir / "federation_scree.json"
    scree_path.write_text("{}", encoding="utf-8")
    bottleneck_path = tmp_path / "bottleneck_report.json"
    bottleneck_path.write_text("{}", encoding="utf-8")
    output_path = tmp_path / "docs" / "dashboard.html"
    status_output_path = tmp_path / "reports" / "dashboard_status.json"

    build_federation_dashboard(
        rollup_path=rollup_path,
        scree_path=scree_path,
        runtime_registry_path=metrics_dir / "runtime_registry.json",
        runtime_registry_report_path=tmp_path / "reports" / "runtime_registry_report.json",
        bottleneck_path=bottleneck_path,
        output_path=output_path,
        status_output_path=status_output_path,
    )

    status = json.loads(status_output_path.read_text(encoding="utf-8"))
    assert status["runtime_registry_consumed"] is False


def test_dashboard_runtime_files_exist() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    assert (repo_root / "build_federation_dashboard.py").exists()
    assert (repo_root / "docs" / "dashboard.html").exists()
    assert (repo_root / "reports" / "dashboard_status.json").exists()
