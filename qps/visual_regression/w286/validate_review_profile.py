#!/usr/bin/env python3
import argparse, json
from pathlib import Path
CLASSES=["PASS","INTENTIONAL_VISUAL_CHANGE","REGRESSION","REVIEW_REQUIRED"]
DIMS=["geometry_and_overflow","typography_and_minimum_readability","table_column_balance_and_wrapping","visual_hierarchy_and_status_prominence","whitespace_and_density","cross_format_information_priority","print_and_export_robustness"]
def validate(d):
    e=[]
    if d.get("schema")!="abacus-qps-visual-regression-profile/1.0": e.append("schema")
    if d.get("authority")!="PRESENTATION_REVIEW_UX_ONLY": e.append("authority")
    if d.get("review_classes")!=CLASSES: e.append("classes")
    if d.get("dimensions")!=DIMS: e.append("dimensions")
    if d.get("sample_only") is not True: e.append("sample_only")
    if d.get("formal_credit_delta")!=0: e.append("formal_credit")
    forbidden=d.get("forbidden_authority_fields") or []
    for required in ["engineering_disposition_override","compliance_override","negotiation_override","semantic_ssot_override"]:
        if required not in forbidden: e.append("forbidden_fields")
    return sorted(set(e))
def main():
    p=argparse.ArgumentParser(); p.add_argument("path",type=Path); a=p.parse_args()
    d=json.loads(a.path.read_text(encoding="utf-8")); e=validate(d)
    print(json.dumps({"passed":not e,"errors":e},sort_keys=True)); return 0 if not e else 2
if __name__=="__main__": raise SystemExit(main())
