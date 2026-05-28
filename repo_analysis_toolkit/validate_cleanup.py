#!/usr/bin/env python3
"""validate_cleanup.py — Phase 4 / 5 validator.

Verify post-cleanup compliance against the DMAIC scorecard and emit a JSON
report consumable by CI or `create_dashboard.py`.

Checks:
    docs:
        - README.md at root, non-empty.
        - CONTRIBUTING.md present.
        - LICENSE present.
        - docs/ directory present.
        - Section READMEs in every top-level dir.
    organization:
        - ≤ 15 top-level files, ≤ 12 top-level dirs.
        - Consistent naming (best-effort heuristic).
        - CHANGELOG.md present.
    automation:
        - ≥ 7 workflows.
        - At least one of: ci.yml, deploy-docs.yml, release.yml, dashboard-health.yml.
    governance:
        - PR template + ≥ 4 issue templates.
        - CODEOWNERS present.

Usage:
    python validate_cleanup.py --repo /path/to/repo --out reports/validation.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


SECTION_KEY_DIRS = {"docs", "src", "tests", "scripts", "tools"}


def is_python_name_compliant(filename: str) -> bool:
    """Best-effort naming check that tolerates common versioned filenames."""
    snake_case = re.match(r"^[a-z0-9_]+\.py$", filename)
    if snake_case:
        return True
    if not filename.endswith(".py"):
        return False
    stem = filename[:-3]
    if "_v" not in stem:
        return False
    base, version_and_suffix = stem.rsplit("_v", 1)
    if not base or any(not (c.isalnum() or c == "_") for c in base):
        return False
    parts = version_and_suffix.split("_")
    version_token = parts[0]
    version_numbers = version_token.split(".")
    if not version_numbers or any(not n.isdigit() for n in version_numbers):
        return False
    for token in parts[1:]:
        if not token or any(not c.isalnum() for c in token):
            return False
    return True


def check_docs(repo: Path) -> dict:
    score = 0
    items = {}

    readme = repo / "README.md"
    items["readme_at_root"] = readme.exists() and readme.stat().st_size > 100
    if items["readme_at_root"]:
        score += 5

    contributing = (repo / "CONTRIBUTING.md").exists() or (repo / ".github" / "CONTRIBUTING.md").exists()
    items["contributing"] = contributing
    if contributing:
        score += 5

    items["license"] = any((repo / n).exists() for n in ("LICENSE", "LICENSE.md", "LICENSE.txt"))
    if items["license"]:
        score += 5

    items["docs_dir"] = (repo / "docs").is_dir()
    if items["docs_dir"]:
        score += 5

    # Section READMEs in top-level real dirs.
    section_ok = True
    section_misses: list[str] = []
    for d in repo.iterdir():
        if not d.is_dir() or d.name.startswith("."):
            continue
        if d.name in {"node_modules", "__pycache__", ".venv"}:
            continue
        if not (d / "README.md").exists():
            section_ok = False
            section_misses.append(d.name)
    items["section_readmes"] = section_ok
    items["section_readme_misses"] = section_misses[:20]
    if section_ok:
        score += 5

    return {"category": "documentation", "score": score, "max": 25, "items": items}


def check_organization(repo: Path) -> dict:
    score = 0
    items: dict = {}

    top_files = [p for p in repo.iterdir() if p.is_file()]
    top_dirs = [p for p in repo.iterdir() if p.is_dir() and not p.name.startswith(".")]
    items["top_level_files"] = len(top_files)
    items["top_level_dirs"] = len(top_dirs)

    if len(top_files) <= 15:
        score += 5
    if len(top_dirs) <= 12:
        score += 5

    # Consistent naming heuristic — ratio-based and tolerant of versioned names.
    py_files = [
        p for p in repo.rglob("*.py")
        if ".git" not in p.parts and ".venv" not in p.parts and "__pycache__" not in p.parts
    ]
    compliant = sum(1 for p in py_files if is_python_name_compliant(p.name))
    compliance_ratio = (compliant / len(py_files)) if py_files else 1.0
    py_consistent = compliance_ratio >= 0.9
    items["python_snake_case"] = py_consistent
    items["python_name_compliance_ratio"] = round(compliance_ratio, 3)
    items["python_name_compliance_threshold"] = 0.9
    if py_consistent:
        score += 5

    items["changelog"] = (repo / "CHANGELOG.md").exists()
    if items["changelog"]:
        score += 5

    versioned = (repo / "docs_versioned").is_dir()
    items["docs_versioned"] = versioned
    if versioned:
        score += 5

    return {"category": "organization", "score": score, "max": 25, "items": items}


def check_automation(repo: Path) -> dict:
    score = 0
    items: dict = {}
    wf_dir = repo / ".github" / "workflows"
    workflows = [p.name for p in wf_dir.iterdir() if p.is_file()] if wf_dir.is_dir() else []
    items["workflow_count"] = len(workflows)
    items["workflows"] = workflows

    if len(workflows) >= 7:
        score += 10
    elif len(workflows) >= 3:
        score += 5

    expected = {"ci.yml", "deploy-docs.yml", "release.yml", "dashboard-health.yml",
                "update-docs.yml", "dmaic-commit-metrics.yml"}
    found_expected = expected.intersection(workflows)
    items["expected_workflows_found"] = sorted(found_expected)
    if "deploy-docs.yml" in workflows or any("deploy" in w for w in workflows):
        score += 5
    if any("release" in w for w in workflows):
        score += 5
    if any("health" in w for w in workflows) or any("metrics" in w for w in workflows):
        score += 5

    return {"category": "automation", "score": min(score, 25), "max": 25, "items": items}


def check_governance(repo: Path) -> dict:
    score = 0
    items: dict = {}
    pr_t = (repo / ".github" / "PULL_REQUEST_TEMPLATE.md").exists()
    items["pr_template"] = pr_t
    if pr_t:
        score += 5

    it_dir = repo / ".github" / "ISSUE_TEMPLATE"
    issue_templates = [p.name for p in it_dir.iterdir() if p.is_file()] if it_dir.is_dir() else []
    items["issue_templates"] = issue_templates
    if len(issue_templates) >= 4:
        score += 5
    elif len(issue_templates) >= 1:
        score += 2

    items["codeowners"] = (repo / ".github" / "CODEOWNERS").exists() or (repo / "CODEOWNERS").exists()
    if items["codeowners"]:
        score += 5

    items["security_md"] = (repo / "SECURITY.md").exists()
    if items["security_md"]:
        score += 5

    items["maintenance_schedule"] = (repo / "MAINTENANCE_SCHEDULE.md").exists() or \
                                    (repo / "docs" / "MAINTENANCE_SCHEDULE.md").exists()
    if items["maintenance_schedule"]:
        score += 5

    return {"category": "governance", "score": score, "max": 25, "items": items}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DMAIC validator — score a cleaned-up repo against the rubric")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", default="reports/validation.json")
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        sys.stderr.write(f"error: {repo} is not a directory\n")
        return 2

    sections = [
        check_docs(repo),
        check_organization(repo),
        check_automation(repo),
        check_governance(repo),
    ]
    total = sum(s["score"] for s in sections)
    band = (
        "Excellent" if total >= 90 else
        "Good" if total >= 75 else
        "Needs improvement" if total >= 60 else
        "Critical"
    )

    payload = {
        "tool": "validate_cleanup",
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_path": str(repo),
        "repo_name": repo.name,
        "sections": sections,
        "total_score": total,
        "max_score": 100,
        "band": band,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"[validate_cleanup] wrote {out_path}")
    for s in sections:
        print(f"  {s['category']:<14} {s['score']:>3} / {s['max']}")
    print(f"  {'TOTAL':<14} {total:>3} / 100   ({band})")
    return 0 if total >= 75 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
