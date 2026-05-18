#!/usr/bin/env python3
"""create_dashboard.py — Phase 2 / 3 visualization.

Read the outputs of analyze_repo.py and classify_artifacts.py and emit a
single self-contained HTML dashboard for stakeholder review.

Inputs (auto-detected in --reports dir):
    baseline.json          (from analyze_repo.py)
    classification.csv     (from classify_artifacts.py)
    lineage.md             (from generate_lineage.py, optional)
    validation.json        (from validate_cleanup.py, optional)

Usage:
    python create_dashboard.py --reports reports/ --out reports/dashboard.html
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def read_baseline(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_classification(path: Path) -> tuple[list[dict], dict]:
    if not path.exists():
        return [], {}
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    summary: Counter[str] = Counter(r.get("tag", "Unclassified") for r in rows)
    return rows, dict(summary)


def read_text_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


HTML_TMPL = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<title>Repo analysis dashboard — {repo_name}</title>
<style>
 body{{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;margin:0;background:#0f172a;color:#e2e8f0;}}
 header{{padding:1.4rem 2rem;background:#1e293b;border-bottom:1px solid #334155;}}
 h1{{margin:0;font-size:1.4rem;}}
 main{{padding:2rem;max-width:1200px;margin:0 auto;}}
 section{{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:1.2rem 1.4rem;margin-bottom:1.2rem;}}
 h2{{margin-top:0;font-size:1.05rem;color:#93c5fd;letter-spacing:.02em;text-transform:uppercase;}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:.8rem;}}
 .stat{{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:.8rem;text-align:center;}}
 .stat .num{{font-size:1.6rem;font-weight:700;display:block;color:#facc15;}}
 .stat .lbl{{font-size:.78rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.04em;}}
 table{{width:100%;border-collapse:collapse;font-size:.88rem;}}
 th,td{{padding:.45rem .6rem;border-bottom:1px solid #334155;text-align:left;}}
 th{{background:#0f172a;color:#93c5fd;text-transform:uppercase;font-size:.72rem;letter-spacing:.04em;}}
 .bar{{height:10px;background:#0f172a;border-radius:5px;overflow:hidden;display:flex;}}
 .bar > span{{display:block;height:100%;}}
 .tag-Active{{background:#22c55e;}} .tag-Archived{{background:#3b82f6;}}
 .tag-Stale{{background:#f59e0b;}} .tag-Redundant{{background:#a855f7;}}
 .tag-Corrupted{{background:#ef4444;}} .tag-Unclassified{{background:#64748b;}}
 .legend{{display:flex;gap:.8rem;flex-wrap:wrap;margin:.5rem 0;font-size:.8rem;}}
 .legend span::before{{content:"";display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:.3rem;vertical-align:middle;}}
 .legend .Active::before{{background:#22c55e;}}.legend .Archived::before{{background:#3b82f6;}}
 .legend .Stale::before{{background:#f59e0b;}}.legend .Redundant::before{{background:#a855f7;}}
 .legend .Corrupted::before{{background:#ef4444;}}.legend .Unclassified::before{{background:#64748b;}}
 pre{{background:#0f172a;border:1px solid #334155;border-radius:6px;padding:.8rem;overflow-x:auto;font-size:.78rem;}}
 footer{{padding:1rem 2rem;color:#64748b;text-align:center;font-size:.78rem;}}
</style></head>
<body>
<header>
  <h1>📊 Repo analysis dashboard — {repo_name}</h1>
  <div style="color:#94a3b8;font-size:.85rem;margin-top:.2rem;">{generated_at}</div>
</header>
<main>
  <section>
    <h2>Snapshot</h2>
    <div class="grid">
      <div class="stat"><span class="num">{total_files}</span><span class="lbl">Files</span></div>
      <div class="stat"><span class="num">{commits}</span><span class="lbl">Commits</span></div>
      <div class="stat"><span class="num">{contributors}</span><span class="lbl">Contributors</span></div>
      <div class="stat"><span class="num">{workflow_count}</span><span class="lbl">Workflows</span></div>
      <div class="stat"><span class="num">{tags_total}</span><span class="lbl">Tags</span></div>
      <div class="stat"><span class="num">{score}</span><span class="lbl">Est. score / 100</span></div>
    </div>
  </section>

  <section>
    <h2>Artifact classification</h2>
    <div class="legend">
      <span class="Active">Active</span>
      <span class="Archived">Archived</span>
      <span class="Stale">Stale</span>
      <span class="Redundant">Redundant</span>
      <span class="Corrupted">Corrupted</span>
      <span class="Unclassified">Unclassified</span>
    </div>
    <div class="bar">{bar_segments}</div>
    <table>
      <thead><tr><th>Tag</th><th>Count</th><th>% of total</th></tr></thead>
      <tbody>{tag_rows}</tbody>
    </table>
  </section>

  <section>
    <h2>Languages (by file count)</h2>
    <table>
      <thead><tr><th>Language</th><th>Files</th></tr></thead>
      <tbody>{lang_rows}</tbody>
    </table>
  </section>

  <section>
    <h2>Documentation & governance presence</h2>
    <table>
      <thead><tr><th>Item</th><th>Status</th></tr></thead>
      <tbody>{doc_rows}</tbody>
    </table>
  </section>

  <section>
    <h2>Workflows</h2>
    <pre>{workflows}</pre>
  </section>

  <section>
    <h2>Lineage (excerpt)</h2>
    <pre>{lineage_excerpt}</pre>
  </section>
</main>
<footer>Generated by repo_analysis_toolkit · create_dashboard.py</footer>
</body></html>
"""


