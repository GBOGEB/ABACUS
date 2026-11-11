// Run with Node 22.13+ (or Node 24): node --test scripts/tests/seed.test.mjs
// Execute the real TypeScript entry point with an in-memory Prisma boundary.
// This never connects to, reads, or changes a database.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { stripTypeScriptTypes } from 'node:module';
import test from 'node:test';
import vm from 'node:vm';

const entry = await readFile(new URL('../seed.ts', import.meta.url), 'utf8');
const prismaImport = "import { PrismaClient } from '@prisma/client';";
assert.equal(entry.split(prismaImport).length, 2, 'seed must have one Prisma import');
const executable = stripTypeScriptTypes(entry.replace(prismaImport, ''));

async function seed(initial = [], failOnPage = null) {
  const records = new Map(initial.map((record) => [record.pageNumber, structuredClone(record)]));
  let disconnects = 0;
  const errors = [];
  const process = { exitCode: 0 };
  class PrismaClient {
    slide = {
      async upsert({ where, update, create }) {
        if (where.pageNumber === failOnPage) throw new Error('synthetic database failure');
        const existing = records.get(where.pageNumber);
        records.set(where.pageNumber, existing
          ? { ...existing, ...structuredClone(update) }
          : structuredClone(create));
      },
    };
    async $disconnect() {
      disconnects += 1;
    }
  }
  await vm.runInNewContext(executable, {
    PrismaClient,
    process,
    console: { log() {}, error(...args) { errors.push(args); } },
  }, { timeout: 2000 });
  return { records, disconnects, errors, exitCode: process.exitCode };
}

test('fresh setup creates all neutral slots without pre-existing review data', async () => {
  const result = await seed();
  assert.equal(result.records.size, 15);
  for (let page = 1; page <= 15; page += 1) {
    const record = result.records.get(page);
    assert.equal(record.pageNumber, page);
    assert.equal(record.title, `Slide ${String(page).padStart(2, '0')}`);
    assert.equal(record.imageFilename, `slide-${String(page).padStart(2, '0')}.png`);
    assert.equal(record.groupName, 'Unclassified placeholders');
    assert.equal(record.starred, false);
    assert.equal(record.votesUp + record.votesDown + record.votesNeutral, 0);
  }
  assert.equal(result.disconnects, 1);
  assert.equal(result.exitCode, 0);
});

test('rerun preserves loaded metadata, votes and custom image paths while filling gaps', async () => {
  const loaded = {
    pageNumber: 3, title: 'Owner supplied title', groupName: 'Reviewed group',
    imageFilename: 'custom-review-03.svg', starred: true,
    votesUp: 7, votesDown: 2, votesNeutral: 4, id: 'existing-record',
  };
  const first = await seed([loaded]);
  assert.deepEqual(first.records.get(3), loaded);
  assert.equal(first.records.size, 15);
  const second = await seed([...first.records.values()]);
  assert.deepEqual([...second.records.values()], [...first.records.values()]);
  assert.equal(second.disconnects, 1);
  assert.equal(second.exitCode, 0);
});

test('database failure retains nonzero exit and disconnects without touching existing metadata', async () => {
  const loaded = { pageNumber: 1, title: 'Keep this title', imageFilename: 'keep.png' };
  const result = await seed([loaded], 2);
  assert.deepEqual(result.records.get(1), loaded);
  assert.equal(result.records.size, 1);
  assert.equal(result.exitCode, 1);
  assert.equal(result.disconnects, 1);
  assert.equal(result.errors.length, 1);
});
