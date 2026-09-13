import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {consume} from './consume_federation_delivery.mjs';

const source = process.argv[2];
assert.ok(source, 'source directory required');
const first = await consume(source);
const repeat = await consume(source);
assert.deepEqual(first, repeat);
assert.equal(first.consumed_action_ids.length, 10);
assert.equal(first.global_dov, 'WITHHELD');
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-negative-'));
try {
  // Even whitespace changes invalidate the exact reviewed byte binding.
  fs.writeFileSync(path.join(temporary, 'delivery_ssot.json'), fs.readFileSync(path.join(source, 'delivery_ssot.json'), 'utf8') + ' ');
  await assert.rejects(consume(temporary), /digest mismatch/);
  fs.writeFileSync(path.join(temporary, 'delivery_ssot.json'), '{}');
  await assert.rejects(consume(temporary), /digest mismatch/);
} finally {
  fs.rmSync(temporary, {recursive: true});
}
console.log('PASS: 10 actions, deterministic repeat, two altered payloads rejected');
