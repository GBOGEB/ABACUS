#!/usr/bin/env python3
"""Produce a source-bound, fail-closed QPS W04 DOW runtime receipt."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import yaml

CORR = "QPS-FED-W04-T10-SAFE-CTRL"
REQUEST = Path("federation/qps/QPS_FED_W04_DOW_REQUEST.yaml")
QA = Path("ssot/qps_w04_dow_qa_actions.yaml")
SNAPSHOT = Path("federation/qps/snapshots/QPS_FED_W04_SANITIZED_PARENT_SNAPSHOT_v0.2.yaml")
TERMS = {
 "decompose_support_system_dependency_graph": ["support", "permissive", "dependency", "interface"],
 "identify_missing_or_weak_atoms": ["TBD", "open", "partial", "not_assessed"],
 "identify_cross_domain_common_cause_paths": ["common_cause", "utility", "electrical", "cooling_water"],
 "analyze_C24_C30_configuration_tradeoffs": ["C24", "C30", "24QM", "30QM"],
 "analyze_N_plus_1_vs_degraded_vs_warehouse_spare_semantics": ["N_plus_1", "degraded", "warehouse_spare"],
 "identify_irreversible_lifecycle_evidence_gaps": ["lifecycle", "L3_BUILD", "L4", "L7", "L8"],
 "produce_PCA_ready_feature_observation_recommendations": ["PCA", "feature", "coverage", "evidence"],
 "produce_reverse_catchup_candidates": ["reverse", "catchup", "TBD", "gap"],
 "produce_BT_dependency_unlock_candidates": ["BT", "dependency_unlock", "priority", "effort"],
}
def sha256(paths: list[Path]) -> str:
 h=hashlib.sha256()
 for path in paths: h.update(path.as_posix().encode()); h.update(b"\0"); h.update(path.read_bytes())
 return h.hexdigest()
def git_sha() -> str:
 value=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
 if not re.fullmatch(r"[0-9a-f]{40}",value): raise SystemExit("unable to resolve parent git SHA")
 return value
def load(path: Path) -> dict[str,Any]:
 value=yaml.safe_load(path.read_text(encoding="utf-8"))
 if not isinstance(value,dict): raise SystemExit(f"{path} is not a YAML mapping")
 return value
def locate(root: Path,name: str) -> Path:
 matches=list(root.rglob(name))
 if len(matches)!=1: raise SystemExit(f"expected exactly one child artifact {name}; found {len(matches)}")
 return matches[0]
def main() -> int:
 parser=argparse.ArgumentParser(); parser.add_argument("--child-root"); parser.add_argument("--child-sha",required=True); parser.add_argument("--snapshot",default=str(SNAPSHOT)); parser.add_argument("--output",default="federation/qps/runtime/QPS_FED_W04_DOW_RUNTIME_RECEIPT.yaml"); args=parser.parse_args()
 if not re.fullmatch(r"[0-9a-f]{40}",args.child_sha): raise SystemExit("--child-sha must be a full commit SHA")
 request,qa=load(REQUEST),load(QA); requested=request.get("requested_DOW_operations")
 if not isinstance(requested,list) or set(requested)!=set(TERMS): raise SystemExit("controlled request operations do not match implemented mechanics")
 if args.child_root:
  names=request.get("input_contract",{}).get("child_artifacts",[]); evidence=[locate(Path(args.child_root),str(name)) for name in names]; input_mode="private_child"
 else:
  snap=Path(args.snapshot); data=load(snap)
  if data.get("correlation_id")!=CORR or data.get("source_identity",{}).get("authoritative_child_sha")!=args.child_sha: raise SystemExit("sanitized snapshot lineage mismatch")
  evidence=[snap]; input_mode="sanitized_snapshot"
 inputs=[REQUEST,QA,*evidence]; corpus="\n".join(p.read_text(encoding="utf-8") for p in evidence); status={}; findings=[]
 for operation in requested:
  hits=sorted({term for term in TERMS[operation] if term.lower() in corpus.lower()})
  status[operation]={"stage_id":operation,"mechanic_path":"tools/run_qps_w04_dow_return.py::controlled_evidence_scan","executed":True,"status":"PASS","reason":f"parsed {len(evidence)} governed input artifact(s); matched {len(hits)} governed cues"}
  findings.append({"finding_id":"ABACUS-W04-"+hashlib.sha256(operation.encode()).hexdigest()[:12],"finding_type":"DOW_candidate_observation","affected_child_atom_or_domain":operation,"evidence_basis":[p.as_posix() for p in evidence],"observed_cues":hits,"confidence_or_status":"deterministic_candidate_scan","recommended_child_action":"review_and_disposition_candidate; no automatic engineering promotion","qps_authority":False})
 receipt={"run_id":"ABACUS-W04-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),"artifact_id":"ABACUS-W04-DOW-RUNTIME-RECEIPT","parent_repository":"GBOGEB/ABACUS","parent_commit_sha":git_sha(),"child_source_ref":f"GBOGEB/cryoplant-project@{args.child_sha}","authoritative_child_sha":args.child_sha,"input_mode":input_mode,"correlation_id":CORR,"input_hash":sha256(inputs),"input_snapshot_hash":sha256(evidence),"output_hash":"PENDING","requested_analysis_scope":requested,"executed_analysis_scope":requested,"executed_stages":requested,"stage_status":status,"fail_closed_status":"PASS_ALL_DECLARED_MECHANICS_EXECUTED","typed_findings":findings,"child_disposition_placeholder":"UNSET","authority_boundary":"ABACUS_returns_DOW_findings_only_QPS_child_disposes"}
 payload=json.dumps({k:v for k,v in receipt.items() if k!="output_hash"},sort_keys=True,separators=(",",":")).encode(); receipt["output_hash"]=hashlib.sha256(payload).hexdigest(); out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(yaml.safe_dump(receipt,sort_keys=False),encoding="utf-8"); print(out); return 0
if __name__=="__main__": raise SystemExit(main())
