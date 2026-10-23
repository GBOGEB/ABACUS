# CODE PURPLE — ABACUS GitHub-first operational handover

**Observation date:** 2026-10-23 (Europe/Brussels). **Primary repository:** GBOGEB/ABACUS. **Consumer repository:** GBOGEB/CODEX. **Mission:** Mission Control Lite, G3A, open-PR PowerShell debug rerun and CI/agent/dashboard lag reconciliation.

**Level:** GITHUB_FIRST_OPERATIONAL; **not** V2_SCHEMA_AND_REPLAY_VERIFIED. This additive snapshot was assembled from live GitHub API, job logs, canonical repository sources and previous chronological chat receipts. GitHub reads are non-atomic and may drift. Full verbatim chat/archive replay and independent byte verification of newly listed artifacts were NOT performed. This document does not grant authorization, security waiver, human approval, merge acceptance, automatic rerun or 14-package closure.

**Template authority:** handover/HANDOVER_MESSAGE_TEMPLATE.md; tools/handover_v2/process_spec.json; CODEX docs/automation/G3A_EXECUTION_CONTRACT.md. Evidence precedence: live branch/PR heads + matching native jobs/artifact bytes > effective rules and human review > dated repository addenda > historical session text.

## 1. Snapshot identity and fidelity

| Item | 23 Oct verified identity / decision |
| --- | --- |
| ABACUS default branch | main = 8c210b8c3768d4252bc2745dab3c60a2fa5795ac; protected=true |
| ABACUS prior main readback | 06b1fdf7aa3b81375d309561422e29e4e7526ef9; two commits behind current snapshot |
| CODEX default branch | main = 3f00b1dac349d2280430f4dc94c2e348713344d6; protected=true at readback |
| ABACUS #1980 | Merged 2026-10-17T17:52:13Z; head b24887d2822e9d3dd2a2281e776bffd4977c5db3; merge e864283660cbd65ca51324be1a813439c351357b |
| ABACUS #2154 | Merged 2026-10-17T17:58:42Z; head f29572b5eb6a0a42685cca6d599aa1e9ef57b322; merge 014217c44ea1c5c2c0e9aa689f3226be7bae1044 |
| ABACUS #2109 | OPEN; PR pull head 0d42735fbb2c41b0b4856744ff416c065a7beffb; main-base 44caccf716a7c20693a2911566289bfc75ea81d9 |
| #2109 event merge | Synthetic pull-request event SHA 4e7138cefc0a6a6d45ef58613e04572c22de1eef; do not substitute for pull head |
| CODEX #1060 | Merged; taxonomy head ea1df6abba98c93b60595dd4765d3119737a91f1; merge 7a1177c4994481361be00dbd4242e295d8151150 |
| ABACUS #2117 | Merged; G3A MIP consumer docs head fee3319624616c636dc6b55605412de9b25cfd4e |
| 14-package root ledger | ABACUS issue #1978 OPEN, P0 HOLD; last historical formal verified-closed count 0/14 (2026-10-14), NOT recomputed against current main |
| Merge admission | HOLD / not established as correctly governed. Observed merged=true records are facts about merges, not proof of independently admissible merge |

**Main drift during this handover:** the first readback returned 06b1fdf7aa3b81375d309561422e29e4e7526ef9. Before write, main advanced to 8c210b8c3768d4252bc2745dab3c60a2fa5795ac. The delta is two commits changing only docs/api/dmaic_metrics.json and docs/api/dmaic_metrics_chart.html. The handover branch was created from the refreshed SHA; no force-push.

**Dashboard provenance caveat:** both generated docs/api assets declare data source SHA 06b1fdf7aa3b while the containing main SHA is 8c210b8. This is a source/publisher SHA mismatch, not demonstrated human, GitHub, code-agent or dashboard failure. Confirm generator input/output contract and observed publish timestamp before attribution.

