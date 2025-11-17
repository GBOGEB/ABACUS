#!/usr/bin/env python3
"""
Export summary to Markdown format.
"""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path("ledger/runs.sqlite")
OUTPUT_PATH = Path("artifacts/markdown/summary.md")


def main():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    runs = conn.execute(
        """SELECT run_id, started_at, finished_at, status, git_sha, total_metrics_json
           FROM runs ORDER BY started_at DESC LIMIT 20"""
    ).fetchall()
    conn.close()
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_PATH, "w") as f:
        f.write("# DMAIC Pipeline Summary\n\n")
        f.write(f"Total runs: {len(runs)}\n\n")
        
        f.write("## Recent Runs\n\n")
        f.write("| Run ID | Started | Status | Git SHA | Metrics |\n")
        f.write("|--------|---------|--------|---------|----------|\n")
        
        for run in runs:
            rid, started, finished, status, git_sha, metrics_json = run
            metrics_preview = ""
            if metrics_json:
                try:
                    metrics = json.loads(metrics_json)
                    metrics_preview = f"σ={metrics.get('score_sigma', 'N/A')}"
                except:
                    pass
            
            f.write(f"| `{rid}` | {started} | {status} | `{git_sha}` | {metrics_preview} |\n")
    
    print(f"Summary written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
