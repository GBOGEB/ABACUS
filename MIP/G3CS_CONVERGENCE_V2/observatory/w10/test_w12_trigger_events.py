"""Adversarial trigger event census, non-authority and N+i data readiness."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('g3cs_w12_trigger',ROOT/'trigger_events.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
DAG=json.loads((ROOT/'SPINE_DAG_W11.json').read_text())
SHA='a'*40

def sample():
    return {'schema':mod.SCHEMA,'repository':'GBOGEB/ABACUS',
     'governance':{'merge_admission':'HOLD','security_waiver':False,
                   'authority_transfer':False,'accepted_rex':None,'crew_worker_id':None},
     'waves':[{'wave_id':'N+1','source_sha':SHA,'source_clock':'EXACT_PR_HEAD',
               'run_id':39123456789,'attempt':1,'jobs':[{'job_id':123456789,
               'steps':[{'step_id':1,'from':'stage:ingest','to':'stage:verify','type':'DERIVES',
                         'fired':True,'started_at':'2026-10-18T16:00:00Z',
                         'completed_at':'2026-10-18T16:00:05Z','conclusion':'success',
                         'first_red_signature':None}]}]}]}

class TriggerEventW12Tests(unittest.TestCase):
 def denied(self, change,reason):
    s=sample();change(s)
    with self.assertRaisesRegex(ValueError,reason):mod.reduce_events(s,DAG)
 def test_valid_source_reported_not_native_accepted(self):
    r=mod.reduce_events(sample(),DAG)
    self.assertEqual((r['wave_clusters_reported'],r['fired_step_events']),(1,1))
    self.assertIsNone(r['independent_wave_clusters'])
    self.assertIsNone(r['p95_edge_latency_seconds'])
 def test_no_events_missing_not_zero_independent(self):
    s=sample();s['waves']=[];r=mod.reduce_events(s,DAG)
    self.assertEqual(r['wave_clusters_reported'],0)
    self.assertIsNone(r['independent_wave_clusters'])
 def test_false_merge_rejected(self):self.denied(lambda s:s['governance'].update(merge_admission='PASS'),'unsafe event authority')
 def test_security_waiver_rejected(self):self.denied(lambda s:s['governance'].update(security_waiver=True),'unsafe event authority')
 def test_crew_forgery_rejected(self):self.denied(lambda s:s['governance'].update(crew_worker_id=1),'unverified REX')
 def test_rex_forgery_rejected(self):self.denied(lambda s:s['governance'].update(accepted_rex=True),'unverified REX')
 def test_bad_sha_rejected(self):self.denied(lambda s:s['waves'][0].update(source_sha='no'),'invalid source SHA')
 def test_missing_job_rejected(self):self.denied(lambda s:s['waves'][0].update(jobs=[]),'job identities required')
 def test_duplicate_step_rejected(self):self.denied(lambda s:s['waves'][0]['jobs'][0]['steps'].append(dict(s['waves'][0]['jobs'][0]['steps'][0])),'duplicate job step')
 def test_duplicate_run_attempt_rejected(self):
    def f(s):
     b=copy.deepcopy(s['waves'][0]);b['wave_id']='N+2';s['waves'].append(b)
    self.denied(f,'duplicate run/attempt')
 def test_duplicate_wave_id_rejected(self):self.denied(lambda s:s['waves'].append(copy.deepcopy(s['waves'][0])),'duplicate wave ID')
 def test_unknown_edge_rejected(self):self.denied(lambda s:s['waves'][0]['jobs'][0]['steps'][0].update(to='missing'),'unbound or forged')
 def test_unfired_success_rejected(self):self.denied(lambda s:s['waves'][0]['jobs'][0]['steps'][0].update(fired=False),'unfired event')
 def test_observation_only_cannot_execute(self):
    def f(s):
     edge=next(e for e in DAG['edges'] if e['type']=='OBSERVATION_ONLY');s['waves'][0]['jobs'][0]['steps'][0].update({'from':edge['from'],'to':edge['to'],'type':edge['type']})
    self.denied(f,'cannot be declared')
 def test_negative_duration_rejected(self):self.denied(lambda s:s['waves'][0]['jobs'][0]['steps'][0].update(completed_at='2026-10-18T15:00:05Z'),'negative observed')
 def test_malformed_utc_rejected(self):self.denied(lambda s:s['waves'][0]['jobs'][0]['steps'][0].update(started_at='2026-10-18T17:00:05+01:00'),'canonical UTC')
 def test_success_with_forged_first_red_rejected(self):self.denied(lambda s:s['waves'][0]['jobs'][0]['steps'][0].update(first_red_signature='fake'),'first-red signature without failed')
 def test_failed_event_counts_but_not_root_closed(self):
    s=sample();s['waves'][0]['jobs'][0]['steps'][0].update(conclusion='failure',first_red_signature='ImportError')
    r=mod.reduce_events(s,DAG);self.assertEqual(r['wave_receipts'][0]['failed_steps'],1);self.assertIsNone(r['formal_root_closures'])
 def test_two_distinct_waves_remain_independence_unknown(self):
    s=sample();x=copy.deepcopy(s['waves'][0]);x.update(wave_id='N+2',run_id=39123456790);s['waves'].append(x)
    r=mod.reduce_events(s,DAG);self.assertEqual(r['wave_clusters_reported'],2);self.assertIsNone(r['independent_wave_clusters'])
 def test_mutation_of_input_does_not_change_previous_receipt(self):
    s=sample();a=mod.reduce_events(s,DAG);s['waves'][0]['jobs'][0]['steps'][0]['completed_at']='2026-10-18T16:00:08Z'
    b=mod.reduce_events(s,DAG);self.assertEqual(a['observed_edge_latencies_seconds'],[5.]);self.assertEqual(b['observed_edge_latencies_seconds'],[8.])

 def test_invalid_calendar_date_rejected(self):
    self.denied(lambda s:s['waves'][0]['jobs'][0]['steps'][0].update(started_at='2026-02-30T16:00:00Z'),'invalid UTC timestamp')
 def test_valid_skipped_trigger_does_not_create_latency(self):
    s=sample();s['waves'][0]['jobs'][0]['steps'][0].update(fired=False,conclusion='skipped')
    r=mod.reduce_events(s,DAG)
    self.assertEqual(r['observed_step_events'],1)
    self.assertEqual(r['fired_step_events'],0)
    self.assertEqual(r['observed_edge_latencies_seconds'],[])
 def test_cli_output_is_source_reported_not_accepted(self):
    from unittest import mock
    import tempfile
    with tempfile.TemporaryDirectory() as folder:
        d=Path(folder); packet=d/'events.json'; graph=d/'graph.json'; output=d/'observed.json'
        packet.write_text(json.dumps(sample()));graph.write_text(json.dumps(DAG))
        with mock.patch('sys.argv',['trigger_events.py','--events',str(packet),'--graph',str(graph),'--output',str(output)]):
            mod.main()
        result=json.loads(output.read_text())
        self.assertEqual(result['wave_receipts'][0]['native_authentication'],'SOURCE_REPORTED_UNVERIFIED')
        self.assertIsNone(result['independent_wave_clusters'])

if __name__=='__main__':unittest.main()