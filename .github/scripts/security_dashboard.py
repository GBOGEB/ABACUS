#!/usr/bin/env python3
"""
ABACUS Security Dashboard Generator
Fetches all code-scanning alerts from GitHub, groups them by tool and REX
category, and writes:
  - .github/security/dashboard.md   (human-readable, committed to repo)
  - .github/security/alerts.yaml    (machine-readable telemetry)

Run locally:  GITHUB_TOKEN=<pat> GITHUB_REPO=GBOGEB/ABACUS python security_dashboard.py
Run in CI:    Called by .github/workflows/security-dashboard.yml
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

REPO     = os.environ.get("GITHUB_REPO", "GBOGEB/ABACUS")
TOKEN    = os.environ.get("GITHUB_TOKEN", "")
API_BASE = "https://api.github.com"

# REX group taxonomy — matches [rex.groups.*] in security.toml
# Maps (tool_name_fragment, rule_id_prefix) → REX group name
REX_MAP = {
    # CodeQL rules
    "py/shell-command-constructed-from-input": "SEC_SUBPROCESS",
    "py/path-injection":                       "SEC_PATH_TRAVERSAL",
    "py/code-injection":                       "SEC_COMPILE_EXEC",
    "py/unused-import":                        "QUAL_DEAD_CODE",
    "py/unused-local-variable":                "QUAL_DEAD_CODE",
    # Bandit / Semgrep / Ruff map by prefix
    "B101": "SEC_ASSERT",   "S101": "SEC_ASSERT",
    "B102": "SEC_COMPILE_EXEC", "S102": "SEC_COMPILE_EXEC",
    "B108": "SEC_TEMPFILE",  "S108": "SEC_TEMPFILE",
    "B602": "SEC_SUBPROCESS", "S602": "SEC_SUBPROCESS",
    "B603": "SEC_SUBPROCESS", "S603": "SEC_SUBPROCESS",
    "B604": "SEC_SUBPROCESS", "S604": "SEC_SUBPROCESS",
    "B105": "SEC_HARDCODED_SECRET", "B106": "SEC_HARDCODED_SECRET",
    "B301": "SEC_DESERIALIZATION", "B302": "SEC_DESERIALIZATION",
    "B506": "SEC_YAML_LOAD",
    "B324": "SEC_WEAK_HASH",
    "F401": "QUAL_DEAD_CODE", "F841": "QUAL_DEAD_CODE",
    # Semgrep
    "python.lang.security.audit.subprocess-shell-true": "SEC_SUBPROCESS",
    "python.lang.security.audit.hardcoded-password":    "SEC_HARDCODED_SECRET",
    "python.lang.security.audit.pickle":                "SEC_DESERIALIZATION",
    "python.lang.security.audit.yaml-load":             "SEC_YAML_LOAD",
    "python.lang.security.insecure-hash-algorithms":    "SEC_WEAK_HASH",
}

REX_META = {
    "SEC_SUBPROCESS":       {"risk": "HIGH",   "emoji": "🔴"},
    "SEC_PATH_TRAVERSAL":   {"risk": "HIGH",   "emoji": "🔴"},
    "SEC_HARDCODED_SECRET": {"risk": "HIGH",   "emoji": "🔴"},
    "SEC_COMPILE_EXEC":     {"risk": "MEDIUM", "emoji": "🟠"},
    "SEC_TEMPFILE":         {"risk": "MEDIUM", "emoji": "🟠"},
    "SEC_DESERIALIZATION":  {"risk": "MEDIUM", "emoji": "🟠"},
    "SEC_YAML_LOAD":        {"risk": "MEDIUM", "emoji": "🟠"},
    "SEC_WEAK_HASH":        {"risk": "MEDIUM", "emoji": "🟠"},
    "SEC_ASSERT":           {"risk": "LOW",    "emoji": "🟡"},
    "QUAL_DEAD_CODE":       {"risk": "LOW",    "emoji": "🟡"},
    "OTHER":                {"risk": "INFO",   "emoji": "⚪"},
}

SEVERITY_ORDER = {"critical": 0, "high": 1, "error": 1,
                  "medium": 2, "warning": 2, "low": 3,
                  "note": 4, "none": 5}


def gh_get(path: str) -> list:
    """Paginate through GitHub API and collect all results."""
    results = []
    url = f"{API_BASE}{path}"
    while url:
        req = Request(url, headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        try:
            with urlopen(req) as r:
                data = json.loads(r.read())
                results.extend(data if isinstance(data, list) else [data])
                link = r.headers.get("Link", "")
                url = None
                for part in link.split(","):
                    if 'rel="next"' in part:
                        url = part.split(";")[0].strip().strip("<>")
        except HTTPError as e:
            print(f"GitHub API error {e.code}: {e.reason} — {path}", file=sys.stderr)
            break
    return results


def classify_rex(rule_id: str) -> str:
    """Map a rule ID to a REX group name."""
    if rule_id in REX_MAP:
        return REX_MAP[rule_id]
    for prefix, group in REX_MAP.items():
        if rule_id.startswith(prefix):
            return group
    return "OTHER"


def fetch_alerts(state: str = "open") -> list:
    alerts = gh_get(f"/repos/{REPO}/code-scanning/alerts?per_page=100&state={state}")
    return alerts


def build_telemetry(alerts: list) -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    by_tool:     dict = defaultdict(list)
    by_rex:      dict = defaultdict(list)
    by_severity: dict = defaultdict(int)
    by_file:     dict = defaultdict(int)

    for a in alerts:
        tool    = a.get("tool", {}).get("name", "unknown")
        rule_id = a.get("rule", {}).get("id", "")
        sev     = a.get("rule", {}).get("severity", "none").lower()
        inst    = a.get("most_recent_instance", {})
        fpath   = inst.get("location", {}).get("path", "unknown")
        line    = inst.get("location", {}).get("start_line", 0)
        msg     = inst.get("message", {}).get("text", "")
        number  = a.get("number")
        url     = a.get("html_url", "")

        rex = classify_rex(rule_id)

        entry = {
            "number":  number,
            "tool":    tool,
            "rule_id": rule_id,
            "severity": sev,
            "file":    fpath,
            "line":    line,
            "message": msg[:120],
            "rex":     rex,
            "url":     url,
        }

        by_tool[tool].append(entry)
        by_rex[rex].append(entry)
        by_severity[sev] += 1
        by_file[fpath] += 1

    # Top 10 hottest files
    hotfiles = sorted(by_file.items(), key=lambda x: -x[1])[:10]

    return {
        "generated_at": now,
        "repo":         REPO,
        "total_open":   len(alerts),
        "by_severity":  dict(by_severity),
        "by_tool":      {t: len(v) for t, v in by_tool.items()},
        "by_rex_group": {g: len(v) for g, v in by_rex.items()},
        "hot_files":    [{"file": f, "count": c} for f, c in hotfiles],
        "groups":       {
            rex: sorted(items, key=lambda x: SEVERITY_ORDER.get(x["severity"], 9))
            for rex, items in by_rex.items()
        },
    }


def render_markdown(tel: dict) -> str:
    ts    = tel["generated_at"]
    total = tel["total_open"]
    lines = []

    lines.append(f"# ABACUS Security Dashboard")
    lines.append(f"> Auto-generated {ts} · repo: `{tel['repo']}`  ")
    lines.append(f"> **{total} open alerts** across {len(tel['by_tool'])} tools")
    lines.append("")

    # ── Severity summary ──────────────────────────────────────────────────────
    lines.append("## Severity Overview")
    lines.append("")
    lines.append("| Severity | Count |")
    lines.append("|----------|------:|")
    for sev in ["critical", "high", "error", "medium", "warning", "low", "note", "none"]:
        c = tel["by_severity"].get(sev, 0)
        if c:
            lines.append(f"| {sev.capitalize()} | {c} |")
    lines.append("")

    # ── Per-tool counts ───────────────────────────────────────────────────────
    lines.append("## Alerts by Tool")
    lines.append("")
    lines.append("| Tool | Open Alerts |")
    lines.append("|------|------------:|")
    for tool, cnt in sorted(tel["by_tool"].items(), key=lambda x: -x[1]):
        lines.append(f"| {tool} | {cnt} |")
    lines.append("")

    # ── REX group summary ─────────────────────────────────────────────────────
    lines.append("## REX Group Summary")
    lines.append("_Groups are defined in [security.toml](security.toml)_")
    lines.append("")
    lines.append("| REX Group | Risk | Count | Fix Priority |")
    lines.append("|-----------|------|------:|-------------|")
    risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}
    sorted_groups = sorted(
        tel["by_rex_group"].items(),
        key=lambda x: (risk_order.get(REX_META.get(x[0], {}).get("risk", "INFO"), 9), -x[1])
    )
    for rex, cnt in sorted_groups:
        meta  = REX_META.get(rex, REX_META["OTHER"])
        emoji = meta["emoji"]
        risk  = meta["risk"]
        pri   = "Fix now" if risk == "HIGH" else ("Fix next sprint" if risk == "MEDIUM" else "Suppress / defer")
        lines.append(f"| {emoji} {rex} | {risk} | {cnt} | {pri} |")
    lines.append("")

    # ── Hot files ─────────────────────────────────────────────────────────────
    lines.append("## Hottest Files (most alerts)")
    lines.append("")
    lines.append("| File | Alert Count |")
    lines.append("|------|------------:|")
    for entry in tel["hot_files"]:
        lines.append(f"| `{entry['file']}` | {entry['count']} |")
    lines.append("")

    # ── Per-group detail ──────────────────────────────────────────────────────
    lines.append("## Alert Detail by REX Group")
    lines.append("")
    for rex, cnt in sorted_groups:
        if cnt == 0:
            continue
        meta  = REX_META.get(rex, REX_META["OTHER"])
        items = tel["groups"].get(rex, [])
        lines.append(f"### {meta['emoji']} {rex} ({cnt} alerts)")
        lines.append("")
        lines.append("| # | Tool | Rule | File | Line | Severity |")
        lines.append("|---|------|------|------|-----:|---------:|")
        for it in items[:30]:   # cap at 30 rows per group in the MD
            num  = f"[{it['number']}]({it['url']})" if it.get("url") else str(it["number"])
            tool = it["tool"].replace("CodeQL", "CodeQL").replace("Bandit", "Bandit")
            lines.append(
                f"| {num} | {tool} | `{it['rule_id']}` "
                f"| `{it['file'].split('/')[-1]}` | {it['line']} | {it['severity']} |"
            )
        if len(items) > 30:
            lines.append(f"| … | _{len(items) - 30} more — see alerts.yaml_ | | | | |")
        lines.append("")

    # ── Quick-win table ───────────────────────────────────────────────────────
    lines.append("## Quick-Win Fix Order")
    lines.append("")
    lines.append("| Priority | REX Group | Est. Alerts | Action |")
    lines.append("|----------|-----------|------------:|--------|")
    quick_wins = [
        (1, "SEC_SUBPROCESS",       "~40", "Add `# noqa: S603` — all calls use list-form args"),
        (2, "SEC_PATH_TRAVERSAL",   "~20", "`pathlib.Path(p).resolve(); assert is_relative_to(BASE)`"),
        (3, "SEC_COMPILE_EXEC",     "~10", "Replace `compile+exec` with `ast.parse()` (syntax-only)"),
        (4, "SEC_TEMPFILE",         "~15", "Remove `delete=False` from `NamedTemporaryFile`"),
        (5, "SEC_ASSERT",           "~10", "Add `# noqa: S101` in pytest files, raise in prod"),
        (6, "QUAL_DEAD_CODE",       "~30", "`ruff check --fix --select F401,F841 DMAIC_V3/`"),
    ]
    for pri, rex, est, action in quick_wins:
        cnt = tel["by_rex_group"].get(rex, 0)
        lines.append(f"| {pri} | {rex} | {cnt} live / {est} est. | {action} |")
    lines.append("")
    lines.append(f"_Dashboard last updated: {ts}_")

    return "\n".join(lines)


def render_yaml(tel: dict) -> str:
    """Minimal YAML serializer (no external deps)."""
    def _val(v, indent=0):
        pad = "  " * indent
        if isinstance(v, dict):
            if not v:
                return "{}"
            rows = [f"\n{pad}  {k}: {_val(vv, indent + 1)}" for k, vv in v.items()]
            return "".join(rows)
        if isinstance(v, list):
            if not v:
                return "[]"
            rows = []
            for item in v:
                if isinstance(item, dict):
                    first = True
                    for k2, v2 in item.items():
                        prefix = f"\n{pad}  - " if first else f"\n{pad}    "
                        rows.append(f"{prefix}{k2}: {_val(v2, indent + 2)}")
                        first = False
                else:
                    rows.append(f"\n{pad}  - {item}")
            return "".join(rows)
        if isinstance(v, str):
            if any(c in v for c in [":", "#", "[", "]", "{"]):
                return f'"{v}"'
            return v
        return str(v)

    lines = ["# ABACUS Security Telemetry — machine-readable",
             f"# generated: {tel['generated_at']}",
             ""]
    for k, v in tel.items():
        if k == "groups":
            continue   # groups go in separate block to keep yaml readable
        lines.append(f"{k}:{_val(v)}")
    lines.append("")
    lines.append("groups:")
    for rex, items in tel["groups"].items():
        lines.append(f"  {rex}:")
        for it in items:
            lines.append(f"    - number: {it['number']}")
            lines.append(f"      tool: {it['tool']}")
            lines.append(f"      rule_id: \"{it['rule_id']}\"")
            lines.append(f"      severity: {it['severity']}")
            lines.append(f"      file: \"{it['file']}\"")
            lines.append(f"      line: {it['line']}")
    return "\n".join(lines)


def main():
    if not TOKEN:
        print("ERROR: GITHUB_TOKEN not set.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching open code-scanning alerts for {REPO}…")
    alerts = fetch_alerts("open")
    print(f"  → {len(alerts)} open alerts fetched")

    tel = build_telemetry(alerts)

    out_dir = Path(".github/security")
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path   = out_dir / "dashboard.md"
    yaml_path = out_dir / "alerts.yaml"

    md_path.write_text(render_markdown(tel), encoding="utf-8")
    yaml_path.write_text(render_yaml(tel),   encoding="utf-8")

    print(f"  → Wrote {md_path}")
    print(f"  → Wrote {yaml_path}")
    print(f"\nSummary:")
    print(f"  Total open : {tel['total_open']}")
    for tool, cnt in sorted(tel["by_tool"].items(), key=lambda x: -x[1]):
        print(f"  {tool:30s}: {cnt}")
    print(f"\nREX groups:")
    for rex, cnt in sorted(tel["by_rex_group"].items(),
                           key=lambda x: -x[1]):
        meta = REX_META.get(rex, REX_META["OTHER"])
        print(f"  {meta['emoji']} {rex:30s}: {cnt} [{meta['risk']}]")


if __name__ == "__main__":
    main()
