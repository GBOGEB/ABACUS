# DROPIN — CODE PURPLE / ABACUS G3A (2026-10-23)

**Transport:** GitHub-first; no sealed LOSSLESS_HANDOVER_V2 capsule or full verbatim transcript was validated. This is an instruction for one bounded interactive execution, NOT unattended background execution or merge authority. Read the companion handover first: handover/mip_20261023/CODE_PURPLE_ABACUS_G3A_HANDOVER.md.

~~~text
CP.RESUME(source="GITHUB_FIRST", mode="VERIFY_REFRESH_EXECUTE",
          horizon="G3P:N_TO_N_PLUS_3")
MISSION = CODE_PURPLE_ABACUS_MCL_PWSH_RECOVERY
REPOS = GBOGEB/ABACUS (primary), GBOGEB/CODEX (taxonomy consumer)
ADMISSION = HOLD
CANONICAL_METHOD = handover/HANDOVER_MESSAGE_TEMPLATE.md
CODEX_METHOD = docs/automation/G3A_EXECUTION_CONTRACT.md

CONTROLLING HANDOVER POINTER:
handover/mip_20261023/CODE_PURPLE_ABACUS_G3A_HANDOVER.md
PERSISTENT BD:
ABACUS issues #1978, #1860, #1738, #1736, #1996, #1929, #1944.

PINNED SNAPSHOT: ABACUS main 8c210b8c3768d4252bc2745dab3c60a2fa5795ac;
CODEX main 3f00b1dac349d2280430f4dc94c2e348713344d6.
These are 23 Oct handover observations, not permission to skip fresh reads.
#1980 Mission Control Lite MERGED: source b24887d2822e9d3dd2a2281e776bffd4977c5db3,
merge e864283660cbd65ca51324be1a813439c351357b.
#2154 all-open-PR PowerShell debug/lag controller MERGED: source
f29572b5eb6a0a42685cca6d599aa1e9ef57b322,
merge 014217c44ea1c5c2c0e9aa689f3226be7bae1044.
#2109 OPEN: real pull head 0d42735fbb2c41b0b4856744ff416c065a7beffb;
event synthetic merge 4e7138cefc0a6a6d45ef58613e04572c22de1eef.
CODEX #1060 taxonomy MERGED; ABACUS #2117 consumer docs MERGED.

FROZEN CURRENT-HEAD EVIDENCE (BECOMES HISTORICAL AFTER SHA CHANGE):
ABACUS #2109: 24 workflow results: 19 success, 4 failure, 1 cancelled.
MCL testflight 39933634218 / native job 120347729473 SUCCESS;
196 focused tests, 82.5949% focused line, 77.8037% focused branch;
comparison UNKNOWN, source actual pull head, merge_admission HOLD.
GitHub artifact 12493260342, ZIP SHA256 reported as
93953f2d5d1a22d795db7be4c4a2443951e5bfe4f8220aacd14da81d16bda280.
Digest not independently redownloaded/recomputed in this handover.
Independent mandatory roots:
- Docs 39933634459: tools/stack/README.md MD060 and YAML line-length
  (includes .pre-commit-config.yaml).
- Governance 39933634221: unclassified config-surface-audit.yml, multiple
  policy owners of code-quality-pilot.yml, Next.js cluster mismatch,
  stale generated WORKFLOW_RATIONALIZATION.md, G3G SUT negative-path
  validation does not reject traversal/absolute/NUL/duplicate paths.
- CI 39933634343: Bandit new debt in 7 of 61 changed Python files, including
  B506:MEDIUM; required Black/isort full scan red; Python 3.10 macOS,
  Windows and Ubuntu collection ERROR from tests/test_config_surface_audit.py
  importing tomllib (not a Python 3.10 stdlib module).
- Python matrix 39933634163: same Python 3.10 root and downstream
  completeness/compatibility failures; do not double-count.
- #2109 A10 and CodeQL SUCCESS, no proof of independent human approval.
No current-main or matched changed-line coverage measurement credited.

GOVERNANCE:
ABACUS main is protected=true; active ruleset 24494381 has no required
status-check rule, zero required approving reviews and six bypass actors.
CODEX main protected=true; ruleset 25554145 has a required-status rule
with EMPTY contexts and zero required reviewers. Effective rulesets must
be re-read, negative RED admission canary required; no claim protected=true
equals fully governed. No automatic waiver, human review or merge.

