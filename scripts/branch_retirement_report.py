#!/usr/bin/env python3
"""Build a branch retirement inventory for a GitHub repository.

The report is intentionally conservative: branches tied to open PRs, configured
protected PRs, the selected base branch, protected branch names, or missing PR
metadata are never emitted as delete commands unless the operator explicitly
opts into the applicable destructive path.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

PROTECTED_BRANCH_PATTERNS = (
    re.compile(r"^main$"),
    re.compile(r"^master$"),
    re.compile(r"^develop$"),
    re.compile(r"^release/"),
    re.compile(r"^hotfix/"),
)


@dataclass(frozen=True)
class PullRequest:
    number: int
    title: str
    state: str
    head: str
    base: str
    url: str
    updated_at: str
    merged_at: str | None


@dataclass(frozen=True)
class BranchRecord:
    branch: str
    ref: str
    sha: str
    last_commit_iso: str
    age_days: int | None
    ahead: int | None
    behind: int | None
    pr: PullRequest | None
    classification: str
    rationale: str
    delete_command: str


def run(cmd: Sequence[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def optional_git(repo: Path, *args: str) -> str:
    completed = run(["git", *args], cwd=repo, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def has_command(name: str) -> bool:
    return shutil.which(name) is not None


def normalize_origin_repo(remote_url: str) -> str | None:
    if not remote_url:
        return None
    match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$", remote_url)
    if not match:
        return None
    return f"{match.group('owner')}/{match.group('repo')}"


def default_base(repo: Path) -> str:
    symbolic = optional_git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if symbolic.startswith("origin/"):
        return symbolic.removeprefix("origin/")
    for candidate in ("main", "master"):
        if optional_git(repo, "rev-parse", "--verify", f"refs/remotes/origin/{candidate}"):
            return candidate
    return "main"


def fetch_prs(repo: Path, repo_slug: str | None) -> dict[str, PullRequest]:
    if not repo_slug or not has_command("gh"):
        return {}
    completed = run(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo_slug,
            "--state",
            "all",
            "--limit",
            "1000",
            "--json",
            "number,title,state,headRefName,baseRefName,url,updatedAt,mergedAt",
        ],
        cwd=repo,
        check=False,
    )
    if completed.returncode != 0:
        return {}
    prs = {}
    for item in json.loads(completed.stdout or "[]"):
        head = item.get("headRefName") or ""
        if not head:
            continue
        prs[head] = PullRequest(
            number=int(item["number"]),
            title=item.get("title") or "",
            state=item.get("state") or "",
            head=head,
            base=item.get("baseRefName") or "",
            url=item.get("url") or "",
            updated_at=item.get("updatedAt") or "",
            merged_at=item.get("mergedAt"),
        )
    return prs


def is_protected_branch(branch: str) -> bool:
    return any(pattern.search(branch) for pattern in PROTECTED_BRANCH_PATTERNS)


def rev_count(repo: Path, spec: str) -> int | None:
    out = optional_git(repo, "rev-list", "--count", spec)
    return int(out) if out.isdigit() else None


def commit_age(repo: Path, ref: str, now: datetime) -> tuple[str, int | None]:
    raw = optional_git(repo, "log", "-1", "--format=%cI", ref)
    if not raw:
        return "unknown", None
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw, None
    return raw, max(0, (now - ts.astimezone(timezone.utc)).days)


def classify(
    branch: str,
    ref: str,
    base_branch: str,
    base_ref: str,
    repo: Path,
    pr: PullRequest | None,
    protected_prs: set[int],
    stale_days: int,
    age_days: int | None,
    force_stale: bool,
) -> tuple[str, str]:
    if branch == base_branch:
        return "KEEP", f"selected base branch {base_branch}"
    if is_protected_branch(branch):
        return "KEEP", "protected branch naming policy"
    if pr and pr.number in protected_prs:
        return "KEEP", f"PR #{pr.number} is explicitly protected"
    if pr and pr.state.upper() == "OPEN":
        return "KEEP", f"open PR #{pr.number}"

    merged = run(["git", "merge-base", "--is-ancestor", ref, base_ref], cwd=repo, check=False).returncode == 0
    if merged:
        return "DELETE", f"tip is already reachable from {base_ref}"
    if pr and pr.state.upper() == "MERGED":
        return "DELETE", f"PR #{pr.number} is merged"
    if pr and pr.state.upper() == "CLOSED":
        return "CHERRY-PICK THEN DELETE", f"closed unmerged PR #{pr.number} has unique commits"
    if pr is None:
        if force_stale and age_days is not None and age_days >= stale_days:
            return "DELETE", f"stale ({age_days} days) and --force-stale was supplied"
        if age_days is not None and age_days >= stale_days:
            return "CHERRY-PICK THEN DELETE", f"stale ({age_days} days) but no PR metadata was found"
        return "KEEP", "no PR metadata was found; manual review required"
    return "MERGE", f"PR #{pr.number} is {pr.state.lower()} and branch has unique commits"


def build_delete_command(branch: str) -> str:
    """Return a shell-safe branch deletion command."""
    return f"git push --delete origin -- {shlex.quote(branch)}"


def remote_branches(repo: Path) -> list[tuple[str, str]]:
    refs = optional_git(repo, "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/remotes/origin")
    branches: list[tuple[str, str]] = []
    for line in refs.splitlines():
        if not line.strip():
            continue
        ref, sha = line.split(maxsplit=1)
        if ref == "origin/HEAD":
            continue
        branches.append((ref, sha))
    return branches


def build_records(repo: Path, args: argparse.Namespace) -> tuple[list[BranchRecord], list[str]]:
    warnings: list[str] = []
    remote_url = optional_git(repo, "remote", "get-url", "origin")
    repo_slug = normalize_origin_repo(remote_url)
    if not remote_url:
        warnings.append(
            "No origin remote is configured; remote branch export and PR mapping cannot be performed in this checkout."
        )
    elif not repo_slug:
        warnings.append(f"Origin remote is not a GitHub URL understood by this tool: {remote_url}")

    if remote_url and not args.no_fetch:
        fetched = run(["git", "fetch", "--prune", "origin"], cwd=repo, check=False)
        if fetched.returncode != 0:
            warnings.append(f"git fetch --prune origin failed: {fetched.stderr.strip() or fetched.stdout.strip()}")

    base = args.base or default_base(repo)
    base_ref = f"refs/remotes/origin/{base}"
    base_available = bool(optional_git(repo, "rev-parse", "--verify", base_ref))
    if not base_available:
        warnings.append(f"Base ref {base_ref} is unavailable; ahead/behind and merge reachability may be incomplete.")

    prs = fetch_prs(repo, repo_slug)
    if repo_slug and not prs:
        warnings.append("PR metadata was not available from gh; classifications are intentionally conservative.")

    now = datetime.now(timezone.utc)
    records: list[BranchRecord] = []
    for ref, sha in remote_branches(repo):
        branch = ref.removeprefix("origin/")
        last_iso, age_days = commit_age(repo, ref, now)
        ahead = rev_count(repo, f"{base_ref}..{ref}") if base_available else None
        behind = rev_count(repo, f"{ref}..{base_ref}") if base_available else None
        pr = prs.get(branch)
        classification, rationale = classify(
            branch,
            ref,
            base,
            base_ref,
            repo,
            pr,
            set(args.protect_pr),
            args.stale_days,
            age_days,
            args.force_stale,
        )
        delete_command = build_delete_command(branch) if classification == "DELETE" else ""
        records.append(
            BranchRecord(
                branch,
                ref,
                sha,
                last_iso,
                age_days,
                ahead,
                behind,
                pr,
                classification,
                rationale,
                delete_command,
            )
        )
    return records, warnings


def write_csv(records: Iterable[BranchRecord], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "branch",
                "sha",
                "last_commit",
                "age_days",
                "ahead",
                "behind",
                "pr",
                "state",
                "classification",
                "rationale",
                "delete_command",
            ]
        )
        for record in records:
            writer.writerow(
                [
                    record.branch,
                    record.sha,
                    record.last_commit_iso,
                    "" if record.age_days is None else record.age_days,
                    "" if record.ahead is None else record.ahead,
                    "" if record.behind is None else record.behind,
                    "" if record.pr is None else f"#{record.pr.number}",
                    "" if record.pr is None else record.pr.state,
                    record.classification,
                    record.rationale,
                    record.delete_command,
                ]
            )


def write_markdown(
    records: list[BranchRecord], warnings: list[str], path: Path, repo: Path, args: argparse.Namespace
) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    classifications = ("KEEP", "MERGE", "CHERRY-PICK THEN DELETE", "DELETE")
    counts = {name: sum(1 for record in records if record.classification == name) for name in classifications}
    lines = [
        "# Branch Retirement Report",
        "",
        f"Generated: {now}",
        f"Repository path: `{repo}`",
        f"Base branch: `{args.base or default_base(repo)}`",
        f"Stale threshold: {args.stale_days} days",
        "",
        "## Summary",
        "",
        "| Classification | Count |",
        "| --- | ---: |",
    ]
    for key in classifications:
        lines.append(f"| {key} | {counts[key]} |")
    lines.extend(["", "## Warnings and Limitations", ""])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Inventory",
            "",
            "| Branch | Last commit | Age | Ahead | Behind | PR | Classification | Rationale |",
            "| --- | --- | ---: | ---: | ---: | --- | --- | --- |",
        ]
    )
    for record in sorted(records, key=lambda item: (item.classification, item.branch)):
        pr_text = "" if record.pr is None else f"[#{record.pr.number}]({record.pr.url}) {record.pr.state}"
        lines.append(
            f"| `{record.branch}` | {record.last_commit_iso} | "
            f"{record.age_days if record.age_days is not None else ''} | "
            f"{record.ahead if record.ahead is not None else ''} | "
            f"{record.behind if record.behind is not None else ''} | "
            f"{pr_text} | {record.classification} | {record.rationale} |"
        )
    if not records:
        lines.append("| _(none)_ |  |  |  |  |  |  | No remote branches were available in this checkout. |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_deletion_script(records: Iterable[BranchRecord], path: Path) -> None:
    commands = [record.delete_command for record in records if record.delete_command]
    content = ["#!/usr/bin/env bash", "set -euo pipefail", ""]
    if commands:
        content.extend(commands)
    else:
        content.append("echo 'No delete commands generated.'")
    path.write_text("\n".join(content) + "\n", encoding="utf-8")
    path.chmod(0o755)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Git repository path. Default: current directory.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/branch-retirement"),
        help="Directory for markdown, CSV, and deletion command outputs.",
    )
    parser.add_argument(
        "--base",
        help="Base branch name. Default: origin/HEAD, then main/master. The selected base is always KEEP.",
    )
    parser.add_argument("--stale-days", type=int, default=60, help="Age threshold for stale branch review. Default: 60.")
    parser.add_argument(
        "--protect-pr",
        type=int,
        action="append",
        default=[],
        help="PR number to force into KEEP classification. May be repeated.",
    )
    parser.add_argument(
        "--force-stale",
        action="store_true",
        help="Classify stale branches without PR metadata as DELETE instead of CHERRY-PICK THEN DELETE.",
    )
    parser.add_argument("--no-fetch", action="store_true", help="Skip git fetch --prune origin before inventory.")
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    repo = args.repo.resolve()
    if not (repo / ".git").exists():
        print(f"error: {repo} is not a Git repository checkout", file=sys.stderr)
        return 2

    records, warnings = build_records(repo, args)
    output_dir = (repo / args.output_dir).resolve() if not args.output_dir.is_absolute() else args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    write_markdown(records, warnings, output_dir / "branch-retirement-report.md", repo, args)
    write_csv(records, output_dir / "branch-retirement-inventory.csv")
    write_deletion_script(records, output_dir / "branch-delete-commands.sh")
    print(f"Wrote {output_dir / 'branch-retirement-report.md'}")
    print(f"Wrote {output_dir / 'branch-retirement-inventory.csv'}")
    print(f"Wrote {output_dir / 'branch-delete-commands.sh'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
