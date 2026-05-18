#!/usr/bin/env python3
"""analyze_repo.py — Phase 1 / DMAIC Define.

Walk a repository and emit a JSON snapshot of its state:
    - file and directory counts
    - language breakdown
    - commit / contributor stats
    - branches / tags
    - documentation presence
    - workflow presence
    - rough health estimate

Usage:
    python analyze_repo.py --repo /path/to/repo --out reports/baseline.json
    python analyze_repo.py --repo . --config config.yaml
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # config-loading becomes optional.


LANG_EXT = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".rb": "Ruby",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C/C++ header",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".html": "HTML",
    ".css": "CSS",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".ipynb": "Jupyter",
    ".sh": "Shell",
    ".ps1": "PowerShell",
}


DEFAULT_EXCLUDES = {".git", "node_modules", "__pycache__", ".venv",
                    ".mypy_cache", ".pytest_cache", ".next", "dist", "build"}


def load_config(path: str | None) -> dict:
    if not path:
        return {}
    if yaml is None:
        sys.stderr.write("PyYAML not installed; ignoring --config\n")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def is_excluded(path: Path, excludes: set[str]) -> bool:
    return any(part in excludes for part in path.parts)


def git(repo: Path, *args: str) -> str:
    """Run git and return stdout (stripped). Empty string on failure."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, check=False,
        )
        return out.stdout.strip()
    except FileNotFoundError:
        return ""


def scan_files(repo: Path, excludes: set[str]) -> dict:
    """Walk the tree and produce file / language stats."""
    total_files = 0
    total_bytes = 0
    top_level_files = 0
    top_level_dirs = 0
    lang_counts: Counter[str] = Counter()
    lang_bytes: Counter[str] = Counter()
    largest: list[tuple[int, str]] = []

    for root, dirs, files in os.walk(repo):
        # Prune excluded dirs in-place for efficiency.
        dirs[:] = [d for d in dirs if d not in excludes]
        rel_root = Path(root).relative_to(repo)

        if rel_root == Path("."):
            top_level_dirs = len(dirs)
            top_level_files = len(files)

        for fname in files:
            fp = Path(root) / fname
            if is_excluded(fp.relative_to(repo), excludes):
                continue
            try:
                size = fp.stat().st_size
            except OSError:
                continue
            total_files += 1
            total_bytes += size
            ext = fp.suffix.lower()
            lang = LANG_EXT.get(ext, "Other")
            lang_counts[lang] += 1
            lang_bytes[lang] += size
            largest.append((size, str(fp.relative_to(repo))))

    largest.sort(reverse=True)
    return {
        "total_files": total_files,
        "total_bytes": total_bytes,
        "top_level_files": top_level_files,
        "top_level_dirs": top_level_dirs,
        "languages_by_count": lang_counts.most_common(),
        "languages_by_bytes": lang_bytes.most_common(),
        "largest_files": [{"bytes": s, "path": p} for s, p in largest[:20]],
    }


def scan_git(repo: Path) -> dict:
    """Collect git metadata: commits, contributors, branches, tags."""
    if not (repo / ".git").exists():
        return {"is_git_repo": False}

    n_commits = git(repo, "rev-list", "--all", "--count")
    contributors = git(repo, "shortlog", "-sn", "--all")
    branches = git(repo, "branch", "-a", "--format=%(refname:short)")
    tags = git(repo, "tag", "--list", "--sort=-creatordate")
    first_commit = git(repo, "log", "--reverse", "--pretty=format:%ai", "--all")
    last_commit = git(repo, "log", "-1", "--pretty=format:%ai", "--all")

    contributor_lines = [line for line in contributors.splitlines() if line.strip()]
    branch_list = [b for b in branches.splitlines() if b]
    tag_list = [t for t in tags.splitlines() if t]

    first_commit_date = first_commit.split("\n")[0] if first_commit else ""
    return {
        "is_git_repo": True,
        "commits": int(n_commits) if n_commits.isdigit() else 0,
        "contributors_total": len(contributor_lines),
        "top_contributors": contributor_lines[:10],
        "branches_total": len(branch_list),
        "branches_sample": branch_list[:30],
        "tags_total": len(tag_list),
        "tags_recent": tag_list[:20],
        "first_commit": first_commit_date,
        "last_commit": last_commit,
    }


