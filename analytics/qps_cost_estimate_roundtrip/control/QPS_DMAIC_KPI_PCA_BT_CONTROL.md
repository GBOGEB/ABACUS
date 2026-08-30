<!-- markdownlint-disable MD013 MD060 -->
# QPS COST_Master DMAIC / KPI / PCA / Bradley-Terry Control

Control: GOV-001  
Scope: remaining Phase 2–4 execution after Phase 5 source-side closure  
Release disposition: **HOLD** until physical Windows/OneDrive acceptance gates pass.

## 1. Measurement boundary

Do not collapse source/control readiness and physical execution into one completion percentage.

Current tracker counts:

| Phase | Prepared / completed controls | Remaining physical execution gates | Control readiness | Verified physical execution |
|---|---:|---:|---:|---:|
| Phase 2 – clean build/evidence | 11 | 10 | 100% of listed preparation controls | 0/10 = 0% |
| Phase 3 – immutable publication | 6 | 9 | 100% of listed preparation controls | 0/9 = 0% |
| Phase 4 – Office assimilation | 5 | 12 | 100% of listed preparation controls | 0/12 = 0% |
| Phase 5 – hardening | source-side closed | 0 | 100% | source-side complete |

The 0% physical-execution values are not failure scores. They mean that the corresponding real-machine gates have not yet produced retained proof receipts.

## 2. DMAIC state

### DEFINE

Goal: complete the controlled chain

`verified evidence -> clean Build A/B -> QA -> semantic equality -> immutable OneDrive release -> raw hash parity -> review copy -> normalized review change -> PR -> successor release`.

Primary CTQs:

1. no unverified evidence enters the build;
2. Build A and B are semantically identical;
3. QA status is PASS;
4. published OneDrive bytes equal local release bytes;
5. immutable release is not modified by Office review;
6. every accepted Office edit returns through normalized source and a new PR/release.

### MEASURE

Primary KPIs:

| KPI | Definition | Target / gate |
|---|---|---|
| Evidence verification ratio | verified required evidence / required evidence | 8/8 = 100% |
| Evidence hash mismatch count | SHA-256 mismatches | 0 |
| Evidence size-pending count | required files without verified byte size | 0 |
| Clean-build success ratio | successful independent builds / attempted clean builds | 2/2 |
| Semantic parity | identical semantic manifests / compared output classes | 4/4 = 100% |
| QA pass ratio | passed required QA gates / required QA gates | 100% |
| Formula-error count | explicit formula errors / broken references | 0 |
| Stale-reference count | unresolved stale source/release references | 0 |
| Release artifact parity | OneDrive files matching local SHA-256 / release files | 100% |
| Unexpected release file count | destination files outside manifest | 0 |
| Review isolation | review copies physically separate from immutable release | 100% |
| Review assimilation closure | approved review items completing review->source->PR->rebuild | 100% |
| HOLD escape violations | ACCEPTED without full acceptance evidence | 0 |

Secondary operating metrics:

- successful run count;
- failed run count;
- current consecutive-success streak;
- last successful build/release ID and timestamp;
- time since last successful run;
- backlog count by phase and change class;
- backlog age P50/P90/max;
- catch-up delta = current open actions minus trailing mean open actions;
- reverse-load score for underdeveloped factors.

### ANALYZE – descriptive PCA

A 13-action x 6-factor ordinal matrix (0–3) is maintained for prioritization using:

- CriticalPath
- EvidenceIntegrity
- Reproducibility
- ReleaseAssurance
- ReviewAssimilation
- Readiness

This is **descriptive PCA**, not inferential statistics. The matrix is expert-scored and small; loadings are used to compress correlated priority factors, not to claim statistical confidence.

Current standardized PCA:

- PC1 = **61.22%** explained variance
- PC2 = **19.97%**
- PC3 = **10.46%**
- cumulative PC1–PC3 = **91.65%**

Interpretation after sign orientation:

- **PC1 – execution/evidence readiness:** high positive loading on CriticalPath, EvidenceIntegrity, Reproducibility and Readiness; negative against late review-assimilation work.
- **PC2 – release assurance:** dominated by ReleaseAssurance, separating publication/parity/release-receipt work from early evidence binding.
- **PC3 – reproducibility/review coupling:** emphasizes Reproducibility and ReviewAssimilation, useful for successor-release work.

PCA is therefore used to identify *families* of work and reverse-load neglected dimensions. It does **not** override hard dependencies.

### ANALYZE – Bradley-Terry priority model

For operational ranking, each action receives an additive utility score:

`u = 0.30 CriticalPath + 0.20 EvidenceIntegrity + 0.20 Reproducibility + 0.15 ReleaseAssurance + 0.05 ReviewAssimilation + 0.10 Readiness`

Pairwise Bradley-Terry preference is:

`P(i > j) = exp(u_i) / (exp(u_i) + exp(u_j))`.

The normalized `exp(u)` share is reported only as a ranking aid; it is not a probability that an action will succeed.

Current unconstrained BT ranking:

