import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { test } from 'node:test';
import { project, validateProjection } from './cbd_recurse_public_w48.mjs';

function canonical(obj) {
  if (Array.isArray(obj)) return `[${obj.map(canonical).join(',')}]`;
  if (obj && typeof obj === 'object') {
    return `{${Object.keys(obj).sort().map(k =>
      `${JSON.stringify(k)}:${canonical(obj[k])}`).join(',')}}`;
  }
  return JSON.stringify(obj);
}

function sign(data) {
  const copy = structuredClone(data);
  delete copy.receipt_sha256;
  copy.receipt_sha256 = createHash('sha256').update(canonical(copy)).digest('hex');
  return copy;
}

function sample() {
  return sign({
    schema: 'cbd.recurse.structural.v1',
    authority: 'READ_ONLY_LOCAL_STRUCTURAL_PROJECTION',
    control: {repository: 'GBOGEB/ABACUS', head_sha: 'a'.repeat(40), origin: 'SYNTHETIC'},
    dmaic: {
      DEFINE: 'typed local scope',
      MEASURE: {observations: 2, typed_edges: 1},
      ANALYZE: {candidate_first_red_fingerprints: ['A10_GUARD'], deduplicated_engineering_root_count: null},
      IMPROVE: {candidates: ['task_read_only'], execution_performed: false},
      CONTROL: {
        admission: 'HOLD', accepted_root_open: null, accepted_root_closed: null,
        authenticated_crew_launch: null, accepted_main_coverage_delta: null,
        independent_approval: null, execution_performed: false,
      },
    },
    segments: [{
      segment: 'python', observed_nodes: 2, git_branches: ['main', 'feature_w48'],
      native_job_receipts_present: 2, terminal_success_observations: 2,
      terminal_failure_observations: 0, distinct_run_attempts: 2,
    }],
    graph: {
      visibility: {
        segment_flows: [{upstream: 'python', downstream: 'python', edges: 1}],
        branch_flows: [{upstream: 'GBOGEB/ABACUS:main', downstream: 'GBOGEB/ABACUS:feature_w48', edges: 1}],
        cross_segment_edges: 0, cross_branch_edges: 1,
        observed_segment_count: 1, expected_segment_count: 2,
        penetration_is_native_acceptance: false,
      },
      topological_order: ['before', 'after'], edges: [{from: 'before', to: 'after', kind: 'lineage'}],
      observations: [
        {
          id: 'before', segment: 'python', branch: 'main', source_sha: 'a'.repeat(40),
          kind: 'native', status: 'completed', conclusion: 'success', first_red_fingerprint: null,
          native_job_identity_present: true, direct_outdegree: 1, reachable_nodes: 1,
          reached_segments: ['python'], reached_branches: ['feature_w48'],
          reach_is_causal_proof: false,
        },
        {
          id: 'after', segment: 'python', branch: 'feature_w48', source_sha: 'b'.repeat(40),
          kind: 'native', status: 'completed', conclusion: 'success', first_red_fingerprint: null,
          native_job_identity_present: true, direct_outdegree: 0, reachable_nodes: 0,
          reached_segments: [], reached_branches: [],
          reach_is_causal_proof: false,
        },
      ],
    },
    matched_coverage_candidates: [{
      before: 'before', after: 'after', scope: 'synthetic_module', source_blob_sha: 'c'.repeat(40),
      acceptance: 'CANDIDATE_LOCAL_VALIDATION_ONLY', measures: {
        statements: {before: 20, after: 30, eligible: 40, delta: 10},
        branches: {before: 4, after: 6, eligible: 8, delta: 2},
      },
    }],
    tasks: [{id: 'task_read_only', segment: 'python', state: 'pending', kind: 'read_only', approval_required: false}],
  });
}

test('safe source-bound projection strips hidden logs and arbitrary payloads', () => {
  const x = sample();
  x.graph.observations[0].secret_raw_log = 'DO_NOT_PUBLISH';
  x.graph.observations[0].private_source = 'DO_NOT_PUBLISH';
  const p = project(sign(x));
  assert.equal(p.governed_merge_admission, 'HOLD');
  assert.equal(p.canonical_root_open, null);
  assert.equal(p.authenticated_crew_launch, null);
  assert.equal(p.structural_reach[0].reachable_nodes, 1);
  assert.ok(!JSON.stringify(p).includes('DO_NOT_PUBLISH'));
});

