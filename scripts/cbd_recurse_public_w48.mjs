/** W48: strict, read-only public projection for CODEX/Mycelium consumption.
 *  No web calls, worker dispatch, native attestation or merge-authority grant.
 */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

function canonical(obj) {
  if (Array.isArray(obj)) return `[${obj.map(canonical).join(',')}]`;
  if (obj && typeof obj === 'object') {
    return `{${Object.keys(obj).sort().map(k =>
      `${JSON.stringify(k)}:${canonical(obj[k])}`).join(',')}}`;
  }
  return JSON.stringify(obj);
}

function ownKeys(obj, keys) {
  assert.ok(obj && typeof obj === 'object' && !Array.isArray(obj));
  assert.deepEqual(Object.keys(obj).sort(), [...keys].sort());
}

const SHA = /^[a-f0-9]{40}$/;
const HASH = /^[a-f0-9]{64}$/;
const ID = /^[A-Za-z0-9._:-]{1,90}$/;

export function validateProjection(report) {
  ownKeys(report, [
    'schema', 'control', 'dmaic', 'segments', 'graph',
    'matched_coverage_candidates', 'tasks', 'authority', 'receipt_sha256',
  ]);
  assert.equal(report.schema, 'cbd.recurse.structural.v1');
  assert.match(report.receipt_sha256, HASH);
  const { receipt_sha256: digest, ...content } = report;
  const actual = createHash('sha256').update(canonical(content)).digest('hex');
  assert.equal(actual, digest, 'producer structural receipt was modified');
  assert.match(report.control.head_sha, SHA);
  assert.ok(['READ_ONLY_EXPORT', 'SYNTHETIC'].includes(report.control.origin));
  assert.equal(report.authority, 'READ_ONLY_LOCAL_STRUCTURAL_PROJECTION');
  assert.equal(report.dmaic.CONTROL.admission, 'HOLD');
  assert.equal(report.dmaic.CONTROL.accepted_root_open, null);
  assert.equal(report.dmaic.CONTROL.accepted_root_closed, null);
  assert.equal(report.dmaic.CONTROL.authenticated_crew_launch, null);
  assert.equal(report.dmaic.CONTROL.accepted_main_coverage_delta, null);
  assert.equal(report.dmaic.CONTROL.execution_performed, false);
  assert.equal(report.dmaic.IMPROVE.execution_performed, false);
  assert.ok(Array.isArray(report.segments));
  const vis = report.graph.visibility;
  assert.equal(vis.penetration_is_native_acceptance, false);
  assert.ok(Number.isSafeInteger(vis.expected_segment_count));
  assert.ok(Number.isSafeInteger(vis.observed_segment_count));
  assert.ok(vis.expected_segment_count >= vis.observed_segment_count);
  for (const group of report.segments) {
    assert.match(group.segment, ID);
    for (const branch of group.git_branches) assert.match(branch, ID);
  }
  for (const flows of [vis.segment_flows, vis.branch_flows]) {
    for (const row of flows) {
      assert.ok(Number.isSafeInteger(row.edges) && row.edges > 0);
      assert.ok(row.upstream.length && row.downstream.length);
    }
  }
  assert.ok(Array.isArray(report.graph.observations));
  assert.ok(Array.isArray(report.matched_coverage_candidates));
  for (const node of report.graph.observations) {
    assert.match(node.source_sha, SHA);
    assert.match(node.id, ID);
    assert.match(node.segment, ID);
    assert.match(node.branch, ID);
    assert.equal(node.reach_is_causal_proof, false);
    assert.ok(Number.isSafeInteger(node.reachable_nodes));
    assert.ok(node.reachable_nodes >= 0);
  }
  for (const match of report.matched_coverage_candidates) {
    assert.equal(match.acceptance, 'CANDIDATE_LOCAL_VALIDATION_ONLY');
    for (const kind of ['statements', 'branches']) {
      const m = match.measures[kind];
      for (const key of ['before', 'after', 'eligible', 'delta']) {
        assert.ok(Number.isSafeInteger(m[key]));
      }
      assert.equal(m.after - m.before, m.delta);
      assert.ok(m.before >= 0 && m.after >= 0);
      assert.ok(m.before <= m.eligible && m.after <= m.eligible);
    }
  }
  return report;
}

export function project(report) {
  validateProjection(report);
  return {
    schema: 'cbd.recurse.public.v1',
    source_repo: report.control.repository,
    source_sha: report.control.head_sha,
    input_origin: report.control.origin,
    source_receipt_sha256: report.receipt_sha256,
    segments: report.segments.map(s => ({
      segment: s.segment,
      observed_nodes: s.observed_nodes,
      git_branches: s.git_branches,
      native_job_receipts_present: s.native_job_receipts_present,
      terminal_success_observations: s.terminal_success_observations,
      terminal_failure_observations: s.terminal_failure_observations,
    })),
    flow_matrix: report.graph.visibility,
    structural_reach: report.graph.observations.map(n => ({
      id: n.id, segment: n.segment, branch: n.branch,
      source_sha: n.source_sha, direct_outdegree: n.direct_outdegree,
      reachable_nodes: n.reachable_nodes,
      reached_segments: n.reached_segments,
      reached_branches: n.reached_branches,
      reach_is_causal_proof: false,
    })),
    coverage_candidates: report.matched_coverage_candidates.map(m => ({
      before: m.before, after: m.after, scope: m.scope,
      measures: m.measures, acceptance: 'CANDIDATE_LOCAL_VALIDATION_ONLY',
    })),
    local_candidate_task_ids: report.dmaic.IMPROVE.candidates,
    candidate_first_red_fingerprints:
      report.dmaic.ANALYZE.candidate_first_red_fingerprints,
    canonical_root_open: null,
    canonical_root_closed: null,
    authenticated_crew_launch: null,
    matched_global_coverage_credit: null,
    governed_merge_admission: 'HOLD',
    rendered_data_authority: 'READ_ONLY_LOCAL_STRUCTURAL_PROJECTION',
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [input, output] = process.argv.slice(2);
  assert.ok(input && output, 'Usage: node cbd_recurse_public_w48.mjs INPUT OUTPUT');
  const payload = JSON.parse(fs.readFileSync(input, 'utf8'));
  const result = project(payload);
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, `${JSON.stringify(result, null, 2)}\n`, { flag: 'wx' });
  console.log('CBD W48 CODEX public projection PASS; read-only; admission HOLD');
}
