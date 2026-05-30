from pathlib import Path

from build_qplant_visualization import DEFAULT_OUTPUT_PATH, build_qplant_visualization


def test_qplant_visualization_html_generation(tmp_path):
    output_path = tmp_path / "dist" / "qplant_visualization.html"

    generated_path = build_qplant_visualization(output_path=output_path)

    assert generated_path == output_path
    assert generated_path.exists()

    html = generated_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert "<svg" in html
    assert "<math" in html
    assert "QPLANT Lifecycle" in html
    assert "130 QPLANT Utilities" in html
    assert "L0 Procurement" in html
    assert "Carnot Efficiency" in html


def test_qplant_visualization_default_output_is_dist_html():
    expected = Path(__file__).resolve().parents[2] / "dist" / "qplant_visualization.html"
    assert DEFAULT_OUTPUT_PATH == expected
