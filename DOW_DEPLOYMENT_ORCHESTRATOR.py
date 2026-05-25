#!/usr/bin/env python3
"""
DOW Deployment Orchestrator
============================
Generates monitoring dashboard reports for the DOW integration pipeline.

Usage:
    python DOW_DEPLOYMENT_ORCHESTRATOR.py --dashboard
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


LOG_DIR = Path("DOW_LOGS")


def generate_dashboard() -> int:
    """Generate a monitoring dashboard report in DOW_LOGS/."""
    LOG_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    ts_str = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = timestamp.strftime("%Y-%m-%d")

    # Collect basic status information
    repo_root = Path(__file__).parent
    dmaic_tests_dir = repo_root / "DMAIC_V3" / "tests"
    agents_dir = repo_root / "DMAIC_V3" / "local_mcp" / "agents" if (
        repo_root / "DMAIC_V3" / "local_mcp" / "agents"
    ).exists() else repo_root / "local_mcp" / "agents"

    test_count = len(list(dmaic_tests_dir.glob("test_*.py"))) if dmaic_tests_dir.exists() else 0
    dow_agents = list(agents_dir.glob("dow_*.py")) if agents_dir.exists() else []

    # Build dashboard data
    dashboard = {
        "generated_at": ts_str,
        "status": "ok",
        "components": {
            "dmaic_test_files": test_count,
            "dow_agents": len(dow_agents),
            "dow_agent_names": [p.name for p in sorted(dow_agents)],
        },
        "pipeline": {
            "orchestrator": str(Path(__file__).name),
            "version": "1.0.0",
        },
    }

    # Write JSON report
    json_path = LOG_DIR / f"dashboard_{date_str}.json"
    with open(json_path, "w") as fh:
        json.dump(dashboard, fh, indent=2)

    # Write / overwrite latest.json for quick access
    latest_path = LOG_DIR / "latest.json"
    with open(latest_path, "w") as fh:
        json.dump(dashboard, fh, indent=2)

    # Write human-readable markdown summary
    md_path = LOG_DIR / "dashboard.md"
    lines = [
        "# DOW Monitoring Dashboard",
        "",
        f"**Generated:** {ts_str}",
        f"**Status:** {dashboard['status'].upper()}",
        "",
        "## Components",
        f"- DMAIC test files: {test_count}",
        f"- DOW agents: {len(dow_agents)}",
    ]
    if dow_agents:
        lines.append("")
        lines.append("### DOW Agents")
        for name in sorted(p.name for p in dow_agents):
            lines.append(f"- `{name}`")
    lines.append("")
    with open(md_path, "w") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"Dashboard generated: {json_path}, {latest_path}, {md_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="DOW Deployment Orchestrator")
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Generate monitoring dashboard report in DOW_LOGS/",
    )
    args = parser.parse_args()

    if args.dashboard:
        return generate_dashboard()

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
