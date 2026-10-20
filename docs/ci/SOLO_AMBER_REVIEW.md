# Solo maintainer AMBER exception process (v1)

This is an **evidence ledger only**, not a branch-protection bypass, a GitHub
approval, or a merge-admission authority. The repository's existing A10, native
CI, workflow-policy SSOT and branch rules remain unchanged.

## Decision sequence

1. GBO produces an exact-head native test and check census; no stale run is
   attributed to a new SHA. Record the complete list, not just failed checks.
2. GEB performs a separate-context adversarial review. This is **AI-assisted
   self-review**, not a second independent human.
3. Categorize each non-success check. Security, confidentiality, governance,
   provenance, correctness, release and data integrity are always hard HOLD.
4. Low-risk formatting, docs, telemetry or CI infrastructure may be proposed
   as an explicit carry-over with an issue, root fingerprint, risk, mitigation,
   expiry, owner and GitHub Actions run URL. Unknown and skipped must be
   classified; unclassified remains HOLD. Do not mark failed checks as passed.
5. Run the read-only validator. `AMBER_REQUESTED` is **not merge approval**.
6. The repository owner separately decides whether and how to configure an
   authorized GitHub ruleset bypass or alter a rule. Record the actual
   GitHub audit trail. Never circumvent with a false status context.
7. Verify merged main with a new exact-main pulse and keep carried-over issues
   open until their native root evidence proves closure. On expiry, escalate.
8. Recover the original strict protections after a time-bounded exception
   window. Reconcile main, checks, ruleset ID and actual waiver disposition.

## Usage

```bash
python -m unittest discover -s ci/governance/tests -p 'test_solo_amber.py' -v
python ci/governance/solo_amber.py \
  --input /path/to/operator-reviewed-request.json \
  --output /path/to/solo-amber-decision.json
```

The input JSON uses schema `abacus.solo-amber.v1`. It includes
`repository`, `pr_number`, `head_sha`, `decision`, `checks` and
optional `pulses`. Inspect `ci/governance/tests/test_solo_amber.py` for a
complete synthetic example. Do not submit synthetic examples as operational
readiness evidence.

## Wave/pulse KPI contract

Each pulse carries a unique wave ID and exact SHA, native test pass/fail/skip
counts, distinct root counts, fingerprint first-reds, workers, and matched
source/config/denominator coverage. `COMPARABLE` reports percentage-point
gain; `UNKNOWN` and `INCOMPARABLE` report null, never zero.

Consume the existing `mip_wave_pulse.json` and
`mip_backlog_delta.json` producer receipts from PR #1990 as the primary
data source. This validator displays their submitted values but does **not**
independently verify the native receipts. Production integration shall verify
run IDs, artifact bytes, SHA256, check completeness, exact SHA, and timestamps.
A source-defined cohort expansion is distinct from matched-cohort improvement.

Recommended columns per wave: head SHA, native run ID, check statuses, first-red
root count, repeated manifestations, tests passed/failed/skipped, line/branch
coverage numerators and denominators, matched percentage-point delta,
worker-hours, CI duration and queue/download/install/execution/upload time.
Never fabricate missing metrics. Evaluate scaling as coverage gain per worker
hour, root closures per wave, native CI wall time and reopened roots.

## Manual GitHub owner configuration

Live observed repository ruleset on 2026-10-15:
`ABACUS Main Hard Gate` (#24494381) required one approving reviewer,
approval of last push, review thread resolution, and had no bypass actors.
This makes the single owner unable to self-approve. The ruleset did not itself
require status checks. Other protection controls were not fully accessible
through the active GitHub App.

Suggested phased refinement: allow accountable solo-owner merge by adjusting
the required external approval rule or enabling an explicitly authorized,
time-bounded repository ruleset bypass. Preserve deletion/non-fast-forward
protection, native security checks, and named exception records. Prefer
GitHub's supported pull-request-only bypass when available. A bypass is not
per-check in a general sense; this producer implements **item-level evidence**
rather than falsely promising a per-check GitHub bypass. Capture before/after
screenshots or API receipts from the actual ruleset edit.

Do not apply a repository-wide bypass automatically, lower formatter/security
thresholds, edit A10 allowlists, or claim that Copilot or a second account
supplies independent human review. No automated merge is performed here.
