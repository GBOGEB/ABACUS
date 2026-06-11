import pytest
import xml.etree.ElementTree as ET

from renderers.process_flow_renderer import ProcessFlowRenderer


VALID_SCHEMA = {
    "type": "process_flow",
    "title": "Example Process",
    "nodes": [
        {"id": "A", "label": "Compressor"},
        {"id": "B", "label": "Heat Exchanger"},
        {"id": "C", "label": "Cold Box"},
    ],
    "edges": [
        {"from": "A", "to": "B"},
        {"from": "B", "to": "C"},
    ],
}


def test_invalid_schema_rejection():
    renderer = ProcessFlowRenderer()

    with pytest.raises(ValueError, match="schema type"):
        renderer.render({"type": "sankey", "title": "X", "nodes": [], "edges": []})

    with pytest.raises(ValueError, match="missing required fields"):
        renderer.render({"type": "process_flow", "title": "X", "nodes": []})

    with pytest.raises(ValueError, match="unknown node"):
        renderer.render(
            {
                "type": "process_flow",
                "title": "Bad Edges",
                "nodes": [{"id": "A", "label": "A"}],
                "edges": [{"from": "A", "to": "B"}],
            }
        )


def test_node_and_edge_rendering():
    renderer = ProcessFlowRenderer()
    svg = renderer.render(VALID_SCHEMA)
    root = ET.fromstring(svg)

    rects = root.findall("{http://www.w3.org/2000/svg}rect")
    lines = root.findall("{http://www.w3.org/2000/svg}line")
    labels = [
        (element.text or "")
        for element in root.findall("{http://www.w3.org/2000/svg}text")
    ]

    assert len(rects) == 3
    assert len(lines) == 2
    assert "Compressor" in labels
    assert "Heat Exchanger" in labels
    assert "Cold Box" in labels
