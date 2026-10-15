"""Native telemetry contract tests; no network requests."""
import importlib.util
from pathlib import Path
from unittest.mock import patch
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'server.py'
spec = importlib.util.spec_from_file_location('code_purple_telemetry', SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SHA = 'a' * 40
BASE = 'b' * 40


def run(name, id, state, conclusion):
    return {'id': id, 'name': name, 'status': state, 'conclusion': conclusion,
            'head_sha': SHA, 'html_url': f'https://github.com/GBOGEB/ABACUS/actions/runs/{id}',
            'created_at': '2026-10-14T10:00:00Z'}


class NativeTelemetry(unittest.TestCase):
    def test_native_source_bound_denominator(self):
        def fetch(path, token=None):
            if path.endswith('per_page=100') and '/actions/runs?' in path:
                return {'total_count': 4, 'workflow_runs': [
                    run('SUT GUI', 101, 'completed', 'success'),
                    run('EVERRED', 102, 'completed', 'failure'),
                    run('MIP', 103, 'in_progress', None),
                    run('Docs', 104, 'queued', None)]}
            if '/actions/runs/102/jobs?' in path:
                return {'total_count': 1, 'jobs': [{
                    'id': 200, 'name': 'test 3.10', 'conclusion': 'failure',
                    'html_url': 'https://github.com/GBOGEB/ABACUS/actions/runs/102/job/200',
                    'steps': [{'name': 'Black check', 'conclusion': 'failure', 'number': 6}]}]}
            raise AssertionError(path)
        with patch.object(mod, 'fetch_github', side_effect=fetch):
            x = mod._native_ci(None, SHA)
        self.assertEqual(x['metrics']['terminal'], 2)
        self.assertEqual(x['metrics']['success'], 1)
        self.assertEqual(x['metrics']['failure'], 1)
        self.assertEqual(x['metrics']['queued'], 1)
        self.assertEqual(x['metrics']['in_progress'], 1)
        self.assertEqual(x['total_count'], 4)
        self.assertTrue(x['sample_complete'])
        self.assertEqual(x['first_red_completeness'], 'COMPLETE')
        self.assertEqual(x['first_reds'][0]['classification'], 'UNCLASSIFIED')
        self.assertIsNone(x['first_reds'][0]['root_id'])

    def test_truncated_actions_are_partial(self):
        with patch.object(mod, 'fetch_github', return_value={
            'total_count': 101, 'workflow_runs': [run('A', 100, 'completed', 'success')]}):
            x = mod._native_ci(None, SHA)
        self.assertFalse(x['sample_complete'])
        self.assertEqual(x['first_red_completeness'], 'PARTIAL')

    def test_sha_mismatch_is_rejected(self):
        row = run('A', 100, 'completed', 'success')
        row['head_sha'] = BASE
        with patch.object(mod, 'fetch_github', return_value={'total_count': 1, 'workflow_runs': [row]}):
            with self.assertRaisesRegex(ValueError, 'SHA'):
                mod._native_ci(None, SHA)

    def test_no_pr_sha_is_unknown_not_zero(self):
        x = mod._native_ci(None, None)
        self.assertIsNone(x['metrics']['success'])
        self.assertEqual(x['status'], 'UNKNOWN')

    def test_native_failed_job_without_details_is_unknown(self):
        def fetch(path, token=None):
            if '/actions/runs?' in path:
                return {'total_count': 1, 'workflow_runs': [run('EVERRED', 13, 'completed', 'failure')]}
            raise OSError('API denied')
        with patch.object(mod, 'fetch_github', side_effect=fetch):
            x = mod._native_ci(None, SHA)
        self.assertEqual(x['metrics']['failure'], 1)
        self.assertEqual(x['first_reds'][0]['classification'], 'UNKNOWN')
        self.assertEqual(x['first_red_completeness'], 'PARTIAL')

    def test_full_snapshot_gov_holds_and_observed_review_not_authority(self):
        def fetch(path, token=None):
            if '/branches/main' in path:
                return {'commit': {'sha': BASE}, 'protected': False}
            if '/rulesets/' in path:
                return {'id': 24494381, 'enforcement': 'active', 'rules': []}
            if '/pulls/1956/reviews?' in path:
                return [{'state': 'APPROVED', 'commit_id': SHA, 'user': {'login': 'different'}}]
            if '/pulls/1956' in path:
                return {'state': 'open', 'draft': True, 'merged': False, 'head': {'sha': SHA},
                        'user': {'login': 'author'}}
            if '/pulls/1951' in path:
                return {'state': 'closed', 'merged': True, 'head': {'sha': BASE},
                        'user': {'login': 'author'}}
            if '/actions/runs?' in path:
                return {'total_count': 1, 'workflow_runs': [run('SUT', 1, 'completed', 'success')]}
            raise AssertionError(path)
        with patch.object(mod, 'fetch_github', side_effect=fetch):
            x = mod.live_snapshot()
        self.assertFalse(x['repositories']['GBOGEB/ABACUS']['protected'])
        self.assertEqual(x['ruleset']['rule_count'], 0)
        self.assertEqual(x['independent_review'], 'OBSERVED_NOT_ELIGIBILITY')
        self.assertFalse(x['merge_authorized'])
        self.assertFalse(x['security_waiver'])
        self.assertFalse(x['authority_transfer'])
        self.assertEqual(x['collection'], 'COMPLETE')


if __name__ == '__main__':
    unittest.main()
