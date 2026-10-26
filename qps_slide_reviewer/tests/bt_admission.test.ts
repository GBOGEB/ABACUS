import { test } from 'node:test';
import assert from 'node:assert/strict';
import { assessBtAdmission } from '../lib/bt_admission';
const edge = (winner: number, loser: number) => ({
  slideAId: winner, slideBId: loser, winnerId: winner, isTie: false
});
test('strongly-connected graph is eligible only for provider fit', () => {
  const result = assessBtAdmission([1, 2, 3], [edge(1, 2), edge(2, 3), edge(3, 1)]);
  assert.equal(result.status, 'BT_PREFLIGHT_ELIGIBLE');
  assert.equal(result.authority, 'CONSUMER_PREFLIGHT_ONLY');
  assert.equal(result.provider, 'GBOGEB/gg_MATH');
});
test('separated graph defers without ranking', () => {
  assert.equal(assessBtAdmission([1, 2, 3, 4], [
    edge(1, 2), edge(2, 1), edge(3, 4), edge(4, 3)
  ]).status, 'DEFER_DISCONNECTED_COMPARISON_GRAPH');
});
test('one-way total order does not meet Ford condition', () => {
  assert.equal(assessBtAdmission([1, 2, 3], [edge(1, 2), edge(2, 3), edge(1, 3)])
    .status, 'DEFER_NO_FINITE_MLE');
});
test('empty and tie-only inputs cannot pass', () => {
  assert.equal(assessBtAdmission([1, 2], []).status, 'DEFER_NO_USABLE_COMPARISONS');
  assert.equal(assessBtAdmission([1, 2], [
    { slideAId: 1, slideBId: 2, winnerId: null, isTie: true }
  ]).eligible, false);
});
test('unrecognized winner, self-comparison, inconsistent tie and duplicate id defer', () => {
  assert.equal(assessBtAdmission([1, 2], [edge(3, 1)]).status, 'DEFER_INVALID_COMPARISON');
  assert.equal(assessBtAdmission([1, 2], [edge(1, 1)]).status, 'DEFER_INVALID_COMPARISON');
  assert.equal(assessBtAdmission([1, 2], [
    { slideAId: 1, slideBId: 2, winnerId: 1, isTie: true }
  ]).status, 'DEFER_INVALID_COMPARISON');
  assert.equal(assessBtAdmission([1, 1], []).status, 'DEFER_INVALID_COMPARISON');
});
