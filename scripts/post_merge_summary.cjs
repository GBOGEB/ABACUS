"use strict";

// Read-only classification for GitHub check-runs at TWO independently pinned SHAs.
// This is NOT a required-status check evaluator, a reviewer or merge authority.
const FAILURE = new Set(["failure", "timed_out", "action_required", "startup_failure"]);
const NON_PROOF = new Set(["cancelled", "skipped", "neutral", "stale"]);
const SHA = /^[0-9a-f]{40}$/;

function classify(checks, expectedSha, sourceComplete) {
  if (!SHA.test(expectedSha)) throw new Error("Expected exact 40-character source SHA");
  if (!Array.isArray(checks)) throw new TypeError("checks must be an array");
  const result = { source_sha: expectedSha, source_complete: sourceComplete === true,
    passing: 0, failing: 0, cancelled: 0, skipped: 0, neutral: 0,
    pending: 0, unknown: 0, observed: 0, failures: [], cancelled_checks: [],
    pending_checks: [], state: "HOLD_INCOMPLETE" };
  for (const check of checks) {
    if (!check || typeof check !== "object") throw new TypeError("Invalid check");
    // Self-referential reporter success must never validate its own subject.
    if (check.name === "summarize-merged-pr" ||
        check.name === "Publish merged PR quality summary") continue;
    result.observed++;
    const label = String(check.name || "unnamed check");
    const c = check.conclusion || "";
    if (check.status !== "completed") {
      result.pending++;
      result.pending_checks.push(label + " (" + String(check.status || "unknown") + ")");
    } else if (c === "success") {
      result.passing++;
    } else if (FAILURE.has(c)) {
      result.failing++;
      result.failures.push(label + " (" + c + ")");
    } else if (c === "cancelled") {
      result.cancelled++;
      result.cancelled_checks.push(label);
    } else if (c === "skipped") result.skipped++;
    else if (c === "neutral") result.neutral++;
    else {
      result.unknown++;
      result.pending_checks.push(label + " (unclassified:" + c + ")");
    }
  }
  if (result.failing > 0) result.state = "FAIL";
  else if (!result.source_complete || result.pending || result.cancelled ||
           result.unknown || result.observed === 0 || result.passing === 0) {
    result.state = "HOLD_INCOMPLETE";
  } else if (result.skipped || result.neutral) result.state = "PARTIAL_NON_ADMISSION";
  else result.state = "OBSERVED_PASS_NON_ADMISSION";
  return result;
}

function pairState(head, merge) {
  if (head.failing > 0 || merge.failing > 0) return "FAIL";
  if (head.state !== "OBSERVED_PASS_NON_ADMISSION" ||
      merge.state !== "OBSERVED_PASS_NON_ADMISSION") return "HOLD";
  return "OBSERVED_PASS_NON_ADMISSION";
}

function render(pr, head, merge, metadata) {
  const status = pairState(head, merge);
  const lines = [
    "## Post-Merge PR Summary — source-bound, non-admission",
    "",
    "**PR:** #" + String(pr.number),
    "**Head SHA:** " + head.source_sha,
    "**Merge SHA:** " + merge.source_sha,
    "**Status:** " + status + " (informational only; NOT merger approval)",
    "",
    "| Native check population | Observed | Passed | Failed | Cancelled | Skipped | Neutral | Pending | Unknown | Complete | Disposition |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"
  ];
  for (const entry of [["PR exact head", head], ["Merge commit", merge]]) {
    const r = entry[1];
    lines.push("| " + entry[0] + " | " +
      [r.observed, r.passing, r.failing, r.cancelled, r.skipped,
       r.neutral, r.pending, r.unknown].join(" | ") + " | " +
      (r.source_complete ? "YES" : "NO") + " | " + r.state + " |");
  }
  lines.push("", "Check populations are separate: denominators must not be added.");
  lines.push("A green reporting job, an empty check population and a cancelled job NEVER establish admission.");
  const hasIssues = head.failing || merge.failing || head.cancelled ||
    merge.cancelled || head.pending || merge.pending || head.unknown ||
    merge.unknown || !head.source_complete || !merge.source_complete ||
    head.passing === 0 || merge.passing === 0;
  lines.push("", "### Failed / cancelled / incomplete checks");
  for (const entry of [["PR head", head], ["Merge commit", merge]]) {
    const r = entry[1];
    lines.push("**" + entry[0] + ":**");
    if (!r.source_complete) lines.push("- [ ] Incomplete GitHub check-run readback");
    if (r.observed === 0 || r.passing === 0) lines.push("- [ ] No successful, non-reporting check proven");
    for (const item of r.failures.slice(0, 25)) lines.push("- [ ] FAIL " + item);
    for (const item of r.cancelled_checks.slice(0, 25)) lines.push("- [ ] CANCELLED " + item);
    for (const item of r.pending_checks.slice(0, 25)) lines.push("- [ ] PENDING/UNKNOWN " + item);
    if (r.failures.length > 25 || r.cancelled_checks.length > 25 ||
        r.pending_checks.length > 25) lines.push("- [ ] Additional observations omitted; inspect raw checks");
  }
  if (!hasIssues) lines.push("- No failed/cancelled/incomplete checks observed in these two snapshots; review still required.");
  lines.push("", "### Change and provenance");
  lines.push("- Changed files: " + String(pr.changed_files) +
             "; additions: " + String(pr.additions) +
             "; deletions: " + String(pr.deletions));
  lines.push("- Source code changed: " + String(metadata.codeChanged));
  lines.push("- Staleness review suggested: " + String(metadata.staleRisk));
  lines.push("- This readback does not fetch effective required contexts, branch protection, human review, or security waivers.");
  lines.push("- Owner action: re-check all exact-head terminal jobs and current-main protections before crediting closure.");
  return lines.join("\n");
}

module.exports = { classify, pairState, render };
