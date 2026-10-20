"use strict";
/* W1: pure, non-admission PR evidence renderer. Existing check classifier stays SSOT. */
const fs = require("node:fs");
const { classify } = require("./post_merge_summary.cjs");
const SHA = /^[0-9a-f]{40}$/;
const START = "<!-- abacus-pr-evidence:start -->";
const END = "<!-- abacus-pr-evidence:end -->";
function requireTrue(ok, message) { if (!ok) throw new Error(message); }
function record(v) { return v && typeof v === "object" && !Array.isArray(v); }
function plain(v) { return typeof v === "string" && v.trim() ? v.trim().slice(0, 200)
  .replace(/\r?\n/g, " ").replace(/\|/g, "\\|").replace(/</g, "&lt;").replace(/>/g, "&gt;") : "UNKNOWN"; }
function project(source) {
  requireTrue(record(source) && source.schema === "abacus.pr-evidence-input.v1", "schema mismatch");
  requireTrue(source.repository === "GBOGEB/ABACUS", "repository mismatch");
  requireTrue(record(source.source) && SHA.test(source.source.head_sha) &&
    SHA.test(source.source.base_sha) && source.source.head_sha !== source.source.base_sha, "exact SHA mismatch");
  requireTrue(source.admission == null || source.admission === "HOLD", "admission forgery");
  requireTrue(source.merge_authorized !== true && source.authority_transfer !== true, "authority forgery");
  const head = source.source.head_sha, checks = source.checks;
  let state = { state: "HOLD_INCOMPLETE", passing: 0, failing: 0, pending: 0,
    cancelled: 0, skipped: 0, neutral: 0, unknown: 0, observed: 0, source_complete: false };
  if (checks != null) {
    requireTrue(record(checks) && checks.head_sha === head &&
      typeof checks.source_complete === "boolean" && Array.isArray(checks.items) &&
      checks.items.length <= 500, "check identity or completeness invalid");
    requireTrue(checks.items.every(x => record(x) && (x.head_sha == null || x.head_sha === head)),
      "stale individual check");
    state = classify(checks.items, head, checks.source_complete);
  }
  const coverage = source.coverage;
  let summary = "UNKNOWN (numerator and denominator unavailable)";
  if (coverage != null) {
    requireTrue(record(coverage) && ["REPORTED", "UNKNOWN", "INCOMPARABLE"].includes(coverage.status),
      "coverage status invalid");
    if (coverage.status === "REPORTED") {
      requireTrue(coverage.head_sha === head && Number.isSafeInteger(coverage.numerator) &&
        Number.isSafeInteger(coverage.denominator) && coverage.denominator > 0 &&
        coverage.numerator >= 0 && coverage.numerator <= coverage.denominator &&
        typeof coverage.cohort === "string" && !!coverage.cohort.trim(), "coverage identity/denominator invalid");
      summary = coverage.numerator + "/" + coverage.denominator + " (" + plain(coverage.cohort) + "; unverified)";
    } else {
      requireTrue(coverage.numerator == null && coverage.denominator == null, "false coverage value");
      summary = coverage.status + " (no comparable gain)";
    }
  }
  const root = record(source.first_red) ? source.first_red : {};
  return { head_sha: head, base_sha: source.source.base_sha, checks: state,
    coverage: summary, first_red: plain(root.root_id), owner: plain(root.owner),
    next_action: plain(root.next_action), admission: "HOLD",
    native_authenticated: null, math_status: "DOCK_ONLY_UNQUALIFIED" };
}
function render(p) {
  const c = p.checks;
  return [START, "### Machine evidence (non-admission)", "",
    "**MERGE_ADMISSION: HOLD** - native authentication UNKNOWN", "",
    "**Head:** `" + p.head_sha + "`",
    "**Base:** `" + p.base_sha + "`", "",
    "| Observed checks | Pass | Fail | Pending | Cancelled | Skipped | Unknown | Complete |",
    "|---|---:|---:|---:|---:|---:|---:|---|",
    "| " + c.observed + " | " + c.passing + " | " + c.failing + " | " +
      c.pending + " | " + c.cancelled + " | " + c.skipped + " | " + c.unknown +
      " | " + (c.source_complete ? "claimed" : "NO") + " |", "",
    "**Observed state:** " + c.state + " (not policy approval)",
    "**Coverage:** " + p.coverage,
    "**First red:** " + p.first_red + "; owner: " + p.owner,
    "**Next action:** " + p.next_action,
    "**gg_MATH:** docking only; no PCA/BT or M2/M3 credit.", "",
    "Required checks, review eligibility, A10 and Safety remain independent.",
    END].join("\n");
}
function replaceManaged(body, block) {
  requireTrue(typeof body === "string", "invalid PR body");
  const a = body.split(START).length - 1, b = body.split(END).length - 1;
  requireTrue(a === b && a <= 1, "bad markers");
  if (!a) return body.trimEnd() + "\n\n" + block + "\n";
  const first = body.indexOf(START), last = body.indexOf(END);
  requireTrue(first < last, "reversed markers");
  return body.slice(0, first) + block + body.slice(last + END.length);
}
function main(argv) {
  requireTrue(argv.length === 2 && argv[0] === "--input", "usage: --input receipt.json");
  const path = argv[1], stat = fs.lstatSync(path);
  requireTrue(stat.isFile() && !stat.isSymbolicLink() && stat.size > 0 && stat.size < 2000000,
    "untrusted input");
  process.stdout.write(render(project(JSON.parse(fs.readFileSync(path, "utf8")))) + "\n");
}
if (require.main === module) {
  try { main(process.argv.slice(2)); }
  catch (e) { process.stderr.write("PR evidence HOLD: " + e.message + "\n"); process.exitCode = 2; }
}
module.exports = { project, render, replaceManaged, START, END };
