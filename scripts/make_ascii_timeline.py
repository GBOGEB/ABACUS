#!/usr/bin/env python3
"""
Generate ASCII timeline from run ledger.
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path("ledger/runs.sqlite")
OUTPUT_PATH = Path("artifacts/ascii/timeline.txt")


def main():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}", file=sys.stderr)
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT run_id, started_at, finished_at, status FROM runs ORDER BY started_at"
    ).fetchall()
    conn.close()
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_PATH, "w") as f:
        f.write("# DMAIC Timeline\n\n")
        
        if not rows:
            f.write("No runs found.\n")
            return
        
        for rid, started, finished, status in rows:
            duration = "ongoing" if not finished else f"{started} → {finished}"
            f.write(f"- {duration} | {rid} | {status}\n")
    
    print(f"Timeline written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
