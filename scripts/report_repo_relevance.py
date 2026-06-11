#!/usr/bin/env python3
"""Summarize ABACUS/CODEX pipeline relevance for CLI and workflow summaries."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

REPO_PROFILES = {
    "ABACUS": {
        "role": "abacus-main",
        "stack": ["DMAIC_V3", "bridge-testing", "docs-validation"],
        "recommendations": [
            "Run python -m pytest DMAIC_V3/tests -q before merge.",
            "Validate workflows with bash scripts/verify_workflows.sh.",
            "Use run_deployment_test_system.py for bridge smoke and deployment checks.",
        ],
    },
    "CODEX": {
        "role": "codex-main",
        "stack": ["phase0-smoke", "pre-commit", "pytest"],
        "recommendations": [
            "Run pre-commit and pytest in matrix jobs before artifact upload.",
            "Keep CODEX-only workflow gating tied to github.repository.",
            "Reuse repo relevance summaries to surface bridge/shared tooling expectations.",
        ],
    },
}

WORKFLOW_CHECKS = {
    "ci": ".github/workflows/ci.yml",
    "bridge": ".github/workflows/bridge-ci.yml",
    "codex": ".github/workflows/ci-codex.yml",
    "integration": ".github/workflows/gbogeb-abacus-integration-ci-cd.yml",
}

UTILITY_CHECKS = {
    "deployment_runner": "run_deployment_test_system.py",
    "workflow_validator": "scripts/verify_workflows.sh",
    "docs_validator": "scripts/validate_docs_links.py",
    "repo_relevance": "scripts/report_repo_relevance.py",
}


def detect_repository(explicit_repo: str | None, workspace: Path) -> str:
    """Resolve a repository slug or local repository name."""
    if explicit_repo:
        return explicit_repo

    env_repo = os.getenv("GITHUB_REPOSITORY")
    if env_repo:
        return env_repo

    return workspace.name


def build_report(repo_slug: str, workspace: Path) -> dict:
    """Build a relevance report for the current repository."""
    repo_name = repo_slug.split("/")[-1].upper()
    profile = REPO_PROFILES.get(
        repo_name,
        {
            "role": "generic",
            "stack": ["unknown"],
            "recommendations": [
                "Review repository-specific test and workflow entrypoints before pipeline changes.",
            ],
        },
    )

    workflows = {
        name: rel_path
        for name, rel_path in WORKFLOW_CHECKS.items()
        if (workspace / rel_path).exists()
    }
    utilities = {
        name: rel_path
        for name, rel_path in UTILITY_CHECKS.items()
        if (workspace / rel_path).exists()
    }

    similarities = []
    if "codex" in workflows and "integration" in workflows:
        similarities.append(
            "Workflow coverage exists for both CODEX matrix and ABACUS integration paths."
        )
    if "bridge" in workflows and "deployment_runner" in utilities:
        similarities.append(
            "Bridge workflows and the deployment runner share the same smoke/deployment entrypoint."
        )
    if repo_name == "ABACUS":
        similarities.append(
            "ABACUS keeps bridge and dormant-integration assets that benefit from explicit pipeline summaries."
        )
    if repo_name == "CODEX":
        similarities.append(
            "CODEX can reuse the same summary utility to align matrix jobs with shared bridge expectations."
        )

    return {
        "repository": repo_slug,
        "role": profile["role"],
        "stack": profile["stack"],
        "workflows": workflows,
        "utilities": utilities,
        "similarities": similarities,
        "recommendations": profile["recommendations"],
    }


def render_text(report: dict) -> str:
    """Render a plain-text report."""
    lines = [
        f"Repository: {report['repository']}",
        f"Role: {report['role']}",
        f"Stack: {', '.join(report['stack'])}",
        "",
        "Relevant workflows:",
    ]
    lines.extend(f"- {name}: {path}" for name, path in report["workflows"].items())
    lines.append("")
    lines.append("Accessible utilities:")
    lines.extend(f"- {name}: {path}" for name, path in report["utilities"].items())
    lines.append("")
    lines.append("Shared relevance:")
    lines.extend(f"- {item}" for item in report["similarities"])
    lines.append("")
    lines.append("Improvement steps:")
    lines.extend(f"- {item}" for item in report["recommendations"])
    return "\n".join(lines)


def render_markdown(report: dict) -> str:
    """Render a GitHub Step Summary-friendly report."""
    lines = [
        "## Repo relevance summary",
        "",
        f"- **Repository:** `{report['repository']}`",
        f"- **Role:** `{report['role']}`",
        f"- **Stack:** {', '.join(f'`{item}`' for item in report['stack'])}",
        "",
        "### Relevant workflows",
    ]
    lines.extend(f"- `{name}` → `{path}`" for name, path in report["workflows"].items())
    lines.append("")
    lines.append("### Accessible utilities")
    lines.extend(f"- `{name}` → `{path}`" for name, path in report["utilities"].items())
    lines.append("")
    lines.append("### Shared relevance")
    lines.extend(f"- {item}" for item in report["similarities"])
    lines.append("")
    lines.append("### Improvement steps")
    lines.extend(f"- {item}" for item in report["recommendations"])
    return "\n".join(lines)


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Report ABACUS/CODEX repo relevance for pipelines."
    )
    parser.add_argument("--repo", help="Repository slug override, e.g. GBOGEB/ABACUS")
    parser.add_argument("--workspace", default=".", help="Workspace to inspect")
    parser.add_argument(
        "--format", choices=["text", "json", "github-step-summary"], default="text"
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    report = build_report(detect_repository(args.repo, workspace), workspace)

    if args.format == "json":
        print(json.dumps(report, indent=2))
        return 0

    rendered = (
        render_markdown(report)
        if args.format == "github-step-summary"
        else render_text(report)
    )
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
