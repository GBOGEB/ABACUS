import assert from 'node:assert/strict';
import {test} from 'node:test';
import {projectReceipt, validateReceipt, compareReceipts} from './federation_receipt_policy.mjs';
import {SOURCE_SHA, INPUT_DIGEST, CONTRACT_DIGEST} from './consume_federation_delivery.mjs';

// Synthetic fixtures exercise the disclosure boundary; never runtime evidence.
function raw(repeat = '1') {
  return {
    schema_version: '1.0.0', producer_repo: 'GBOGEB/CODEX', producer_sha: SOURCE_SHA,
    ssot_sha256: INPUT_DIGEST, contract_sha256: CONTRACT_DIGEST,
    consumer_repo: 'GBOGEB/ABACUS', consumer_carrier_sha: 'a'.repeat(40),
    run_id: '123', run_attempt: '1', repeat_id: repeat,
    consumed_action_ids: Array.from({length: 10}, (_, i) => `A${String(i + 1).padStart(2, '0')}`),
    result: 'STRUCTURE_VALIDATED', global_dov: 'WITHHELD', child_disposition: 'NOT_REQUESTED',
    execution_context: 'GITHUB_ACTIONS', stdout: 'DO_NOT_UPLOAD', source_payload: 'DO_NOT_UPLOAD',
    runner_name: 'DO_NOT_UPLOAD', scope: 'DO_NOT_UPLOAD', observed_at: 'DO_NOT_UPLOAD',
  };
}
test('projection removes raw logs, source payloads and free text', () => {
  const r = projectReceipt(raw());
  assert.ok(!JSON.stringify(r).includes('DO_NOT_UPLOAD'));
  assert.equal(r.action_count, 10);
  assert.equal(Object.keys(r).length, 15);
});
test('serialized receipt rejects extra fields', () => {
  assert.throws(() => validateReceipt({...projectReceipt(raw()), stderr: 'unapproved'}));
});
test('local validation cannot be projected as hosted proof', () => {
  assert.throws(() => projectReceipt({...raw(), execution_context: 'LOCAL_VALIDATION'}));
});
test('invalid IDs and source bindings fail closed', () => {
  for (const mutation of [{run_id: 'secret'}, {ssot_sha256: 'b'.repeat(64)},
    {consumed_action_ids: ['secret']}, {child_disposition: 'ACCEPT'}, {global_dov: 'PASS'}]) {
    assert.throws(() => projectReceipt({...raw(), ...mutation}));
  }
});
test('two distinct repeat IDs with identical bindings match', () => {
  const result = compareReceipts([projectReceipt(raw('1')), projectReceipt(raw('2'))]);
  assert.equal(result.result, 'REPEAT_MATCH');
  assert.equal(result.global_dov, 'WITHHELD');
});
test('missing, duplicate and differently bound repeats fail', () => {
  const first = projectReceipt(raw('1'));
  assert.throws(() => compareReceipts([first]));
  assert.throws(() => compareReceipts([first, first]));
  for (const mutation of [{run_id: '456'}, {consumer_carrier_sha: 'b'.repeat(40)}, {run_attempt: '2'}]) {
    assert.throws(() => compareReceipts([first, {...projectReceipt(raw('2')), ...mutation}]));
  }
});
