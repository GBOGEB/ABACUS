import copy
import unittest

from acceptance import core


def fixture():
    sh = 'a' * 40
    ab = 'GBOGEB/ABACUS'
    ctx = {repo: {'repo': repo, 'ref': 'main', 'head_sha': x * 40, 'base_sha': x * 40,
                  'policy_sha': 'f' * 40, 'epoch': 1}
           for repo, x in [(ab, 'a'), ('GBOGEB/CODEX', 'b'),
                           ('GBOGEB/cryoplant-project', 'c')]}
    contract = {'schema': core.SCHEMA, 'obligations': [
        {'id': 'ACC-001', 'repo': ab, 'title': 'Evidence capture',
         'kind': 'provenance', 'scope': 'head', 'depends_on': []},
        {'id': 'ACC-002', 'repo': ab, 'title': 'Test receipts',
         'kind': 'test', 'scope': 'head', 'depends_on': ['ACC-001']},
        {'id': 'ACX-001', 'repo': 'GBOGEB/CODEX', 'title': 'Reviewer',
         'kind': 'review', 'scope': 'main', 'depends_on': ['ACC-002']},
        {'id': 'ACQ-001', 'repo': 'GBOGEB/cryoplant-project', 'title': 'Engineering',
         'kind': 'engineering', 'scope': 'main', 'depends_on': ['ACX-001']},
        {'id': 'ACC-000', 'repo': ab, 'title': 'Frozen 253 run baseline',
         'kind': 'telemetry', 'scope': 'historical', 'depends_on': [],
         'frozen_source_sha': 'd' * 40},
    ]}
    def event(id='OBS-001', code='ACC-001', repo=ab, head=None, epoch=1,
              pulse=0, seq=0, verdict='PASS'):
        subject = copy.deepcopy(ctx[repo]); subject['head_sha'] = head or subject['head_sha']
        subject['epoch'] = epoch
        return {'schema': core.EVENT_SCHEMA, 'id': id, 'obligation_id': code,
                'subject': subject, 'verdict': verdict, 'pulse': pulse,
                'sequence': seq, 'authority_transfer': False,
                'security_waiver': False,
                'evidence': {'url': 'https://github.com/' + repo + '/actions/runs/39021567900',
                             'artifact_sha256': '1' * 64, 'classification': 'native_api'}}
    return contract, ctx, event