| Rank | Action | u | normalized BT share |
|---:|---|---:|---:|
| 1 | A3 Verify evidence hashes/sizes | 2.70 | 12.64% |
| 2= | A6 Run QA | 2.55 | 10.88% |
| 2= | A7 Compare semantic manifests | 2.55 | 10.88% |
| 4 | A4 Promote registry VERIFIED | 2.50 | 10.35% |
| 5 | A5 Build A/B | 2.40 | 9.37% |
| 6 | A2 Bind evidence root | 2.35 | 8.91% |
| 7= | A9 Verify OneDrive parity/receipt | 2.25 | 8.06% |
| 7= | A13 Rebuild/publish successor | 2.25 | 8.06% |
| 9 | A1 Clone/fetch repositories | 2.15 | 7.29% |
| 10 | A8 Publish immutable release | 1.75 | 4.89% |
| 11 | A12 Assimilate review to source PR | 1.50 | 3.81% |
| 12 | A10 Open separate review copy | 1.25 | 2.97% |
| 13 | A11 Register/classify review changes | 0.80 | 1.89% |

**Dependency rule:** BT ranks urgency/value, but executable order is constrained. A3 cannot run before A1/A2; A4 cannot precede A3; A6/A7 cannot precede A5; A8/A9 cannot precede Phase-2 closure; A10–A13 cannot precede the immutable release/review copy.

### IMPROVE – dependency-aware action order

Current executable critical path:

1. **A1** clone/fetch ABACUS, CODEX, cryoplant-project and DOCX_RTM_Automation under `C:\DEV\REPOS`.
2. **A2** bind the actual governed evidence root.
3. **A3** run evidence verifier; record exact size and SHA-256 for all eight sources.
4. **A4** promote private registry to VERIFIED only after 8/8 match.
5. **A5** run independent Build A and Build B outside Git/OneDrive.
6. **A6** run formula/render/structural/lineage/stale-reference QA.
7. **A7** compare semantic manifests and resolve all unexplained drift.
8. **A8** publish immutable release to a new `10_RELEASES/<release-id>` folder.
9. **A9** prove local vs OneDrive raw SHA-256 parity and emit release/acceptance receipts.
10. **A10** create/open separate `20_WORKING_REVIEW/<release-id>` copy.
11. **A11** register and classify actual review changes.
12. **A12** assimilate approved changes into normalized source and open PR.
13. **A13** repeat clean build and publish successor release.

### CONTROL

Each execution attempt must append a retained receipt with at least:

- run/build/release ID;
- timestamp;
- CODEX + ABACUS + private-overlay source SHAs;
- evidence-registry status/hash;
- success/failure status;
- failed gate and diagnostic when failed;
- repair commit/PR where applicable;
- rerun result;
- semantic hash set;
- artifact manifest hash;
- local/OneDrive parity result;
- disposition HOLD / ACCEPTED / REJECTED / DEFERRED.

A failed test is retained as evidence; it must not be overwritten by the repaired rerun.

## 3. Reverse-loading / catch-up control

PCA factors with below-mean achieved execution are treated as reverse-loading targets. Priority is increased for an underdeveloped factor only when its predecessor dependencies are satisfied.

For each factor `f`:

`catchup_f = mean(execution_completion_all_factors) - execution_completion_f`

Positive values indicate underdevelopment. Track both absolute percentage-point gap and standardized gap (`z`) after at least five comparable execution snapshots exist. Before enough snapshots exist, report raw gaps only; do not manufacture a stable z-score.

Current qualitative reverse-load order is:

1. **EvidenceIntegrity / execution proof** – first physical deficit; blocks everything downstream.
2. **Reproducibility** – Build A/B and semantic comparison.
3. **ReleaseAssurance** – immutable publication and raw parity.
4. **ReviewAssimilation** – intentionally last because it requires a real review copy.

## 4. TODO state machine

Allowed states:

`BLOCKED -> READY -> RUNNING -> FAILED -> REPAIRING -> RETEST -> PASSED -> CLOSED`

Every FAILED item must retain:

- failure timestamp;
- failed command/gate;
- minimal diagnostic;
- repair link/commit;
- retest timestamp;
- final status.

No item jumps from FAILED to CLOSED without a RETEST/PASSED record.

## 5. Immediate next TODOs

| ID | Action | State now | Exit evidence |
|---|---|---|---|
| A1 | Clone/fetch four repositories | READY | exact repo SHAs + clean working-tree receipt |
| A2 | Bind governed evidence root | BLOCKED by A1/local PC | resolved path stored privately; no confidential path in public pointer |
| A3 | Verify 8 evidence files | BLOCKED by A2 | 8/8 SHA-256 + exact size; zero mismatch |
| A4 | Promote registry VERIFIED | BLOCKED by A3 | merged private registry update |
| A5 | Build A/B | BLOCKED by A4 | two successful independent build receipts |
| A6 | Full QA | BLOCKED by A5 | 100% required gates PASS |
| A7 | Semantic compare | BLOCKED by A5 | zero unexplained semantic differences |
| A8 | Publish immutable release | BLOCKED by A6/A7 | new release folder + manifest |
| A9 | Raw parity + acceptance receipts | BLOCKED by A8 | 100% raw hash parity + schema-valid receipts |
| A10 | Office review copy | BLOCKED by A9 | physically separate review folder |
| A11 | Review change register | BLOCKED by A10 | all requested edits registered/classified |
| A12 | Source assimilation PR | BLOCKED by A11 | normalized source PR, no binary SSOT mutation |
| A13 | Successor build/release | BLOCKED by A12 | new immutable version with old release preserved |

## 6. Programme KPI interpretation

The control plane is mature; the execution plane is the backlog. Therefore the key KPI for the next pulse is **not more source files or PR count**. It is the number of physical gates converted from BLOCKED/READY into retained PASS receipts without weakening the HOLD rule.
