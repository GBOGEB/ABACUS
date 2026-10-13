#!/usr/bin/env python3
"""
ABACUS Security Dashboard Generator
Fetches all code-scanning alerts from GitHub, groups them by tool and REX
category, and writes:
  - .github/security/dashboard.md   (human-readable, committed to repo)
  - aggregates only, without per-alert file paths or messages

Run locally:  GITHUB_TOKEN=<pat> GITHUB_REPO=GBOGEB/ABACUS python security_dashboard.py
Run in CI:    Called by .github/workflows/security-dashboard.yml
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from http.client import HTTPSConnection
from urllib.parse import urlsplit

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
    """Fetch code-scanning pages from one HTTPS origin, without redirects.

    An untrusted GitHub Link header must never receive the bearer token on
    another host or change the API resource being read.
    """
    results = []
    expected_path = path.split("?", 1)[0]
    allowed_paths = {expected_path}
    # GitHub may canonicalize this public repository's code-scanning route
    # to its stable numeric repository ID in the Link header.
    if REPO == "GBOGEB/ABACUS" and expected_path == (
        "/repos/GBOGEB/ABACUS/code-scanning/alerts"
    ):
        allowed_paths.add("/repositories/1054507184/code-scanning/alerts")
    url = f"{API_BASE}{path}"
    while url:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "api.github.com"
            or parsed.path not in allowed_paths
            or parsed.fragment
        ):
            raise ValueError("Unsafe GitHub pagination URL")

        target = parsed.path
        if parsed.query:
            target += "?" + parsed.query
        connection = HTTPSConnection("api.github.com", timeout=20)
        try:
            connection.request(
                "GET",
                target,
                headers={
                    "Authorization": f"Bearer {TOKEN}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            response = connection.getresponse()
            if response.status != 200:
                raise RuntimeError(
                    f"GitHub code-scanning API returned HTTP {response.status}"
                )
            data = json.loads(response.read())
            if not isinstance(data, list):
                raise ValueError("Expected list of code-scanning alerts")
            results.extend(data)
            link = response.getheader("Link", "")
        finally:
            connection.close()

        url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part.split(";", 1)[0].strip().strip("<>")
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
    """Render aggregate-only Markdown; never publish alert-level source data."""
    lines = [
        "# ABACUS Security Dashboard",
        "",
        f"> Auto-generated {tel['generated_at']} from GitHub code scanning",
        f"> **{tel['total_open']} open alerts** across "
        f"{len(tel['by_tool'])} tools",
        "",
        "## Severity counts",
        "",
    ]
    for sev, count in sorted(
        tel["by_severity"].items(),
        key=lambda item: (SEVERITY_ORDER.get(item[0], 9), item[0]),
    ):
        lines.append(f"- {sev}: {count}")

    lines.extend(["", "## Scanner counts", ""])
    for tool, count in sorted(
        tel["by_tool"].items(), key=lambda item: (-item[1], item[0])
    ):
        lines.append(f"- {tool}: {count}")

    lines.extend(["", "## REX group counts", ""])
    for group, count in sorted(
        tel["by_rex_group"].items(), key=lambda item: (-item[1], item[0])
    ):
        risk = REX_META.get(group, REX_META["OTHER"])["risk"]
        lines.append(f"- {group} ({risk}): {count}")

    lines.extend(
        [
            "",
            "## Source and limitations",
            "",
            "Individual findings, source file paths and evidence belong in the",
            "repository Security code-scanning interface. These aggregate",
            "counts do not constitute acceptance or formal engineering credit.",
            "",
            f"_Dashboard last updated: {tel['generated_at']}_",
            "",
        ]
    )
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
        rendered = _val(v)
        sep = "" if rendered.startswith("\n") else " "
        lines.append(f"{k}:{sep}{rendered}")
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
    return "\n".join(lines) + "\n"


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

    md_path = out_dir / "dashboard.md"

    # Per-alert details stay in the authoritative code-scanning service.
    # No raw alert snapshot is published into this public worktree.
    md_path.write_text(render_markdown(tel), encoding="utf-8")
    print(f"  → Wrote {md_path}")
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
