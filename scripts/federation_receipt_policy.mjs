// Approved public artifact boundary: hashes, IDs, counts and dispositions only.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {SOURCE_SHA, INPUT_DIGEST, CONTRACT_DIGEST} from './consume_federation_delivery.mjs';

const actionIds = Array.from({length: 10}, (_, i) => `A${String(i + 1).padStart(2, '0')}`);
const fields = ['schema_version', 'producer_repo', 'producer_sha', 'ssot_sha256',
  'contract_sha256', 'consumer_repo', 'consumer_carrier_sha', 'run_id',
  'run_attempt', 'repeat_id', 'consumed_action_ids', 'action_count', 'result',
  'global_dov', 'child_disposition'];

export function validateReceipt(r) {
  assert.deepEqual(Object.keys(r).sort(), [...fields].sort(), 'Unapproved receipt fields');
  assert.equal(r.schema_version, '1.0.0');
  assert.equal(r.producer_repo, 'GBOGEB/CODEX');
  assert.equal(r.consumer_repo, 'GBOGEB/ABACUS');
  assert.equal(r.producer_sha, SOURCE_SHA);
  assert.equal(r.ssot_sha256, INPUT_DIGEST);
  assert.equal(r.contract_sha256, CONTRACT_DIGEST);
  assert.match(r.consumer_carrier_sha, /^[a-f0-9]{40}$/);
  assert.match(r.run_id, /^[1-9][0-9]*$/);
  assert.match(r.run_attempt, /^[1-9][0-9]*$/);
  assert.ok(['1', '2'].includes(r.repeat_id));
  assert.deepEqual(r.consumed_action_ids, actionIds);
  assert.equal(r.action_count, actionIds.length);
  assert.equal(r.result, 'STRUCTURE_VALIDATED');
  assert.equal(r.global_dov, 'WITHHELD');
  assert.equal(r.child_disposition, 'NOT_REQUESTED');
  return r;
}

export function projectReceipt(raw) {
  assert.equal(raw.execution_context, 'GITHUB_ACTIONS', 'Hosted receipt required');
  const projected = {};
  for (const key of fields) projected[key] = raw[key];
  projected.action_count = raw.consumed_action_ids?.length;
  return validateReceipt(projected);
}

export function compareReceipts(receipts) {
  assert.equal(receipts.length, 2, 'Exactly two independent job receipts required');
  const checked = receipts.map(validateReceipt);
  assert.deepEqual(checked.map(r => r.repeat_id).sort(), ['1', '2']);
  const stable = r => Object.fromEntries(Object.entries(r).filter(([key]) => key !== 'repeat_id'));
  assert.deepEqual(stable(checked[0]), stable(checked[1]), 'Repeat binding mismatch');
  return {
    schema_version: '1.0.0',
    consumer_carrier_sha: checked[0].consumer_carrier_sha,
    producer_sha: SOURCE_SHA,
    ssot_sha256: INPUT_DIGEST,
    contract_sha256: CONTRACT_DIGEST,
    run_id: checked[0].run_id,
    run_attempt: checked[0].run_attempt,
    repeat_count: 2,
    action_count: actionIds.length,
    result: 'REPEAT_MATCH',
    global_dov: 'WITHHELD',
    child_disposition: 'NOT_REQUESTED',
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [mode, output, ...inputs] = process.argv.slice(2);
  assert.ok(output && inputs.length, 'Usage: policy.mjs project|compare OUTPUT INPUT...');
  const data = inputs.map(p => JSON.parse(fs.readFileSync(p, 'utf8')));
  let result;
  if (mode === 'project') {
    assert.equal(data.length, 1);
    result = projectReceipt(data[0]);
  } else {
    assert.equal(mode, 'compare');
    result = compareReceipts(data);
  }
  fs.mkdirSync(path.dirname(output), {recursive: true});
  fs.writeFileSync(output, JSON.stringify(result, null, 2) + '\n', {flag: 'wx'});
  console.log('Receipt policy PASS');
}
