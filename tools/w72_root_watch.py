"""W72 historical source-bound first-red and queue watch (not an admission gate).

One row represents one native W72 run/job attempt, not an independent trial.
No source-owned BD root is closed from a missing failure signature.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from collections import Counter
from pathlib import Path

SCHEMA = "abacus.w72.first-red-control.v1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
ROOT_MAP = {
    "WINDOWS_SNAPSHOT_PATH": {"root_family": "SNAPSHOT_PATH", "owner": "ABACUS#2046", "priority": "P1"},
    "BACKUP_OLD_CONTENT": {"root_family": "BACKUP_INTEGRITY", "owner": "ABACUS#2046", "priority": "P1"},
    "WORKFLOW_GOVERNANCE": {"root_family": "CI_POLICY_INVENTORY", "owner": "ABACUS#2041/#1995", "priority": "P0"},
    "RECEIPT_WRONG_CHECKOUT_SHA": {"root_family": "W72_SOURCE_PROVENANCE", "owner": "ABACUS#1860", "priority": "P0"},
    "SECURITY_A10": {"root_family": "A10_CONFIDENTIALITY", "owner": "ABACUS#1996", "priority": "P0"},
    "SAFETY_BANDIT": {"root_family": "INDEPENDENT_SECURITY", "owner": "ABACUS#1738/#2027", "priority": "P0"},
}
QUEUE_WATCH_SECONDS = 600  # Operator-specified threshold, NOT statistical UCL.


def _number(value: str, label: str) -> int:
    if not isinstance(value,str) or not value.isdecimal():
        raise ValueError("invalid " + label)
    n=int(value)
    if n < 0:
        raise ValueError("negative " + label)
    return n


def snapshot(rows: list[dict], *, source_description: str) -> dict:
    if not isinstance(rows, list) or not rows:
        raise ValueError("no observed W72 rows")
    if not isinstance(source_description, str) or not source_description.strip():
        raise ValueError("missing source description")
    seen=set()
    observed=[]
    signatures=Counter()
    queues=[]
    for row in rows:
        sha=row.get("source_sha")
        if not isinstance(sha,str) or not SHA40.fullmatch(sha):
            raise ValueError("missing exact SHA")
        run=_number(row.get("run_id"),"run_id")
        job=_number(row.get("job_id"),"job_id")
        if not run or not job or (run,job) in seen:
            raise ValueError("invalid/duplicate native run-job identity")
        seen.add((run,job))
        passed=_number(row.get("passed"),"passed")
        failed=_number(row.get("failed"),"failed")
        skipped=_number(row.get("skipped"),"skipped")
        if not (passed+failed+skipped):
            raise ValueError("zero effective test collection")
        queued=_number(row.get("queue_s"),"queue_s")
        queues.append(queued)
        red=row.get("signature","") or ""
        tokens=[p for p in red.split(";") if p]
        if len(tokens)!=len(set(tokens)):
            raise ValueError("duplicate first-red signature in one run")
        for value in tokens:
            if value not in ROOT_MAP:
                raise ValueError("unregistered first-red signature")
            signatures[value]+=1
        state=row.get("state")
        if state not in ("GREEN","RED"):
            raise ValueError("invalid observed state")
        if state=="GREEN" and (failed or tokens):
            raise ValueError("false-green claim: failed tests or red signature")
        if state=="RED" and not failed:
            raise ValueError("RED without reported failed tests")
        raw=row.get("receipt_sha_matches_checkout","")
        if raw not in ("True","False",""):
            raise ValueError("unrecognized receipt validity")
        observed.append({"run_id":run,"job_id":job,"source_sha":sha,"state":state,
                         "passed":passed,"failed":failed,"skipped":skipped,
                         "queue_s":queued,"first_red_signatures":tokens,
                         "receipt_source_matched":None if raw=="" else raw=="True"})
    ordered=sorted(observed,key=lambda x:x["run_id"])
    qsort=sorted(queues)
    p95=qsort[math.ceil(0.95*len(qsort))-1]
    mismatches=[x for x in observed if x['receipt_source_matched'] is False]
    return {
        "schema":SCHEMA,
        "source_description":source_description,
        "evidence_level":"HISTORICAL_NATIVE_LOG_PROJECTION_REQUIRES_INDEPENDENT_AUTHENTICATION",
        "run_job_observations":len(ordered),
        "distinct_source_shas":len(set(x['source_sha'] for x in ordered)),
        "terminal_green_observations":sum(x['state']=='GREEN' for x in ordered),
        "terminal_red_observations":sum(x['state']=='RED' for x in ordered),
        "test_pass_total_observed":sum(x['passed'] for x in ordered),
        "test_failed_total_observed":sum(x['failed'] for x in ordered),
        "test_skipped_total_observed":sum(x['skipped'] for x in ordered),
        "receipt_wrong_checkout_observations":len(mismatches),
        "receipt_not_measured_observations":sum(x['receipt_source_matched'] is None for x in ordered),
        "queue_threshold_s":QUEUE_WATCH_SECONDS,
        "queue_threshold_basis":"OPERATOR_WATCH_NOT_STATISTICAL_CONTROL_LIMIT",
        "queue_p50_s":statistics.median(queues),
        "queue_p95_nearest_rank_s":p95,
        "queue_over_threshold_observations":sum(q>QUEUE_WATCH_SECONDS for q in queues),
        "queue_over_threshold_rate":round(sum(q>QUEUE_WATCH_SECONDS for q in queues)/len(queues),6),
        "root_manifestations":[{**ROOT_MAP[code],"signature":code,"observations":n,
                                "root_closed":None} for code,n in sorted(signatures.items())],
        "control_carry_forward":[
            {"family":"W72_SOURCE_PROVENANCE","owner":"ABACUS#1860",
             "state":"PROOF_PENDING","next":"native checkout-bound receipt and changed-head retest"},
            {"family":"CI_POLICY_INVENTORY","owner":"ABACUS#2041/#1995",
             "state":"INDEPENDENT_GATE","next":"source-owned governance pass"},
            {"family":"A10_AND_SECURITY","owner":"ABACUS#1996/#2027",
             "state":"INDEPENDENT_GATE","next":"owner-disposition and terminal separate receipts"},
            {"family":"QUEUE_DELAY","owner":"ABACUS#1877/#2033",
             "state":"WATCH" if max(queues)>QUEUE_WATCH_SECONDS else "NO_WATCH_EVENT",
             "next":"differentiate created-to-start wait from actual suite runtime"},
            {"family":"W72_SKIP_CLASSIFICATION","owner":"ABACUS#1877",
             "state":"OWNER_CLASSIFICATION_PENDING" if any(x['skipped'] for x in ordered) else "NONE_OBSERVED",
             "next":"classify environment and Docker test skips before admissible denominator"},
        ],
        "samples":ordered,
        "unique_causal_roots_closed":None,
        "independent_trials":None,
        "statistical_ucl_s":None,
        "coverage_main_delta_pp":None,
        "coverage_pr_delta_pp":None,
        "crew_launch_authenticated":None,
        "rex_accepted":None,
        "authority_transfer":False,"security_waiver":False,"merge_authorized":False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    opts=p.parse_args()
    with opts.csv.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    result=snapshot(rows,source_description="W72 native source-bound six-wave historical log")
    opts.out.parent.mkdir(parents=True,exist_ok=True)
    opts.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"observations":result['run_job_observations'],
                      "wrong_sha":result['receipt_wrong_checkout_observations'],
                      "queue_p95_s":result['queue_p95_nearest_rank_s'],
                      "root_closures":None},sort_keys=True))

if __name__=='__main__':main()
