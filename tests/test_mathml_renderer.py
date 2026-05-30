import json
import xml.etree.ElementTree as ET

import pytest

from renderers.mathml_renderer import MathMLRenderer, qplant_equation_definitions


_MATHML_NS = "{http://www.w3.org/1998/Math/MathML}"


def _first(root, tag):
    return root.find(f"{_MATHML_NS}{tag}")


def test_mathml_generation_for_initial_qplant_examples():
    renderer = MathMLRenderer()
    examples = qplant_equation_definitions()

    rendered = {name: ET.fromstring(renderer.render(defn)) for name, defn in examples.items()}

    for root in rendered.values():
        assert root.tag == f"{_MATHML_NS}math"
        assert root.attrib.get("display") == "block"

    carnot = rendered["carnot_efficiency"]
    assert carnot.find(f".//{_MATHML_NS}mfrac") is not None
    assert carnot.find(f".//{_MATHML_NS}msub") is not None
    assert "η" in [elem.text for elem in carnot.findall(f".//{_MATHML_NS}mi") if elem.text]

    cop = rendered["cop"]
    assert cop.find(f".//{_MATHML_NS}mfrac") is not None
    assert len(cop.findall(f".//{_MATHML_NS}msub")) >= 2

    heat_balance = rendered["heat_balance"]
    assert heat_balance.find(f".//{_MATHML_NS}msup") is not None
    assert "Δ" in [elem.text for elem in heat_balance.findall(f".//{_MATHML_NS}mi") if elem.text]


def test_lineage_metadata_annotation_is_included():
    renderer = MathMLRenderer()
    definition = qplant_equation_definitions()["cop"]

    root = ET.fromstring(renderer.render(definition, lineage={"repo": "ABACUS"}))
    annotation = root.find(f".//{_MATHML_NS}annotation")

    assert annotation is not None
    assert annotation.attrib["encoding"] == "application/json"
    payload = json.loads(annotation.text)
    assert payload["wave"] == "W003"
    assert payload["renderer"] == "mathml"
    assert payload["runtime_evidence"] is True
    assert payload["repo"] == "ABACUS"


def test_invalid_equation_definitions_are_rejected():
    renderer = MathMLRenderer()

    with pytest.raises(ValueError, match="missing required field"):
        renderer.render({"expression": {"type": "identifier", "value": "x"}})

    with pytest.raises(ValueError, match="unsupported node type"):
        renderer.render(
            {
                "name": "Bad Equation",
                "expression": {"type": "matrix", "rows": []},
            }
        )

    with pytest.raises(ValueError, match="greek node requires a supported symbol"):
        renderer.render(
            {
                "name": "Bad Greek",
                "expression": {
                    "type": "row",
                    "items": [{"type": "greek", "symbol": "not_a_symbol"}],
                },
            }
        )


def test_style_hook_override_applies_math_class():
    renderer = MathMLRenderer(style_hooks={"math_class": "custom-mathml"})
    definition = qplant_equation_definitions()["carnot_efficiency"]

    root = ET.fromstring(renderer.render(definition))
    assert root.attrib["class"] == "custom-mathml"
