# ABACUS open-PR debug reruns and lag-diff ledger

**Status:** review-first implementation; no automatic merge, waiver, approval or branch-rule modification.

## Intended user commands (PowerShell 7, GitHub CLI, Python 3.9+)

```powershell
# One-time native prerequisites and authorization
winget install --id GitHub.cli
# Install PowerShell 7 and Python 3.9+ if not already present
gh auth login
gh auth status

# A. Census ALL open PRs, including drafts; inspect existing reds, no dispatch
pwsh -File ./scripts/Invoke-AbacusPrDebug.ps1 -Mode Plan

# B. Re-run only eligible transient failures, with GitHub Actions debug logging;
# capped at eight workflow runs, spaced by 20 s, with a 45 min cooldown.
pwsh -File ./scripts/Invoke-AbacusPrDebug.ps1 -Mode Apply -Yes

# C. Explicitly request ALL current-head failed workflow families, even persistent
# deterministic roots, with debug, bounded to 20 runs. This costs CI minutes and
# does not resolve source A10/Bandit/Safety/formatting debt by itself.
pwsh -File ./scripts/Invoke-AbacusPrDebug.ps1 -Mode Apply -Policy AllFailed -Yes -MaxReruns 20 -DelaySeconds 30 -CooldownMinutes 0

# D. Refresh later and compare N-1 to N telemetry without dispatch
pwsh -File ./scripts/Invoke-AbacusPrDebug.ps1 -Mode Refresh

# E. Narrow to known PRs; optional read-only external telemetry receipts
pwsh -File ./scripts/Invoke-AbacusPrDebug.ps1 -Mode Plan -OnlyPR 1980,2109 -DashboardReceipts ./dashboard-receipts.json -AgentReceipts ./agent-receipts.json
```

Backend can be used directly: `python scripts/abacus_pr_rerun_audit.py --mode plan`.
`gh run rerun RUN_ID --failed --debug --repo GBOGEB/ABACUS` is the native action
used for accepted dispatches; **GitHub** runs failed jobs and their dependencies.
The `--debug` flag enables debug logging in that new attempt; it does not add
`pytest -vv` or change test source/thresholds.

## Selection and safety invariants

1. Enumerate **all open pull requests** via paginated GitHub REST, including drafts.
   On pagination exhaustion the census fails closed; do not mistake page one
   for the whole portfolio. Optional `-MaxPRs` is explicitly a partial scan.
2. Resolve the actual `.head.sha` and `.head.ref` independently for every PR.
   Accept only runs with identical `head_sha` and matching native PR linkage
   (or unambiguous branch identity where GitHub omits PR linkage).
   Historic failures from earlier SHAs are observations, never rerun targets.
3. Retain only the latest run/attempt per `(workflow ID, trigger event)` family
   on that head. Do **not** rerun old attempts after a newer success.
4. Failed-jobs rerun is permitted only after run state and PR head are checked
   again immediately before dispatch. `-Mode Apply -Yes` is explicit; no tool
   writes in Plan/Refresh. No destructive Git action or auto-merge is present.
5. By default, deterministic or administration-owned roots (A10, Safety,
   Bandit, Black/isort, disabled dependency graph, installation API quota)
   require owner decisions. Use `-Policy AllFailed` to explicitly override the
   *retry selection policy*, **not** to waive native CI or security gates.
6. Dispatch is serial, capped, rate-spaced and journaled by
   `PR:run:attempt:SHA` **before** calling GitHub. An unknown result following
   a network outage requires manual reconciliation rather than silent repeat.
7. Native admission remains `HOLD` regardless of successes or logs.

## What the tool emits

Under `.artifacts/abacus-pr-debug/` (not committed):

| File | Meaning |
| --- | --- |
| `latest.json` | Exact PR head, latest per-workflow CI attempt, first failed steps, open reviewer requests, red/pending/stale counts and lag flags |
| `snapshots/*.json` | Time-pinned previous observations; do not rewrite history |
| `diff.json`, `diff.md` | Source-head and CI-attempt transitions, disappeared and newly observed workflow families, agent/dashboard receipt changes |
| `bd_queue.csv` | Excel-friendly root/worker run candidates with exact run and SHA |
| `rerun_actions.json` | GitHub dispatch accepted vs skipped vs failed, never equated to passed tests |
| `rerun_journal.json` | Durable idempotency key, including uncertain failed requests |
| `manifest.json` | Local SHA-256 and byte count of the latest report files (not remote authentication) |

Native job first failed **step** is collected from GitHub job metadata. The default
controller avoids storing full failed logs, as they might contain confidential
material. Use `gh run view RUN_ID --log-failed --repo GBOGEB/ABACUS` in an
authorized terminal for deeper forensic investigation.

## Lag attribution / root classes

| Symptom | Evidence-based classification | Interpretation |
| --- | --- | --- |
| New PR SHA, zero linked native runs | `MISSING_CURRENT_HEAD_CI` | Workflow trigger/dispatch gap; source may be ready but proof is absent |
| Queued/running latest head | `GITHUB_CI_NONTERMINAL` | GitHub job pending; distinguish queue from workflow dependency time |
| Older CI runs exist on same branch | `HISTORICAL_STALE_RUNS_PRESENT` | Historical evidence, **not** current-head proof |
| Supplied agent receipt has old SHA | `AGENT_SNAPSHOT_STALE` | Agent observation is behind source; **not proof of agent fault** |
| Supplied dashboard receipt has old SHA | `DASHBOARD_SNAPSHOT_STALE` | Dashboard has not displayed current source head |
| Native completion newer than dashboard timestamp | `DASHBOARD_PUBLICATION_LAG` | Measurable observation/publication gap (if a timestamp was supplied) |
| Reviewers requested | `REVIEW_OBLIGATION_PENDING` | Human decision outstanding; duration/reason is **unknown** unless separately measured |
| Missing external receipts | `NO_RECEIPT` | No comparable evidence; do **not** show zero lag |

**Never** infer human, GitHub or coding-agent culpability from a label alone.
The reader must check run-job-attempt IDs, actual artifact bytes, event SHA
versus pull-head SHA, and provenance if claiming independently verified closure.
The receipt inputs below are advisory, not cryptographically authenticated.

### Optional dashboard and coding-agent JSON receipts

```json
{
  "schema": "code-purple.external-observation.v1",
  "prs": {
    "1980": {
      "head_sha": "9536539e88a8aecc5d052c7d63d17cf2396570af",
      "observed_at": "2026-10-17T16:30:00Z",
      "last_run_id": 39036748739
    }
  }
}
```

Each channel can supply its own `-AgentReceipts` or `-DashboardReceipts`
file. If either is absent, the report keeps the channel **UNKNOWN/NO_RECEIPT**
without inventing a numeric delay. Do not supply credentials or tender content.

### Scope/DoD/DoV

- **DoD:** command loads, dry-run enumerates all open PRs, exact-head and
  rerun idempotency negative controls pass, manifest/diff produced.
- **DoV:** an authorized operator performs a bounded debug rerun, compares
  pre/post exact-head job+attempt receipts and confirms any failures/coverage
  changes with native GitHub Actions and authenticated artifact bytes.
- **Not supported:** automatically modifying agent/dashboard apps, forcibly
  merging PRs, bypassing A10/Safety/Bandit, weakening required checks, or
  claiming an agent/human caused lag without identity/timing evidence.
