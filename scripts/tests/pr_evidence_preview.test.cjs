"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { project, render, replaceManaged, START, END } = require("../pr_evidence_preview.cjs");
const A = "a".repeat(40), B = "b".repeat(40);
function fixture() {
  return { schema: "abacus.pr-evidence-input.v1", repository: "GBOGEB/ABACUS",
    source: { head_sha: A, base_sha: B },
    checks: { head_sha: A, source_complete: true,
      items: [{ name: "unit", status: "completed", conclusion: "success", head_sha: A }] } };
}
test("a passing check is observational, never admission", () => {
  const p = project(fixture());
  assert.equal(p.checks.state, "OBSERVED_PASS_NON_ADMISSION");
  assert.equal(p.admission, "HOLD");
  assert.equal(p.native_authenticated, null);
  assert.match(render(p), /MERGE_ADMISSION: HOLD/);
});
test("missing check observation remains HOLD", () => {
  const x = fixture(); delete x.checks;
  assert.equal(project(x).checks.state, "HOLD_INCOMPLETE");
});
test("true failed check is not green", () => {
  const x = fixture(); x.checks.items[0].conclusion = "failure";
  assert.equal(project(x).checks.state, "FAIL");
});
test("pending check does not become PASS", () => {
  const x = fixture(); x.checks.items[0].status = "queued";
  assert.equal(project(x).checks.state, "HOLD_INCOMPLETE");
});
test("incomplete source readback blocks even success", () => {
  const x = fixture(); x.checks.source_complete = false;
  assert.equal(project(x).checks.state, "HOLD_INCOMPLETE");
});
test("stale grouped and individual check SHA refused", () => {
  const x = fixture(); x.checks.head_sha = B;
  assert.throws(() => project(x), /check identity/);
  x.checks.head_sha = A; x.checks.items[0].head_sha = B;
  assert.throws(() => project(x), /stale individual/);
});
test("source identity and repository are checked", () => {
  const x = fixture(); x.source.head_sha = "bad";
  assert.throws(() => project(x), /exact SHA/);
  x.source.head_sha = A; x.repository = "foreign/repo";
  assert.throws(() => project(x), /repository/);
});
test("claimed admission is never accepted", () => {
  const x = fixture(); x.admission = "PASS";
  assert.throws(() => project(x), /forgery/);
  x.admission = "HOLD"; x.merge_authorized = true;
  assert.throws(() => project(x), /forgery/);
});
test("coverage denominator and SHA require correct identity", () => {
  const x = fixture(); x.coverage = { status: "REPORTED", head_sha: A,
    numerator: 7, denominator: 10, cohort: "matched" };
  assert.match(project(x).coverage, /7\/10/);
  x.coverage.head_sha = B;
  assert.throws(() => project(x), /denominator invalid/);
  x.coverage.head_sha = A; x.coverage.numerator = 11;
  assert.throws(() => project(x), /denominator invalid/);
});
test("unknown coverage cannot claim numeric gain", () => {
  const x = fixture(); x.coverage = { status: "UNKNOWN", numerator: 5 };
  assert.throws(() => project(x), /false coverage/);
});
test("managed projection preserves author rationale", () => {
  const prior = "Human intent\n" + START + "OLD" + END + "\nReviewer notes";
  const next = replaceManaged(prior, render(project(fixture())));
  assert.match(next, /^Human intent/);
  assert.match(next, /Reviewer notes$/);
  assert.doesNotMatch(next, /<!-- abacus-pr-evidence:start -->OLD/);
});
test("duplicate, missing or reversed marker sets fail safely", () => {
  for (const body of [START, END, START + START + END + END, END + START]) {
    assert.throws(() => replaceManaged(body, "NEW"), /markers/);
  }
  assert.match(replaceManaged("Human note", "NEW"), /^Human note\n\nNEW/);
});
test("first-red text is safely escaped", () => {
  const x = fixture(); x.first_red = { root_id: "<bad>|text", owner: "owner" };
  assert.match(render(project(x)), /&lt;bad&gt;/);
});
