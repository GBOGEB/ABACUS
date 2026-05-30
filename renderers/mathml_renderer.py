"""MathML renderer for scientific equations."""

import json
import xml.etree.ElementTree as ET
from typing import Dict, Mapping, Optional


_GREEK_SYMBOLS = {
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "epsilon": "ε",
    "eta": "η",
    "theta": "θ",
    "lambda": "λ",
    "mu": "μ",
    "pi": "π",
    "sigma": "σ",
    "phi": "φ",
    "omega": "ω",
    "Delta": "Δ",
    "Gamma": "Γ",
    "Lambda": "Λ",
    "Pi": "Π",
    "Sigma": "Σ",
    "Omega": "Ω",
}


DEFAULT_STYLE_HOOKS = {
    "math_class": "abacus-mathml-renderer",
    "equation_class": "abacus-equation",
}


class MathMLRenderer:
    """Render validated equation definitions into MathML."""

    def __init__(self, style_hooks: Optional[Mapping[str, str]] = None):
        self.style_hooks = dict(DEFAULT_STYLE_HOOKS)
        if style_hooks:
            self.style_hooks.update(dict(style_hooks))

    def render(
        self,
        equation_definition: Mapping[str, object],
        lineage: Optional[Mapping[str, object]] = None,
    ) -> str:
        definition = self.validate_definition(equation_definition)

        root = ET.Element(
            "math",
            {
                "xmlns": "http://www.w3.org/1998/Math/MathML",
                "display": "block",
                "class": self.style_hooks["math_class"],
            },
        )
        semantics = ET.SubElement(root, "semantics")

        equation_row = ET.SubElement(
            semantics,
            "mrow",
            {
                "class": self.style_hooks["equation_class"],
            },
        )
        ET.SubElement(equation_row, "mtext").text = definition["name"]
        ET.SubElement(equation_row, "mo").text = ":"
        equation_row.append(self._render_node(definition["expression"]))

        metadata = ET.SubElement(semantics, "annotation", {"encoding": "application/json"})
        metadata.text = json.dumps(self._lineage_payload(lineage), sort_keys=True)

        return ET.tostring(root, encoding="unicode")

    def validate_definition(self, equation_definition: Mapping[str, object]) -> Dict[str, object]:
        if not isinstance(equation_definition, Mapping):
            raise ValueError("equation definition must be a mapping")

        for field in ("name", "expression"):
            if field not in equation_definition:
                raise ValueError(f"equation definition missing required field: {field}")

        name = equation_definition["name"]
        expression = equation_definition["expression"]

        if not isinstance(name, str) or not name.strip():
            raise ValueError("equation name must be a non-empty string")

        self._validate_node(expression)

        return {
            "name": name,
            "expression": expression,
        }

    def _validate_node(self, node: Mapping[str, object]) -> None:
        if not isinstance(node, Mapping):
            raise ValueError("equation node must be a mapping")

        node_type = node.get("type")
        if node_type not in {
            "row",
            "identifier",
            "number",
            "operator",
            "greek",
            "fraction",
            "subscript",
            "superscript",
        }:
            raise ValueError(f"unsupported node type: {node_type}")

        if node_type in {"identifier", "number", "operator"}:
            value = node.get("value")
            if not isinstance(value, str) or not value:
                raise ValueError(f"{node_type} node requires a non-empty string value")
            return

        if node_type == "greek":
            symbol = node.get("symbol")
            if not isinstance(symbol, str) or symbol not in _GREEK_SYMBOLS:
                raise ValueError("greek node requires a supported symbol")
            return

        if node_type == "row":
            items = node.get("items")
            if not isinstance(items, list):
                raise ValueError("row node requires list 'items'")
            for item in items:
                self._validate_node(item)
            return

        if node_type == "fraction":
            numerator = node.get("numerator")
            denominator = node.get("denominator")
            if numerator is None or denominator is None:
                raise ValueError("fraction node requires numerator and denominator")
            self._validate_node(numerator)
            self._validate_node(denominator)
            return

        base = node.get("base")
        script = node.get("sub" if node_type == "subscript" else "sup")
        if base is None or script is None:
            raise ValueError(f"{node_type} node requires base and script")
        self._validate_node(base)
        self._validate_node(script)

    def _render_node(self, node: Mapping[str, object]) -> ET.Element:
        node_type = node["type"]

        if node_type == "row":
            element = ET.Element("mrow")
            for item in node["items"]:
                element.append(self._render_node(item))
            return element

        if node_type == "identifier":
            element = ET.Element("mi")
            element.text = node["value"]
            return element

        if node_type == "number":
            element = ET.Element("mn")
            element.text = node["value"]
            return element

        if node_type == "operator":
            element = ET.Element("mo")
            element.text = node["value"]
            return element

        if node_type == "greek":
            element = ET.Element("mi")
            element.text = _GREEK_SYMBOLS[node["symbol"]]
            return element

        if node_type == "fraction":
            element = ET.Element("mfrac")
            element.append(self._render_node(node["numerator"]))
            element.append(self._render_node(node["denominator"]))
            return element

        if node_type == "subscript":
            element = ET.Element("msub")
            element.append(self._render_node(node["base"]))
            element.append(self._render_node(node["sub"]))
            return element

        if node_type == "superscript":
            element = ET.Element("msup")
            element.append(self._render_node(node["base"]))
            element.append(self._render_node(node["sup"]))
            return element

        raise ValueError(f"unsupported node type: {node_type}")

    def _lineage_payload(self, lineage: Optional[Mapping[str, object]]) -> Dict[str, object]:
        payload = {
            "wave": "W003",
            "renderer": "mathml",
            "runtime_evidence": True,
        }
        if lineage:
            payload.update(dict(lineage))
        return payload


def qplant_equation_definitions() -> Dict[str, Dict[str, object]]:
    """Provide initial QPLANT MathML equation definitions."""
    return {
        "carnot_efficiency": {
            "name": "Carnot Efficiency",
            "expression": {
                "type": "row",
                "items": [
                    {"type": "greek", "symbol": "eta"},
                    {"type": "operator", "value": "="},
                    {"type": "number", "value": "1"},
                    {"type": "operator", "value": "-"},
                    {
                        "type": "fraction",
                        "numerator": {
                            "type": "subscript",
                            "base": {"type": "identifier", "value": "T"},
                            "sub": {"type": "identifier", "value": "c"},
                        },
                        "denominator": {
                            "type": "subscript",
                            "base": {"type": "identifier", "value": "T"},
                            "sub": {"type": "identifier", "value": "h"},
                        },
                    },
                ],
            },
        },
        "cop": {
            "name": "COP",
            "expression": {
                "type": "row",
                "items": [
                    {"type": "identifier", "value": "COP"},
                    {"type": "operator", "value": "="},
                    {
                        "type": "fraction",
                        "numerator": {"type": "identifier", "value": "Q"},
                        "denominator": {"type": "identifier", "value": "W"},
                    },
                ],
            },
        },
        "heat_balance": {
            "name": "Heat Balance",
            "expression": {
                "type": "row",
                "items": [
                    {"type": "identifier", "value": "Q"},
                    {"type": "operator", "value": "="},
                    {"type": "identifier", "value": "m"},
                    {"type": "operator", "value": "·"},
                    {"type": "identifier", "value": "cp"},
                    {"type": "operator", "value": "·"},
                    {"type": "greek", "symbol": "Delta"},
                    {"type": "identifier", "value": "T"},
                ],
            },
        },
    }
