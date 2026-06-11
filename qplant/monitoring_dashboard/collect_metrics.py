#!/usr/bin/env python3
"""QPLANT Monitoring Dashboard — Metrics Collector

Gathers system health metrics and generates dashboard data.
Designed to run standalone or be called from the monitoring dashboard.

Usage:
    python collect_metrics.py                    # Print metrics JSON
    python collect_metrics.py --output=report    # Generate HTML report
    python collect_metrics.py --check            # Run health checks only

Output:
    monitoring_data.json — Machine-readable metrics snapshot
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path("/home/ubuntu/handover_dashboard")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def collect_version_info() -> Dict[str, Any]:
    """Collect version information from all sources."""
    versions = {}

    # config.yaml
    try:
        import yaml
        config_path = PROJECT_ROOT / "data" / "config.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        versions["config_yaml"] = config.get("version", "unknown")
    except Exception as e:
        versions["config_yaml"] = f"ERROR: {e}"

    # VERSION.json
    try:
        vj = PROJECT_ROOT / "VERSION.json"
        versions["version_json"] = json.loads(vj.read_text()).get("version", "unknown")
    except Exception:
        versions["version_json"] = "missing"

    # Git
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        versions["git_commit"] = result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        versions["git_commit"] = "unknown"

    versions["aligned"] = versions.get("config_yaml") == versions.get("version_json")
    return versions


def collect_test_results() -> Dict[str, Any]:
    """Run test suite and collect results."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-q"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=60
        )
        output = result.stdout
        # Parse test counts
        lines = output.strip().split("\n")
        last_line = lines[-1] if lines else ""

        passed = 0
        failed = 0
        if "passed" in last_line:
            import re
            m = re.search(r"(\d+) passed", last_line)
            if m:
                passed = int(m.group(1))
            m = re.search(r"(\d+) failed", last_line)
            if m:
                failed = int(m.group(1))

        return {
            "passed": passed,
            "failed": failed,
            "total": passed + failed,
            "pass_rate": round(passed / max(passed + failed, 1) * 100, 1),
            "duration": last_line,
            "status": "pass" if failed == 0 else "fail",
        }
    except Exception as e:
        return {"passed": 0, "failed": 0, "total": 0, "pass_rate": 0, "status": f"error: {e}"}


def collect_compliance() -> Dict[str, Any]:
    """Load compliance report data."""
    path = PROJECT_ROOT / "TRIAGE_COMPLIANCE_REPORT.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {"compliance_score": 0, "status": "unknown"}


def collect_config_drift() -> List[Dict[str, Any]]:
    """Check for configuration drift between SSoT and expectations."""
    try:
        from src.config_loader import ConfigLoader
        cfg = ConfigLoader()

        checks = [
            ("compressor_specifications.hp_compressors.count", 3),
            ("compressor_specifications.fsd575.motor_power_kW", 315),
            ("financial.compressor_capex.total_3_units_eur", 600000),
            ("financial.compressor_capex.total_system_eur", 1420000),
            ("flow_parameters.wcs_hp.design_flow_gs", 350),
            ("compressor_specifications.three_skid_totals.max_total_flow_gs", 337.62),
        ]

        results = []
        for path, expected in checks:
            actual = cfg.get(path)
            results.append({
                "parameter": path,
                "expected": expected,
                "actual": actual,
                "aligned": actual == expected,
            })

        return results
    except Exception as e:
        return [{"error": str(e)}]


def collect_file_stats() -> Dict[str, Any]:
    """Collect file statistics."""
    stats = {
        "python_files": len(list((PROJECT_ROOT / "src").glob("*.py"))),
        "html_docs": len(list((PROJECT_ROOT / "docs").rglob("*.html"))),
        "test_files": len(list((PROJECT_ROOT / "tests").glob("*.py"))),
        "total_charts": 0,
    }

    # Count charts
    for vdir in ["visualizations", "visualizations_v3", "plots"]:
        chart_dir = PROJECT_ROOT / "docs" / vdir
        if chart_dir.exists():
            stats["total_charts"] += len(list(chart_dir.glob("*.html")))

    return stats


def collect_todo_status() -> Dict[str, Any]:
    """Parse TODO status from consolidated file."""
    todo_file = Path("/home/ubuntu/phase1_consolidated_todos.md")
    if not todo_file.exists():
        return {"total": 0, "done": 0, "remaining": 0}

    content = todo_file.read_text()
    done_count = content.count("✅ DONE")
    # Count total items (lines with | C- or | H- or | M- or | L-)
    import re
    items = re.findall(r"\| [CHML]-\d+", content)
    total = len(items)

    return {
        "total": total,
        "done": done_count,
        "remaining": total - done_count,
        "completion_pct": round(done_count / max(total, 1) * 100, 1),
    }


def collect_all_metrics() -> Dict[str, Any]:
    """Collect all monitoring metrics."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": "MYRRHA QPLANT Cryogenic Dashboard",
        "versions": collect_version_info(),
        "tests": collect_test_results(),
        "compliance": collect_compliance(),
        "config_drift": collect_config_drift(),
        "file_stats": collect_file_stats(),
        "todos": collect_todo_status(),
        "status": "healthy",  # Will be set based on checks
    }


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="QPLANT Metrics Collector")
    parser.add_argument("--output", choices=["json", "report"], default="json")
    parser.add_argument("--check", action="store_true", help="Run health checks only")
    args = parser.parse_args()

    metrics = collect_all_metrics()

    # Determine overall status
    issues = []
    if not metrics["versions"].get("aligned"):
        issues.append("Version mismatch")
    if metrics["tests"].get("failed", 0) > 0:
        issues.append(f"{metrics['tests']['failed']} tests failing")
    drift_issues = [d for d in metrics["config_drift"] if isinstance(d, dict) and not d.get("aligned", True)]
    if drift_issues:
        issues.append(f"{len(drift_issues)} config drift(s)")

    metrics["status"] = "healthy" if not issues else "degraded"
    metrics["issues"] = issues

    if args.check:
        status = "✅ HEALTHY" if not issues else f"⚠️ DEGRADED: {', '.join(issues)}"
        print(f"QPLANT Health Check: {status}")
        return 0 if not issues else 1

    # Write JSON
    output_path = Path("/home/ubuntu/monitoring_dashboard/monitoring_data.json")
    output_path.write_text(json.dumps(metrics, indent=2, default=str))
    print(json.dumps(metrics, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