## 2. Source-owned execution and immutable N-to-N+3 lineage

### Pinned historical observations — do not replace with current-head proof

| Wave / source | Native observation | Historical outcome and boundary |
| --- | --- | --- |
| #1980 d7740c7d95d4e304846bf47c3331ab0f2e1f0075 | MCL run 38624410381 | FAIL: Python SyntaxError in mission_control_lite/core.py; no valid artifact receipt |
| #1980 c0f75f2c26ae39675496c7070c8198c473419a4f | MCL run 38626368234 | Historical SUCCESS; artifact/receipt source identities must be checked, not current evidence |
| #1980 b344a4b... | MCL run 38627296781 | Historical SUCCESS; its receipt was previously observed to name synthetic merge source, not real pull head |
| #2109 d5aeb6b... | CI matrix 39026231334 | B9 changed-line gate red, previously 79% vs 80% floor, population historical |
| #2109 cafd1f7b3b3d10a79a30d69c9389fa11c2878a63 | CI matrix 39028081336 | Earlier 87% changed-line B9 PASS; separate full-CI/A10 controls still needed |
| #2124 12c508a231db4033222c44f54f3ed4293286e580 | 12 workflows | 12/12 native PASS, focused BD telemetry 100% local lines/branches; later merged to #1980 feature |
| #2125 dbe17123e2d40ad51c65f9aea325108f5ea9a54f | CodeQL rerun 39034596235 attempt 2 | FAIL installation API quota; later #1980 exact-head scanner infrastructure recovered; do not propagate historical root status |
| #1980 9536539e88a8aecc5d052c7d63d17cf2396570af | MCL run 39036748739 | Historical 83 executed, 60 summarized (23-test BD log omission), 389/452 lines 86.06%, 169/194 branches 87.11% |
| #2109 2858df0744f01926306b6a7153a7f980a7ab0f2a | Merge of #2109 old head + then-current #1980 | Stale-base ancestry fixed (behind 10 -> 0) at that time; initial queued CI not current proof |
| #2154 f29572b5eb6a0a42685cca6d599aa1e9ef57b322 | 23 workflow records | 18 SUCCESS, 4 FAILURE, 1 CANCELLED on merged PR's final head; NOT proof its merge satisfied all intended gates |

### Current #2109 exact-head native evidence (23 October)

- Real pull head: 0d42735fbb2c41b0b4856744ff416c065a7beffb; synthetic merge event: 4e7138cefc0a6a6d45ef58613e04572c22de1eef.
- Current-head cohort: 24 completed workflows: 19 SUCCESS, 4 FAILURE, 1 CANCELLED.
- Native MCL Testflight run 39933634218, job 120347729473: SUCCESS. Log-produced summary: **196 focused tests**, line 82.5949%, branch 77.8037%, comparison=UNKNOWN, merge_admission=HOLD, source_sha=actual pull head.
- GitHub artifact 12493260342 (mission-control-lite-evidence): reported ZIP SHA-256 93953f2d5d1a22d795db7be4c4a2443951e5bfe4f8220aacd14da81d16bda280, size 21774 bytes, unexpired at readback. **Only GitHub metadata/log was inspected in this handover**; downloaded ZIP digest and every inner receipt byte must still be independently checked before external-byte DoV.
- This is focused Mission Control Lite test coverage; NOT repository-main coverage and NOT the eligible changed-line B9 figure. The 196 count and historical 83 count are different exact-head test populations; no credited fixed-denominator delta.
- #2109 A10 and CodeQL workflows passed on this same head. That cannot clear independent security ratchets, governance, review or main protection.

### Current #2109 failed workflows and first-red hierarchy

