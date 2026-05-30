#!/usr/bin/env python3
"""Build a standalone QPLANT visualization page."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import List, Mapping, Optional

import yaml

from renderers.mathml_renderer import MathMLRenderer
from renderers.process_flow_renderer import ProcessFlowRenderer


REPO_ROOT = Path(__file__).resolve().parent
CONTENT_DIR = REPO_ROOT / "content" / "qplant"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "dist" / "qplant_visualization.html"


def _load_yaml(path: Path) -> Mapping[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError(f"content file must load to a mapping: {path}")
    return data


def _render_process_flow(process_flow_document: Mapping[str, object]) -> str:
    process_flow = process_flow_document["process_flow"]
    renderer_input = {
        "type": "process_flow",
        "title": process_flow_document["visualization"]["title"],
        "nodes": process_flow["nodes"],
        "edges": process_flow["edges"],
    }
    renderer = ProcessFlowRenderer()
    return renderer.render(renderer_input, lineage=process_flow_document.get("lineage"))


def _render_thermodynamics(thermodynamics_document: Mapping[str, object]) -> str:
    equations: List[Mapping[str, object]] = thermodynamics_document["equations"]
    renderer = MathMLRenderer()
    rendered = []
    for equation in equations:
        mathml = renderer.render(
            {"name": equation["name"], "expression": equation["expression"]},
            lineage=thermodynamics_document.get("lineage"),
        )
        display = equation.get("display")
        display_markup = (
            f'<p class="equation-display">{escape(str(display))}</p>' if isinstance(display, str) else ""
        )
        rendered.append(
            f"<article><h3>{escape(str(equation['name']))}</h3>{display_markup}{mathml}</article>"
        )
    return "".join(rendered)


def _render_lifecycle(lifecycle_document: Mapping[str, object]) -> str:
    stages: List[Mapping[str, str]] = lifecycle_document["timeline"]["stages"]
    stage_markup = "".join(
        f'<li><strong>{escape(stage["id"])}</strong><span>{escape(stage["label"])}</span></li>'
        for stage in stages
    )
    return f'<ol class="lifecycle-list">{stage_markup}</ol>'


def _render_utilities(utilities_document: Mapping[str, object]) -> str:
    rows: List[Mapping[str, object]] = utilities_document["utilities"]
    table_rows = "".join(
        "<tr>"
        f"<td>{escape(str(row['name']))}</td>"
        f"<td>{escape(str(row['capacity']))}</td>"
        f"<td>{escape(str(row['unit']))}</td>"
        "</tr>"
        for row in rows
    )
    return (
        "<table>"
        "<thead><tr><th>Utility</th><th>Capacity</th><th>Unit</th></tr></thead>"
        f"<tbody>{table_rows}</tbody>"
        "</table>"
    )


def _render_html(
    process_flow_document: Mapping[str, object],
    thermodynamics_document: Mapping[str, object],
    lifecycle_document: Mapping[str, object],
    utilities_document: Mapping[str, object],
) -> str:
    process_flow_svg = _render_process_flow(process_flow_document)
    thermodynamics_mathml = _render_thermodynamics(thermodynamics_document)
    lifecycle_timeline = _render_lifecycle(lifecycle_document)
    utilities_table = _render_utilities(utilities_document)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>QPLANT Visualization</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #17212b; }}
    h1, h2 {{ margin-bottom: 0.3em; }}
    section {{ margin-bottom: 2rem; }}
    .abacus-process-node {{ fill: #eff5ff; stroke: #205090; stroke-width: 1.2; }}
    .abacus-process-edge {{ stroke: #205090; stroke-width: 1.6; fill: none; }}
    .abacus-process-label {{ fill: #102030; font-weight: 600; }}
    .abacus-process-title {{ fill: #102030; font-weight: 700; }}
    .equation-display {{ font-style: italic; color: #455a70; margin: 0.35rem 0; }}
    article {{ margin-bottom: 1rem; }}
    .lifecycle-list {{ list-style: none; padding-left: 0; display: grid; gap: 0.5rem; }}
    .lifecycle-list li {{ display: flex; gap: 0.75rem; align-items: baseline; }}
    .lifecycle-list li strong {{ min-width: 2.5rem; }}
    table {{ border-collapse: collapse; min-width: 320px; }}
    th, td {{ border: 1px solid #cad5e1; padding: 0.45rem 0.6rem; text-align: left; }}
    th {{ background: #f5f8fc; }}
  </style>
</head>
<body>
  <main>
    <h1>QPLANT Visualization</h1>
    <section aria-label="Process Flow">
      <h2>{escape(str(process_flow_document["visualization"]["title"]))}</h2>
      {process_flow_svg}
    </section>
    <section aria-label="Thermodynamics">
      <h2>{escape(str(thermodynamics_document["visualization"]["title"]))}</h2>
      {thermodynamics_mathml}
    </section>
    <section aria-label="Lifecycle Timeline">
      <h2>{escape(str(lifecycle_document["visualization"]["title"]))}</h2>
      {lifecycle_timeline}
    </section>
    <section aria-label="Utilities">
      <h2>{escape(str(utilities_document["visualization"]["title"]))}</h2>
      {utilities_table}
    </section>
  </main>
</body>
</html>
"""


def build_qplant_visualization(output_path: Optional[Path] = None) -> Path:
    process_flow_document = _load_yaml(CONTENT_DIR / "process_flow.yaml")
    thermodynamics_document = _load_yaml(CONTENT_DIR / "thermodynamics.yaml")
    lifecycle_document = _load_yaml(CONTENT_DIR / "lifecycle.yaml")
    utilities_document = _load_yaml(CONTENT_DIR / "utilities.yaml")

    output_target = output_path or DEFAULT_OUTPUT_PATH
    output_target.parent.mkdir(parents=True, exist_ok=True)
    output_target.write_text(
        _render_html(
            process_flow_document=process_flow_document,
            thermodynamics_document=thermodynamics_document,
            lifecycle_document=lifecycle_document,
            utilities_document=utilities_document,
        ),
        encoding="utf-8",
    )
    return output_target


def main() -> int:
    output_path = build_qplant_visualization()
    print(f"Generated: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
