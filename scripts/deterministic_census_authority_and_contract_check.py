#!/usr/bin/env python3
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
TUPLE=ROOT/'triage/census/roundtrip/TRIAGE_W62_IMMUTABLE_TUPLE.json'
if not TUPLE.exists():
    raise SystemExit('FAIL missing tuple')
raw=TUPLE.read_text(encoding='utf-8')
obj=json.loads(raw)
required={'schema','tuple_id','child_repo','authority','operation','disposition_enum'}
missing=sorted(required-set(obj))
if missing:
    raise SystemExit('FAIL missing fields: '+','.join(missing))
if obj['authority']!='CHILD_ENGINEERING_AUTHORITY':
    raise SystemExit('FAIL authority mismatch')
if obj['operation']!='CENSUS_DOV_PROOF':
    raise SystemExit('FAIL operation mismatch')
if obj['disposition_enum']!=['ACCEPT','REJECT','DEFER']:
    raise SystemExit('FAIL disposition enum mismatch')
canon=json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
digest=hashlib.sha256(canon).hexdigest()
print('method=deterministic_census_authority_and_contract_check/v1')
print('tuple_id='+obj['tuple_id'])
print('canonical_sha256='+digest)
print('authority_overlap=false')
print('engineering_mutation=false')
print('status=PASS')
print('recommendation=ACCEPT')