def render(repo_name: str, baseline: dict, summary: dict, rows: list[dict],
           lineage_md: str) -> str:
    files = baseline.get("files", {})
    git = baseline.get("git", {})
    docs = baseline.get("docs", {})
    ci = baseline.get("ci", {})

    total = sum(summary.values()) or 1
    bar_segments = "".join(
        f'<span class="tag-{tag}" style="width:{count/total*100:.1f}%" title="{tag}: {count}"></span>'
        for tag, count in sorted(summary.items(), key=lambda kv: -kv[1])
    )
    tag_rows = "".join(
        f"<tr><td>{html.escape(tag)}</td><td>{count}</td><td>{count/total*100:.1f}%</td></tr>"
        for tag, count in sorted(summary.items(), key=lambda kv: -kv[1])
    )
    lang_rows = "".join(
        f"<tr><td>{html.escape(l)}</td><td>{c}</td></tr>"
        for l, c in (files.get("languages_by_count") or [])[:12]
    )
    doc_rows = "".join(
        f"<tr><td>{html.escape(k)}</td><td>{'✅' if v else '❌'}</td></tr>"
        for k, v in [
            ("README at root", bool(docs.get("readmes_at_root"))),
            ("`docs/` directory", docs.get("docs_dir")),
            ("`docs_versioned/`", docs.get("docs_versioned")),
            ("CONTRIBUTING.md", docs.get("contributing_md")),
            ("LICENSE", docs.get("license_present")),
            ("SECURITY.md", docs.get("security_md")),
            ("PR template", ci.get("pr_template")),
            ("Issue templates", bool(ci.get("issue_templates"))),
            ("Dependabot config", ci.get("dependabot")),
        ]
    )
    wf_text = "\n".join(ci.get("workflows", [])) or "(none)"

    lineage_excerpt = lineage_md[:2000] if lineage_md else "(no lineage report found)"
    return HTML_TMPL.format(
        repo_name=html.escape(repo_name or baseline.get("repo_name", "—")),
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_files=files.get("total_files", "—"),
        commits=git.get("commits", "—"),
        contributors=git.get("contributors_total", "—"),
        workflow_count=ci.get("workflow_count", 0),
        tags_total=git.get("tags_total", 0),
        score=baseline.get("estimated_health_score", "—"),
        bar_segments=bar_segments or "<span></span>",
        tag_rows=tag_rows or "<tr><td colspan='3'>No data</td></tr>",
        lang_rows=lang_rows or "<tr><td colspan='2'>No data</td></tr>",
        doc_rows=doc_rows,
        workflows=html.escape(wf_text),
        lineage_excerpt=html.escape(lineage_excerpt),
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DMAIC visualization — build an HTML dashboard")
    ap.add_argument("--reports", required=True, help="Reports directory containing baseline.json / classification.csv")
    ap.add_argument("--out", default="reports/dashboard.html")
    ap.add_argument("--repo-name", default=None)
    args = ap.parse_args(argv)

    rdir = Path(args.reports)
    baseline = read_baseline(rdir / "baseline.json")
    rows, summary = read_classification(rdir / "classification.csv")
    lineage_md = read_text_if_exists(rdir / "lineage.md")
    html_out = render(args.repo_name or baseline.get("repo_name", "—"), baseline, summary, rows, lineage_md)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_out, encoding="utf-8")
    print(f"[create_dashboard] wrote {out_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
