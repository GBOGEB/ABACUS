#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
REQ_TABS={"overview","requirement","minutes","engineering","federation","health","control"}
REQ_DENSITIES={"clean","balanced","dense"}
FORBIDDEN={"engineering_disposition_override","compliance_override","bidder_status_override"}

def validate(data):
    errors=[]
    if data.get("schema")!="abacus-qps-human-rendition-profile/1.0": errors.append("schema")
    if data.get("authority")!="PRESENTATION_AND_REVIEW_UX_ONLY": errors.append("authority")
    if set(data.get("tabs") or [])!=REQ_TABS: errors.append("tabs")
    if set((data.get("densities") or {}).keys())!=REQ_DENSITIES: errors.append("densities")
    if set(data.get("forbidden_authority_fields") or [])!=FORBIDDEN: errors.append("forbidden_authority_fields")
    if data.get("formal_credit_delta")!=0: errors.append("formal_credit")
    for name,cfg in (data.get("densities") or {}).items():
        if not cfg.get("primary_question") or int(cfg.get("max_primary_cards",0))<1: errors.append(f"density_{name}")
    return errors

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("path",type=Path); args=ap.parse_args()
    data=json.loads(args.path.read_text(encoding="utf-8")); errors=validate(data)
    print(json.dumps({"passed":not errors,"errors":errors},indent=2,sort_keys=True))
    return 0 if not errors else 2
if __name__=="__main__": raise SystemExit(main())
