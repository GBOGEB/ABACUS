"""Generic SVG renderer primitives for scientific visualizations."""

import json
import xml.etree.ElementTree as ET
from typing import Dict, Iterable, Mapping, Optional


DEFAULT_STYLE_HOOKS = {
    "svg_class": "abacus-svg-renderer",
    "node_class": "abacus-process-node",
    "edge_class": "abacus-process-edge",
    "label_class": "abacus-process-label",
    "title_class": "abacus-process-title",
}


class SVGRenderer:
    """Render process flow graphs to SVG."""

    def __init__(self, scale: float = 1.0, style_hooks: Optional[Mapping[str, str]] = None):
        if scale <= 0:
            raise ValueError("scale must be greater than zero")
        self.scale = float(scale)
        self.style_hooks = dict(DEFAULT_STYLE_HOOKS)
        if style_hooks:
            self.style_hooks.update(dict(style_hooks))

    def render(
        self,
        nodes: Iterable[Mapping[str, str]],
        edges: Iterable[Mapping[str, str]],
        title: str = "",
        lineage: Optional[Mapping[str, object]] = None,
    ) -> str:
        node_list = list(nodes)
        edge_list = list(edges)

        x_margin = 40.0 * self.scale
        y_margin = 40.0 * self.scale
        node_width = 160.0 * self.scale
        node_height = 72.0 * self.scale
        node_gap = 80.0 * self.scale

        canvas_width = max(300.0 * self.scale, x_margin * 2 + len(node_list) * (node_width + node_gap) - node_gap)
        canvas_height = max(200.0 * self.scale, y_margin * 2 + node_height + 40.0 * self.scale)

        svg = ET.Element(
            "svg",
            {
                "xmlns": "http://www.w3.org/2000/svg",
                "version": "1.1",
                "width": f"{canvas_width:.0f}",
                "height": f"{canvas_height:.0f}",
                "viewBox": f"0 0 {canvas_width:.0f} {canvas_height:.0f}",
                "class": self.style_hooks["svg_class"],
                "data-scale": f"{self.scale}",
            },
        )

        metadata = ET.SubElement(svg, "metadata")
        metadata.text = json.dumps(self._lineage_payload(lineage), sort_keys=True)

        self._add_arrow_marker(svg)

        if title:
            ET.SubElement(
                svg,
                "text",
                {
                    "x": f"{x_margin:.2f}",
                    "y": f"{(y_margin * 0.7):.2f}",
                    "class": self.style_hooks["title_class"],
                    "font-size": f"{16.0 * self.scale:.2f}",
                    "font-family": "Arial, sans-serif",
                },
            ).text = title

        coordinates = {}
        y = y_margin + 20.0 * self.scale
        for idx, node in enumerate(node_list):
            x = x_margin + idx * (node_width + node_gap)
            node_id = node["id"]
            coordinates[node_id] = {
                "x": x,
                "y": y,
                "center_x": x + node_width / 2,
                "center_y": y + node_height / 2,
            }

            ET.SubElement(
                svg,
                "rect",
                {
                    "x": f"{x:.2f}",
                    "y": f"{y:.2f}",
                    "width": f"{node_width:.2f}",
                    "height": f"{node_height:.2f}",
                    "rx": f"{8.0 * self.scale:.2f}",
                    "ry": f"{8.0 * self.scale:.2f}",
                    "class": self.style_hooks["node_class"],
                    "data-node-id": str(node_id),
                },
            )

            ET.SubElement(
                svg,
                "text",
                {
                    "x": f"{(x + node_width / 2):.2f}",
                    "y": f"{(y + node_height / 2):.2f}",
                    "class": self.style_hooks["label_class"],
                    "font-size": f"{13.0 * self.scale:.2f}",
                    "font-family": "Arial, sans-serif",
                    "text-anchor": "middle",
                    "dominant-baseline": "middle",
                },
            ).text = str(node.get("label", node_id))

        for edge in edge_list:
            src = coordinates.get(edge["from"])
            dst = coordinates.get(edge["to"])
            if not src or not dst:
                continue
            ET.SubElement(
                svg,
                "line",
                {
                    "x1": f"{(src['x'] + node_width):.2f}",
                    "y1": f"{src['center_y']:.2f}",
                    "x2": f"{dst['x']:.2f}",
                    "y2": f"{dst['center_y']:.2f}",
                    "class": self.style_hooks["edge_class"],
                    "marker-end": "url(#abacus-arrowhead)",
                    "data-edge-from": str(edge["from"]),
                    "data-edge-to": str(edge["to"]),
                },
            )

        if not node_list:
            ET.SubElement(
                svg,
                "text",
                {
                    "x": f"{(canvas_width / 2):.2f}",
                    "y": f"{(canvas_height / 2):.2f}",
                    "class": self.style_hooks["label_class"],
                    "font-size": f"{13.0 * self.scale:.2f}",
                    "font-family": "Arial, sans-serif",
                    "text-anchor": "middle",
                },
            ).text = "No process nodes defined"

        return ET.tostring(svg, encoding="unicode")

    def to_html(self, svg: str, title: str = "Process Flow") -> str:
        return (
            "<!DOCTYPE html>"
            "<html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>{title}</title>"
            "</head><body>"
            f"{svg}"
            "</body></html>"
        )

    def _lineage_payload(self, lineage: Optional[Mapping[str, object]]) -> Dict[str, object]:
        payload = {
            "wave": "W003",
            "renderer": "process_flow",
            "runtime_evidence": True,
        }
        if lineage:
            payload.update(dict(lineage))
        return payload

    def _add_arrow_marker(self, svg: ET.Element) -> None:
        defs = ET.SubElement(svg, "defs")
        marker = ET.SubElement(
            defs,
            "marker",
            {
                "id": "abacus-arrowhead",
                "markerWidth": f"{10.0 * self.scale:.2f}",
                "markerHeight": f"{7.0 * self.scale:.2f}",
                "refX": f"{9.0 * self.scale:.2f}",
                "refY": f"{3.5 * self.scale:.2f}",
                "orient": "auto",
                "markerUnits": "strokeWidth",
            },
        )
        ET.SubElement(
            marker,
            "polygon",
            {
                "points": f"0 0, {10.0 * self.scale:.2f} {3.5 * self.scale:.2f}, 0 {7.0 * self.scale:.2f}",
            },
        )
