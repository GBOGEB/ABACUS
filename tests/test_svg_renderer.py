import json
import xml.etree.ElementTree as ET

from renderers.svg_renderer import SVGRenderer


def test_svg_generation_and_root_validation():
    renderer = SVGRenderer(scale=1.5)
    svg = renderer.render(
        nodes=[{"id": "A", "label": "Compressor"}, {"id": "B", "label": "Heat Exchanger"}],
        edges=[{"from": "A", "to": "B"}],
        title="Example Process",
    )

    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert root.attrib["xmlns"] == "http://www.w3.org/2000/svg"
    assert root.attrib["data-scale"] == "1.5"
    assert int(root.attrib["width"]) > 0
    assert int(root.attrib["height"]) > 0

    metadata = root.find("{http://www.w3.org/2000/svg}metadata")
    assert metadata is not None
    lineage = json.loads(metadata.text)
    assert lineage["wave"] == "W003"
    assert lineage["renderer"] == "process_flow"
    assert lineage["runtime_evidence"] is True


def test_empty_graph_handling_returns_valid_svg_with_message():
    renderer = SVGRenderer()
    svg = renderer.render(nodes=[], edges=[], title="Empty Process")
    root = ET.fromstring(svg)

    labels = [
        (element.text or "")
        for element in root.findall("{http://www.w3.org/2000/svg}text")
    ]
    assert "No process nodes defined" in labels


def test_svg_generation_supports_style_hook_overrides():
    renderer = SVGRenderer(style_hooks={"node_class": "custom-node", "edge_class": "custom-edge"})
    svg = renderer.render(
        nodes=[{"id": "A", "label": "Compressor"}, {"id": "B", "label": "Heat Exchanger"}],
        edges=[{"from": "A", "to": "B"}],
        title="Styled",
    )
    root = ET.fromstring(svg)

    rects = root.findall("{http://www.w3.org/2000/svg}rect")
    lines = root.findall("{http://www.w3.org/2000/svg}line")
    assert any(rect.attrib.get("class") == "custom-node" for rect in rects)
    assert any(line.attrib.get("class") == "custom-edge" for line in lines)