| Root owner / exact native evidence | Grounded first red / required action |
| --- | --- |
| Documentation: run 39933634459, job 120347730178 | tools/stack/README.md MD060 table style; changed YAML files and .pre-commit-config.yaml line-length violations. Use the declared markdownlint/yamllint toolchains with exact paths and rerun. |
| Governance: run 39933634221, job 120347729357 | policy-and-inventory: unclassified config-surface-audit.yml; code-quality-pilot.yml has multiple policy owners [12,20,21]; Next.js Pages delivery cluster mismatch; generated docs/ci/WORKFLOW_RATIONALIZATION.md stale. Independently, G3G SUT negative fixtures fail to reject ../secret.py, absolute/drive paths, NUL and duplicate paths. No auto-allowlist or governance relaxation. |
| Full CI: run 39933634343, security job 120347730154 | Bandit new debt in 7 of 61 changed Python files (including scripts/recursive_build.py, tools/triage/config_surface_audit.py); B506:MEDIUM BaseLoader finding among LOW findings. Preserve scanner configuration and triage test-fixture false positives with owner evidence. Do not equate tool failure with a verified vulnerability. |
| Full CI: run 39933634343, code-quality job 120347730452 | Required BLACK and ISORT full scans failed. Separate from successful standalone Format Check. Reproduce exact tool versions/config on disjoint formatting branch and avoid wide unrelated edits. |
| Python 3.10 compatibility: run 39933634343, jobs 120347730622 (macOS), 120347730694 (Windows), 120347787495 (Ubuntu matrix) | tests/test_config_surface_audit.py collection raises ModuleNotFoundError: No module named 'tomllib' on Python 3.10. Establish supported interpreter policy and use tomli compatibility path if 3.10 is required; do not simply omit the test. |
| Python matrix: run 39933634163, job 120347787495 | Primary Python 3.10 compatibility proof fails; proof-completeness job 120350408288 and compatibility-gate job 120350489728 fail downstream. One causal issue, three job manifestations. |

Do not count every red workflow, negative fixture or descendant gate as a distinct resolved root. At least the Python 3.10 tomllib import, policy/path-validation logic, stale generated inventory, security new-debt and quality tooling warrant separate owner dispositions.

## 3. DMAIC, MIP, telemetry and coverage contract

**Define:** ABACUS Mission Control Lite bounded recovery, all-open-PR CLI planning/debug reruns, exact-head telemetry, audit of CI/human/agent/dashboard lag. **Measure:** PR head/main/event SHA, first native job/step, run attempt, coverage numerators/denominators, queue/job clocks, external receipt observation timestamps, missingness. **Analyze:** independent root vs propagated first-red, stale vs missing receipts, source-owned repairs, A-to-B-to-A drift. **Improve:** disjoint smallest root repair with negative tests; one controlled fan-in. **Control:** native exact-head testflight and artifact bytes; current-main recensus; effective ruleset and eligible review; no automatic admission.

**MIP semantics:** Modernize/Innovate/Perpetuate only when a measurable defect exists, bounded owner fix and native DoV. Do not call three sequential pulses three independent trials or assert Six Sigma stability. PCA/BT, rate or confidence intervals are WITHHELD without qualified independent comparable data.

**G3A:** one planned N -> N+3 engagement with P1/P2/P3 sequential DMAIC pulses; reported dispositions are 3 evaluated / x native verified / y independently accepted, never automatically 3 successes. G3W means three independently received waves; read-only scouts can fan out, write paths remain disjoint.

| Coverage or telemetry | Observed | Comparison decision |
| --- | --- | --- |
| #1980 historical focused lines | 389/452 = 86.06% | Historical, not directly comparable to #2109 |
| #1980 historical focused branches | 169/194 = 87.11% | Historical |
| #2109 current focused lines | 82.5949% | Native summary valid on 0d42735f... only; numerator/denominator from ZIP pending |
| #2109 current focused branches | 77.8037% | Scope/config comparison=UNKNOWN |
| #2109 eligible changed-line B9 | UNKNOWN for latest current-head full acceptance | Do not reuse the 87% value from cafd1f7... |
| Broad current ABACUS main line/branch/diff | UNKNOWN | Need current-main native producer and matched denominator |
| Current live GitHub queue p50/p95 | UNKNOWN | Only native created/started/completed timestamps and censoring permit estimates |
| Debug rerun operation on all open PRs | NOT EXECUTED in this handover | Do not claim external Apply or user trigger |
| Verified closed 14-package roots | NOT RECOUNTED; do not credit a new closure | Formal source ledger remains open |

