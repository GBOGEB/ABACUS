import { test } from 'node:test';
import assert from 'node:assert/strict';
import { countBtObservations } from '../lib/bt_observed.ts';
test('observed counts survive separated Bradley-Terry graph', () => {
  const rows = countBtObservations([1, 2, 3], [
    {slideAId: 1, slideBId: 2, winnerId: 1, isTie: false},
    {slideAId: 1, slideBId: 3, winnerId: 1, isTie: false},
    {slideAId: 2, slideBId: 3, winnerId: null, isTie: true}
  ]);
  assert.deepEqual(rows.get(1), {wins: 2, losses: 0, ties: 0, comparisons: 2, winRate: 1});
  assert.deepEqual(rows.get(2), {wins: 0, losses: 1, ties: 1, comparisons: 2, winRate: 0});
  assert.deepEqual(rows.get(3), {wins: 0, losses: 1, ties: 1, comparisons: 2, winRate: 0});
});
test('invalid winners do not contaminate descriptive telemetry', () => {
  const rows = countBtObservations([1, 2], [
    {slideAId: 1, slideBId: 2, winnerId: 999, isTie: false},
    {slideAId: 1, slideBId: 2, winnerId: null, isTie: true}
  ]);
  assert.equal(rows.get(1)?.comparisons, 1);
  assert.equal(rows.get(2)?.ties, 1);
});
