"""Two link levels, one rule for moving up.

  mycelium       deep/keb_candidates.jsonl - every candidate link, alias and similarity, with its evidence. Regenerated.
  golden thread  GOLDEN_THREAD.jsonl       - accepted links only (source -> requirement -> object -> verification -> decision).
                                             Append-only, never regenerated, never written by a reader.

A candidate moves up only with BOTH an authority (who accepts it) and evidence (where it is written or shown).
A link whose only evidence is geometry (GEOMETRIC_TOUCH) needs --reviewed: a person looked at the drawing.
A relation that is still DEFER must be given a typed --relation by the authority; the tool never types it.

    python -I -X utf8 DMAIC_V3/binary_engines/thread_promote.py list [--grep TEXT]
    python -I -X utf8 DMAIC_V3/binary_engines/thread_promote.py promote <source_locator> --authority "<name>" --evidence "<doc/page>" [--relation process_flow] [--reviewed]
    python -I -X utf8 DMAIC_V3/binary_engines/thread_promote.py show
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estate_spec import ESTATE  # noqa: E402

EST = ESTATE
MYC = EST / "deep" / "keb_candidates.jsonl"
GOLD = EST / "GOLDEN_THREAD.jsonl"


def load(p: Path) -> list[dict]:
    return (
        [json.loads(l) for l in p.read_text("utf-8").split("\n") if l.strip()]
        if p.exists()
        else []
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "promote", "show"])
    ap.add_argument("locator", nargs="?")
    ap.add_argument("--grep", default="")
    ap.add_argument("--authority")
    ap.add_argument("--evidence")
    ap.add_argument("--relation")
    ap.add_argument("--reviewed", action="store_true")
    a = ap.parse_args()
    myc, gold = load(MYC), load(GOLD)
    if a.cmd == "list":
        for x in [x for x in myc if a.grep.lower() in x["statement"].lower()][:50]:
            print(
                f"{x['evidence']:16} {x['relation'][:20]:20} {x['statement'][:90]}  [{x['source_locator']}]"
            )
        print(f"mycelium: {len(myc)} candidates; golden thread: {len(gold)} accepted")
        return 0
    if a.cmd == "show":
        for g in gold:
            print(
                f"{g['accepted_on']} {g['relation']:16} {g['statement'][:80]}  by {g['authority']}  ({g['evidence_ref']})"
            )
        print(f"golden thread: {len(gold)} accepted")
        return 0
    cand = next((x for x in myc if x["source_locator"] == a.locator), None)
    problems = []
    if cand is None:
        problems.append("no mycelium candidate with that source_locator")
    if not a.authority:
        problems.append("--authority is required (who accepts this link)")
    if not a.evidence:
        problems.append("--evidence is required (where the link is written or shown)")
    if cand and cand["evidence"] != "FILE_CONNECTED" and not a.reviewed:
        problems.append(
            f"evidence is {cand['evidence']}: geometry alone needs --reviewed (a person looked at the drawing)"
        )
    relation = a.relation or (cand or {}).get("relation", "DEFER")
    if relation == "DEFER":
        problems.append(
            "relation is DEFER: the authority must give a typed --relation; the tool never invents one"
        )
    if cand and any(
        g["source_locator"] == cand["source_locator"]
        and g["source_digest"] == cand["source_digest"]
        for g in gold
    ):
        problems.append("already in the golden thread for this file version")
    if problems:
        print("REFUSED:\n  " + "\n  ".join(problems))
        return 2
    rec = {
        **{
            k: cand[k]
            for k in (
                "statement",
                "from",
                "to",
                "source_locator",
                "source_digest",
                "evidence",
                "drawn",
                "drawn_direction",
            )
        },
        "level": "golden_thread",
        "relation": relation,
        "authority": a.authority,
        "evidence_ref": a.evidence,
        "reviewed": a.reviewed,
        "accepted_on": dt.date.today().isoformat(),
    }
    GOLD.parent.mkdir(parents=True, exist_ok=True)
    with GOLD.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"ACCEPTED into golden thread: {rec['statement'][:90]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
