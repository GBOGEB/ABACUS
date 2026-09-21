#!/usr/bin/env python3
from __future__ import annotations
import argparse, itertools, json
from pathlib import Path

SCHEMA="MC2-W83-NG1-NONGOVERNANCE-OUTCOME-LEDGER-0.1.0"

def auc(labels, scores):
    pos=[s for y,s in zip(labels,scores) if y==1]
    neg=[s for y,s in zip(labels,scores) if y==0]
    if not pos or not neg:
        raise ValueError("AUC requires both outcome classes")
    wins=0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p>n else 0.5 if p==n else 0.0
    return wins/(len(pos)*len(neg))

def evaluate(ledger):
    if ledger.get("schema_version") != SCHEMA:
        raise ValueError("W83-NG1 ledger schema mismatch")
    if ledger.get("repository") != "GBOGEB/ABACUS":
        raise ValueError("W83-NG1 repository mismatch")
    rows=list(ledger.get("rows") or [])
    expected={f"s{i:02d}" for i in range(5,16)}
    if len(rows)!=11 or {r.get("label") for r in rows}!=expected:
        raise ValueError("W83-NG1 requires exact s05..s15 population")
    labels=[int(r["outcome"]["docs_failure"]) for r in rows]
    if sum(labels)!=8:
        raise ValueError("W83-NG1 requires governed 8-fail/3-pass docs outcome geometry")
    if ledger["feature_policy"]["included_blocks"] != ["semantic_composition","consumer_graph_distribution"]:
        raise ValueError("W83-NG1 non-governance block contract drift")
    if ledger["feature_policy"]["excluded_blocks"] != ["workflow_governance_composition"]:
        raise ValueError("W83-NG1 governance exclusion drift")
    if ledger["feature_policy"]["pca_fit_permitted"] is not False or ledger["feature_policy"]["bt_permitted"] is not False:
        raise ValueError("W83-NG1 must remain non-promotional")

    flat=[]
    sem_hashes=set()
    graph_hashes=set()
    for row in rows:
        if row["source_sha"] != row["outcome"]["source_sha"]:
            raise ValueError(f"source mismatch for {row['label']}")
        src=row["w83_source_receipt"]
        if int(src["run_id"]) != 35577332406 or int(src["job_id"])<=0 or int(src["artifact_id"])<=0:
            raise ValueError("W83 source receipt lineage missing")
        if not str(src["artifact_digest"]).startswith("sha256:"):
            raise ValueError("W83 source artifact digest missing")
        sem_hashes.add(src["semantic_block_sha256"])
        graph_hashes.add(src["consumer_graph_block_sha256"])
        f={}
        f.update({f"semantic_composition.{k}":int(v) for k,v in row["semantic_composition"].items()})
        f.update({f"consumer_graph_distribution.{k}":int(v) for k,v in row["consumer_graph_distribution"].items()})
        flat.append(f)
    names=sorted(flat[0])
    if any(sorted(f)!=names for f in flat):
        raise ValueError("W83-NG1 feature schema drift")
    variable=[n for n in names if len({f[n] for f in flat})>1]
    combos=list(itertools.combinations(range(len(rows)),sum(labels)))
    stats=[]
    for name in variable:
        scores=[f[name] for f in flat]
        observed=auc(labels,scores)
        distance=abs(observed-0.5)
        extreme=0
        for chosen in combos:
            candidate=[0]*len(rows)
            for idx in chosen:
                candidate[idx]=1
            if abs(auc(candidate,scores)-0.5)+1e-12 >= distance:
                extreme += 1
        stats.append({
            "feature":name,
            "distinct_value_count":len(set(scores)),
            "auc":round(observed,6),
            "auc_distance_from_chance":round(distance,6),
            "exact_p":round(extreme/len(combos),6),
        })
    stats.sort(key=lambda r:(r["exact_p"],-r["auc_distance_from_chance"],r["feature"]))
    running=0.0
    m=len(stats)
    for i,row in enumerate(stats):
        running=max(running,min(1.0,row["exact_p"]*(m-i)))
        row["holm_adjusted_p"]=round(running,6)
        row["signal_candidate"]=row["holm_adjusted_p"]<=0.05 and row["auc_distance_from_chance"]>=0.25
    significant=[r for r in stats if r["signal_candidate"]]
    strongest=stats[0]
    result={
        "schema_version":"MC2-W83-NG1-NONGOVERNANCE-OUTCOME-DIAGNOSTIC-0.1.0",
        "status":"NON_GOVERNANCE_SIGNAL_CANDIDATE_DIAGNOSTIC" if significant else "CONTROLLED_NEGATIVE_NON_GOVERNANCE_OUTCOME_DIAGNOSTIC",
        "authority":"derived_operational_analysis_only",
        "measurement_basis":"harvested_exact_source_W83_non_governance_features_plus_independent_W80_docs_outcomes",
        "sample_geometry":{
            "state_count":len(rows),
            "docs_failure_count":sum(labels),
            "docs_pass_count":len(rows)-sum(labels),
            "unique_semantic_vectors":len(sem_hashes),
            "unique_consumer_graph_vectors":len(graph_hashes),
            "variable_non_governance_feature_count":len(variable),
            "exact_label_permutation_count":len(combos),
        },
        "inference":{
            "primary_outcome":"docs_validation_failure",
            "test":"two-sided exact permutation of absolute AUC distance from 0.5",
            "multiplicity":"Holm FWER",
            "alpha":0.05,
            "minimum_auc_distance_from_chance_for_signal":0.25,
            "feature_results":stats,
            "significant_feature_count":len(significant),
            "signal_supported":bool(significant),
        },
        "interpretation":{
            "supported":(
                "at least one predeclared non-governance feature survives exact multiplicity control as a diagnostic signal candidate"
                if significant else
                "measured non-governance semantic/consumer-graph variation does not discriminate the independent docs outcome after exact multiplicity control"
            ),
            "strongest_raw_feature":strongest["feature"],
            "strongest_raw_auc":strongest["auc"],
            "strongest_raw_exact_p":strongest["exact_p"],
            "strongest_holm_p":strongest["holm_adjusted_p"],
            "causal_effect_claimed":False,
        },
        "pca_fit_performed":False,
        "timing_pca_reopened":False,
        "pc1_predictive_validation":False,
        "pairwise_outcome_accumulation_permitted":False,
        "pairwise_events":[],
        "bt_status":"WITHHELD_NO_CONNECTED_ELIGIBLE_OBSERVED_PAIRWISE_GRAPH",
        "global_allocation_authority":False,
        "engineering_compliance_release_authority":False,
        "authority_transfer":False,
        "formal_credit_delta":0,
        "math_skill_resolution":{
            "schema":"gbogeb.skill.receipt.v1",
            "skill":"math",
            "task_id":"MC2_W83_NG1_EXACT_NONGOVERNANCE_OUTCOME_DISCRIMINATION",
            "source_repo":"GBOGEB/ABACUS",
            "source_ref":"75a2e880760af08d1f76674e7b39da570bf4485f",
            "resolved_skill_path":"skills/math/SKILL.md",
            "authority_transfer":False,
            "status":"PASS_SKILL_RESOLUTION",
        },
        "next_frontier":(
            "replicate the signal on distinct exact-source outcome states before any multivariate or allocation use"
            if significant else
            "seek broader independent outcomes and/or change-delta features; do not fit PCA or BT to this negative small-sample block"
        ),
    }
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("ledger")
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    ledger=json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    result=evaluate(ledger)
    Path(args.out).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":
    main()