test('sample genuinely binds same-source statement and branch candidate', () => {
  const p = project(sample());
  assert.deepEqual(p.coverage_candidates[0].measures.statements, {
    before: 20, after: 30, eligible: 40, delta: 10,
  });
  assert.equal(p.matched_global_coverage_credit, null);
});

test('mutated producer receipt digest fails closed', () => {
  const x = sample();
  x.segments[0].observed_nodes = 999;
  assert.throws(() => validateProjection(x), /modified/);
});

test('top-level unapproved field fails closed even if rehashed', () => {
  const x = sample();
  x.authority_transfer = true;
  assert.throws(() => validateProjection(sign(x)));
});

test('future or incorrect schema fails closed', () => {
  const x = sample(); x.schema = 'cbd.recurse.future';
  assert.throws(() => validateProjection(sign(x)));
});

test('forged new HEAD representation fails closed', () => {
  const x = sample(); x.control.head_sha = 'latest';
  assert.throws(() => validateProjection(sign(x)));
});

test('forged authenticated execution origin fails closed', () => {
  const x = sample(); x.control.origin = 'MUTATION_APPROVED';
  assert.throws(() => validateProjection(sign(x)));
});

test('forged effective merge admission fails closed', () => {
  const x = sample(); x.dmaic.CONTROL.admission = 'PASS';
  assert.throws(() => validateProjection(sign(x)));
});

test('forged root closure or Crew launch fails closed', () => {
  for (const key of ['accepted_root_open', 'accepted_root_closed', 'authenticated_crew_launch']) {
    const x = sample(); x.dmaic.CONTROL[key] = 0;
    assert.throws(() => validateProjection(sign(x)));
  }
});

test('false causal reach and negative reach fail closed', () => {
  for (const patch of [{reach_is_causal_proof: true}, {reachable_nodes: -1}]) {
    const x = sample(); Object.assign(x.graph.observations[0], patch);
    assert.throws(() => validateProjection(sign(x)));
  }
});

test('coverage error/negative/test-culling promotion rejected', () => {
  for (const patch of [
    {acceptance: 'ACCEPTED_GLOBAL'},
    {measures: {statements: {before: 20, after: 30, eligible: 40, delta: 0},
      branches: {before: 4, after: 6, eligible: 8, delta: 2}}},
    {measures: {statements: {before: 20, after: 41, eligible: 40, delta: 21},
      branches: {before: 4, after: 6, eligible: 8, delta: 2}}},
  ]) {
    const x = sample(); Object.assign(x.matched_coverage_candidates[0], patch);
    assert.throws(() => validateProjection(sign(x)));
  }
});

test('local planner is never presented as executed dispatch', () => {
  const x = sample(); x.dmaic.IMPROVE.execution_performed = true;
  assert.throws(() => validateProjection(sign(x)));
});

test('public projection exposes four family-friendly browse dimensions', () => {
  const p = project(sample());
  for (const key of ['segments', 'structural_reach', 'coverage_candidates', 'local_candidate_task_ids']) {
    assert.ok(Array.isArray(p[key]));
  }
  assert.equal(p.segments[0].segment, 'python');
  assert.deepEqual(p.segments[0].git_branches, ['main', 'feature_w48']);
  assert.equal(p.rendered_data_authority, 'READ_ONLY_LOCAL_STRUCTURAL_PROJECTION');
});

test('malicious segment and branch HTML fails closed', () => {
  for (const mutation of [
    x => { x.segments[0].segment = '<script>'; },
    x => { x.graph.observations[0].branch = '<img>'; },
  ]) {
    const x = sample(); mutation(x);
    assert.throws(() => validateProjection(sign(x)));
  }
});

test('flow visibility cannot imply native admission', () => {
  const x = sample(); x.graph.visibility.penetration_is_native_acceptance = true;
  assert.throws(() => validateProjection(sign(x)));
});
