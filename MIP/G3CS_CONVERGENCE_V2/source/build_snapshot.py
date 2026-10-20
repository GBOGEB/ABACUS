"""Build a frozen source-bound G3C-S observation from supplied native GitHub artifacts.

Uses only downloaded files and user-provided GitHub readback values. It never
calls GitHub, guesses missing counters, changes acceptance, or launches workers.
"""
from pathlib import Path
import argparse
from datetime import date
import zipfile, json, hashlib

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--artifact-dir', type=Path, required=True, help='Directory containing the six native ZIP archives')
parser.add_argument('--out', type=Path, default=ROOT / 'source/G3CS_CONVERGENCE_INPUT.json')
args = parser.parse_args()
ORIGINAL = args.artifact_dir
SHA = {
 'S1': '6e23c38b2ee6504216887210769d119b4e6a709a',
 'S2': '38277a30cd5638a82f5dd5447d511d253d5846c0',
 'S3': '0f98f4f091b433c0984c361826ca7c2e9b3630c9',
}
CENSUS = {
 'S1': {'pr':2217,'observed':20,'success':14,'nonterminal':6,'run_ids':[39135344276,39134199171,39134198949,39134199001,39134198899,39134199027,39134199000,39134198907,39134198958,39134199006,39134198927,39134198914,39134198948,39134198956,39134198965,39134199003,39134199018,39134198999,39134199023,39134198981], 'merged_at':'2026-10-18T14:17:45Z','merge_sha':'b77348263d94b14ddf574bbf78ef7949f200d8c8'},
 'S2': {'pr':2219,'observed':21,'success':16,'nonterminal':5,'run_ids':[39135431172,39134282594,39134282669,39134282622,39134282776,39134282720,39134282702,39134282694,39134282910,39134282597,39134282675,39134282646,39134282798,39134282616,39134282779,39134282657,39134283101,39134282747,39134282604,39134283046,39134282783], 'merged_at':'2026-10-18T14:18:56Z','merge_sha':'4e159a745a32de0530f4228dc8cd5d168dfdd11e'},
 'S3': {'pr':2220,'observed':21,'success':16,'nonterminal':5,'run_ids':[39135416072,39134658882,39134658595,39134658623,39134658591,39134658631,39134658665,39134658614,39134658657,39134658673,39134658667,39134658652,39134658605,39134658616,39134658666,39134658626,39134658658,39134658678,39134658664,39134658670,39134658641], 'merged_at':'2026-10-18T14:18:41Z','merge_sha':'8bcb5729b3407685edb78af80378715ce61e70a2'},
}
EVIDENCE = []
def collect(name, member):
 p=ORIGINAL/name
 if not p.is_file():
  raise FileNotFoundError(f'Native artifact required: {p}')
 with zipfile.ZipFile(p) as zipf:
  raw=zipf.read(member)
 EVIDENCE.append({'locator':name+'#'+member,'sha256':hashlib.sha256(raw).hexdigest(),'container_zip_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 return json.loads(raw)

waves=[]
for index,w in enumerate(('S1','S2','S3')):
 i=index+1
 w70=collect(f'dmaic-g3cs-w{i}w70.zip','W70_METRICS.json')
 dab=collect(f'dmaic-g3cs-w{i}dab.zip','dab_flake8_census.json')
 info=CENSUS[w]
 assert w70['source_sha']==SHA[w] == dab['exact_sha']
 assert info['observed']==len(info['run_ids'])
 assert len(info['run_ids'])==len(set(info['run_ids']))
 waves.append({
  'wave':w,'clock':'PARALLEL_PR_HEAD','pr':info['pr'],'source_sha':SHA[w],
  'source_base_sha':'e08c51232edbb0ede05eab5bcd21f039539adf92',
  'main_merge_sha':info['merge_sha'],'merged_at_utc':info['merged_at'],'merged':True,
  'eligible_approvals':0,
  'workflow_census':{'scope':'SELECTED_PR_TRIGGERED_FIRST_PAGE','observed':info['observed'],'success':info['success'],
     'failure':0,'nonterminal':info['nonterminal'],'other_terminal':0,'run_ids':info['run_ids'],
     'completeness':'FIRST_PAGE_ONLY','run_attempt_status':'ONE_LATEST_OBSERVATION_PER_RUN'},
  'w70':{'source_sha':w70['source_sha'],'run_id':w70['run_id'],'attempt':w70['run_attempt'],
     'scope':'tools/w70_wave_pulse_metrics.py', 'scope_sha256':w70['coverage']['source_sha256'],
     'test_selection':w70['coverage']['test_selection'], 'tool_version':w70['coverage']['tool_version'],
     'lines':w70['coverage']['line'], 'branches':w70['coverage']['branch'],
     'lanes':w70['lanes'],'closed_manifestations':w70['debt']['closed_manifestations_sum'],
     'open_manifestations':w70['debt']['open_manifestations_sum'],
     'unique_confirmed_roots':w70['debt']['unique_confirmed_roots'],
     'coverage_delta':w70['coverage_delta']},
  'dab':{'source_sha':dab['exact_sha'],'run_id':{'S1':39134199001,'S2':39134282622,'S3':39134658652}[w],
     'command':dab['command'],'total':dab['total'],
     'families':{'E225':dab['all_families'].get('E225'),'W292':dab['all_families'].get('W292')}},
  'proofs':({'handover_native_tests':14,'native_smoke':'success'} if w=='S1'
   else {'pytest_validation_workflow':'success'} if w=='S3' else {}),
 })

snapshot={
 'schema':'codepurple.g3cs.convergence-input.v2',
 'repository':'GBOGEB/ABACUS','observed_date_utc':str(date(2026,10,18)),
 'live_observation_origin':'MCP_GITHUB_READBACK_WITH_DOWNLOADED_NATIVE_ARTIFACTS',
 'observed_main_sha':'585dd7476d3b3c629f864c37ec7d7526a648b4c0',
 'before_main_sha':'e08c51232edbb0ede05eab5bcd21f039539adf92',
 'parallel_heads_are_not_serial':'REQUIRED',
 'governance':{'admission':'HOLD','ruleset_id':24494381,'required_approvals':0,
    'required_status_contexts':[],'negative_red_canary_proven':False,
    'security_waiver':False,'authority_transfer':False,'review_eligibility_verified':False},
 'external':{'issues_open':38,'issues_closed':267,'issue_reference':'https://github.com/GBOGEB/ABACUS/issues/1860',
    'admission_todo_completed':1,'admission_todo_total':12,'dispatch_todo_completed':0,'dispatch_todo_total':7,
    'deduplicated_roots_open':None,'deduplicated_roots_closed':None,
    'main_statement_coverage':None,'main_branch_coverage':None,'diff_coverage':None,
    'remote_crew_launch_verified':False},
 'native_main_after_merge':{'terminal_full_ci':None,'postmerge_coverage':None,'negative_merge_canary':None},
 'history':{'historical_main_coverage':{'covered':34222,'eligible':51264,
    'source_sha':'49c945268ba26a8addb8a9cfa788de057b93fe1e','scope':'HISTORICAL_COMBINED_NOT_CURRENT_MAIN'},
    'previous_snapshot':{'successful':42,'observed':60,'run_population_hash':None,
         'comparability':'UNMATCHED_DIFFERENT_DENOMINATOR'}},
 'waves':waves,'evidence_files':EVIDENCE,
 'existing_providers':{
  'acceptance_graph':'tools/everred_v3/acceptance/graph.py',
  'acceptance_sipoc':'tools/everred_v3/acceptance/graph.py#sipoc',
  'acceptance_temporal':'tools/everred_v3/acceptance/telemetry.py',
  'ci_temporal':'tools/mip_ci_temporal_rollup.py',
  'coverage_delta':'scripts/cbd_matched_coverage_delta.py',
  'governance_owner_pr':'https://github.com/GBOGEB/ABACUS/pull/2144'},
}
p=args.out
p.parent.mkdir(parents=True,exist_ok=True)
p.write_text(json.dumps(snapshot,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
print(p, 'size',p.stat().st_size,'evidence_objects',len(EVIDENCE))
