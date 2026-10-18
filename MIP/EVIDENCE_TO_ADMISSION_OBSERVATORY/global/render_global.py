#!/usr/bin/env python3
"""Deterministic W38 global review-projection renderer (no remote writes)."""
from __future__ import annotations
import argparse, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
def render(ledger: dict, template: str) -> str:
    if ledger.get("schema")!="codepurple.global_dov_rollup.v1":
        raise ValueError("unsupported rollup schema")
    if ledger.get("governed_admission")!="HOLD" or ledger.get("global_control") is not False:
        raise ValueError("no unverified admission/control promotion")
    for repo in ledger["repos"]:
        sha=repo["main_sha"]
        if not isinstance(sha,str) or len(sha)!=40 or any(x not in "0123456789abcdef" for x in sha):
            raise ValueError("invalid source SHA")
    f=ledger["focused_coverage"]
    if sum(r["covered"] for r in f["families"])!=f["covered"] or sum(r["eligible"] for r in f["families"])!=f["eligible"]:
        raise ValueError("family numerator/denominator mismatch")
    if template.count("__GLOBAL_ROLLUP_JSON__")!=1:
        raise ValueError("missing/duplicate template slot")
    raw=json.dumps(ledger,ensure_ascii=True,separators=(",",":"))
    safe=raw.replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026")
    return template.replace("__GLOBAL_ROLLUP_JSON__",safe)

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--check",action="store_true")
    args=p.parse_args(argv)
    data=json.loads((HERE/"ledger.json").read_text(encoding="utf-8"))
    rendered=render(data,(HERE/"index.template.html").read_text(encoding="utf-8"))
    dest=HERE/"index.html"
    if args.check:
        if not dest.exists() or dest.read_text(encoding="utf-8")!=rendered:
            raise SystemExit("stale global dashboard (generate with python render_global.py)")
        print("W38 global HTML is source-matched")
    else:
        dest.write_text(rendered,encoding="utf-8")
        print("generated "+str(dest))
if __name__=="__main__":
    main()
