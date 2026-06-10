#!/usr/bin/env python3
"""Build a static federation telemetry dashboard from existing JSON artifacts."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_ROLLUP_PATH = REPO_ROOT / "metrics" / "federation" / "federation_rollup.json"
DEFAULT_SCREE_PATH = REPO_ROOT / "metrics" / "federation" / "federation_scree.json"
DEFAULT_RUNTIME_REGISTRY_PATH = REPO_ROOT / "metrics" / "federation" / "runtime_registry.json"
DEFAULT_RUNTIME_REGISTRY_REPORT_PATH = REPO_ROOT / "reports" / "runtime_registry_report.json"
DEFAULT_BOTTLENECK_PATH = REPO_ROOT / "bottleneck_report.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "docs" / "dashboard.html"
DEFAULT_STATUS_OUTPUT_PATH = REPO_ROOT / "reports" / "dashboard_status.json"
FEDERATION_REPOS = ("ABACUS", "ARTSTYLE", "QPLANT", "CODEX")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _pick_value(source: Mapping[str, Any], *candidates: str) -> Any:
    lowered = {str(k).lower(): v for k, v in source.items()}
    for key in candidates:
        if key in source:
            return source[key]
        lowered_key = key.lower()
        if lowered_key in lowered:
            return lowered[lowered_key]
    return "N/A"


def _extract_program_overview(rollup: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "Forward PCA": _pick_value(rollup, "forward_pca", "Forward PCA"),
        "Backward PCA": _pick_value(rollup, "backward_pca", "Backward PCA"),
        "GETI": _pick_value(rollup, "geti", "GETI"),
        "PCI": _pick_value(rollup, "pci", "PCI"),
        "Expansion Factor": _pick_value(rollup, "expansion_factor", "Expansion Factor"),
    }


def _extract_federation_status(rollup: Mapping[str, Any]) -> Dict[str, Any]:
    status = _pick_value(rollup, "federation_status", "federation")
    status_map = status if isinstance(status, Mapping) else {}
    return {
        "ABACUS": _pick_value(status_map, "ABACUS", "abacus"),
        "ARTSTYLE": _pick_value(status_map, "ARTSTYLE", "artstyle"),
        "QPLANT": _pick_value(status_map, "QPLANT", "qplant"),
        "CODEX": _pick_value(status_map, "CODEX", "codex"),
    }


def _extract_scree(scree_payload: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    components = _pick_value(scree_payload, "components", "scree", "principal_components")
    items = components if isinstance(components, list) else []
    indexed: Dict[str, Mapping[str, Any]] = {}
    for component in items:
        if not isinstance(component, Mapping):
            continue
        name = str(_pick_value(component, "pc", "component", "name")).upper()
        indexed[name] = component

    result: Dict[str, Dict[str, Any]] = {}
    for i in range(1, 6):
        key = f"PC{i}"
        source = indexed.get(key, {})
        result[key] = {
            "variance": _pick_value(source, "variance", "explained_variance"),
            "rank": _pick_value(source, "rank"),
            "cumulative variance": _pick_value(source, "cumulative_variance", "cumulative variance"),
        }
    return result


def _extract_bottleneck(bottleneck: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "dominant_repo": _pick_value(bottleneck, "dominant_repo"),
        "dominant_wave": _pick_value(bottleneck, "dominant_wave"),
        "dominant_bottleneck": _pick_value(bottleneck, "dominant_bottleneck"),
        "recommended_next_action": _pick_value(bottleneck, "recommended_next_action"),
    }


def _extract_wave_progress(rollup: Mapping[str, Any]) -> Dict[str, Any]:
    progress = _pick_value(rollup, "wave_progress", "waves")
    progress_map = progress if isinstance(progress, Mapping) else {}
    return {f"W{i:03d}": _pick_value(progress_map, f"W{i:03d}") for i in range(11)}


def _extract_repo_runtime_registry(
    runtime_registry: Mapping[str, Any], runtime_report: Mapping[str, Any]
) -> Dict[str, Mapping[str, Any]]:
    registry_repos = _pick_value(runtime_registry, "repositories", "repos", "registry")
    report_repos = _pick_value(runtime_report, "repositories", "repos", "runtime_report")
    registry_map = registry_repos if isinstance(registry_repos, Mapping) else {}
    report_map = report_repos if isinstance(report_repos, Mapping) else {}

    rows: Dict[str, Mapping[str, Any]] = {}
    for repo in FEDERATION_REPOS:
        merged: Dict[str, Any] = {}
        registry_entry = registry_map.get(repo) or registry_map.get(repo.lower())
        report_entry = report_map.get(repo) or report_map.get(repo.lower())
        if isinstance(registry_entry, Mapping):
            merged.update(registry_entry)
        if isinstance(report_entry, Mapping):
            merged.update(report_entry)
        rows[repo] = merged
    return rows


def _extract_runtime_evidence(rows: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        repo: _pick_value(data, "runtime_evidence", "evidence", "runtime_status", "status")
        for repo, data in rows.items()
    }


def _extract_truth_matrix(rows: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        repo: _pick_value(data, "truth_matrix", "truth_matrix_status", "truth_status")
        for repo, data in rows.items()
    }


def _extract_renderability(rows: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        repo: _pick_value(data, "renderability", "renderability_status", "render_status")
        for repo, data in rows.items()
    }


def _extract_runtime_coverage(rows: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        repo: _pick_value(data, "runtime_coverage", "coverage", "runtime_coverage_pct", "coverage_pct")
        for repo, data in rows.items()
    }


def _parse_percent(value: Any) -> Optional[int]:
    if isinstance(value, (int, float)):
        rounded = int(round(float(value)))
        if 0 <= rounded <= 100:
            return rounded
        return None
    if isinstance(value, str):
        cleaned = value.strip().replace("%", "")
        try:
            parsed = float(cleaned)
        except ValueError:
            return None
        rounded = int(round(parsed))
        if 0 <= rounded <= 100:
            return rounded
    return None


def _render_key_value_table(title: str, rows: Mapping[str, Any]) -> str:
    row_html = "".join(
        f"<tr><th>{escape(str(k))}</th><td>{escape(str(v))}</td></tr>" for k, v in rows.items()
    )
    return f"""
    <section class=\"card\">
      <h2>{escape(title)}</h2>
      <table>{row_html}</table>
    </section>
    """


def _render_scree_table(scree: Mapping[str, Mapping[str, Any]]) -> str:
    rows = "".join(
        "<tr>"
        f"<th>{escape(pc)}</th>"
        f"<td>{escape(str(values.get('variance', 'N/A')))}</td>"
        f"<td>{escape(str(values.get('rank', 'N/A')))}</td>"
        f"<td>{escape(str(values.get('cumulative variance', 'N/A')))}</td>"
        "</tr>"
        for pc, values in scree.items()
    )
    return f"""
    <section class=\"card\">
      <h2>Scree Analysis</h2>
      <table>
        <thead>
          <tr><th>Component</th><th>Variance</th><th>Rank</th><th>Cumulative variance</th></tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    """


def _render_runtime_coverage_gauges(runtime_coverage: Mapping[str, Any]) -> str:
    rows = []
    for repo, value in runtime_coverage.items():
        pct = _parse_percent(value)
        if pct is None:
            gauge_html = "N/A"
        else:
            gauge_html = f"<progress max=\"100\" value=\"{pct}\"></progress> {pct}%"
        rows.append(
            "<tr>"
            f"<th>{escape(repo)}</th>"
            f"<td>{gauge_html}</td>"
            f"<td>{escape(str(value))}</td>"
            "</tr>"
        )
    return f"""
    <section class=\"card\">
      <h2>Runtime Coverage Gauges</h2>
      <table>
        <thead>
          <tr><th>Repository</th><th>Gauge</th><th>Reported Coverage</th></tr>
        </thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </section>
    """


def _render_gate_rollup_card() -> str:
    return """
    <section class="card">
      <h2>CI Gate Rollup</h2>
      <p>
        Last updated:
        <strong id="gate-rollup-last-updated">N/A</strong>
      </p>
      <table>
        <thead>
          <tr>
            <th>PR</th>
            <th>Status</th>
            <th>First Failed Gate</th>
            <th>Failed Gates</th>
            <th>Total Gates Run</th>
            <th>Last Updated</th>
          </tr>
        </thead>
        <tbody id="gate-rollup-body">
          <tr><td colspan="6">No gate rollup data yet.</td></tr>
        </tbody>
      </table>
    </section>
    """


def _render_dashboard(
    program_overview: Mapping[str, Any],
    federation_status: Mapping[str, Any],
    scree: Mapping[str, Mapping[str, Any]],
    bottleneck: Mapping[str, Any],
    wave_progress: Mapping[str, Any],
    runtime_evidence: Mapping[str, Any],
    truth_matrix: Mapping[str, Any],
    renderability: Mapping[str, Any],
    runtime_coverage: Mapping[str, Any],
) -> str:
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Federation Telemetry Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f7f9fc; color: #162033; }}
    main {{ width: min(1100px, calc(100% - 2rem)); margin: 0 auto; padding: 2rem 0; }}
    h1 {{ margin-top: 0; }}
    .grid {{ display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }}
    .card {{ background: #fff; border: 1px solid #d9e1ec; border-radius: 10px; padding: 1rem; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: .45rem .6rem; border: 1px solid #d9e1ec; }}
    th {{ background: #f0f5fc; }}
    progress {{ width: 120px; vertical-align: middle; }}
  </style>
</head>
<body>
  <main>
    <h1>Federation Telemetry Dashboard</h1>
    <p>
      <a href="./">Home</a> ·
      <a href="cryo/">Cryo</a> ·
      <a href="12-cluster/">12-Cluster</a> ·
      <a href="dow/">DOW</a> ·
      <a href="testing/">Testing</a> ·
      <a href="tools/">Tools</a> ·
      <a href="versions/">Versions</a>
    </p>
    <div class=\"grid\">
      {_render_key_value_table('Program Overview', program_overview)}
      {_render_key_value_table('Federation Status', federation_status)}
      {_render_scree_table(scree)}
      {_render_key_value_table('Bottleneck Report', bottleneck)}
      {_render_key_value_table('Wave Progress Board', wave_progress)}
      {_render_key_value_table('Runtime Evidence', runtime_evidence)}
      {_render_key_value_table('Federation Truth Matrix', truth_matrix)}
      {_render_key_value_table('Renderability', renderability)}
      {_render_runtime_coverage_gauges(runtime_coverage)}
      {_render_gate_rollup_card()}
    </div>
  </main>
  <script>
    (function () {{
      var body = document.getElementById("gate-rollup-body");
      var updated = document.getElementById("gate-rollup-last-updated");

      function safe(value) {{
        if (value === null || value === undefined || value === "") {{
          return "N/A";
        }}
        return String(value);
      }}

      function escapeHtml(value) {{
        return value
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#39;");
      }}

      function renderRows(payload) {{
        var rows = Array.isArray(payload && payload.prs) ? payload.prs : [];
        updated.textContent = safe(payload && payload.generated_at);
        if (!rows.length) {{
          body.innerHTML = '<tr><td colspan="6">No CI gate runs recorded yet.</td></tr>';
          return;
        }}

        body.innerHTML = rows.map(function (row) {{
          var failed = Array.isArray(row.failed_gates) && row.failed_gates.length
            ? row.failed_gates.join(", ")
            : "None";
          return "<tr>"
            + "<th>" + escapeHtml(safe(row.pr_id)) + "</th>"
            + "<td>" + escapeHtml(safe(row.status)) + "</td>"
            + "<td>" + escapeHtml(safe(row.first_failed_gate)) + "</td>"
            + "<td>" + escapeHtml(safe(failed)) + "</td>"
            + "<td>" + escapeHtml(safe(row.total_gates_run)) + "</td>"
            + "<td>" + escapeHtml(safe(row.last_updated)) + "</td>"
            + "</tr>";
        }}).join("");
      }}

      fetch("dashboard-gates.json", {{ cache: "no-store" }})
        .then(function (response) {{
          if (!response.ok) {{
            throw new Error("HTTP " + response.status);
          }}
          return response.json();
        }})
        .then(renderRows)
        .catch(function () {{
          body.innerHTML = '<tr><td colspan="6">Gate rollup feed unavailable.</td></tr>';
        }});
    }})();
  </script>
</body>
</html>
"""


