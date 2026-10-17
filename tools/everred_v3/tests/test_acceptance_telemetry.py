import copy
import unittest

from acceptance import core, graph, telemetry
from test_acceptance_core import fixture


def snapshot(pulse, observations, ctx=None):
    c, baseline, _ = fixture()
    result = core.project(c, ctx or baseline, observations)
    g = graph.graph_projection(result)
    deps = sorted((e for e in g['edges'] if e['kind'] == 'DEPENDS_ON'), key=lambda e: (e['from'], e['to'], e['kind']))
    return {'pulse': pulse, 'projection': result,
            'graph_hash': core.digest(g), 'dependency_hash': core.digest(deps),
            'evidence_class': 'LOCAL_SYNTHETIC_FIXTURE'}


class TemporalMethodTests(unittest.TestCase):
    def test_three_pulse_observability_increases_without_admission(self):
        _, _, event = fixture()
        p = [snapshot(0, []), snapshot(1, [event()]),
             snapshot(2, [event(), event(id='OBS-002', code='ACC-002', pulse=2)])]
        result = telemetry.analyze(p)
        self.assertEqual([0, 1, 2], [x['observed_evidence'] for x in result['pulses']])
        self.assertEqual(2, result['metrics']['net_observed_gain'])
        self.assertTrue(result['metrics']['dependency_edges_stable'])
        self.assertIsNone(result['metrics']['formal_convergence'])

    def test_reverse_red_is_not_hidden_by_old_green(self):
        _, _, event = fixture()
        p = [snapshot(0, []), snapshot(1, [event()]),
             snapshot(2, [event(), event(id='OBS-002', verdict='FAIL', pulse=2)])]
        result = telemetry.analyze(p)
        self.assertEqual(1, result['metrics']['reverse_regressions'])
        self.assertEqual(0, result['pulses'][-1]['observed_evidence'])

    def test_a_b_a_epoch_invalidation_is_measured(self):
        _, ctx, event = fixture()
        old = event()
        a = copy.deepcopy(ctx)
        b = copy.deepcopy(ctx); b['GBOGEB/ABACUS']['head_sha'] = '9' * 40
        b['GBOGEB/ABACUS']['epoch'] = 2
        a3 = copy.deepcopy(a); a3['GBOGEB/ABACUS']['epoch'] = 3
        result = telemetry.analyze([snapshot(0, [old], a), snapshot(1, [old], b),
                                    snapshot(2, [old], a3)])
        self.assertEqual([1, 0, 0], [x['observed_evidence'] for x in result['pulses']])
        self.assertFalse(result['metrics']['context_identity_stable'])
        self.assertIsNone(result['metrics']['qualified_pca_result'])

    def test_duplicate_pulse_rejected(self):
        s = snapshot(1, [])
        with self.assertRaisesRegex(ValueError, 'pulse'):
            telemetry.analyze([s, s])

    def test_non_atomic_order_rejected(self):
        with self.assertRaisesRegex(ValueError, 'pulse'):
            telemetry.analyze([snapshot(2, []), snapshot(1, [])])

    def test_changed_contract_refuses_mismatched_denominator(self):
        a, b = snapshot(0, []), snapshot(1, [])
        b['projection']['source_contract_sha256'] = 'd' * 64
        with self.assertRaisesRegex(ValueError, 'contract'):
            telemetry.analyze([a, b])

    def test_missing_status_not_automatically_acceptance(self):
        report = telemetry.analyze([snapshot(0, []), snapshot(1, [])])
        self.assertEqual(0, report['metrics']['final_evidence_observed'])
        self.assertIsNone(report['metrics']['causal_roots_closed'])
        self.assertIsNone(report['metrics']['main_coverage_delta'])

    def test_negative_promoted_admission_rejected(self):
        a, b = snapshot(0, []), snapshot(1, [])
        b['projection']['admission'] = 'PASS'
        with self.assertRaisesRegex(ValueError, 'promotion'):
            telemetry.analyze([a, b])

    def test_forecast_scored_from_preregistered_clock(self):
        forecast = {'schema': 'codepurple.acceptance.forecast.v1',
                    'prediction_clock': 2, 'target_clock': 3,
                    'predict_tests_min': 40, 'predict_coverage_min_fraction': .9,
                    'predict_unauthorized_admissions': 0}
        scored = telemetry.score_pre_registered_forecast(
            forecast, {'pulse': 3, 'tests_passed': 47,
                       'coverage_fraction': .98, 'unauthorized_admissions': 0})
        self.assertTrue(scored['tests_min_met'])
        self.assertTrue(scored['coverage_target_met'])
        self.assertEqual(7, scored['test_signed_error_vs_minimum'])
        self.assertFalse(scored['forecast_is_statistical'])

    def test_hindsight_forecast_is_rejected(self):
        forecast = {'schema': 'codepurple.acceptance.forecast.v1',
                    'prediction_clock': 5, 'target_clock': 3,
                    'predict_tests_min': 4, 'predict_coverage_min_fraction': .9,
                    'predict_unauthorized_admissions': 0}
        with self.assertRaisesRegex(ValueError, 'precede'):
            telemetry.score_pre_registered_forecast(
                forecast, {'pulse': 3, 'tests_passed': 5,
                           'coverage_fraction': .9, 'unauthorized_admissions': 0})


if __name__ == '__main__':
    unittest.main()