class AcceptanceContractTests(unittest.TestCase):
    def test_empty_has_no_fabricated_accepted(self):
        contract, ctx, _ = fixture()
        r = core.project(contract, ctx, [])
        self.assertEqual(5, r['metrics']['evidence_missing'])
        self.assertEqual(0, r['metrics']['admitted'])
        self.assertIsNone(r['metrics']['accepted_causal_roots_closed'])
        self.assertEqual('HOLD', r['admission'])

    def test_positive_observed_never_promotes_review(self):
        contract, ctx, event = fixture()
        r = core.project(contract, ctx, [event()])
        self.assertEqual(1, r['metrics']['evidence_observed'])
        self.assertTrue(next(x for x in r['obligations'] if x['id'] == 'ACC-001')['evidence_checked'])
        self.assertEqual(0, r['metrics']['admitted'])
        self.assertTrue(all(not x['admission_checked'] for x in r['obligations']))

    def test_dependencies_block_unproven_pass(self):
        contract, ctx, event = fixture()
        r = core.project(contract, ctx, [event(code='ACC-002')])
        t = next(x for x in r['obligations'] if x['id'] == 'ACC-002')
        self.assertEqual('BLOCKED_DEPENDENCY', t['evidence_state'])

    def test_repeated_event_is_alias_not_progress(self):
        contract, ctx, event = fixture()
        r = core.project(contract, ctx, [event(), event()])
        self.assertEqual(1, r['metrics']['distinct_observations'])
        self.assertEqual(1, r['metrics']['duplicate_aliases'])

    def test_conflicting_duplicate_event_id_rejected(self):
        contract, ctx, event = fixture()
        with self.assertRaisesRegex(ValueError, 'conflicting'):
            core.project(contract, ctx, [event(), event(verdict='FAIL')])

    def test_latest_fail_reverses_old_pass(self):
        contract, ctx, event = fixture()
        r = core.project(contract, ctx, [event(), event(id='OBS-002', pulse=2, verdict='FAIL')])
        self.assertEqual(0, r['metrics']['evidence_observed'])
        self.assertEqual(1, r['metrics']['evidence_blocked'])

    def test_head_epoch_a_b_a_must_not_reuse_proof(self):
        contract, ctx, event = fixture()
        old = event(epoch=1)
        ctx['GBOGEB/ABACUS']['epoch'] = 3
        r = core.project(contract, ctx, [old])
        self.assertEqual(1, r['metrics']['evidence_stale'])
        self.assertEqual(0, r['metrics']['evidence_observed'])

    def test_source_policy_sha_change_invalidates(self):
        contract, ctx, event = fixture()
        old = event()
        ctx['GBOGEB/ABACUS']['policy_sha'] = 'e' * 40
        self.assertEqual(1, core.project(contract, ctx, [old])['metrics']['evidence_stale'])

    def test_historical_source_does_not_inherit_current_head(self):
        contract, ctx, event = fixture()
        old = event(id='OBS-099', code='ACC-000', head='d' * 40)
        r = core.project(contract, ctx, [old])
        self.assertEqual(1, r['metrics']['evidence_observed'])

    def test_reject_forged_waiver_and_merge_flags(self):
        contract, ctx, event = fixture()
        for key in ('merge_authorized', 'reviewer_approved', 'accepted_root_closed'):
            bad = event(); bad[key] = True
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'forbidden'):
                core.project(contract, ctx, [bad])
        bad = event(); bad['security_waiver'] = True
        with self.assertRaisesRegex(ValueError, 'authority'):
            core.project(contract, ctx, [bad])

    def test_cross_repo_forgery_rejected(self):
        contract, ctx, event = fixture()
        bad = event(); bad['subject']['repo'] = 'GBOGEB/CODEX'
        with self.assertRaisesRegex(ValueError, 'cross-repo'):
            core.project(contract, ctx, [bad])

    def test_url_must_be_correct_repo(self):
        contract, ctx, event = fixture()
        bad = event(); bad['evidence']['url'] = 'https://attacker.com/GBOGEB/ABACUS/run'
        with self.assertRaisesRegex(ValueError, 'URL'):
            core.project(contract, ctx, [bad])

    def test_missing_denominator_invalid_not_zero(self):
        contract, ctx, event = fixture()
        bad = event(); bad['measurement'] = {'scope': 'module', 'numerator': 0, 'denominator': 0}
        with self.assertRaisesRegex(ValueError, 'denominator'):
            core.project(contract, ctx, [bad])

    def test_positive_module_measurement_keeps_scope(self):
        contract, ctx, event = fixture()
        good = event(); good['measurement'] = {'scope': 'module', 'numerator': 168, 'denominator': 168}
        r = core.project(contract, ctx, [good])
        self.assertIsNone(r['metrics']['current_main_coverage'])
        self.assertEqual(1, r['metrics']['evidence_observed'])

    def test_cyclic_dep_rejected(self):
        contract, ctx, _ = fixture()
        contract['obligations'][0]['depends_on'] = ['ACC-002']
        with self.assertRaisesRegex(ValueError, 'cycle'):
            core.project(contract, ctx, [])

    def test_withheld_does_not_count_as_observed(self):
        contract, ctx, event = fixture()
        r = core.project(contract, ctx, [event(verdict='WITHHELD')])
        self.assertEqual(1, r['metrics']['evidence_withheld'])
        self.assertEqual(0, r['metrics']['evidence_observed'])
        self.assertFalse(next(x for x in r['obligations'] if x['id'] == 'ACC-001')['evidence_checked'])

    def test_path_owner_lease_traversal_overlap(self):
        a = {'repo': 'GBOGEB/ABACUS', 'path': 'tools/a', 'owner': 'test'}
        b = {'repo': 'GBOGEB/CODEX', 'path': 'tools/a', 'owner': 'other'}
        self.assertEqual(2, core.disjoint_leases([a, b]))
        with self.assertRaisesRegex(ValueError, 'overlapping'):
            core.disjoint_leases([a, {**a, 'path': 'tools/a/payload'}])
        with self.assertRaisesRegex(ValueError, 'traversal'):
            core.disjoint_leases([{**a, 'path': 'tools/../README.md'}])


if __name__ == '__main__':
    unittest.main()
