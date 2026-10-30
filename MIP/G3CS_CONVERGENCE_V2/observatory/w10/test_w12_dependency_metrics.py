"""W12 negative graph-statistics, temporal gate and provenance regression tests."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('w12_metrics', HERE/'dependency_metrics.py')
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class DependencyW12Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history = json.loads((HERE/'W10_FROZEN_HISTORY.json').read_text())
        cls.epoch = json.loads((HERE/'W11_OBSERVED_MAIN_EPOCH.json').read_text())
        cls.graph = m._contract().make_dag(cls.history)

    def test_graph_nodes_edges_exact(self):
        g = m.summarize_graph(self.graph)
        self.assertEqual((g['nodes'],g['edges']), (37,46))
        self.assertEqual(g['edge_type_counts'],{'DERIVES':12,'OBSERVATION_ONLY':2,'OWNS':24,'SOURCE_INPUT':8})

    def test_density_uses_directed_denominator(self):
        g = m.summarize_graph(self.graph)
        self.assertAlmostEqual(g['directed_density'],46/(37*36),places=8)

    def test_distinct_paths_count_correct(self):
        g = m.summarize_graph(self.graph)
        self.assertEqual(g['distinct_source_to_customer_paths'],6)

    def test_only_structural_path_hops_no_elapsed_time(self):
        g = m.summarize_graph(self.graph)
        self.assertEqual(g['longest_dependency_path_hops'],6)
        self.assertEqual(len(g['longest_dependency_path']),7)
        self.assertIsNone(g['wall_clock_critical_path_seconds'])

    def test_mandatory_path_bottlenecks(self):
        g=m.summarize_graph(self.graph)
        self.assertEqual(set(g['all_path_mandatory_nodes']), {
            'stage:ingest','stage:verify','stage:graph','stage:publish','stage:federation_return'})

    def test_top_betweenness_is_design_node(self):
        g=m.summarize_graph(self.graph)
        self.assertEqual(g['top_structural_betweenness'][0]['id'],'stage:graph')
        self.assertGreater(g['top_structural_betweenness'][0]['structural_betweenness'],0)

    def test_all_asset_ownership_preserved(self):
        g=m.summarize_graph(self.graph)
        self.assertEqual(sum(g['asset_nodes_by_owner'].values()),24)

    def test_no_executed_trigger_claim(self):
        g=m.summarize_graph(self.graph)
        self.assertFalse(g['edges_are_executed_triggers'])
        self.assertIsNone(g['observed_failure_propagation_probability'])

    def test_graph_evidence_only_beyond_local(self):
        a=m.build(self.history,self.epoch)
        self.assertFalse(a['inference']['inference_ready'])
        self.assertEqual(a['governance']['merge_admission'],'HOLD')
        self.assertIsNone(a['governance']['authenticated_workers'])
        self.assertIsNone(a['governance']['formal_root_closure'])

    def test_observed_main_three_epochs(self):
        a=m.temporal_observations(self.history,self.epoch)
        self.assertEqual(a['successive_green_main_epochs'],3)
        self.assertEqual(a['observed_transitions'],2)
        self.assertEqual(a['observed_uncovered_counts'],[17036,17046,16926])
        self.assertEqual([x['uncovered_delta'] for x in a['deltas']],[10,-120])

    def test_coverage_trend_composition_not_fixed_attribution(self):
        a=m.temporal_observations(self.history,self.epoch)
        self.assertEqual([d['covered_delta'] for d in a['deltas']],[636,417])
        self.assertEqual([d['eligible_delta'] for d in a['deltas']],[646,297])
        self.assertTrue(all(d['fixed_population_causal_delta'] is None for d in a['deltas']))

    def test_no_pca_anova_manova_dnn_significance(self):
        a=m.build(self.history,self.epoch)
        q=a['inference']
        for k in ('PCA','ANOVA','MANOVA','Bradley_Terry_BT','bootstrap_temporal','Bayesian_trend','SPC_control_chart','DNN_temporal'):
            self.assertEqual(q[k]['state'],'NOT_QUALIFIED')
        self.assertIsNone(q['p_values'])
        self.assertIsNone(q['confidence_intervals'])
        self.assertIsNone(q['next_wave_prediction'])

    def test_avoids_pseudoreplication_from_nodes(self):
        a=m.build(self.history,self.epoch)
        self.assertEqual(a['sample_design']['unit'],'INDEPENDENT_SOURCE_BOUND_WAVE_CLUSTER_NOT_TEST_JOB')
        self.assertEqual(a['inference']['effective_independent_waves'],'UNKNOWN_UNTIL_WAVE_CLUSTER_DEDUP_AND_SCOPE_AUDIT')

    def test_immutable_native_sha_rejects_bad_sha(self):
        e=copy.deepcopy(self.epoch);e['measurements'][0]['source_sha']='bad'
        with self.assertRaisesRegex(ValueError,'SHA'):m.build(self.history,e)

    def test_duplicate_native_sha_rejected(self):
        e=copy.deepcopy(self.epoch);e['measurements'][1]['source_sha']=e['measurements'][0]['source_sha']
        with self.assertRaisesRegex(ValueError,'duplicate source'):m.build(self.history,e)

    def test_nonterminal_cannot_be_green_main(self):
        e=copy.deepcopy(self.epoch);e['measurements'][0]['native_b0_terminal']='queued'
        with self.assertRaisesRegex(ValueError,'nonterminal'):m.build(self.history,e)

    def test_missing_digest_rejected(self):
        e=copy.deepcopy(self.epoch);e['measurements'][1]['archive_sha256']=None
        with self.assertRaisesRegex(ValueError,'digest'):m.build(self.history,e)

    def test_coverage_denominator_conservation(self):
        e=copy.deepcopy(self.epoch);e['measurements'][1]['combined']['eligible']+=1
        with self.assertRaisesRegex(ValueError,'coverage conservation'):m.build(self.history,e)

    def test_coverage_statement_partition_conservation(self):
        e=copy.deepcopy(self.epoch);e['measurements'][1]['branches']['covered']+=1
        with self.assertRaisesRegex(ValueError,'statement-branch covered mismatch'):m.build(self.history,e)

    def test_coverage_branch_partition_conservation(self):
        e=copy.deepcopy(self.epoch);e['measurements'][1]['branches']['eligible']+=1
        with self.assertRaisesRegex(ValueError,'statement-branch denominator mismatch'):m.build(self.history,e)

    def test_retreat_from_frozen_parent_rejected(self):
        e=copy.deepcopy(self.epoch);e['measurements'][0]['source_sha']='f'*40
        with self.assertRaisesRegex(ValueError,'not linked'):m.build(self.history,e)

    def test_cannot_promote_merge_from_client(self):
        e=copy.deepcopy(self.epoch);e['governance']['merge_admission']='PASS'
        with self.assertRaisesRegex(ValueError,'admission'):m.build(self.history,e)

    def test_no_security_waiver_from_client(self):
        e=copy.deepcopy(self.epoch);e['governance']['security_waiver']=True
        with self.assertRaisesRegex(ValueError,'waiver'):m.build(self.history,e)

    def test_cycle_fails_closed_before_centrality(self):
        g=copy.deepcopy(self.graph)
        g['edges'].append(m._contract()._edge('stage:federation_return','stage:ingest','DERIVES'))
        with self.assertRaisesRegex(ValueError,'cycle'):m.summarize_graph(g)

    def test_unknown_edge_type_fails_closed(self):
        g=copy.deepcopy(self.graph)
        g['edges'][0]['type']='REMOTE_EXECUTOR'
        with self.assertRaisesRegex(ValueError,'unknown/unapproved'):m.summarize_graph(g)

    def test_no_transferred_authority_edge(self):
        g=copy.deepcopy(self.graph)
        g['edges'][0]['authority_transfer']=True
        with self.assertRaisesRegex(ValueError,'unsafe edge'):m.summarize_graph(g)

    def test_source_history_tamper_blocked(self):
        history=copy.deepcopy(self.history)
        history['clocks']['issues'][-1]['total_open']=0
        with self.assertRaisesRegex(ValueError,'issue conservation'):m.build(history,self.epoch)

    def test_repeated_rebuild_byte_equal(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            m.write_bundle(HERE/'W10_FROZEN_HISTORY.json',HERE/'W11_OBSERVED_MAIN_EPOCH.json',p)
            first=(p/'SPINE_STATS_W12.json').read_bytes()
            m.write_bundle(HERE/'W10_FROZEN_HISTORY.json',HERE/'W11_OBSERVED_MAIN_EPOCH.json',p)
            self.assertEqual(first,(p/'SPINE_STATS_W12.json').read_bytes())
            self.assertEqual(json.loads(first)['schema'],m.SCHEMA)

    def test_graph_permutation_score_invariant(self):
        g=copy.deepcopy(self.graph)
        o=m.summarize_graph(g)
        g['nodes'].reverse();g['edges'].reverse()
        new=m.summarize_graph(g)
        self.assertEqual(o,new)

    def test_a_b_a_provenance_reversible(self):
        before=m.build(self.history,self.epoch)
        changed=copy.deepcopy(self.history)
        changed['source_registry'][0]['purpose']='source-owned amended note'
        middle=m.build(changed,self.epoch)
        self.assertNotEqual(before['source_history_sha256'],middle['source_history_sha256'])
        again=m.build(self.history,self.epoch)
        self.assertEqual(before,again)


    def test_cli_exact_files_and_terminal_source_contract(self):
        import contextlib, io
        from unittest import mock
        with tempfile.TemporaryDirectory() as folder:
            argv=['dependency_metrics.py','--history',str(HERE/'W10_FROZEN_HISTORY.json'),
                  '--epoch',str(HERE/'W11_OBSERVED_MAIN_EPOCH.json'),'--outdir',folder]
            with mock.patch('sys.argv',argv),contextlib.redirect_stdout(io.StringIO()) as out:
                m.main()
            self.assertIn('inferential readiness= False',out.getvalue())
            a=json.loads((Path(folder)/'SPINE_STATS_W12.json').read_text())
            self.assertEqual(a['graph']['distinct_source_to_customer_paths'],6)


if __name__=='__main__':
    unittest.main()