def build_federation_dashboard(
    rollup_path: Optional[Path] = None,
    scree_path: Optional[Path] = None,
    runtime_registry_path: Optional[Path] = None,
    runtime_registry_report_path: Optional[Path] = None,
    bottleneck_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    status_output_path: Optional[Path] = None,
) -> Path:
    resolved_rollup = rollup_path or DEFAULT_ROLLUP_PATH
    resolved_scree = scree_path or DEFAULT_SCREE_PATH
    resolved_runtime_registry = runtime_registry_path or DEFAULT_RUNTIME_REGISTRY_PATH
    resolved_runtime_registry_report = runtime_registry_report_path or DEFAULT_RUNTIME_REGISTRY_REPORT_PATH
    resolved_bottleneck = bottleneck_path or DEFAULT_BOTTLENECK_PATH
    resolved_output = output_path or DEFAULT_OUTPUT_PATH
    resolved_status = status_output_path or DEFAULT_STATUS_OUTPUT_PATH

    rollup = _read_json(resolved_rollup)
    scree = _read_json(resolved_scree)
    runtime_registry = _read_json(resolved_runtime_registry)
    runtime_registry_report = _read_json(resolved_runtime_registry_report)
    bottleneck = _read_json(resolved_bottleneck)
    repo_runtime_rows = _extract_repo_runtime_registry(runtime_registry, runtime_registry_report)

    html = _render_dashboard(
        _extract_program_overview(rollup),
        _extract_federation_status(rollup),
        _extract_scree(scree),
        _extract_bottleneck(bottleneck),
        _extract_wave_progress(rollup),
        _extract_runtime_evidence(repo_runtime_rows),
        _extract_truth_matrix(repo_runtime_rows),
        _extract_renderability(repo_runtime_rows),
        _extract_runtime_coverage(repo_runtime_rows),
    )

    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_text(html, encoding="utf-8")

    all_inputs_present = all(path.exists() for path in (resolved_rollup, resolved_scree, resolved_bottleneck))
    runtime_registry_consumed = all(
        path.exists() for path in (resolved_runtime_registry, resolved_runtime_registry_report)
    )
    status_payload = {
        "wave": "W005.2",
        "status": "dashboard_generated",
        "dashboard_generated": True,
        "github_pages_compatible": True,
        "json_consumed": all_inputs_present,
        "runtime_registry_consumed": runtime_registry_consumed,
    }
    resolved_status.parent.mkdir(parents=True, exist_ok=True)
    resolved_status.write_text(json.dumps(status_payload, indent=2), encoding="utf-8")

    return resolved_output


def main() -> int:
    output = build_federation_dashboard()
    print(f"Generated: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
