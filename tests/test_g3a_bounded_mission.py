"""19 stand-alone positive/adversarial tests for G3A fail-closed progression."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

P = Path(__file__).resolve().parents[1] / 'scripts/g3a_bounded_mission.py'
spec = importlib.util.spec_from_file_location('g3a_bounded_mission', P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
HEAD = 'a' * 40


def mission(step_kind='syntax'):
    steps = []
    for i in range(1, 4):
        steps.append({'id': f'A{i}', 'kind': step_kind, 'path': f's{i}.py',
                      'objective': f'proof {i}', 'moniker': 'RECEIPT'})
    return {'schema': m.SCHEMA, 'mode': 'G3A', 'repository': 'GBOGEB/ABACUS',
            'mission_id': 'fixture-3', 'start_n': 12, 'steps': steps}


class G3AContracts(unittest.TestCase):
    def test_three_distinct_verified_advances(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for i in range(1, 4):
                (root / f's{i}.py').write_text(f'v{i} = {i}\n')
            result = m.execute(mission(), root, HEAD, HEAD)
            self.assertEqual((result['start_n'], result['target_n'], result['actual_n']), (12, 15, 15))
            self.assertEqual((result['attempted'], result['accepted_checkpoints']), (3, 3))
            self.assertEqual(result['status'], 'COMPLETE_LOCAL_3_OF_3')
            self.assertEqual(result['merge_admission'], 'HOLD')
            self.assertEqual([s['n_after'] for s in result['steps']], [13, 14, 15])

    def test_major_blocker_early_stop(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 's1.py').write_text('one = 1\n')
            result = m.execute(mission(), root, HEAD, HEAD)
            self.assertEqual((result['status'], result['accepted_checkpoints'], result['attempted']), ('BLOCKED_MAJOR', 1, 2))
            self.assertEqual(result['actual_n'], 13)

    def test_first_step_failure_no_advancement(self):
        with tempfile.TemporaryDirectory() as d:
            result = m.execute(mission(), Path(d), HEAD, HEAD)
            self.assertEqual((result['attempted'], result['actual_n']), (1, 12))

    def test_checkout_mismatch_prevents_execution(self):
        with self.assertRaisesRegex(m.ContractError, 'checkout'):
            m.execute(mission(), Path('.'), HEAD, 'b' * 40)

    def test_absent_or_malformed_sha_rejected(self):
        for sha in ('', 'a' * 39, 'not-a-sha'):
            with self.subTest(sha=sha), self.assertRaisesRegex(m.ContractError, 'expected head'):
                m.execute(mission(), Path('.'), sha, sha)

    def test_zero_and_negative_start_rejected(self):
        for bad in (True, -1, 1.2):
            v = mission()
            v['start_n'] = bad
            with self.subTest(bad=bad), self.assertRaises(m.ContractError):
                m.validate(v)

    def test_only_three_steps_are_allowed(self):
        for qty in (0, 1, 2, 4):
            v = mission()
            v['steps'] = v['steps'][:qty] if qty < 4 else v['steps'] + [v['steps'][-1]]
            with self.subTest(qty=qty), self.assertRaises(m.ContractError):
                m.validate(v)

    def test_duplicate_proof_scope_not_three_advances(self):
        v = mission()
        v['steps'][1]['path'] = 's1.py'
        with self.assertRaisesRegex(m.ContractError, 'duplicate checkpoint proof'):
            m.validate(v)

    def test_out_of_order_step_rejected(self):
        v = mission()
        v['steps'][1]['id'] = 'A3'
        with self.assertRaisesRegex(m.ContractError, 'IDs'):
            m.validate(v)

    def test_arbitrary_command_not_allowed(self):
        v = mission()
        v['steps'][0]['kind'] = 'shell'
        with self.assertRaises(m.ContractError):
            m.validate(v)

    def test_action_moniker_must_be_existing_global_taxonomy(self):
        v = mission()
        v['steps'][0]['moniker'] = 'CG'
        with self.assertRaises(m.ContractError):
            m.validate(v)

    def test_absolute_parent_and_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for path in ('../outside.py', '/tmp/elsewhere.py', 'x/../y.py', 'back\\slash.py'):
                with self.subTest(path=path), self.assertRaises(m.ContractError):
                    m.file_at(root, path)

    def test_digest_match_and_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            data = b'x=1\n'
            (root / 's1.py').write_bytes(data)
            step = dict(mission()['steps'][0], kind='file_sha256', expected_sha256=hashlib.sha256(data).hexdigest())
            self.assertTrue(m.perform(root, step, HEAD)['ok'])
            step['expected_sha256'] = '0' * 64
            self.assertFalse(m.perform(root, step, HEAD)['ok'])

    def test_bad_digest_rejected_in_manifest(self):
        v = mission()
        v['steps'][0].update(kind='file_sha256', expected_sha256='short')
        with self.assertRaises(m.ContractError):
            m.validate(v)

    def test_syntax_error_is_major_blocker(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 's1.py').write_text('if broken\n')
            result = m.execute(mission(), root, HEAD, HEAD)
            self.assertEqual(result['status'], 'BLOCKED_MAJOR')
            self.assertEqual(result['accepted_checkpoints'], 0)

    def test_metric_pass_and_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'data.json').write_text(json.dumps({'head_sha': HEAD, 'covered': 81, 'total': 100}))
            step = {'kind': 'metric_min', 'path': 'data.json', 'minimum_percent': 80}
            self.assertTrue(m.perform(root, step, HEAD)['ok'])
            step['minimum_percent'] = 82
            self.assertFalse(m.perform(root, step, HEAD)['ok'])

    def test_metric_wrong_head_invalid_and_zero_denominator(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / 'data.json'
            for obj in ({'head_sha': 'b' * 40, 'covered': 5, 'total': 10},
                        {'head_sha': HEAD, 'covered': 5, 'total': 0},
                        {'head_sha': HEAD, 'covered': True, 'total': 10}):
                path.write_text(json.dumps(obj))
                with self.assertRaises(m.ContractError):
                    m.perform(root, {'kind': 'metric_min', 'path': 'data.json', 'minimum_percent': 50}, HEAD)

    def test_unittest_pattern_must_be_bounded(self):
        for pat in ('*', '../bad.py', 'test_x.py;echo', 'unit.py'):
            v = mission()
            v['steps'][0] = {'id': 'A1', 'kind': 'unittest', 'pattern': pat,
                             'minimum_tests': 1, 'moniker': 'HARDEN', 'objective': 'tests'}
            with self.assertRaises(m.ContractError):
                m.validate(v)

    def test_unittest_runs_real_subprocess(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'tests').mkdir()
            (root / 'tests' / 'test_small.py').write_text('import unittest\nclass TestSmall(unittest.TestCase):\n def test_pass(self): self.assertTrue(True)\n')
            step = {'kind': 'unittest', 'pattern': 'test_small.py', 'minimum_tests': 1}
            result = m.perform(root, step, HEAD)
            self.assertTrue(result['ok'])
            self.assertEqual(result['tests_executed'], 1)

    def test_security_and_merge_never_inferred(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for i in range(1, 4):
                (root / f's{i}.py').write_text('x=1\n')
            r = m.execute(mission(), root, HEAD, HEAD)
            self.assertIs(r['security_waiver'], False)
            self.assertIs(r['authority_transfer'], False)
            self.assertEqual((r['formal_root_closures'], r['main_merges']), (0, 0))

    def test_bad_schema_mode_repo_and_mission_id(self):
        for key, value in (('schema', 'other'), ('mode', '3W'),
                           ('repository', 'untrusted/example'), ('mission_id', '../escape')):
            v = mission()
            v[key] = value
            with self.subTest(key=key), self.assertRaises(m.ContractError):
                m.validate(v)

    def test_missing_path_bad_minimum_and_bad_metric_threshold(self):
        v = mission()
        v['steps'][0].pop('path')
        with self.assertRaisesRegex(m.ContractError, 'path'):
            m.validate(v)
        for bad in (True, 0, 'many'):
            v = mission()
            v['steps'][0] = {'id': 'A1', 'kind': 'unittest',
                              'pattern': 'test_a.py', 'minimum_tests': bad,
                              'objective': 'test', 'moniker': 'HARDEN'}
            with self.subTest(minimum=bad), self.assertRaises(m.ContractError):
                m.validate(v)
        for bad in (-1, 101, '100'):
            v = mission()
            v['steps'][0] = {'id': 'A1', 'kind': 'metric_min',
                              'path': 'x.json', 'minimum_percent': bad,
                              'objective': 'metric', 'moniker': 'RECEIPT'}
            with self.subTest(threshold=bad), self.assertRaises(m.ContractError):
                m.validate(v)

    def test_timed_out_tests_do_not_count(self):
        with mock.patch.object(m.subprocess, 'run', side_effect=m.subprocess.TimeoutExpired('python', 120)):
            row = m.perform(Path('.'), {'kind': 'unittest', 'pattern': 'test_small.py',
                                         'minimum_tests': 1}, HEAD)
        self.assertFalse(row['ok'])
        self.assertIsNone(row['tests_executed'])

    def test_main_emits_three_step_receipt_with_git_head_readback(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for i in range(1, 4):
                (root / f's{i}.py').write_text('ok = True\n')
            spec_path, out = root / 'plan.json', root / 'receipt.json'
            spec_path.write_text(json.dumps(mission()))
            with mock.patch.object(m.subprocess, 'check_output', side_effect=lambda command, **kw: ('HEAD?' if 'no-such-command' in command else ('' if 'status' in command else HEAD + '\n'))):
                code = m.main(['--spec', str(spec_path), '--repo-root', str(root),
                               '--expected-head', HEAD, '--out', str(out)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.read_text())['actual_n'], 15)
            (root / 's3.py').unlink()
            with mock.patch.object(m.subprocess, 'check_output', side_effect=lambda command, **kw: ('HEAD?' if 'no-such-command' in command else ('' if 'status' in command else HEAD + '\n'))):
                code = m.main(['--spec', str(spec_path), '--repo-root', str(root),
                               '--expected-head', HEAD, '--out', str(out)])
            self.assertEqual(code, 3)
            self.assertEqual(json.loads(out.read_text())['actual_n'], 14)

    def test_git_dirty_tracked_file_prevents_exact_head_proof(self):
        with mock.patch.object(m.subprocess, 'check_output', return_value=' M scripts/g3a_bounded_mission.py\n'):
            with self.assertRaisesRegex(m.ContractError, 'tracked working tree'):
                m.verify_clean_checkout(Path('.'))

    def test_clean_tracked_worktree_passes_preflight(self):
        with mock.patch.object(m.subprocess, 'check_output', return_value=''):
            self.assertEqual(m.verify_clean_checkout(Path('.')), 'TRACKED_FILES_CLEAN')

    def test_git_dirty_main_returns_precheck_hold_and_no_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            specfile = root / 'spec.json'
            specfile.write_text(json.dumps(mission()))
            def git_response(args, **kw):
                return ' M tests/test_g3a_bounded_mission.py\n' if 'status' in args else HEAD + '\n'
            with mock.patch.object(m.subprocess, 'check_output', side_effect=git_response):
                with self.assertRaises(SystemExit) as err:
                    m.main(['--spec', str(specfile), '--repo-root', str(root),
                            '--expected-head', HEAD, '--out', str(root / 'receipt.json')])
            self.assertEqual(err.exception.code, 2)
            self.assertFalse((root / 'receipt.json').exists())

    def metric_delta_fixture(self):
        return {
            'schema': 'g3a.matched-metric.v1', 'repository': 'GBOGEB/ABACUS',
            'measurement': 'branches', 'module_path': 'scripts/target.py',
            'source_sha256': 'f' * 64,
            'before': {'head_sha': 'b' * 40, 'run_id': 100, 'run_attempt': 1,
                       'job_id': 101, 'covered': 10, 'total': 40},
            'after': {'head_sha': HEAD, 'run_id': 102, 'run_attempt': 2,
                      'job_id': 103, 'covered': 21, 'total': 40},
        }

    def test_matched_delta_positive_measurable_gain(self):
        row = m.matched_metric_delta(self.metric_delta_fixture(), HEAD, 5, 'd' * 64)
        self.assertTrue(row['ok'])
        self.assertEqual(row['delta_covered'], 11)
        self.assertEqual(row['delta_percentage_points'], 27.5)
        self.assertEqual(row['evidence_class'], 'DECLARED_NOT_NATIVE_AUTHENTICATED')
        self.assertFalse(row['native_approval'])

    def test_matched_delta_below_required_gain_no_advancement(self):
        row = m.matched_metric_delta(self.metric_delta_fixture(), HEAD, 12, 'd' * 64)
        self.assertFalse(row['ok'])
        self.assertEqual(row['after'], [21, 40])

    def test_metric_absent_before_or_after_fails_closed(self):
        for missing in ('before', 'after'):
            obj = self.metric_delta_fixture()
            obj.pop(missing)
            with self.subTest(missing=missing), self.assertRaisesRegex(m.ContractError, 'before and after'):
                m.matched_metric_delta(obj, HEAD, 1, 'd' * 64)

    def test_metric_malformed_producer_head_fails_closed(self):
        obj = self.metric_delta_fixture()
        obj['before']['head_sha'] = 'not-a-commit'
        with self.assertRaisesRegex(m.ContractError, 'missing exact head'):
            m.matched_metric_delta(obj, HEAD, 1, 'd' * 64)

    def test_script_entrypoint_requires_arguments(self):
        import runpy
        import sys
        with mock.patch.object(sys, 'argv', [str(P)]):
            with self.assertRaises(SystemExit) as err:
                runpy.run_path(str(P), run_name='__main__')
        self.assertEqual(err.exception.code, 2)

    def test_matched_delta_regression_cannot_pass(self):
        obj = self.metric_delta_fixture()
        obj['after']['covered'] = 9
        row = m.matched_metric_delta(obj, HEAD, 1, 'd' * 64)
        self.assertEqual(row['delta_covered'], -1)
        self.assertFalse(row['ok'])

    def test_denominator_drift_fails_closed(self):
        obj = self.metric_delta_fixture()
        obj['after']['total'] = 41
        with self.assertRaisesRegex(m.ContractError, 'denominator drift'):
            m.matched_metric_delta(obj, HEAD, 1, 'd' * 64)

    def test_recycled_attempt_and_job_fails_closed(self):
        obj = self.metric_delta_fixture()
        for field in ('run_id', 'run_attempt', 'job_id'):
            obj['after'][field] = obj['before'][field]
        with self.assertRaisesRegex(m.ContractError, 'recycled'):
            m.matched_metric_delta(obj, HEAD, 1, 'd' * 64)

    def test_invalid_metric_schema_and_source_identity(self):
        obj = self.metric_delta_fixture()
        for key, value in (('schema', 'arbitrary'), ('source_sha256', 'SHORT'),
                           ('repository', 'GBOGEB/CODEX'), ('measurement', 'fake'),
                           ('module_path', '../secret.py')):
            trial = json.loads(json.dumps(obj))
            trial[key] = value
            with self.subTest(key=key), self.assertRaises(m.ContractError):
                m.matched_metric_delta(trial, HEAD, 1, 'd' * 64)

    def test_invalid_metric_count_and_missing_job_identity(self):
        obj = self.metric_delta_fixture()
        for key, value in (('covered', True), ('covered', 50), ('total', 0),
                           ('run_attempt', 0), ('job_id', True), ('run_id', None)):
            trial = json.loads(json.dumps(obj))
            trial['after'][key] = value
            with self.subTest(key=key), self.assertRaises(m.ContractError):
                m.matched_metric_delta(trial, HEAD, 1, 'd' * 64)

    def test_after_head_has_to_match_checkout(self):
        obj = self.metric_delta_fixture()
        obj['after']['head_sha'] = 'c' * 40
        with self.assertRaisesRegex(m.ContractError, 'does not match checkout'):
            m.matched_metric_delta(obj, HEAD, 1, 'd' * 64)

    def test_metric_min_new_covered_rejects_zero_and_boolean(self):
        for minimum in (0, True, -1, 1.2):
            spec = mission()
            spec['steps'][0]['kind'] = 'metric_delta'
            spec['steps'][0]['minimum_new_covered'] = minimum
            with self.subTest(value=minimum), self.assertRaises(m.ContractError):
                m.validate(spec)

    def test_local_delta_step_executes_but_not_native_authority(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'metrics.json').write_text(json.dumps(self.metric_delta_fixture()))
            row = m.perform(root, {'kind': 'metric_delta', 'path': 'metrics.json',
                                   'minimum_new_covered': 3}, HEAD)
            self.assertTrue(row['ok'])
            self.assertEqual(row['evidence_class'], 'DECLARED_NOT_NATIVE_AUTHENTICATED')

    def test_metric_delta_early_stop_returns_actual_n(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 's1.py').write_text('x=1\n')
            (root / 'metric.json').write_text(json.dumps(self.metric_delta_fixture()))
            spec = mission()
            spec['steps'][1].update(kind='metric_delta', path='metric.json', minimum_new_covered=12)
            result = m.execute(spec, root, HEAD, HEAD)
            self.assertEqual(result['status'], 'BLOCKED_MAJOR')
            self.assertEqual(result['actual_n'], 13)
            self.assertFalse(result['native_evidence_verified'])
            self.assertEqual(result['attempted'], 2)

    def test_main_untrusted_checkout_precheck_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec_path, out = root / 'plan.json', root / 'receipt.json'
            spec_path.write_text(json.dumps(mission()))
            with mock.patch.object(m.subprocess, 'check_output', side_effect=lambda command, **kw: ('' if 'status' in command else 'b' * 40 + '\n')):
                with self.assertRaises(SystemExit) as result:
                    m.main(['--spec', str(spec_path), '--repo-root', str(root),
                            '--expected-head', HEAD, '--out', str(out)])
            self.assertEqual(result.exception.code, 2)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
