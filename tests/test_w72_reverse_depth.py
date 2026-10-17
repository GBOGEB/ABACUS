"""Deep negative W72 controls: CLI, I/O, bogus collection, provenance & CSV."""
from __future__ import annotations
import csv
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from tools import w72_receipt_provenance as provenance
from tools import w72_root_watch as roots
from tools import w72_testcase_telemetry as junit

HEAD='a'*40
MERGE='b'*40
GOOD=b'<testsuites><testsuite tests="1"><testcase classname="a" name="test_x" time=".01"/></testsuite></testsuites>'

class W72ExtendedNegativeTests(unittest.TestCase):
    def test_multiple_test_suites_accepted(self):
        xml=b'<testsuites><testsuite tests="1"><testcase classname="a" name="x"/></testsuite><testsuite tests="1"><testcase classname="a" name="y"/></testsuite></testsuites>'
        self.assertEqual(junit.parse_junit(xml)['counts']['collected'],2)

    def test_unexpected_xml_root_rejected(self):
        with self.assertRaises(ValueError):junit.parse_junit(b'<objects><object/></objects>')

    def test_nested_unexpected_suite_rejected(self):
        with self.assertRaises(ValueError):junit.parse_junit(b'<testsuites><thing/></testsuites>')

    def test_blank_case_name_rejected(self):
        with self.assertRaises(ValueError):junit.parse_junit(b'<testsuite tests="1"><testcase classname="a"/></testsuite>')

    def test_xml_empty_bytes_and_nonbytes_rejected(self):
        for payload in (b'',None,'text'):
            with self.subTest(payload=payload),self.assertRaises(ValueError):junit.parse_junit(payload)

    def test_unreasoned_skip_is_unclassified(self):
        x=junit.parse_junit(b'<testsuite tests="1"><testcase classname="a" name="sk"><skipped/></testcase></testsuite>')
        self.assertFalse(x['cases'][0]['skip_reason_present'])
        self.assertFalse(x['skip_owner_classified'])

    def test_no_skips_skip_owner_classification_is_unknown(self):
        self.assertIsNone(junit.parse_junit(GOOD)['skip_owner_classified'])

    def test_invalid_junit_comparison_counts_rejected(self):
        a=junit.parse_junit(GOOD)
        b=junit.parse_junit(GOOD)
        b['counts']['collected']=10
        with self.assertRaises(ValueError):junit.compare(a,b)

    def test_case_cli_generates_structural_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            inp=Path(d)/'junit.xml';out=Path(d)/'out.json';inp.write_bytes(GOOD)
            with patch.object(sys,'argv',['prog','--junit',str(inp),'--out',str(out)]),redirect_stdout(io.StringIO()):
                junit.main()
            self.assertEqual(json.loads(out.read_text())['counts']['passed'],1)

    def test_event_too_large_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);(base/'event.json').write_bytes(b' '*520000)
            with self.assertRaisesRegex(ValueError,'bounded'):
                provenance.run(root=base,event_file=base/'event.json',junit_file=base/'none.xml',
                               output=base/'out',cases_output=base/'cases')

    def test_malformed_event_json_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);(base/'event.json').write_text('no json')
            with self.assertRaises(json.JSONDecodeError):
                provenance.run(root=base,event_file=base/'event.json',junit_file=base/'none.xml',
                               output=base/'out',cases_output=base/'cases')

    def test_event_wrong_type_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);(base/'event.json').write_text('[]')
            with self.assertRaises(ValueError):
                provenance.run(root=base,event_file=base/'event.json',junit_file=base/'none.xml',
                               output=base/'out',cases_output=base/'cases')

    def test_provenance_main_argument_parsing(self):
        with patch.object(sys,'argv',['prog','--event','evt','--junit','case','--out','receipt','--cases-out','cases']):
            with patch.object(provenance,'run',return_value={'schema':'x','status':'PASS','source_sha':HEAD,'test_counts':{'collected':1}}) as f,redirect_stdout(io.StringIO()):
                provenance.main()
                self.assertEqual(f.call_count,1)

    def test_invalid_counts_missing_field_rejected(self):
        j=junit.parse_junit(GOOD);del j['counts']['passed']
        with self.assertRaises(ValueError):
            provenance.receipt(observed_sha=HEAD,event_name='pull_request',
                payload={'pull_request':{'head':{'sha':HEAD}}},context_sha=MERGE,
                run_id=1,run_attempt=1,job_id='clean-clone',junit=j,junit_bytes=GOOD)

    def test_no_case_evidence_cannot_pass(self):
        j=junit.parse_junit(GOOD);j['cases']=[]
        with self.assertRaises(ValueError):
            provenance.receipt(observed_sha=HEAD,event_name='pull_request',
                payload={'pull_request':{'head':{'sha':HEAD}}},context_sha=MERGE,
                run_id=1,run_attempt=1,job_id='clean-clone',junit=j,junit_bytes=GOOD)

    def test_root_dup_manifestation_rejected(self):
        r={'run_id':'1','job_id':'101','source_sha':HEAD,'passed':'1','failed':'2',
            'skipped':'0','queue_s':'1','signature':'WINDOWS_SNAPSHOT_PATH;WINDOWS_SNAPSHOT_PATH',
            'state':'RED','receipt_sha_matches_checkout':'False'}
        with self.assertRaises(ValueError):roots.snapshot([r],source_description='sample')

    def test_root_unknown_state_rejected(self):
        r={'run_id':'1','job_id':'101','source_sha':HEAD,'passed':'1','failed':'0',
            'skipped':'0','queue_s':'1','signature':'','state':'YELLOW',
            'receipt_sha_matches_checkout':''}
        with self.assertRaises(ValueError):roots.snapshot([r],source_description='sample')

    def test_root_empty_title_rejected(self):
        r={'run_id':'1','job_id':'101','source_sha':HEAD,'passed':'1','failed':'0',
            'skipped':'0','queue_s':'1','signature':'','state':'GREEN',
            'receipt_sha_matches_checkout':''}
        with self.assertRaises(ValueError):roots.snapshot([r],source_description='')

    def test_root_zero_case_collection_rejected(self):
        r={'run_id':'1','job_id':'101','source_sha':HEAD,'passed':'0','failed':'0',
            'skipped':'0','queue_s':'1','signature':'','state':'GREEN',
            'receipt_sha_matches_checkout':''}
        with self.assertRaises(ValueError):roots.snapshot([r],source_description='sample')

    def test_root_cli_runtime_outputs_deterministically(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);csvpath=base/'input.csv';out=base/'control.json'
            with csvpath.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=('run_id','job_id','source_sha','passed','failed',
                    'skipped','queue_s','signature','state','receipt_sha_matches_checkout'))
                w.writeheader();w.writerow({'run_id':'1','job_id':'101','source_sha':HEAD,
                    'passed':'1','failed':'0','skipped':'0','queue_s':'12','signature':'',
                    'state':'GREEN','receipt_sha_matches_checkout':''})
            with patch.object(sys,'argv',['prog','--csv',str(csvpath),'--out',str(out)]),redirect_stdout(io.StringIO()):
                roots.main()
            self.assertEqual(json.loads(out.read_text())['queue_p50_s'],12)

if __name__=='__main__':unittest.main()

class W72PytestSubtestBoundary(unittest.TestCase):
    def test_pytest_subtest_aggregate_not_forged_as_case_rows(self):
        xml=b'<?xml version="1.0"?><testsuites name="pytest tests"><testsuite name="pytest" tests="3" errors="0" failures="0" skipped="0"><testcase classname="suite" name="test_one" time="0.1"/></testsuite></testsuites>'
        r=junit.parse_junit(xml)
        self.assertEqual(r['counts']['collected'],1)
        self.assertEqual(r['reported_total_test_iterations'],3)
        self.assertEqual(r['unmaterialized_pytest_unittest_subtests'],2)
        self.assertFalse(r['case_identity_census_complete'])

    def test_non_pytest_missing_case_nodes_rejected(self):
        xml=b'<testsuites><testsuite tests="3"><testcase name="one"/></testsuite></testsuites>'
        with self.assertRaises(ValueError):junit.parse_junit(xml)

    def test_pytest_declares_less_than_actual_rejected(self):
        xml=b'<testsuites name="pytest tests"><testsuite name="pytest" tests="1"><testcase name="one"/><testcase name="two"/></testsuite></testsuites>'
        with self.assertRaises(ValueError):junit.parse_junit(xml)
