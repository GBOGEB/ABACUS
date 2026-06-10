from pathlib import Path
import json

from build_qplant_visualization import build_qplant_visualization


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_docs_index_exists() -> None:
    assert (REPO_ROOT / "docs" / "index.html").exists()


def test_generated_visualization_contains_expected_title(tmp_path: Path) -> None:
    generated_path = build_qplant_visualization(output_path=tmp_path / "qplant_visualization.html")
    generated_html = generated_path.read_text(encoding="utf-8")
    assert "<title>QPLANT Visualization</title>" in generated_html


def test_workflow_yaml_present() -> None:
    workflow_path = REPO_ROOT / ".github" / "workflows" / "pages.yml"
    assert workflow_path.exists()
    workflow_text = workflow_path.read_text(encoding="utf-8")
    assert "cp dist/qplant_visualization.html docs/index.html" in workflow_text


def test_runtime_publish_status_json_generated() -> None:
    status_path = REPO_ROOT / "reports" / "runtime_publish_status.json"
    assert status_path.exists()

    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status == {
        "wave": "W005.1",
        "runtime_status": "published",
        "runtime_evidence": True,
        "deployment_evidence": True,
    }
