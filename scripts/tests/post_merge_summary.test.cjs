"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { classify, pairState, render } = require("../post_merge_summary.cjs");
const A = "a".repeat(40), B = "b".repeat(40);
const check = (name, conclusion, status = "completed") => ({ name, conclusion, status });

test("zero successful checks is HOLD, never PASS", () => {
  const h = classify([check("x", "skipped")], A, true);
  assert.equal(h.state, "HOLD_INCOMPLETE");
  assert.equal(h.passing, 0);
  assert.equal(pairState(h, classify([], B, true)), "HOLD");
});
test("reporter-only success is not independent evidence", () => {
  const h = classify([check("summarize-merged-pr", "success")], A, true);
  assert.equal(h.observed, 0);
  assert.equal(h.state, "HOLD_INCOMPLETE");
});
test("cancelled checks are not test failures and still block PASS", () => {
  const h = classify([check("unit", "success"), check("macOS", "cancelled")], A, true);
  assert.equal(h.failing, 0);
  assert.equal(h.cancelled, 1);
  assert.equal(h.state, "HOLD_INCOMPLETE");
});
test("timed_out and startup_failure count as genuine check failure class", () => {
  const h = classify([check("a", "timed_out"), check("b", "startup_failure")], A, true);
  assert.equal(h.failing, 2);
  assert.equal(h.state, "FAIL");
});
test("pending checks are held separately", () => {
  const h = classify([check("x", null, "queued"), check("y", "success")], A, true);
  assert.equal(h.pending, 1);
  assert.equal(h.state, "HOLD_INCOMPLETE");
});
test("incomplete pagination remains HOLD even when green", () => {
  const h = classify([check("x", "success")], A, false);
  assert.equal(h.state, "HOLD_INCOMPLETE");
});
test("nonfatal neutral/skipped remains partial non admission", () => {
  const h = classify([check("x", "success"), check("y", "neutral")], A, true);
  assert.equal(h.state, "PARTIAL_NON_ADMISSION");
  assert.equal(h.neutral, 1);
});
test("merge green cannot hide PR-head red", () => {
  const head = classify([check("test", "failure")], A, true);
  const merge = classify([check("test", "success")], B, true);
  assert.equal(pairState(head, merge), "FAIL");
  const body = render({ number: 2058, changed_files: 1, additions: 2, deletions: 0 },
      head, merge, { codeChanged: true, staleRisk: true });
  assert.match(body, /PR exact head/);
  assert.match(body, /Merge commit/);
  assert.match(body, /FAIL test/);
  assert.match(body, /non-admission/);
});
test("green heads are observational only and distinct populations", () => {
  const head = classify([check("tests", "success")], A, true);
  const merge = classify([check("tests", "success")], B, true);
  assert.equal(pairState(head, merge), "OBSERVED_PASS_NON_ADMISSION");
  assert.match(render({ number: 10, changed_files: 0, additions: 0, deletions: 0 },
      head, merge, { codeChanged: false, staleRisk: false }), /denominators must not be added/);
});
test("invalid source identity and malformed check fail closed", () => {
  assert.throws(() => classify([], "short", true), /source SHA/);
  assert.throws(() => classify([null], A, true), /Invalid check/);
});
