#!/usr/bin/env python3
"""
Generate docs HTML entry page and dashboard from docs/manifest.yml.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT_DIR / "docs"
MANIFEST_FILE = DOCS_DIR / "manifest.yml"


def _parse_manifest() -> Dict[str, Any]:
    if not MANIFEST_FILE.exists():
        return {"site": {"title": "ABACUS Docs", "version": "unknown"}, "articles": [], "smoke_tested_repos": []}

    try:
        import yaml
        return yaml.safe_load(MANIFEST_FILE.read_text(encoding="utf-8")) or {}
    except ImportError:
        pass
    except Exception:
        pass

    # Minimal fallback parser for simple key/list YAML structure
    data: Dict[str, Any] = {"site": {}, "articles": [], "smoke_tested_repos": []}
    section = None
    for raw in MANIFEST_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith(":") and not line.startswith("-"):
            section = line[:-1]
            if section not in data:
                data[section] = {}
            continue
        if line.startswith("- "):
            if section and isinstance(data.get(section), list):
                data[section].append(line[2:].strip())
            continue
        if ":" in line and section == "site":
            k, v = [part.strip() for part in line.split(":", 1)]
            data["site"][k] = v
    return data


def _safe_read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _build_index_html(manifest: Dict[str, Any]) -> str:
    site = manifest.get("site", {}) if isinstance(manifest, dict) else {}
    title = site.get("title", "ABACUS Project Docs")
    version = site.get("version", "unknown")
    articles: List[str] = manifest.get("articles", []) if isinstance(manifest, dict) else []
    repos: List[str] = manifest.get("smoke_tested_repos", []) if isinstance(manifest, dict) else []
    article_links = "\n".join(
        f'<li><a href="{a}">{a}</a></li>' for a in articles
    ) or "<li>No articles listed</li>"
    repo_links = "\n".join(
        f'<li><a href="https://github.com/{r}" target="_blank" rel="noopener">{r}</a></li>' for r in repos
    ) or "<li>No repositories listed</li>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} - Entry</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; max-width: 960px; }}
    .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }}
    code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p><strong>Version:</strong> {version}</p>
  <p>This is the HTML entrypoint for ABACUS docs navigation.</p>
  <div class="card">
    <h2>Documentation</h2>
    <ul>
      <li><a href="index.md">Markdown hub</a></li>
      {article_links}
    </ul>
  </div>
  <div class="card">
    <h2>Repository Navigation</h2>
    <ul>
      <li><a href="https://github.com/GBOGEB/ABACUS/tree/main/DMAIC_V3" target="_blank" rel="noopener">DMAIC_V3/</a></li>
      <li><a href="https://github.com/GBOGEB/ABACUS/tree/main/.github/workflows" target="_blank" rel="noopener">.github/workflows/</a></li>
      <li><a href="https://github.com/GBOGEB/ABACUS/tree/main/handover" target="_blank" rel="noopener">handover/</a></li>
      <li><a href="dashboard.html">System dashboard</a></li>
    </ul>
  </div>
  <div class="card">
    <h2>Smoke-tested Repositories</h2>
    <ul>{repo_links}</ul>
  </div>
  <p><small>Generated: {datetime.now().isoformat()}</small></p>
</body>
</html>
"""


def _build_dashboard_html(manifest: Dict[str, Any]) -> str:
    maturity = _safe_read_json(ROOT_DIR / "maturity_assessment.json")
    convergence = _safe_read_json(ROOT_DIR / "DMAIC_V3" / "state" / "convergence_status.json")

    maturity_score = maturity.get("overall_score", "n/a") if isinstance(maturity, dict) else "n/a"
    convergence_status = convergence.get("status", "unknown") if isinstance(convergence, dict) else "unknown"
    repos_count = len(manifest.get("smoke_tested_repos", [])) if isinstance(manifest, dict) else 0
    articles_count = len(manifest.get("articles", [])) if isinstance(manifest, dict) else 0

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ABACUS System Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; max-width: 960px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; }}
    .tile {{ border: 1px solid #ddd; border-radius: 8px; padding: 1rem; }}
    .label {{ color: #555; font-size: 0.9rem; }}
    .value {{ font-size: 1.4rem; font-weight: 700; }}
    nav a {{ margin-right: 1rem; text-decoration: none; color: #0969da; }}
    nav a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <nav>
    <a href="./">Home</a>
    <a href="cryo/">Cryo</a>
    <a href="12-cluster/">12-Cluster</a>
    <a href="dow/">DOW</a>
    <a href="testing/">Testing</a>
    <a href="tools/">Tools</a>
    <a href="versions/">Versions</a>
  </nav>
  <h1>ABACUS State of System</h1>
  <p><a href="index.html">Back to HTML entry</a></p>
  <div class="grid">
    <div class="tile"><div class="label">Idempotency Contract</div><div class="value">Enabled</div></div>
    <div class="tile"><div class="label">Lineage Source</div><div class="value">Persistent Provenance</div></div>
    <div class="tile"><div class="label">Convergence Status</div><div class="value">{convergence_status}</div></div>
    <div class="tile"><div class="label">Maturity Score</div><div class="value">{maturity_score}</div></div>
    <div class="tile"><div class="label">Docs Articles</div><div class="value">{articles_count}</div></div>
    <div class="tile"><div class="label">Integrated Repos</div><div class="value">{repos_count}</div></div>
  </div>
  <p><small>Generated: {datetime.now().isoformat()}</small></p>
</body>
</html>
"""


def main() -> int:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = _parse_manifest()
    (DOCS_DIR / "index.html").write_text(_build_index_html(manifest), encoding="utf-8")
    (DOCS_DIR / "dashboard.html").write_text(_build_dashboard_html(manifest), encoding="utf-8")
    print("[OK] Generated docs/index.html and docs/dashboard.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