TELEMETRY LAG:
At initial read main 06b1fdf7aa3b... advanced 2 commits to 8c210b8...
The later main contains docs/api/dmaic_metrics.json and chart.html,
whose data source SHA is the preceding 06b1fdf7aa3b snapshot.
Determine generator input/publisher contract and deployed Pages
observation before declaring human/agent/dashboard delay or causation.
Unknown external receipts mean NO_RECEIPT, not zero delay.

P1 OBSERVE:
- Refresh main/head SHA, effective rulesets, owner lease, native jobs and
  artifacts BEFORE any mutation. Distinguish pull head and event merge.
- Take one exact-head census, first independent reds and untouched
  historical receipts; collect source/test/config identities and
  denominators. Avoid re-running obsolete or nonterminal cohorts.
- Inventory issue/PR closed/superseded lineage and owner-only obligations;
  emit N snapshot with queue missingness and censored waits.

P2 ANALYZE/IMPROVE:
- Prioritize by true root severity and unblock reach, independent test
  impact, risk, available owner lease and measured execution cost.
- Candidate A: Python 3.10 tomllib import compatibility (only if supported);
  candidate B: strict G3G path traversal/absolute/NUL/duplicate validation;
  candidate C: unique governance workflow assignment and safe regeneration.
- Disjoint file-owner writes only. Independent security/Bandit, formatter,
  documentation and UI owners; at most one integrated source head after fan-in.
- Negative/reverse/security tests, no broad ignore/nosec or weakening policy.
- Keep CODEX taxonomy in CODEX and ABACUS telemetry evidence in ABACUS;
  do not transfer private QPS, bidder or controlled content.

P3 VERIFY/CONTROL:
- Run focused negatives plus full native matrix (3.10/3.11/3.12 where
  supported), security, governance, docs, Quality, A10 and CodeQL.
- Download current-head ZIP, recompute SHA256 against GitHub digest, verify
  each inner receipt-listed output byte length/hash, source SHA vs merge SHA.
- Measure line/branch/diff coverage only with same eligible population,
  numerator/denominator, instrumentation and source/config. Preserve
  historical 83/111-prediction/196 as non-comparable until proven otherwise.
- Run PowerShell Plan then optionally one explicit authorized Retryable
  debug rerun after source-head revalidation; preserve idempotency journal.
- Recheck effective required status contexts and independent eligible human
  review; merge/admission remains HOLD if any gate missing.

MANDATORY STOP:
Head/policy drift, lost owner lease, evidence mismatch, nonterminal gate,
Security/A10 uncertainty, scanner quota, runner saturation, insufficient
permissions or private engineering data -> stop, append HOLD receipt.
No force-push, auto-merge, fake review, broad repeated AllFailed reruns,
scheduler claim or waiver. No asynchronous work unless separately scheduled.

RETURN REQUIREMENTS:
- P1/P2/P3 receipts with N/N+1/N+2/N+3 exact SHA + job/run/attempt, tests
  planned/executed PASS/FAIL/SKIP, coverage N/D and external evidence SHA256.
- Deduplicated BD roots with reopened/closed lineage, owner, DoD vs DoV,
  retry/root displacement and same-head metrics; include uncertainty.
- DAG + SIPOC typed interfaces, chronology, security/admission blockers.
- Planned vs actual, independent x/3 native verified and y/3 accepted
  steps, decisive next action. Final admission HOLD absent all proof.
- Next GitHub-first handover and DROPIN additive update, NOT fictitious V2.
~~~

## Operator PowerShell 7 quick start (at an existing ABACUS checkout)

~~~powershell
gh auth status
git status --short
gh pr view 2109 --repo GBOGEB/ABACUS --json headRefOid,baseRefOid,state
pwsh -File ./scripts/Invoke-AbacusPrDebug.ps1 -Mode Plan
pwsh -File ./scripts/Invoke-AbacusPrDebug.ps1 -Mode Plan -OnlyPR 2109
pwsh -File ./scripts/Invoke-AbacusPrDebug.ps1 -Mode Refresh
gh run view 39933634163 --repo GBOGEB/ABACUS --log-failed
gh run view 39933634221 --repo GBOGEB/ABACUS --log-failed

# ONLY with owner authorization and current-head/rerun eligibility confirmed:
pwsh -File ./scripts/Invoke-AbacusPrDebug.ps1 -Mode Apply -Yes -OnlyPR 2109 -MaxReruns 1 -CooldownMinutes 45 -DelaySeconds 30
~~~

**Do not claim the example commands ran.** Do not count a debug-rerun dispatch as native test success or human decision. Do not delete this session before preserving its non-GitHub attachments or explicitly marking their original bytes unavailable.
