import copy
import importlib.util
import json
import pathlib
import unittest
import tempfile
from unittest.mock import patch
from collections import Counter

ROOT=pathlib.Path(__file__).resolve().parents[1]
PINNED_DAG=ROOT/'SPINE_DAG_W11.json'
PINNED_SIPOC=ROOT/'SPINE_SIPOC_W11.json'
if not PINNED_DAG.exists():PINNED_DAG=pathlib.Path('/mnt/data/W11_SPINE_DAG_W11.json')
if not PINNED_SIPOC.exists():PINNED_SIPOC=pathlib.Path('/mnt/data/W11_SPINE_SIPOC_W11.json')
spec=importlib.util.spec_from_file_location('w13_visual',ROOT/'build_spine_neural_w13.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)

class NeuralW13(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d=json.loads(PINNED_DAG.read_text())
        cls.s=json.loads(PINNED_SIPOC.read_text())
        cls.v=M.compile_data(cls.d,cls.s)
    def test_original_preserved(self):
        self.assertEqual(self.v['pinned_source']['original_nodes'],37)
        self.assertEqual(self.v['pinned_source']['original_edges'],46)
    def test_additive_extended_counts(self):
        self.assertEqual(self.v['summary']['extended_nodes'],55)
        self.assertEqual(self.v['summary']['extended_edges'],73)
    def test_method_family_count(self):
        self.assertEqual(self.v['summary']['node_kinds']['METHOD'],7)
    def test_sipoc_both_sides(self):
        self.assertEqual(self.v['summary']['node_kinds']['SUPPLIER'],5)
        self.assertEqual(self.v['summary']['node_kinds']['CUSTOMER'],5)
    def test_distinct_repositories(self):
        self.assertEqual(self.v['summary']['node_kinds']['REPOSITORY'],4)
    def test_sipoc_source_links(self):
        self.assertEqual(self.v['summary']['edge_types']['SIPOC_SUPPLIES'],5)
        self.assertEqual(self.v['summary']['edge_types']['SIPOC_SERVES'],5)
    def test_math_source_links(self):
        self.assertEqual(self.v['summary']['edge_types']['MATH_REFERENCE'],7)
    def test_federation_only_proposed(self):
        x=[e for e in self.v['edges'] if e['type']=='FEDERATION_REFERENCE']
        self.assertEqual(len(x),3)
        self.assertTrue(all(e['tier']=='PROPOSED_METADATA_ROUTE_ONLY' for e in x))
    def test_edges_degree_conserve(self):
        self.assertEqual(sum(n['in'] for n in self.v['nodes']),73)
        self.assertEqual(sum(n['out'] for n in self.v['nodes']),73)
    def test_distinct_sizes_not_equal(self):
        degrees={n['total'] for n in self.v['nodes']}
        self.assertGreater(len(degrees),4)
        self.assertEqual(self.v['summary']['max_output'],16)
    def test_no_observed_runtime_fabricated(self):
        self.assertTrue(all(e['actual_runtime_hits'] is None for e in self.v['edges']))
    def test_unique_shortcodes(self):
        names=[x['short'] for x in self.v['nodes']]
        self.assertEqual(len(names),len(set(names)))
    def test_every_node_has_full_name(self):
        self.assertTrue(all(n['name'] and n['kind'] for n in self.v['nodes']))
    def test_sipoc_process_linked(self):
        self.assertTrue(all(row['process_node'] in {n['id'] for n in self.v['nodes']} for row in self.v['sipoc']))
    def test_unsafe_endpoint_rejected(self):
        x=copy.deepcopy(self.d);x['edges'][0]['to']='stage:fake'
        with self.assertRaises(ValueError):M.compile_data(x,self.s)
    def test_bad_dag_count_denied(self):
        x=copy.deepcopy(self.d);x['nodes'].pop()
        with self.assertRaises(AssertionError):M.compile_data(x,self.s)
    def test_duplicate_node_denied(self):
        x=copy.deepcopy(self.d);x['nodes'][1]['id']=x['nodes'][0]['id']
        with self.assertRaises(AssertionError):M.compile_data(x,self.s)
    def test_invalid_method_url_denied(self):
        x=copy.deepcopy(self.d);x['nodes'][0]['source_url']='javascript:alert(1)'
        with self.assertRaises(ValueError):M.compile_data(x,self.s)
    def test_no_authority(self):
        self.assertTrue(self.v['statistical_limitations']['no_merge_credit'])
        self.assertTrue(self.v['statistical_limitations']['no_remote_dispatch'])
    def test_deterministic_bytes(self):
        a=json.dumps(M.compile_data(self.d,self.s),sort_keys=True)
        b=json.dumps(M.compile_data(self.d,self.s),sort_keys=True)
        self.assertEqual(a,b)
    def test_embedding_safe(self):
        x=M.make_html(self.v,'<script id="graphData">__GRAPH_DATA__</script>')
        self.assertTrue(x.startswith('<script'))
        self.assertIn('extended_nodes',x)
    def test_input_output_toggles_exposed(self):
        h=(ROOT/'neural_spine_w13.template.html').read_text()
        self.assertIn('value="input"',h)
        self.assertIn('value="output"',h)
        self.assertIn('value="62"',h)
    def test_registry_search_and_sticky_legend(self):
        h=(ROOT/'neural_spine_w13.template.html').read_text()
        self.assertIn('registrySearch',h)
        self.assertIn('position:sticky',h)
        self.assertIn('nodeColors',h)
    def test_cli_generates_identical_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('sys.argv',['build_spine_neural_w13.py','--dag',str(PINNED_DAG),'--sipoc',str(PINNED_SIPOC),'--template',str(ROOT/'neural_spine_w13.template.html'),'--outdir',tmp]):
                M.main()
            p=pathlib.Path(tmp)
            self.assertEqual(json.loads((p/'W13_NEURAL_SPINE_DATA.json').read_text())['summary']['extended_nodes'],55)
            self.assertIn('Content density',(p/'W13_NEURAL_SPINE_INTERACTIVE.html').read_text())

    def test_no_dnn_claim(self):
        self.assertIsNone(self.v['statistical_limitations']['independent_wave_count'])

if __name__=='__main__':unittest.main()
