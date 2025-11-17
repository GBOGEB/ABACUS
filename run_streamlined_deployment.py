#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlined DOW Deployment - Sprint 5, DMAIC Phase 0-9, MCP Iteration
Fast execution with Git/GitHub integration
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

def log(msg, level="INFO"):
    icons = {"INFO": "[INFO]", "SUCCESS": "[OK]", "ERROR": "[ERR]", "RUN": "[RUN]"}
    print(f"{icons.get(level, '     ')} {msg}")

def run(cmd, cwd=None):
    """Execute command and return success status"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    log("=" * 80)
    log("STREAMLINED DOW DEPLOYMENT")
    log("=" * 80)

    results = {}

    # Step 1: Git Status
    log("Step 1: Git Integration Check", "RUN")
    success, stdout, _ = run("git status --short | wc -l")
    if success:
        modified = stdout.strip()
        log(f"Modified files: {modified}")
        results["git_modified"] = modified

    success, stdout, _ = run("git branch --show-current")
    if success:
        branch = stdout.strip()
        log(f"Branch: {branch}", "SUCCESS")
        results["git_branch"] = branch

    # Step 2: Run Direct Improvements (3 iterations)
    log("\nStep 2: DOW Direct Improvements (3 iterations)", "RUN")
    for i in range(1, 4):
        log(f"  Iteration {i}/3...", "RUN")
        success, stdout, stderr = run("python run_direct_improvements.py", cwd="ABACUS-v031")
        if success:
            log(f"  Iteration {i} complete", "SUCCESS")
            run(f'git add -A && git commit -m "[DOW] Auto-improvement iteration {i}"')
        else:
            log(f"  Iteration {i} failed: {stderr[:100]}", "ERROR")
            break

    results["improvement_iterations"] = i

    # Step 3: Quality Assessment
    log("\nStep 3: Quality Assessment", "RUN")
    rankings_file = Path("ABACUS-v031/artifact_rankings.json")
    if rankings_file.exists():
        try:
            with open(rankings_file) as f:
                rankings = json.load(f)
            if isinstance(rankings, list):
                scores = [r.get("metrics", {}).get("overall_score", 0) for r in rankings]
                avg_score = sum(scores) / len(scores) if scores else 0
                low_count = sum(1 for s in scores if s < 0.3)

                log(f"  Total artifacts: {len(rankings)}")
                log(f"  Average score: {avg_score:.3f}")
                log(f"  Low-scoring (<0.3): {low_count}")

                results["total_artifacts"] = len(rankings)
                results["avg_score"] = avg_score
                results["low_scoring"] = low_count

                if avg_score >= 0.5:
                    log("  Quality target achieved!", "SUCCESS")
                else:
                    log(f"  Target: 0.500, Current: {avg_score:.3f}")
        except Exception as e:
            log(f"  Error reading rankings: {e}", "ERROR")

    # Step 4: CI/CD Validation
    log("\nStep 4: CI/CD Configuration", "RUN")
    cicd_files = [
        ".github/workflows/ci.yml",
        ".github/workflows/cd.yml",
        "ABACUS-v031/.pre-commit-config.yaml"
    ]
    found = [f for f in cicd_files if Path(f).exists()]
    log(f"  CI/CD configs found: {len(found)}")
    results["cicd_configs"] = len(found)

    # Step 5: Git Remote Check
    log("\nStep 5: GitHub Integration", "RUN")
    success, stdout, _ = run("git remote get-url origin")
    if success:
        remote = stdout.strip()
        log(f"  Remote: {remote}")
        log("  Ready to push", "SUCCESS")
        results["remote_url"] = remote
        results["ready_to_push"] = True
    else:
        log("  No remote configured", "ERROR")
        results["ready_to_push"] = False

    # Generate Report
    log("\n" + "=" * 80)
    log("DEPLOYMENT SUMMARY")
    log("=" * 80)

    print(f"\nResults:")
    print(f"  Git Branch:          {results.get('git_branch', 'N/A')}")
    print(f"  Modified Files:      {results.get('git_modified', 'N/A')}")
    print(f"  Iterations:          {results.get('improvement_iterations', 0)}")
    print(f"  Total Artifacts:     {results.get('total_artifacts', 'N/A')}")
    print(f"  Average Score:       {results.get('avg_score', 0):.3f}")
    print(f"  Low-Scoring:         {results.get('low_scoring', 'N/A')}")
    print(f"  CI/CD Configs:       {results.get('cicd_configs', 0)}")
    print(f"  Ready to Push:       {'Yes' if results.get('ready_to_push') else 'No'}")

    # Save report
    report_file = Path("streamlined_deployment_report.json")
    with open(report_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results
        }, f, indent=2)

    log(f"\nReport saved: {report_file}", "SUCCESS")
    log("\nDEPLOYMENT COMPLETE!", "SUCCESS")

    return 0

if __name__ == "__main__":
    sys.exit(main())
