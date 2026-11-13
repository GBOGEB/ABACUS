"""Propose the physical grouping of root files: GG_<L>_<TYPE>\\<EPIC>\\[_superseded\\]<name>.

Writes inventory/MOVE_PLAN.csv only. Nothing moves until Invoke-EstateMove.ps1 -Execute is run by the owner.
Excluded from automatic moves (action != MOVE): git-tracked (needs git mv on a branch), Office-locked, path too long.

    python -I -X utf8 DMAIC_V3/binary_engines/estate_moveplan.py [--root-id ID]
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estate_spec import EPIC_SHORT, PRIVATE_EPICS, ROOTS, inv_dir  # noqa: E402

SHORT = EPIC_SHORT  # short folder names per epic, from configuration
RETIRE = {"SUPERSEDED", "DUPLICATE", "STALE_ARCHIVE"}
MAX_PATH = 250


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root-id", default="MI", choices=sorted(ROOTS))
    rid = ap.parse_args().root_id
    ROOT, INV = ROOTS[rid][0], inv_dir(rid)
    rows = json.loads((INV / "root_inventory_final.json").read_text("utf-8"))
    plan, stats = [], collections.Counter()
    for r in sorted(
        rows, key=lambda r: (r["letter"], r["epic_final"], r["name"].lower())
    ):
        if r.get("og5_repo") == "_personal":
            dest = Path("_personal") / Path(r["name"]).name
        else:
            sub = Path(f"GG_{r['letter']}_{r['type']}") / SHORT[r["epic_final"]]
            if r["decision_hint"] in RETIRE:
                sub /= "_superseded"
            dest = sub / Path(r["name"]).name
        full = ROOT / dest
        if r.get("location") == "grouped":
            # already grouped by an earlier move: never moved again automatically
            action = "IN_PLACE" if Path(r["name"]) == dest else "REGROUP_PROPOSED"
        elif r.get("cloud_only"):
            action = "SKIP_CLOUD_ONLY"
        elif r["git_tracked"]:
            action = "GIT_MV_ON_BRANCH"
        elif r["office_lock_present"]:
            action = "SKIP_LOCKED"
        elif len(str(full)) > MAX_PATH:
            action = "SKIP_PATH_TOO_LONG"
        elif full.exists():
            action = "SKIP_DEST_EXISTS"
        else:
            action = "MOVE"
        stats[action] += 1
        plan.append(
            {
                "action": action,
                "src": r["name"],
                "dest": str(dest),
                "type": r["type"],
                "epic": r["epic_final"],
                "epic_source": r["epic_source"],
                "decision_hint": r["decision_hint"],
                "sha256": r["sha256"],
                "bytes": r["bytes"],
            }
        )
    with (INV / "MOVE_PLAN.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(plan[0]))
        w.writeheader()
        w.writerows(plan)
    print(dict(stats))
    tracked_private = sum(
        1
        for p in plan
        if p["action"] == "GIT_MV_ON_BRANCH" and p["epic"] in PRIVATE_EPICS
    )
    print(f"git-tracked files of private epics in this git checkout: {tracked_private}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