**Lag taxonomy:** SOURCE_TO_NATIVE, NATIVE_QUEUE, WORKFLOW_DAG_DEPENDENCY, JOB_RUNTIME, NATIVE_TO_AGENT_OBSERVATION, NATIVE_TO_DASHBOARD_PUBLICATION and HUMAN_DECISION_PENDING. Missing external timestamp=NO_RECEIPT, not zero. Queued jobs are right-censored; no human/agent blame without causally linked event receipts.

**Recent live generated dashboard:** main 8c210b8 contains docs/api/dmaic_metrics.json and docs/api/dmaic_metrics_chart.html with data source SHA 06b1fdf7aa3b (the immediately preceding main snapshot). Whether that one-source-head difference is acceptable depends on generator contract; not yet proven stale user-facing publication or Pages deployment defect.

**PowerShell controller shipped on main via #2154:**
- scripts/Invoke-AbacusPrDebug.ps1 (PowerShell 7; Plan, Apply, Refresh);
- scripts/abacus_pr_rerun_audit.py (GitHub CLI bridge, exact-head/attempt selection, serial dispatch journal, lag/root diff);
- tests/test_abacus_pr_rerun_audit.py (earlier local 28/28 passing, historical not current-main CI proof);
- docs/ci/ABACUS_PWSH_PR_DEBUG_AUDIT.md (operator contract).
- Default Plan read-only. Apply requires -Yes, accepts -Policy Retryable (default) or explicitly -Policy AllFailed. No merge/review/ruleset/waiver capability. Debug rerun uses GitHub's --failed --debug, not automatic pytest verbosity.
- Audit output: .artifacts/abacus-pr-debug/latest.json, snapshots/*.json, diff.json, diff.md, bd_queue.csv, rerun_actions.json, rerun_journal.json and manifest.json. Report files are local observations, not signed GitHub artifact attestations.

## 4. DAG and SIPOC

| Supplier | Input | Process | Output | Customer |
| --- | --- | --- | --- | --- |
| ABACUS/CODEX, owner/admin and GitHub | PR head, merge/event SHA, native jobs and rules | Refresh -> classify -> lease -> repair/test -> exact-head verify -> DoV | Source-bound immutable observations and guarded candidate repair | ABACUS #1978, #1860, MIP and CODEX taxonomy |
| Native scanners/CI | Bandit, Safety, docs lint, policy, Python matrix, coverage, artifact bytes | Independent first-red and denominator census | Typed security/governance/quality/compatibility evidence | Independent reviewer and source owner |
| Agents and dashboards (read-only consumers) | Source SHA, native receipt, observed_at and optional publish pointer | Source-to-observation joins, freshness and missingness | Lag diagnosis without blame | USER, HTML metrics/PAGES operator |
| External human authority | Real rulesets, eligible reviews, confidentiality/security adjudication | Enforce gates and decide admission | Verified owner decision or explicit HOLD | Main/release control |

~~~mermaid
flowchart TD
  A[Live ABACUS PR and CODEX main identity] --> B[Pin source HEAD, rulesets, denominator and timestamp]
  B --> C[Classify exact-head native job and artifact evidence]
  C --> D1[Python 3.10 tomllib repair]
  C --> D2[Governance/negative path-validation repair]
  C --> D3[Documentation policy/format repair]
  C --> D4[Bandit and Safety independent disposition]
  C --> D5[Black and isort source-owner repair]
  D1 --> E[One owner-leased fan-in and exact-head CI]
  D2 --> E
  D3 --> E
  D4 --> E
  D5 --> E
  E --> F{All native DoV and verified artifact bytes complete?}
  F -->|No| H[HOLD plus attributable BD queue]
  F -->|Yes| G{Effective required checks and eligible human review?}
  G -->|No| H
  G -->|Yes| I[Owner-controlled serial merge and current-main remeasure]
  I --> J[Read-only CODEX/USER dashboard consumption]
~~~

Feedback and historical-reference links are *not* DAG dispatch dependencies. New repair iteration becomes a new N+1 node rather than a live directed cycle. SIPOC-to-SIPOC interface edges connect prior Customer output to next Supplier only when both identities/evidence contracts agree.

## 5. Independent P0 control ledger

| Control | Live evidence / disposition |
| --- | --- |
| ABACUS effective main status and human review | Active ruleset 24494381: deletion, PR and non-fast-forward rules, plus code-quality/copilot rules. Zero required approving reviews; no required_status_checks rule; no last-push approval; no mandatory thread resolution; six bypass integrations. **OWNER CONFIGURATION GAP**; do not claim fully governed merge. |
| CODEX effective main protection | Active ruleset 25554145: required_status_checks rule exists but required-status list EMPTY, zero required reviews, stale dismissal=false, last-push=false, thread-resolution=false. **PROTECTED=true is not full DoV**. |
| A10 | #2109 head A10 SUCCESS, but #1996 remains open for separate restricted-content owner determination and historic file hash acceptance. Never extrapolate one head to other PRs. |
| Bandit / Safety / CodeQL | #2109 CodeQL SUCCESS; full CI Bandit ratchet FAIL, current independent Safety disposition requires job-specific verification. No scanner waiver. |
| External worker token scope | Not authenticated in this handover; negative denials/TTL/replay and real dispatch still require independent receipts. |
| Trusted-byte ingestion | Earlier historical ZIP/digest equality and negative tests recorded; latest #2109 ZIP/inner bytes not independently downloaded and verified in this turn. |
| Reviewer | #2109 has six COMMENTED review submissions but no APPROVED review returned; automations are not independent human approval. |
| Correctly governed main merge | NOT VERIFIED; merged PR statuses cannot substitute for rule+review+status policy at the actual merge timestamp. |
| Cross-repo QPS/MINERVA data | No private QPS or bidder content authorized for publication/transfer to public ABACUS/CODEX. Engineering acceptance not claimed. |

**Policy/authority stop:** new main/head SHA, changed policy hash, missing owner lease, inconclusive byte provenance, secret/controlled-data risk, nonterminal mandatory workflow, budget exhaustion, or a fresh independent red -> stop, append source-bound HOLD receipt, never force-push, bypass, auto-merge or self-approve.

## 6. Canonical TODO / BD queue / DoD / DoV

| Priority | Canonical owner/root | Delivered DoD | Missing DoV and next action |
| --- | --- | --- | --- |
| P0 | #1978 14-package admission | 14 defined packages (4 P0, 4 P1, 4 P2, 2 conditional P3) and MCL source/PowerShell improvements merged | Recompute genuine per-package closures from current main, not PR status; all required gates independently proved |
| P0 | #1860 effective admission | Main now reports protected=true in both repos | Owner/admin restore required check identities, approvals, last push/thread policies, negative RED canary and eligible merge readback |
| P0 | #2109 governance/path safety | Negative tests and inventory existing | Reject path traversal/absolute/NUL/duplicates; classify config-surface-audit.yml and one owner per workflow; regenerate inventory source-owned |
| P0/P1 | #1738 Bandit/Safety | Native source-bound red logs and security report artifacts | Classify seven files with Bandit new debt, including B506 MEDIUM, independently verify Safety, repair and rerun full scanner |
| P1 | #2109 Python 3.10 | Same first-red on three OS/runner cells | Fix tomllib import compatibility or formally change supported matrix with owner and tests; require native 3.10 negative proof |
| P1 | #2109 docs lint | MD060 and YAML exact errors known | Fix named source files, run markdownlint/yamllint and exact-head docs CI |
| P1 | #2109 Black/isort | Full-CI failure measured | Produce minimal formatted diff with tool-version receipt; no broad unrelated rewrite or new exclusions |
| P1 | #2109 B9/main/diff coverage | 196 current-head focused tests SUCCESS | Extract ZIP line/branch denominators; separately measure eligible diff and current-main; compare only fixed scope/config |
| P1 | PowerShell all-open-PR CLI (#2154) | Merged source/scripts and operator documentation, earlier local 28/28 tests | Native PowerShell 7 dry-run then one authorized bounded Apply, journal/readback, current-head ref check, independent remote admission |
| P2 | #1736 dependency snapshots | Dependency Review passed on some exact heads historically | Ensure PR-head dependency snapshot producer and current-head completeness; do not infer no vulnerabilities from missing snapshots |
| P2 | #1929 BD-LDAB/REX lineage | Read-only join contract exists | Distinct causal-root IDs, native evidence join, CODEX consumer, no fake authenticated worker dispatch |
| P2 | DMAIC metrics/PAGES | New docs/api JSON and HTML committed | Source-vs-publisher contract, actual deployed Pages URL/sha, freshness SLA and link/browser QA |
| P3 | Container/Kubernetes/Temporal/Dagster | Candidate architecture documented | Conditional adoption only after bounded Docker, durability or orchestration measurement shows actual value |

**DoD:** source on bounded branch plus focused test and source-blob readback. **DoV:** terminal exact-head same-cohort CI with verified artifact bytes, denominator and accountable owner review. **Merge admission:** effective independent rules + eligible approval + serial authorized merge + terminal current-main recensus. Last historical formal 14-package closure was 0/14 on 14 Oct; **current exact per-package closed count is UNVERIFIED** and must not be carried as fresh 0/14 measurement.

## 7. Copy-ready receiver, QA and retirement rule

**Companion receiver:** handover/mip_20261023/CODE_PURPLE_ABACUS_G3A_DROPIN.md. It must first reread both main branches, #2109, #1978, #1860, ABACUS ruleset 24494381, CODEX ruleset 25554145 and newest exact-head run/job/artifact identities. No mutation before the refreshed snapshot and owner lease.

**Local user preflight (PowerShell 7 + authenticated gh + Python):**

~~~powershell
gh auth status
gh repo view GBOGEB/ABACUS --json defaultBranchRef
pwsh -File ./scripts/Invoke-AbacusPrDebug.ps1 -Mode Plan -OnlyPR 2109
pwsh -File ./scripts/Invoke-AbacusPrDebug.ps1 -Mode Refresh
gh run view 39933634163 --repo GBOGEB/ABACUS --log-failed
~~~

For a separately authorized *transient-only* rerun, execute only after dry-run and exact-head reconfirmation; cap to one initial attempt, preserve 45-minute cooldown. Do not call AllFailed on the full portfolio until security/queue capacity and owner risk are understood.

**Reader QA:** live heads verified at moment of use, historical source vs event identities separated, P1–P3 receipts independently numbered, count denominators and NULL preserved, no claimed user blame, CODEX feedback only read-only, V2 closure WITHHELD absent sealed full archive and replay test. The referenced historical ZIP archives and conversation contents have not been fully recaptured byte-for-byte here.

**Retirement condition:** This dated addendum + DROPIN are durable GitHub pointers, but a conversation is only fully losslessly retired once the authorized transcript and historical generated artifact bytes are preserved or explicitly excluded with a documented completeness limitation, the canonical V2 generator/replay has passed, and the newest PR/main/issue state has been refreshed. No new engineering, security or release credit arises from publishing a handover.
