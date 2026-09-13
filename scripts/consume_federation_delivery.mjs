// Read-only DOW consumer: no action-state or engineering promotion.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL, fileURLToPath} from 'node:url';

export const SOURCE_SHA = '3bfda0e50d2e89b12d850a98f2929e73a3f3c234';
export const SOURCE_PATH = 'federation/delivery/FED_PCA_20260912';
export const INPUT_DIGEST = 'a66451759a3854427de68e260396b791e11d061c27fc02cfb8811f4867029b76';
export const CONTRACT_DIGEST = '515c0d5228a325fe969c5ab595783be774d8b7d23cb1d7e39619637ad8f8eddb';
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

export async function consume(sourceDir) {
  const bytes = fs.readFileSync(path.join(sourceDir, 'delivery_ssot.json'));
  const digest = hash(bytes);
  if (digest !== INPUT_DIGEST) throw Error('Register digest mismatch: reviewed source changed');
  const contractDigest = hash(fs.readFileSync(path.join(sourceDir, 'contract.mjs')));
  if (contractDigest !== CONTRACT_DIGEST) throw Error('Contract digest mismatch');
  const {Register} = await import(pathToFileURL(path.resolve(sourceDir, 'contract.mjs')));
  const data = Register.parse(JSON.parse(bytes));
  return {
    schema_version: '1.0.0',
    producer_repo: 'GBOGEB/CODEX',
    producer_sha: SOURCE_SHA,
    producer_path: SOURCE_PATH + '/delivery_ssot.json',
    ssot_sha256: digest,
    contract_sha256: contractDigest,
    release: data.release,
    consumer_repo: 'GBOGEB/ABACUS',
    result: 'STRUCTURE_VALIDATED',
    consumed_action_ids: data.actions.map(a => a.id).sort(),
    global_dov: data.global_dov,
    child_disposition: 'NOT_REQUESTED',
    scope: 'Exact reviewed register bytes and Zod structure; not live evidence verification or engineering acceptance',
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [sourceDir, output] = process.argv.slice(2);
  if (!sourceDir || !output) throw Error('Usage: node consume_federation_delivery.mjs SOURCE_DIR OUTPUT.json');
  const receipt = await consume(sourceDir);
  // CI caller verifies both checkouts before invoking this CLI.
  const runtime = process.env.GITHUB_ACTIONS === 'true';
  if (runtime && (!/^[a-f0-9]{40}$/.test(process.env.GITHUB_SHA || '') || !/^\d+$/.test(process.env.GITHUB_RUN_ID || ''))) {
    throw Error('Missing runtime binding');
  }
  Object.assign(receipt, {
    execution_context: runtime ? 'GITHUB_ACTIONS' : 'LOCAL_VALIDATION',
    consumer_carrier_sha: runtime ? process.env.GITHUB_SHA : null,
    run_id: runtime ? process.env.GITHUB_RUN_ID : null,
    run_attempt: runtime ? process.env.GITHUB_RUN_ATTEMPT : null,
    repeat_id: runtime ? process.env.DELIVERY_REPEAT || null : null,
    runner_name: runtime ? process.env.RUNNER_NAME || null : null,
    observed_at: new Date().toISOString(),
  });
  fs.mkdirSync(path.dirname(output), {recursive: true});
  fs.writeFileSync(output, JSON.stringify(receipt, null, 2) + '\n', {flag: 'wx'});
  console.log(JSON.stringify(receipt));
}
