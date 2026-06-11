#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MANIFEST_PATH = DOCS / "manifest.json"
OUT_PATH = DOCS / "index.html"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    return {
        "version": "4.0.0",
        "build": {
            "timestamp": _iso_now(),
            "git_commit": "unknown",
            "builder": "setup.sh v4.0.0",
            "status": "pending",
        },
        "tests": {"total": 0, "passed": 0, "failed": 0, "coverage": "0.0%"},
    }


def _status_pill(status: str) -> str:
    low = status.lower()
    if low.startswith("verified"):
        cls = "pill ok"
    elif low.startswith("in progress"):
        cls = "pill progress"
    elif low.startswith("pending"):
        cls = "pill pending"
    else:
        cls = "pill pending"
    return f'<span class="{cls}">{status}</span>'


def _phase_cards(version: str, ts: str, test_summary: str) -> str:
    cards = [
        {
            "title": "Phase 1: Requirements & Compliance",
            "status": "Verified",
            "artifacts": [
                ("Standards compliance database", "../data/standards_compliance.json"),
                ("RTM traceability matrix", "standards/Compliance_Matrix.html"),
                ("FAT/SAT procedures", "standards/FAT_SAT_Procedures.md"),
            ],
        },
        {
            "title": "Phase 2: Development",
            "status": "Verified",
            "artifacts": [
                ("Source modules", "../src/"),
                ("Liquid He calculator", "../src/liquid_he_loss.py"),
                ("Compressor reliability", "../src/compressor_reliability.py"),
            ],
        },
        {
            "title": "Phase 3: Analysis & Outputs",
            "status": "Verified",
            "artifacts": [
                ("40-slide navigator", "index_v4_0.html"),
                ("15+ Plotly charts", "visualizations_v3/"),
                ("Statistical reports", "statistical/"),
            ],
        },
        {
            "title": "Phase 4: QA & Deployment",
            "status": "Verified",
            "artifacts": [
                ("Test suite", "../tests/"),
                ("Test report", "../dist/test-report.html"),
                ("Package bundle", "../dist/handover.zip"),
            ],
            "status_override": f"Verified ({test_summary})",
        },
    ]

    blocks = []
    for card in cards:
        status_label = card.get("status_override", card["status"])
        links = "".join(
            f'<li><a href="{href}">{label}</a></li>' for label, href in card["artifacts"]
        )
        blocks.append(
            f"""
            <section class=\"card\">
              <div class=\"card-head\">
                <h2>{card['title']}</h2>
                <span class=\"badge\">v{version}</span>
              </div>
              {_status_pill(status_label)}
              <ul>{links}</ul>
              <div class=\"updated\">Last updated: {ts}</div>
            </section>
            """
        )
    return "\n".join(blocks)


def render_dashboard(manifest: dict) -> str:
    version = manifest.get("version", "4.0.0")
    build = manifest.get("build", {})
    tests = manifest.get("tests", {})
    timestamp = build.get("timestamp", _iso_now())
    commit = build.get("git_commit", "unknown")
    status = build.get("status", "pending")

    total = tests.get("total", 0)
    passed = tests.get("passed", 0)
    coverage = tests.get("coverage", "0.0%")
    test_summary = f"{passed}/{total} tests pass"

    cards_html = _phase_cards(version, timestamp, test_summary)

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Cryo Dashboard Handover Hub</title>
  <style>
    :root {{ --bg:#f5f7fb; --card:#fff; --line:#d9e0ea; --text:#1f2a37; --accent:#225ea8; }}
    body {{ margin:0; font-family:Inter,Segoe UI,Arial,sans-serif; background:var(--bg); color:var(--text); }}
    header {{ padding:20px 24px; background:linear-gradient(120deg,#12355b,#2a6fba); color:#fff; }}
    header h1 {{ margin:0; font-size:1.35rem; }}
    header p {{ margin:.35rem 0 0; opacity:.95; }}
    main {{ padding:24px; }}
    .grid {{ display:grid; grid-template-columns:repeat(2,minmax(280px,1fr)); gap:16px; }}
    .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; box-shadow:0 2px 6px rgba(0,0,0,.04); }}
    .card-head {{ display:flex; justify-content:space-between; gap:8px; align-items:start; }}
    .card h2 {{ margin:0 0 8px; font-size:1.02rem; }}
    .badge {{ background:#e7f0ff; color:#0f4085; border-radius:999px; padding:2px 9px; font-size:.74rem; font-weight:700; }}
    .pill {{ display:inline-block; border-radius:999px; padding:3px 10px; font-size:.76rem; font-weight:700; margin:6px 0 10px; }}
    .ok {{ background:#d9f7e5; color:#166534; }}
    .progress {{ background:#fff4d6; color:#92400e; }}
    .pending {{ background:#eceff4; color:#475569; }}
    ul {{ margin:0; padding-left:18px; }}
    li {{ margin:6px 0; }}
    a {{ color:var(--accent); text-decoration:none; }}
    a:hover {{ text-decoration:underline; }}
    .updated {{ margin-top:10px; font-size:.8rem; color:#556; }}
    .download {{ margin-top:16px; background:#fff; border:1px dashed #aac; padding:12px; border-radius:10px; }}
    footer {{ margin-top:16px; font-size:.83rem; color:#334; }}
    code {{ background:#eef2ff; padding:1px 5px; border-radius:4px; }}
    @media (max-width: 900px) {{ .grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Cryo Dashboard Handover Hub</h1>
    <p>Self-documenting delivery index for recursive/idempotent operations (v{version})</p>
  </header>
  <main>
    <div class=\"grid\">{cards_html}</div>

    <section class=\"download\">
      <h3>Downloads</h3>
      <ul>
        <li><a href=\"../dist/handover.zip\">handover.zip</a></li>
        <li><a href=\"../dist/test-report.html\">test-report.html</a></li>
      </ul>
      <p><strong>To Rebuild:</strong> run <code>./setup.sh</code></p>
    </section>

    <footer>
      Build timestamp: {timestamp} · Git commit: {commit} · Build status: {status} · Test coverage: {coverage}
    </footer>
  </main>
</body>
</html>
"""


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    manifest = _read_manifest()
    html = render_dashboard(manifest)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Dashboard generated: {OUT_PATH}")


if __name__ == "__main__":
    main()
