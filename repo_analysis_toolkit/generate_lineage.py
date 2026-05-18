#!/usr/bin/env python3
"""generate_lineage.py — Phase 2 / DMAIC Measure.

Walk git history and produce:
    - A Markdown lineage report (LINEAGE_ANALYSIS.md).
    - A Mermaid block describing branch/tag ancestry (embedded in the .md).
    - Optionally an SVG diagram if --diagram is given and Mermaid CLI is installed.

Notes:
    - We rely on `git for-each-ref` and `git log` only. No third-party git library.
    - Abandoned branch heuristic: no commits for `abandoned_branch_days` (default 180).

Usage:
    python generate_lineage.py --repo /path/to/repo --out reports/lineage.md
    python generate_lineage.py --repo . --out reports/lineage.md --diagram reports/lineage.svg
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


def load_config(path: str | None) -> dict:
    if not path or yaml is None:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=False,
    )
    return out.stdout


def collect_tags(repo: Path) -> list[dict]:
    raw = git(repo, "for-each-ref", "--sort=creatordate",
              "--format=%(refname:short)|%(creatordate:iso8601)|%(objectname:short)",
              "refs/tags")
    tags: list[dict] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        name, _, rest = line.partition("|")
        date, _, sha = rest.partition("|")
        tags.append({"name": name, "date": date, "sha": sha})
    return tags


def collect_branches(repo: Path, abandoned_after_days: int) -> list[dict]:
    raw = git(repo, "for-each-ref", "--sort=-committerdate",
              "--format=%(refname:short)|%(committerdate:iso8601)|%(authorname)",
              "refs/heads", "refs/remotes")
    branches: list[dict] = []
    now = datetime.now(timezone.utc)
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        name, date, author = parts[0], parts[1], parts[2]
        abandoned = False
        try:
            dt = datetime.strptime(date, "%Y-%m-%d %H:%M:%S %z") if date else None
        except ValueError:
            try:
                dt = datetime.fromisoformat(date.replace(" ", "T", 1)) if date else None
            except ValueError:
                dt = None
        if dt:
            if dt and dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt and (now - dt).days > abandoned_after_days:
                abandoned = True
        branches.append({
            "name": name,
            "date": date,
            "author": author,
            "abandoned": abandoned,
        })
    return branches


def collect_history(repo: Path, limit: int = 1000) -> list[dict]:
    raw = git(repo, "log", "--all", f"--max-count={limit}",
              "--pretty=format:%H|%ai|%an|%s")
    commits: list[dict] = []
    for line in raw.splitlines():
        sha, _, rest = line.partition("|")
        date, _, rest2 = rest.partition("|")
        author, _, subject = rest2.partition("|")
        commits.append({"sha": sha, "date": date, "author": author, "subject": subject})
    return commits


def build_mermaid(tags: list[dict], branches: list[dict], tag_limit: int) -> str:
    """Produce a very simple Mermaid timeline + branch list."""
    lines = ["```mermaid", "timeline", "    title Version lineage"]
    for t in tags[:tag_limit]:
        date_short = t["date"][:10] if t["date"] else ""
        lines.append(f"    {date_short} : {t['name']}")
    lines.append("```")
    if branches:
        lines.append("")
        lines.append("**Branch state**")
        lines.append("")
        lines.append("| Branch | Last commit | Author | Abandoned? |")
        lines.append("| ------ | ----------- | ------ | ---------- |")
        for b in branches[:30]:
            lines.append(f"| `{b['name']}` | {b['date'][:10]} | {b['author']} | {'YES' if b['abandoned'] else 'no'} |")
    return "\n".join(lines)


def render_markdown(repo: Path, tags: list[dict], branches: list[dict],
                    commits: list[dict], mermaid: str) -> str:
    n_abandoned = sum(1 for b in branches if b["abandoned"])
    n_commits = len(commits)
    first = commits[-1] if commits else None
    last = commits[0] if commits else None
    md = [
        f"# Lineage analysis — {repo.name}",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        "",
        f"- Tags found: **{len(tags)}**",
        f"- Branches inspected: **{len(branches)}** ({n_abandoned} flagged abandoned)",
        f"- Commits sampled: **{n_commits}** (most recent 1 000)",
    ]
    if first and last:
        md.append(f"- First commit (within sample): `{first['sha'][:10]}` — {first['date'][:10]} — {first['author']}")
        md.append(f"- Latest commit: `{last['sha'][:10]}` — {last['date'][:10]} — {last['author']}")

    md += ["", "## Tag timeline", "", mermaid, "", "## Recent commits", "",
           "| SHA | Date | Author | Subject |",
           "| --- | ---- | ------ | ------- |"]
    for c in commits[:25]:
        subj = c["subject"].replace("|", "\\|")
        md.append(f"| `{c['sha'][:8]}` | {c['date'][:10]} | {c['author']} | {subj} |")

    md += ["", "## Notes",
           "",
           "Branches flagged 'abandoned' have not received commits in the configured threshold (default 180 days). "
           "Review each before deleting or archiving.",
           ""]
    return "\n".join(md)


def maybe_render_svg(mermaid_block: str, diagram_path: Path) -> None:
    """If mermaid-cli (mmdc) is on PATH, render the diagram to an SVG."""
    mmdc = shutil.which("mmdc")
    if not mmdc:
        sys.stderr.write("[generate_lineage] mermaid-cli (mmdc) not found; skipping SVG.\n")
        return
    # Extract content between code fences.
    inner = mermaid_block
    if "```mermaid" in inner:
        inner = inner.split("```mermaid", 1)[1]
        inner = inner.split("```", 1)[0].strip()
    tmp = diagram_path.with_suffix(".mmd")
    tmp.write_text(inner, encoding="utf-8")
    subprocess.run([mmdc, "-i", str(tmp), "-o", str(diagram_path)], check=False)
    tmp.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DMAIC Phase 2 — version lineage tracer")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", default="reports/lineage.md")
    ap.add_argument("--diagram", default=None, help="Optional SVG output path (requires mmdc)")
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        sys.stderr.write(f"error: {repo} is not a git repository\n")
        return 2

    cfg = load_config(args.config)
    lineage_cfg = cfg.get("lineage", {}) or {}
    abandoned_after = int(lineage_cfg.get("abandoned_branch_days", 180))
    tag_limit = int(lineage_cfg.get("diagram_tag_limit", 30))

    tags = collect_tags(repo)
    branches = collect_branches(repo, abandoned_after)
    commits = collect_history(repo, limit=1000)
    mermaid = build_mermaid(tags, branches, tag_limit)
    md = render_markdown(repo, tags, branches, commits, mermaid)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")

    if args.diagram:
        maybe_render_svg(mermaid, Path(args.diagram))

    print(f"[generate_lineage] wrote {out_path}")
    print(f"  tags        = {len(tags)}")
    print(f"  branches    = {len(branches)}  (abandoned: {sum(1 for b in branches if b['abandoned'])})")
    print(f"  commits     = {len(commits)} (sampled)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