def scan_docs(repo: Path) -> dict:
    readmes = [p.name for p in repo.iterdir() if p.is_file() and p.name.lower().startswith("readme")]
    docs_dir = (repo / "docs").is_dir()
    docs_versioned = (repo / "docs_versioned").is_dir()
    contributing = (repo / "CONTRIBUTING.md").exists() or (repo / ".github" / "CONTRIBUTING.md").exists()
    license_present = any((repo / n).exists() for n in ("LICENSE", "LICENSE.md", "LICENSE.txt"))
    security = (repo / "SECURITY.md").exists()
    return {
        "readmes_at_root": readmes,
        "docs_dir": docs_dir,
        "docs_versioned": docs_versioned,
        "contributing_md": contributing,
        "license_present": license_present,
        "security_md": security,
    }


def scan_ci(repo: Path) -> dict:
    workflows_dir = repo / ".github" / "workflows"
    workflows = [p.name for p in workflows_dir.iterdir() if p.is_file()] if workflows_dir.is_dir() else []
    issue_templates_dir = repo / ".github" / "ISSUE_TEMPLATE"
    issue_templates = [p.name for p in issue_templates_dir.iterdir() if p.is_file()] if issue_templates_dir.is_dir() else []
    pr_template = (repo / ".github" / "PULL_REQUEST_TEMPLATE.md").exists()
    dependabot = (repo / ".github" / "dependabot.yml").exists()
    return {
        "workflows": workflows,
        "workflow_count": len(workflows),
        "issue_templates": issue_templates,
        "pr_template": pr_template,
        "dependabot": dependabot,
    }


def estimate_score(file_stats: dict, git_stats: dict, doc_stats: dict, ci_stats: dict) -> int:
    """Rough 0-100 score; only used as a starting hint."""
    score = 0
    if doc_stats.get("readmes_at_root"):
        score += 5
    if doc_stats.get("docs_dir"):
        score += 5
    if doc_stats.get("contributing_md"):
        score += 5
    if doc_stats.get("license_present"):
        score += 5
    if doc_stats.get("security_md"):
        score += 3

    if file_stats.get("top_level_files", 0) <= 15:
        score += 5
    if file_stats.get("top_level_dirs", 0) <= 12:
        score += 5

    score += min(ci_stats.get("workflow_count", 0), 10)
    if ci_stats.get("issue_templates"):
        score += 5
    if ci_stats.get("pr_template"):
        score += 5
    if ci_stats.get("dependabot"):
        score += 3

    if git_stats.get("is_git_repo"):
        score += 5
    if git_stats.get("commits", 0) > 50:
        score += 5
    if git_stats.get("tags_total", 0) >= 1:
        score += 5
    return min(score, 100)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DMAIC Phase 1 — repo baseline analyzer")
    ap.add_argument("--repo", required=True, help="Path to the repository root")
    ap.add_argument("--out", default="reports/baseline.json", help="Output JSON path")
    ap.add_argument("--config", default=None, help="Optional YAML config")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        sys.stderr.write(f"error: {repo} is not a directory\n")
        return 2

    excludes = set(DEFAULT_EXCLUDES)
    for pat in (cfg.get("exclude_patterns") or []):
        # Best-effort: strip glob suffixes to support the same exclude style.
        for token in pat.split("/"):
            if token and token != "**" and "*" not in token:
                excludes.add(token)

    file_stats = scan_files(repo, excludes)
    git_stats = scan_git(repo)
    doc_stats = scan_docs(repo)
    ci_stats = scan_ci(repo)
    score = estimate_score(file_stats, git_stats, doc_stats, ci_stats)

    snapshot = {
        "tool": "analyze_repo",
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_path": str(repo),
        "repo_name": repo.name,
        "files": file_stats,
        "git": git_stats,
        "docs": doc_stats,
        "ci": ci_stats,
        "estimated_health_score": score,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print(f"[analyze_repo] wrote {out_path}")
    print(f"  files       = {file_stats['total_files']}")
    print(f"  commits     = {git_stats.get('commits', 0)}")
    print(f"  workflows   = {ci_stats['workflow_count']}")
    print(f"  est. score  = {score} / 100")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
