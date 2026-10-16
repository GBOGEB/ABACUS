"""Fail-closed, evidence-only qualification. Does not execute scanners or authorize merges."""
import json
import sys
from pathlib import Path

REQUIRED = ("repository","source_sha","method_id","tool_version","config_digest",
            "corpus_digest","run_id","job_id","attempt","tp","fp","fn","tn",
            "runtime_seconds","repair_receipt","negative_controls_pass",
            "federation_receipts","adaptive_receipt")
def qualify(e):
    missing = [k for k in REQUIRED if k not in e or e[k] is None]
    if missing:
        return {"state":"UNKNOWN","level":"M0","missing":missing,"merge_authorized":False}
    if any(type(e[k]) is not int or e[k]<0 for k in ("tp","fp","fn","tn")):
        return {"state":"INVALID","level":"M0","merge_authorized":False}
    if not isinstance(e["runtime_seconds"],(int,float)) or e["runtime_seconds"]<0:
        return {"state":"INVALID","level":"M0","merge_authorized":False}
    tp,fp,fn,tn=(e[k] for k in ("tp","fp","fn","tn"))
    precision=tp/(tp+fp) if tp+fp else None
    recall=tp/(tp+fn) if tp+fn else None
    level="M1"
    if tp+fn and fp+tn:
        level="M2"
        if e["repair_receipt"]:
            level="M3"
            if e["negative_controls_pass"] and fn==0:
                level="M4"
                if len(set(e["federation_receipts"]))>=2:
                    level="M5"
                    if e["adaptive_receipt"]:
                        level="M6"
    return {"state":"MEASURED","level":level,"precision":precision,
            "recall":recall,"runtime_seconds":e["runtime_seconds"],
            "merge_authorized":False}
if __name__=="__main__":
    print(json.dumps(qualify(json.loads(Path(sys.argv[1]).read_text())),sort_keys=True))
