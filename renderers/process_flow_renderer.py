"""Process-flow schema renderer."""

from typing import Dict, Mapping, Optional

from .svg_renderer import SVGRenderer


class ProcessFlowRenderer:
    """Renderer for process-flow schema payloads."""

    REQUIRED_FIELDS = ("type", "title", "nodes", "edges")

    def render(
        self,
        schema: Mapping[str, object],
        scale: float = 1.0,
        style_hooks: Optional[Mapping[str, str]] = None,
        lineage: Optional[Mapping[str, object]] = None,
    ) -> str:
        normalized = self.validate_schema(schema)
        renderer = SVGRenderer(scale=scale, style_hooks=style_hooks)
        lineage_payload = {"renderer": "process_flow", "wave": "W003", "runtime_evidence": True}
        if lineage:
            lineage_payload.update(dict(lineage))
        return renderer.render(
            nodes=normalized["nodes"],
            edges=normalized["edges"],
            title=normalized["title"],
            lineage=lineage_payload,
        )

    def render_html(
        self,
        schema: Mapping[str, object],
        scale: float = 1.0,
        style_hooks: Optional[Mapping[str, str]] = None,
        lineage: Optional[Mapping[str, object]] = None,
    ) -> str:
        renderer = SVGRenderer(scale=scale, style_hooks=style_hooks)
        svg = self.render(schema=schema, scale=scale, style_hooks=style_hooks, lineage=lineage)
        return renderer.to_html(svg, title=str(schema.get("title", "Process Flow")))

    def validate_schema(self, schema: Mapping[str, object]) -> Dict[str, object]:
        if not isinstance(schema, Mapping):
            raise ValueError("schema must be a mapping")

        missing = [field for field in self.REQUIRED_FIELDS if field not in schema]
        if missing:
            raise ValueError("schema missing required fields: {}".format(", ".join(missing)))

        if schema["type"] != "process_flow":
            raise ValueError("schema type must be 'process_flow'")

        title = schema["title"]
        nodes = schema["nodes"]
        edges = schema["edges"]

        if not isinstance(title, str) or not title.strip():
            raise ValueError("title must be a non-empty string")
        if not isinstance(nodes, list):
            raise ValueError("nodes must be a list")
        if not isinstance(edges, list):
            raise ValueError("edges must be a list")

        node_ids = set()
        normalized_nodes = []
        for node in nodes:
            if not isinstance(node, Mapping):
                raise ValueError("each node must be a mapping")
            node_id = node.get("id")
            if not isinstance(node_id, str) or not node_id.strip():
                raise ValueError("each node.id must be a non-empty string")
            if node_id in node_ids:
                raise ValueError("duplicate node id: {}".format(node_id))
            node_ids.add(node_id)
            label = node.get("label", node_id)
            if not isinstance(label, str):
                raise ValueError("each node.label must be a string")
            normalized_nodes.append({"id": node_id, "label": label})

        normalized_edges = []
        for edge in edges:
            if not isinstance(edge, Mapping):
                raise ValueError("each edge must be a mapping")
            src = edge.get("from")
            dst = edge.get("to")
            if not isinstance(src, str) or not isinstance(dst, str):
                raise ValueError("each edge must contain string 'from' and 'to'")
            if src not in node_ids or dst not in node_ids:
                raise ValueError("edge references unknown node")
            normalized_edges.append({"from": src, "to": dst})

        return {
            "type": "process_flow",
            "title": title,
            "nodes": normalized_nodes,
            "edges": normalized_edges,
        }
