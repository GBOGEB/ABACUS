#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

HEX64=re.compile(r'^[0-9a-f]{64}$')
HEX40=re.compile(r'^[0-9a-f]{40}$')

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fail(msg: str) -> None:
    raise SystemExit('FAIL '+msg)

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--payload',type=Path,required=True)
    p.add_argument('--expected-source-sha',required=True)
    p.add_argument('--expected-target-sha',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    d=json.loads(a.payload.read_text(encoding='utf-8'))
    if d.get('schema')!='accelerator-abacus-mapping/v0.1': fail('schema')
    if d.get('source_repo')!='GBOGEB/cryogenic-accelerator-workspace': fail('source repo')
    if d.get('target_repo')!='GBOGEB/ABACUS': fail('target repo')
    if d.get('source_sha')!=a.expected_source_sha or not HEX40.fullmatch(a.expected_source_sha): fail('exact source SHA')
    if d.get('target_sha')!=a.expected_target_sha or not HEX40.fullmatch(a.expected_target_sha): fail('exact target SHA')
    rows=d.get('mapping_rows')
    if not isinstance(rows,list) or not rows: fail('mapping_rows required')
    required={'source_requirement_id','source_requirement_sha256','target_artifact','target_test_or_evidence','relation_type','disposition'}
    for i,row in enumerate(rows,1):
        if not required.issubset(row): fail(f'row {i} fields')
        if not HEX64.fullmatch(str(row['source_requirement_sha256'])): fail(f'row {i} source hash')
        if row['disposition'] not in {'ACCEPT','REJECT','DEFER'}: fail(f'row {i} disposition')
        if not row['target_artifact'] or not row['target_test_or_evidence']: fail(f'row {i} target evidence')
    out={
      'schema':'abacus-accelerator-receiver/v0.1',
      'status':'ACCEPTED_AS_EVIDENCE_ONLY',
      'source_repo':d['source_repo'],'source_sha':d['source_sha'],
      'target_repo':d['target_repo'],'target_sha':d['target_sha'],
      'payload_sha256':sha256(a.payload),'mapping_rows':len(rows),
      'authority_effect':'NONE','compliance_credit':False,'release_credit':False
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(out,sort_keys=True))
    return 0

if __name__=='__main__': raise SystemExit(main())
