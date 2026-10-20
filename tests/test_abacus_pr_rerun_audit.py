"""Offline positive/negative controls for the PowerShell-backed ABACUS command."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'scripts' / 'abacus_pr_rerun_audit.py'
SPEC = importlib.util.spec_from_file_location('abacus_pr_rerun_audit', SOURCE)
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)

A, B, C = 'a' * 40, 'b' * 40, 'c' * 40
NOW = core.parse_time('2026-10-17T18:10:00Z')
REPO = 'GBOGEB/ABACUS'


def pr(number=1980, sha=A, branch='feature/mcl', draft=False):
    return {'number': number, 'state': 'open', 'title': 'MCL proof', 'draft': draft,
            'created_at': '2026-10-17T10:00:00Z',
            'updated_at': '2026-10-17T17:00:00Z',
            'head': {'sha': sha, 'ref': branch}, 'base': {'sha': 'd' * 40},
            'requested_reviewers': [{'login': 'reviewer'}] if number == 1980 else [],
            'html_url': f'https://github.com/{REPO}/pull/{number}'}


def run(rid, sha=A, workflow='a10-guard', workflow_id=1, status='completed',
        conclusion='failure', number=1980, branch='feature/mcl', attempt=1, created=None):
    return {'id': rid, 'head_sha': sha, 'head_branch': branch,
            'pull_requests': [{'number': number}], 'name': workflow,
            'workflow_id': workflow_id, 'event': 'pull_request',
            'run_attempt': attempt, 'status': status, 'conclusion': conclusion,
            'created_at': created or '2026-10-17T15:00:00Z',
            'updated_at': '2026-10-17T16:00:00Z',
            'html_url': f'https://github.com/{REPO}/actions/runs/{rid}'}


def job(name='a10-guard', step='Tender guard', conclusion='failure'):
    return {'id': 1001, 'name': name, 'status': 'completed', 'conclusion': conclusion,
            'created_at': '2026-10-17T15:00:00Z',
            'started_at': '2026-10-17T15:02:00Z',
            'completed_at': '2026-10-17T15:04:00Z',
            'steps': [{'number': 1, 'name': step, 'conclusion': conclusion,
                       'started_at': '2026-10-17T15:03:00Z',
                       'completed_at': '2026-10-17T15:04:00Z'}]}


class FakeGh:
    def __init__(self):
        self.prs = [pr(), pr(2109, C, 'evidence/p2109')]
        self.runs = [
            run(11),
            run(10, conclusion='success', created='2026-10-17T13:00:00Z'),
            run(12, workflow='MCL tests', workflow_id=2,
                conclusion='success', created='2026-10-17T16:00:00Z'),
            run(13, workflow='queued scan', workflow_id=3,
                status='queued', conclusion=None, created='2026-10-17T17:00:00Z'),
            run(7, sha=B, branch='feature/mcl',
                created='2026-10-16T12:00:00Z'),
            run(21, sha=C, workflow='MCL tests', workflow_id=4,
                number=2109, branch='evidence/p2109'),
        ]
        self.jobs = {11: [job()], 21: [job('unit tests', 'pytest')]}
        self.dispatched = []
        self.calls = []
        self.fail_dispatch = False

    def json(self, path):
        self.calls.append(path)
        q = urlsplit('https://gh.local/' + path)
        params = parse_qs(q.query)
        page = int(params.get('page', ['1'])[0])
        if q.path.endswith('/pulls'):
            return copy.deepcopy(self.prs) if page == 1 else []
        if '/pulls/' in q.path:
            number = int(q.path.split('/')[-1])
            return copy.deepcopy(next(x for x in self.prs if x['number'] == number))
        if q.path.endswith('/actions/runs'):
            if 'head_sha' in params:
                matches = [r for r in self.runs if r['head_sha'] == params['head_sha'][0]]
            elif 'branch' in params:
                matches = [r for r in self.runs if r['head_branch'] == params['branch'][0]]
            else:
                raise ValueError(path)
            return {'workflow_runs': copy.deepcopy(matches if page == 1 else [])}
        if q.path.endswith('/jobs'):
            rid = int(q.path.split('/')[-2])
            return {'jobs': copy.deepcopy(self.jobs.get(rid, []))}
        if '/actions/runs/' in q.path:
            rid = int(q.path.split('/')[-1])
            return copy.deepcopy(next(r for r in self.runs if r['id'] == rid))
        raise ValueError('unmapped ' + path)

    def rerun_failed(self, repo, run_id, debug):
        if self.fail_dispatch:
            raise RuntimeError('simulated GitHub failure')
        self.dispatched.append((repo, run_id, debug))
        for r in self.runs:
            if r['id'] == run_id:
                r.update(run_attempt=r['run_attempt'] + 1,
                         status='queued', conclusion=None,
                         updated_at='2026-10-17T18:10:01Z')


def scan(gh, policy='retryable', agent=None, dashboard=None, journal=None):
    return core.scan(gh, REPO, 3, 0, False, agent, dashboard, policy, 45,
                     journal or {}, 30, NOW)


class AuditTests(unittest.TestCase):
    def test_source_sha_and_pr_linkage_required(self):
        x = pr()
        self.assertTrue(core.linked_to_pr(run(11), x))
        self.assertFalse(core.linked_to_pr(run(11, sha=B), x))
        self.assertFalse(core.linked_to_pr(run(11, number=2109), x))
        no_pr = run(11)
        no_pr['pull_requests'] = []
        self.assertTrue(core.linked_to_pr(no_pr, x))
        no_pr['head_branch'] = 'other'
        self.assertFalse(core.linked_to_pr(no_pr, x))

    def test_latest_run_per_workflow_not_old_pass(self):
        latest, redundant = core.deduplicate_latest([
            run(10, created='2026-10-17T13:00:00Z', conclusion='failure'),
            run(11, created='2026-10-17T16:00:00Z', conclusion='success'),
        ])
        self.assertEqual(redundant, 1)
        self.assertEqual(latest[0]['id'], 11)
        self.assertEqual(latest[0]['conclusion'], 'success')

    def test_census_exact_head_and_stale_historical(self):
        x = scan(FakeGh(), 'all-failed')
        self.assertEqual(x['all_open_pr_count'], 2)
        self.assertEqual(x['prs']['1980']['current_runs'], 4)
        self.assertEqual(x['prs']['1980']['stale_branch_runs'], 1)
        self.assertEqual(x['prs']['1980']['superseded_same_head_runs'], 1)
        self.assertEqual(x['prs']['1980']['failed_runs'], 1)
        self.assertEqual(x['prs']['1980']['pending_runs'], 1)
        self.assertIn('HISTORICAL_STALE_RUNS_PRESENT', x['prs']['1980']['lag_flags'])
        self.assertEqual(len(x['rerun_candidates']), 2)
        self.assertTrue(all(v['head_sha'] != B for v in x['rerun_candidates']))
        self.assertEqual(x['merge_admission'], 'HOLD')

    def test_retryable_policy_keeps_a10_owner_blocked(self):
        x = scan(FakeGh())
        self.assertEqual(x['prs']['1980']['failed_runs'], 1)
        self.assertEqual(x['summary']['eligible_rerun_runs'], 1)
        self.assertEqual(x['rerun_candidates'][0]['pr'], 2109)
        first = next(w for w in x['prs']['1980']['workflows'] if w['id'] == 11)
        self.assertEqual(first['rerun_disposition'], 'SOURCE_OWNER_OR_ADMIN_ROOT')

    def test_root_fingerprint_has_no_unproven_quota(self):
        self.assertEqual(core.classify_root('CodeQL', 'Analyze', 'Analyze'), 'UNCLASSIFIED')
        self.assertEqual(core.classify_root('CodeQL', 'Analyze', 'Analyze',
                         'API rate limit exceeded for installation'), 'API_QUOTA')
        self.assertEqual(core.classify_root('a10-guard', 'guard', 'Tender guard'), 'A10_REVIEW')
        self.assertEqual(core.classify_root('CI', 'Security Scanning', 'Safety check'), 'SAFETY')
        self.assertEqual(core.classify_root('CI', 'Quality Checks', 'new debt'), 'FORMAT')

    def test_native_first_red_and_timing_join(self):
        red = core.first_failure(job())
        self.assertEqual(red['step'], 'Tender guard')
        j = core.job_telemetry(job(), NOW)
        self.assertEqual(j['runner_wait_seconds'], 120)
        self.assertEqual(j['execution_seconds'], 120)
        queued = job()
        queued.update(status='queued', started_at=None, completed_at=None)
        q = core.job_telemetry(queued, NOW)
        self.assertIsNone(q['runner_wait_seconds'])
        self.assertEqual(q['runner_wait_right_censored_min_seconds'], 11400)

    def test_no_runner_created_timestamp_does_not_become_zero(self):
        j = job()
        j['created_at'] = None
        self.assertIsNone(core.job_telemetry(j, NOW)['runner_wait_seconds'])
        self.assertIsNone(core.seconds_between('bad-date', core.iso(NOW)))

    def test_reviewer_pending_not_human_blame(self):
        x = scan(FakeGh())
        self.assertIn('REVIEW_OBLIGATION_PENDING', x['prs']['1980']['lag_flags'])
        self.assertNotIn('HUMAN_CAUSED_DELAY', x['prs']['1980']['lag_flags'])
        self.assertEqual(x['prs']['1980']['dashboard_receipt']['state'], 'NO_RECEIPT')

    def test_dashboard_stale_sha_vs_publication_lag(self):
        dashboard = {'prs': {'1980': {'head_sha': B, 'observed_at': '2026-10-17T17:59:00Z'}}}
        x = scan(FakeGh(), dashboard=dashboard)
        self.assertEqual(x['prs']['1980']['dashboard_receipt']['state'], 'STALE_SOURCE_SHA')
        self.assertIn('DASHBOARD_SNAPSHOT_STALE', x['prs']['1980']['lag_flags'])
        lag = core.receipt_status({'head_sha': A, 'observed_at': '2026-10-17T12:00:00Z'},
                                  A, '2026-10-17T16:00:00Z', channel='dashboard')
        self.assertEqual(lag['state'], 'BEHIND_NATIVE')
        self.assertEqual(lag['lag_seconds'], 14400)

    def test_agent_stale_and_no_telemetry_not_zero(self):
        agent = {'prs': {'1980': {'head_sha': B, 'observed_at': '2026-10-17T15:00:00Z'}}}
        x = scan(FakeGh(), agent=agent)
        self.assertIn('AGENT_SNAPSHOT_STALE', x['prs']['1980']['lag_flags'])
        self.assertEqual(x['prs']['1980']['dashboard_receipt']['state'], 'NO_RECEIPT')

    def test_diff_head_change_missing_context_and_new_attempt(self):
        before = scan(FakeGh(), 'all-failed')
        gh = FakeGh()
        gh.prs[0]['head']['sha'] = B
        gh.runs = [r for r in gh.runs if r['id'] not in (11, 10, 12, 13)]
        after = scan(gh, 'all-failed')
        diff = core.diff_snapshots(before, after)
        kinds = [x['kind'] for x in diff['changes']]
        self.assertIn('SOURCE_HEAD_ADVANCED', kinds)
        self.assertIn('WORKFLOW_MISSING_FROM_HEAD', kinds)
        self.assertEqual(diff['merge_admission'], 'HOLD')

    def test_diff_catches_attempt_status_transition(self):
        gh = FakeGh()
        before = scan(gh, 'all-failed')
        gh.runs[0]['run_attempt'] = 2
        gh.runs[0]['conclusion'] = 'success'
        after = scan(gh, 'all-failed')
        d = core.diff_snapshots(before, after)
        self.assertIn('WORKFLOW_ATTEMPT_OR_STATUS_CHANGED', d['counts'])

    def test_no_baseline_diff_is_not_declared_stable(self):
        x = scan(FakeGh())
        delta = core.diff_snapshots(None, x)
        self.assertEqual(delta['counts']['PR_NEWLY_OBSERVED'], 2)
        self.assertNotIn('STABLE', delta['counts'])

    def test_apply_requires_yes(self):
        with tempfile.TemporaryDirectory() as p:
            with self.assertRaisesRegex(ValueError, 'requires --yes'):
                core.apply_candidates(FakeGh(), REPO, [], 2, 0, False, Path(p), {}, True)

    def test_apply_rechecks_head_then_run(self):
        gh = FakeGh()
        x = scan(gh, 'all-failed')
        item = next(r for r in x['rerun_candidates'] if r['pr'] == 1980)
        gh.prs[0]['head']['sha'] = B
        with tempfile.TemporaryDirectory() as path:
            result = core.apply_candidates(gh, REPO, [item], 1, 0, True,
                                           Path(path), {}, True)
        self.assertEqual(result[0]['result'], 'SKIPPED_HEAD_DRIFT')
        self.assertEqual(gh.dispatched, [])

    def test_apply_rechecks_changed_run_attempt(self):
        gh = FakeGh()
        item = scan(gh, 'all-failed')['rerun_candidates'][0]
        gh.runs[0]['run_attempt'] = 2
        with tempfile.TemporaryDirectory() as path:
            result = core.apply_candidates(gh, REPO, [item], 1, 0, True,
                                           Path(path), {}, True)
        self.assertEqual(result[0]['result'], 'SKIPPED_RUN_ATTEMPT_DRIFT')
        self.assertEqual(gh.dispatched, [])

    def test_apply_records_debug_and_deduplicates_crash(self):
        gh = FakeGh()
        item = next(r for r in scan(gh, 'all-failed')['rerun_candidates'] if r['pr'] == 1980)
        journal = {}
        with tempfile.TemporaryDirectory() as path:
            target = Path(path)
            result = core.apply_candidates(gh, REPO, [item], 1, 0, True, target, journal, True)
            self.assertEqual(result[0]['result'], 'DISPATCH_ACCEPTED_NOT_COMPLETED')
            self.assertEqual(gh.dispatched, [(REPO, 11, True)])
            saved = json.loads((target / 'rerun_journal.json').read_text())
            self.assertEqual(len(saved), 1)
            # stale client still contains the same candidate: journal holds it
            self.assertFalse(core.select_run(run(11), [job()], 'all-failed', 0,
                                                  NOW, saved, 1980)[0])

    def test_apply_uncertain_result_journaled_no_retry_storm(self):
        gh = FakeGh()
        gh.fail_dispatch = True
        item = scan(gh, 'all-failed')['rerun_candidates'][0]
        with tempfile.TemporaryDirectory() as path:
            journal = {}
            result = core.apply_candidates(gh, REPO, [item], 1, 0, True,
                                           Path(path), journal, True)
            self.assertEqual(result[0]['result'], 'DISPATCH_ERROR_REQUIRES_RECONCILIATION')
            self.assertEqual(len(journal), 1)

    def test_apply_budget_caps_all_failed_reruns(self):
        gh = FakeGh()
        candidates = scan(gh, 'all-failed')['rerun_candidates']
        with tempfile.TemporaryDirectory() as path:
            result = core.apply_candidates(gh, REPO, candidates, 1, 0, True,
                                           Path(path), {}, True)
        self.assertEqual(len(gh.dispatched), 1)
        self.assertEqual(result[-1]['result'], 'SKIPPED_BUDGET')

    def test_cooldown_and_journal(self):
        r = run(11)
        valid, why = core.select_run(r, [job()], 'all-failed', 200, NOW, {}, 1980)
        self.assertFalse(valid)
        self.assertEqual(why, 'COOLDOWN')
        identity = f'1980:11:1:{A}'
        valid, why = core.select_run(r, [job()], 'all-failed', 0, NOW,
                                     {identity: {'result': 'REQUESTED'}}, 1980)
        self.assertFalse(valid)
        self.assertIn('JOURNAL', why)

    def test_write_reports_and_hash_manifest(self):
        with tempfile.TemporaryDirectory() as path:
            x = scan(FakeGh())
            where = Path(path)
            core.write_reports(where, None, x, [])
            manifest = json.loads((where / 'manifest.json').read_text())
            for name, descriptor in manifest['files'].items():
                data = (where / name).read_bytes()
                self.assertEqual(descriptor['sha256'], core.hashlib.sha256(data).hexdigest())
                self.assertEqual(descriptor['bytes'], len(data))
            self.assertIn('HOLD', (where / 'diff.md').read_text())

    def test_repository_selector_and_apply_auth_fail_fast(self):
        with self.assertRaisesRegex(ValueError, 'invalid repository'):
            core.main(['--repo', 'other; echo attack'])
        with self.assertRaisesRegex(ValueError, 'requires explicit --yes'):
            core.main(['--mode', 'apply'])

    def test_pagination_cap_fails_closed(self):
        class Full:
            def json(self, path):
                return [{'number': i} for i in range(100)]
        with self.assertRaisesRegex(ValueError, 'pagination cap'):
            core.paged(Full(), 'repos/GBOGEB/ABACUS/pulls?state=open', None, 1)

    def test_selector_can_scan_drafts(self):
        gh = FakeGh()
        gh.prs[1]['draft'] = True
        full = scan(gh)
        self.assertEqual(full['selected_pr_count'], 2)
        less = core.scan(gh, REPO, 2, 0, True, None, None,
                         'all-failed', 0, {}, 30, NOW)
        self.assertEqual(less['selected_pr_count'], 1)
        self.assertFalse(less['selection_complete'])

    def test_cli_end_to_end_plan_is_read_only_and_exports_artifacts(self):
        gh = FakeGh()
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(core, 'Gh', return_value=gh), \
             patch.object(core, 'utcnow', return_value=NOW):
            target = Path(temp) / 'run'
            exit_code = core.main(['--mode', 'plan', '--policy', 'all-failed',
                                   '--audit-dir', str(target)])
            self.assertEqual(exit_code, 0)
            self.assertEqual(gh.dispatched, [])
            latest = json.loads((target / 'latest.json').read_text())
            self.assertEqual(latest['selected_pr_count'], 2)
            self.assertTrue((target / 'bd_queue.csv').exists())
            self.assertTrue((target / 'diff.md').exists())
            self.assertEqual(len(list((target / 'snapshots').glob('*.json'))), 1)

    def test_cli_end_to_end_apply_then_refresh_diff(self):
        gh = FakeGh()
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(core, 'Gh', return_value=gh), \
             patch.object(core, 'utcnow', return_value=NOW):
            target = Path(temp) / 'run'
            rc = core.main(['--mode', 'plan', '--policy', 'all-failed',
                            '--audit-dir', str(target)])
            self.assertEqual(rc, 0)
            rc = core.main(['--mode', 'apply', '--yes', '--policy', 'all-failed',
                            '--max-reruns', '1', '--cooldown-minutes', '0',
                            '--delay-seconds', '0', '--audit-dir', str(target)])
            self.assertEqual(rc, 0)
            self.assertEqual(gh.dispatched, [(REPO, 11, True)])
            result = json.loads((target / 'diff.json').read_text())
            self.assertIn('WORKFLOW_ATTEMPT_OR_STATUS_CHANGED', result['counts'])
            self.assertEqual(len(list((target / 'snapshots').glob('*.json'))), 2)
            journal = json.loads((target / 'rerun_journal.json').read_text())
            self.assertEqual(len(journal), 1)

    def test_first_red_persistence_same_head_repeat_attempt(self):
        gh = FakeGh()
        a = scan(gh, 'all-failed')
        gh.runs[0]['run_attempt'] = 2
        b = scan(gh, 'all-failed')
        delta = core.diff_snapshots(a, b)
        self.assertIn('SAME_HEAD_FIRST_RED_PERSISTED', delta['counts'])

    def test_synthetic_merge_run_never_admitted(self):
        gh = FakeGh()
        gh.runs[0]['head_sha'] = B
        gh.runs[0]['head_branch'] = 'feature/mcl'
        snapshot = scan(gh, 'all-failed')
        self.assertNotIn(11, [r['run_id'] for r in snapshot['rerun_candidates']])


if __name__ == '__main__':
    unittest.main()
