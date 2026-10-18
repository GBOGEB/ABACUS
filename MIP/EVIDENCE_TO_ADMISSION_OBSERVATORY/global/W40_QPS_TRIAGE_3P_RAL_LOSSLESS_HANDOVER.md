# CODE PURPLE / QPS TRIAGE — W40 3P-RAL + P3R/3PM lossless handover

**Control class:** SOURCE-BOUND CONTINUITY CANDIDATE; append-only, non-promoting.  
**Capture:** 19 October 2026, from GitHub run/branch observations on 18 October 2026.  
**Wave:** W40 continuation of W29→W39, not a newly accepted global release.  
**Execution selector:** `EXECUTION_WAVE_TYPE=PARTIAL`; 3PR → conditional MIP → 3PC; one 3P3 only after independently demonstrated propagation.  
**Global decision:** `MERGE_ADMISSION=HOLD`, `GLOBAL_CONTROL=false`, `authority_transfer=false`, `formal_credit_delta=0`, `engineering_credit_delta=0`, `security_waiver=false`.

## 0. Read these, in this order, before continuing

1. Fresh exact HEAD for each of `GBOGEB/ABACUS`, `GBOGEB/CODEX`, `GBOGEB/cryoplant-project` **and** their affected `hold/` branches; their head SHAs below are *observations*, not permanent latest truth.
2. QPS canonical `handover/qps_recursive/GLOB.yaml` → `SESSION_CLOSE_CURRENT.yaml` → `QTG_CURRENT.yaml` → `QTG_CURRENT_EXTENSIONS.yaml` → `controls/QPS_TRIAGE_CONTROL_PLANE_v1.yaml` → `controls/QPS_TRIAGE_BT_PRESSURE_CURRENT_v1.yaml` → child contract/repo-deep map.
3. QPS method: `triage/w258/QPS_W258_3P_RAL_DMAIC_KPI_TAXONOMY_v0.1.md`, `controls/QPS_3P_RAL_DMAIC_CURRENT_v0.1.yaml`, `handover/qps_recursive/QPS_3P_RAL_DMAIC_CYCLE_TEMPLATE_v1.yaml`, and **separately** `controls/W56_EXECUTION_TAXONOMY_P3R_3PM_v0.1.yaml`.
4. This file → `W40_QPS_TRIAGE_LOSSLESS_CONTROL.json` → `W40_DROPIN_NEXT_AGENT.md` → `ledger.json`, `index.template.html`, `render_global.py`, `test_global_rollup.py`, `qa_playwright.py`, `index.html`.
5. Native W39 proof: [Actions #39170632775](https://github.com/GBOGEB/ABACUS/actions/runs/39170632775), job `117802739785`, head `fc6ea65f2d0322f1a98fde323310c09990522709`, attempt 1.
6. Owner issue hooks: ABACUS [#1991](https://github.com/GBOGEB/ABACUS/issues/1991) and [#2087](https://github.com/GBOGEB/ABACUS/issues/2087); CODEX [#977](https://github.com/GBOGEB/CODEX/issues/977); QPS [#1379](https://github.com/GBOGEB/cryoplant-project/issues/1379) and [#1904](https://github.com/GBOGEB/cryoplant-project/issues/1904).

**Restart precedence:** current QPS pointers and controlled child sources outrank this handover's old QPS snapshot; fresh repo HEAD and exact native logs outrank old GitHub counts. Never reconstruct missing authority from chat narrative.

## 1. Identity and source authority snapshot

| Lane | Last read main SHA | Candidate / owner branch | Governing role |
|---|---|---|---|
| ABACUS / DOW | `2687f2bcb0705027eefe04df789365d6c9970678` | `hold/cbd-w39-gov-dov-qa-20261018` (W40 later unqualified edits) | Runtime, independent evidence, integration admission |
| CODEX / KEB | `843020d9e85b404ac10a94bbc1a1283865d1d57e` | `hold/cbd-w39-abacus-dov-source-nav-20261018` at `9d879a7e11bb9f6e85a316a51724963da77819eb` | Semantic/provenance consumption |
| QPS child | `fc07545c3986181a1b837c0eb7ff9a8393fd4058` | `hold/cbd-w39-abacus-dov-source-nav-20261018` at `e487ec2e2f9929b6f2ad4e74665d2c66f2d98297` | Final engineering/contractual ACCEPT/REJECT/DEFER |

Prior immutable W38 integration: [ABACUS PR #2278](https://github.com/GBOGEB/ABACUS/pull/2278), merge SHA `ccc07c76a506a66fc20cbe821ef0ec4c0a3fe064`; **unqualified** because review/mandatory checks did not protect it. W39 qualified *candidate* head `fc6ea65f2d0322f1a98fde323310c09990522709` is separate from today's W40 taxonomy/handover branch descendants. W40's eventual native result must use its *new* exact head.

The QPS `SESSION_CLOSE_CURRENT` pointer was recorded for a September 29 session. Its queue/priority snapshots are **historical**. Recent three-repo GitHub issue counts do not rewrite QPS `QTG_CURRENT` or any confidential engineering source.

## 2. Evidence classes that must remain separate

- **OBSERVED_NATIVE:** exact head + workflow run/job/attempt + executed steps, typed terminal result and artifact identity. W39 native PASS is in this class.
- **SOURCE_BOUND_STATIC:** committed source and deterministic classifications, but not yet a terminal new-head run. W40 taxonomy source additions remain here until native QA returns.
- **DERIVED_PROJECTION:** HTML, graphs, counters, exported ledger, AI narrative, screenshots. Cannot promote engineering facts.
- **OWNER_DEFER / UNKNOWN:** absent independent consumer, selected QPS source return, security proof, review, RED canary or Pages identity. Never render missing values as zero or green.
- **PROMOTED_STATE:** requires the appropriate authority's explicit ACCEPT. Neither ABACUS nor CODEX can promote child QPS OFFER/RTM/negotiation/compliance truth.

## 3. Measured wave lineage without destructive overwrites

| Wave | Observed engineering fact | Source / result | Admissible scope |
|---|---|---|---|
| W29 | W75/W64 behavioral tests initially 64/64 per Python 3.10/3.12 cell but missing coverage receipt due to pytest-cov file selector; fail-closed evidence gate | ABACUS PR #2250; run 39149390636; correction `312042de13212319c0e85c9d012fa43747508e4e` | Instrumentation first red, **not** accepted coverage gain |
| W30 | Local observatory 108/108; local combined ~90%, collector ~88%; separate source cohort | Local observatory result, no canonical-main credit | Local observatory only |
| W31/32 | Four-source focused 660/723 opportunities, W82 164/215 | run 39159837402 | Frozen comparable focused denominator |
| W34 | One `_programme_stop` variable-shadow root caused 3 failing assertions; source correction recovered tests 201/201 and 697/723 focused coverage | first red run 39161484760; repaired run 39161560713; commit `c51e6b9d112fb9a4e5fecd55189f94680b832503` | One root candidate, not three |
| W35 | Two targeted CLI cases; 203/203, W82 211/215, four families 707/723 | run 39161760486, head `6f51404c121283c56c92cfbabd064f0e63815883` | Local target achieved |
| W36 | Added seven exact workflow classifications; static 198/198, but generated rationalization report stale | run 39161993224 on `a26436955450b8cd27668bffa2a8dc7db458d392` **FAIL** | No governance PASS |
| W37 | Controller records `next_pilot=None`; native 203/203, 707/723 | run 39162185592, head `b69c8e376e25c9345e379a14c371149ba7443adb` | Stop broad same-family coverage |
| W38 | Three-repo global DOV HTML/JSON, navigation and GET-only refresh; premature automatic merge | PR #2278 / merge `ccc07c76...` | Engineering merge not admitted |
| W39 | New current-main workflow census: 201 definitions, three new source-owned classifications; generated report copied byte-for-byte, visual defects repaired | run 39170632775 exact branch head `fc6ea65f...` **PASS** | Native governance+HTML proof on candidate, no protected merge |
| W40 | 28 QPS TRIAGE / 3P-RAL / P3R / 3PM source-linked taxonomy leaves, machine continuity and session handover | `hold/cbd-w39-gov-dov-qa-20261018`; W40 tests **pending on new head** | Derived navigation only, credit delta 0 |

### Focused coverage invariant

W75 = 219/221; W64 = 123/125; W81 = 154/162; W82 = 211/215. Total = **707/723 = 97.79%**, up from 660/723. Residual uncovered = 16 of same cohort, down from 63 (**74.6% reduction in uncovered**). All 4/4 families exceed local 95%; **stop same-source broad coverage expansion**. The W39 258 governance unit tests and 14 HTML contract tests have a different denominator from the W37 203 focused tests and must never be added to the 723 coverage opportunities. Current-main canonical B0 uplift remains UNKNOWN.

## 4. Exact W39 native QA and package receipt

[Run #39170632775](https://github.com/GBOGEB/ABACUS/actions/runs/39170632775) / job `117802739785` / attempt 1 / exact head `fc6ea65f2d0322f1a98fde323310c09990522709`: 258 governance unit tests PASS, 201/201 workflow definitions classified, zero duplicate patterns, byte-identical native-generated `docs/ci/WORKFLOW_RATIONALIZATION.md`, 14 dashboard contract tests PASS, 3/3 Chromium responsive QA viewports (1440×1000, 1280×800, 390×844). Page/console errors 0, document horizontal overflow 0. Browser refresh test used **19 mocked public GET requests**, no authenticated real consumer API return and no mutating requests. Native evidence artifact **#12152052335**, ZIP SHA256 `e4156bdcf3f6a07b2ee8c15debeb79dd93117e165f4c633f470eafc8476b7404`.

The W38 defects corrected by W39 were: truncated EVERRED source SHA, now-deleted W38 branch URL, a double-escaped immutable-source regex, unsafe-eval Playwright assertion incompatible with deliberate CSP, and evidence-type table overflow. These are source/presentation repairs; **no child engineering score, Pages publication or security waiver follows**.

The W39 successful result is immutable historical evidence. A later W40 commit **invalidates it as qualification for the newer HEAD**; never label W40 PASS from W39 tests.


## 5. Global DOV / issue and PR burndown — denominator-safe

Last complete three-repo GitHub search snapshot (18 October 2026):

| Source repository | Open issues | Closed issues | Open PRs | Closed unmerged PRs | Merged PRs |
|---|---:|---:|---:|---:|---:|
| ABACUS | 38 | 267 | 15 | 137 | 1,814 |
| CODEX | 11 | 34 | 3 | 33 | 1,030 |
| QPS / cryoplant-project | 57 | 72 | 0 | 144 | 1,688 |
| **All** | **106** | **373** | **18** | **314** | **4,532** |

These are ordinary GitHub search populations as observed, **not** accepted causal-root or engineering-compliance counts. QPS native `QTG_CURRENT` / `BT_PRESSURE_CURRENT` still carry older 50/50 issue-state snapshots, and their autonomous BDQ denominators may differ from the 57 ordinary open GitHub issues. Treat this as a candidate recensus/reconciliation task, not silent replacement of either authority.

There are two material deduplication exemplars:
- W34 controller root: **three failing assertions, one parameter-shadowing source defect**; correction has native PASS, but no separately authorized root-closure ceremony.
- W38 matrix: **six Windows/macOS failing job manifestations, one `networkx` missing-test-dependency root candidate**; owner dependency PR [#2283](https://github.com/GBOGEB/ABACUS/pull/2283) merged as `2246c7bd3a9bda6a3d43b9a9116cb7088cfbcc88`. Terminal broad matrix proof against new current-main SHA, accepted root fingerprint and non-recurrence are separate gates.

Compute accepted-root convergence only from source-fingerprinted independent root dispositions. No `closed PR = fixed root`, `merged PR = governed admission`, `all jobs queued = healthy`, or `graph rendered = consumer returned` shortcuts.

## 6. QPS TRIAGE authority and true method monikers

**QPS TRIAGE is the federated moniker for QPS + DOW + KEB**, not a synonym for QPS alone. `H1_QPS` / `GBOGEB/cryoplant-project` retains child engineering SSOT and final ACCEPT/REJECT/DEFER. `H2_KEB` / CODEX supplies semantic/provenance challenge. `H3_DOW` / ABACUS supplies independent runtime/evidence. `H4_QPS_TRIAGE` composes their graph/controls but transfers no child authority. Zod validates contracts inside TRIAGE; it is not another decision authority.

**3P-RAL = Three-P Recursive Assurance Ladder** (QPS W258). Its operators are:
- **3PR** — Refresh, Probe, Rank: recover main/pointers, find material first-red and rank noncompensating owners.
- **MIP** — Modernize, Innovate, Perpetuate: conditional structural correction and repeated durability proof.
- **3PC** — Prepare, Prove, Commit: source-bound bounded transaction; `Commit` is withheld if human, security, checks or negative canary are not authorized.
- **3P3** — Preserve/Pin, Propagate/Penetrate, Prove/Promote: conditional **after** local DoV and an independent propagation gap.
- **3P*** = selector wildcard; `3P#n` = maturity-cycle ordinal; `3Pxn` = repetition multiplier. None is executable or credit-bearing alone.

**P3R = Pulse Run and Roll-up** is a different execution topology: PRE → **3PM** → POST → Roll-up → Propagate → Fan-out. **3PM = Three Pulse Method**: P1 Produce, P2 Challenge, P3 Re-enter (ACCEPT/REJECT/DEFER by named owner). Do not rename P3R to 3P-RAL or treat `3PM-P3` as permission to merge.

Use the versioned source-native [3P-RAL cycle template](https://github.com/GBOGEB/cryoplant-project/blob/fc07545c3986181a1b837c0eb7ff9a8393fd4058/handover/qps_recursive/QPS_3P_RAL_DMAIC_CYCLE_TEMPLATE_v1.yaml) to bind real mission, trigger, authority, five DMAIC components, KPI denominators and multiclock before claiming a completed maturity cycle. This W40 mission is a **PARTIAL, local continuity cycle**, not a new globally assigned `3P#n`.

The global QPS graph can carry recursive feedback. A *single* bounded execution DAG and lineage DAG must remain acyclic; temporal events are append-only. This preserves the Golden Thread without graph self-authorization.

## 7. Current QPS external and veto boundaries (preserve, do not restart)

The latest retrieved authoritative QPS `BT_PRESSURE_CURRENT` says **ordinal priority, NOT fitted Bradley–Terry**. Noncompensating vetoes:
- `#943 + SELECTED_SAFETY_SOURCE_SET`: source and safety authority still withheld.
- W155/W199: first actual current externally controlled source return takes precedence when present.
- W191 actual Windows/OneDrive Master_Input, #1379 v6 release, W152 RTM-661/664/680/681, root-input legs and PVPS same-point remain independently sourced/deferred.

Preserve `#923 = CLOSED_COMPLETED_RUNNER_ADMISSION_RECOVERED` and Golden Thread GT_BDQ_0…9 as PASS/CLOSED from their native QPS pointer, unless **new contradictory executed evidence** materializes. A recurrence in ABACUS CI does not reopen QPS #923.

QPS [#1904](https://github.com/GBOGEB/cryoplant-project/issues/1904) remains a candidate advisory REX/triage receiver. Acceptance requires exact producer receipt, independent QPS review, typed severity/evidence and an explicit current child disposition; no REX propagation from a green ABACUS dashboard. The QPS Pages/release front [#1379](https://github.com/GBOGEB/cryoplant-project/issues/1379) remains separately governed.

## 8. Source-controlled presentation and moniker leaves

Root: `MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/global/` in ABACUS.

| Component | Role | Generator/restart authority |
|---|---|---|
| `ledger.json` | Three-repo observational roll-up plus typed moniker dictionary | Derived candidate; source counts/head must be refreshed and pinned |
| `index.template.html` | Authored global dashboard, SPINE, search/filter taxonomy card/leaves | No direct engineering mutation |
| `index.html` | Generated HTML projection | Regenerate only from template + ledger |
| `render_global.py` | Deterministic generator and fail-closed source checks | `python render_global.py --check` |
| `test_global_rollup.py` | Zero-authority/denominator/URL/taxonomy contract | `python -m unittest -v test_global_rollup.py` |
| `qa_playwright.py` | Three-viewport and interaction QA | Tests simulated public read-only GitHub responses, not remote semantic receipts |
| `W40_QPS_TRIAGE_LOSSLESS_CONTROL.json` | Machine continuity state and restart edges | New source-controlled control projection, not QPS child SSOT |
| This handover + `W40_DROPIN_NEXT_AGENT.md` | Human-recoverable current state | Both read after QPS GLOB/QTG pointers |

HTML taxonomy **cards contain expandable leaves** and search/filter. The 28 leaves are grouped into 3P-RAL method, P3R/3PM execution hierarchy, QPS TRIAGE federation, DoD/DoV evidence, and CODE PURPLE operational aliases. Each leaf declares expansion, meaning, STOP, zero credit/authority transfer and immutable source URL. `CBD!` and other programme labels do **not** claim an invented official expansion. The QPS canonical glossary takes precedence; this is an explanatory navigation projection.

CODEX branch `hold/cbd-w39-abacus-dov-source-nav-20261018` adds a link to the exact **W39 native-qualified ABACUS source** in `docs/index.html` without modifying its portal SSOT tile generator. CODEX native CI for that branch was not established in the prior session. QPS branch with the same scoped suffix adds a source-only W39 entry in `governance/QPS_DASHBOARD_FEDERATION_LAUNCH_REGISTRY_v1.md`; a QPS stranded-push guard passed on the branch, but this is **not** QPS Pages, engineering or final child acceptance. Do not merge the two branches simply because ABACUS HTML passed.

## 9. P3R / 3PM and 3P-RAL current cycle state

**PRE — inherited-state mop-up:** retrieved current QPS root/current pointer, audited ABACUS/CODEX/QPS heads, W36 failed report, W39 exact native evidence, W38 premature merge and missing safeguards. Prior accepted defects are not silently reopened.

**3PM-P1 Produce:** ABACUS source now contains governed workflow classification, generated report, repaired dashboard and 28 candidate taxonomy leaves. Machine continuity JSON, this file and the drop-in are additive. Independent child authority and status are untouched.

**3PM-P2 Challenge:** W39 precursor passed 258 governance and 14 dashboard tests plus three Playwright viewport/refresh tests, but this proof is bound **only** to precursor SHA `fc6ea65f...`. W40 taxonomy and handover need fresh exact-head CI and new test denominators (17+ dashboard tests). Explicitly challenge spoofed leaves, unpinned URLs, browser CSP, responsive overflow, no-op QPS promotion and JSON/HTML parity.

**3PM-P3 Re-enter:** **DEFER** until ABACUS administrator protection, mandatory exact-head security/quality, independently eligible review and server-side blocked RED canary. CODEX provenance consumption and QPS final child disposition are separate. No unconditional auto-merge.

**POST / ROLL-UP:** once native W40 qualification is terminal, record exact run/job/attempt, artifact hashes, screenshot QA, stdout first-red and any new root. Bind source hashes in an append-only issue comment. Do not rewrite W39 historical evidence. Re-run main only after a properly governed merge; then refresh 3-repo counts and DOV.

**3P-RAL state:** local method/presentation cycle progressing, independent consumption and C3/C4 stability not earned. `useful_material_delta=true` for taxonomy and handover functionality, `formal_credit_delta=0`. Current STOP for broad W75/W64/W81/W82 tests is maintained.


## 10. Recursive evolution, stop and retrigger

Do not increase runners simply because N+1 is possible. `STOP_LOCAL` applies where all four families exceed 95%, the eligible cohort is unchanged, and no distinct evidence or regression predicate exists. The programme retains separate governance, causal-root, source/safety, human review and federation gates.

A new pulse is admissible only on a material exact-source first red, new critical behavior/denominator, new independent consumer, negative canary, safety/source return, or changed authority contract. Start with **one** disjoint source owner and worker. Increase 1→2→4 only when complete native job-population queue p95, artifact yield, source stability and worker lease budgets are measured. Unknown runner capacity = read-only observation, not geometric fan-out.

A global CONTROL claim requires a predeclared multi-clock stability streak, accepted deduplicated roots, server-enforced required checks/reviews and RED canary, terminal security, and independent CODEX/QPS receipts. A plateau N+1=N over consecutive waves is a legitimate STOP or reallocation signal, not a reason to generate redundant runs.

## 11. Next non-compensating owner actions

| Priority | Owner and action | Required evidence | Present decision |
|---|---|---|---|
| P0 | ABACUS native owner: qualify latest W40 head; isolate new first-red | Exact SHA/run/job/attempt, taxonomy tests, Chromium three-viewport result, artifact SHA256 | Pending W40 HEAD |
| P0 | GitHub admin: enforce required contexts, >=1 eligible human approval, stale/last-push approval, resolved threads, blocked RED canary and no bypass actors | Effective ruleset readback + negative server canary | Ruleset #24494381 observed 0 approvals / 0 checks |
| P0 | A10/security owners: preserve independent CodeQL/Bandit/Safety and confidentiality gates | Terminal exact-head security findings + owner disposition | UNKNOWN for W40 |
| P1 | CODEX/KEB: consume pinned producer source and return own semantic receipt | Source SHA, workflow run/attempt, evidence digest, KEB status | Source-only navigation branch |
| P1 | QPS child: reconcile QTG/BT pointers, source/safety veto and independent child return | Exact QPS main, child ACCEPT/REJECT/DEFER, no score transfer | DEFER |
| P1 | Admission owner: serial PR only after all gates, then distinct post-main verification | Authorized reviews/checks/merge SHA/main SHA | HOLD |
| P2 | Mission Control: deduplicate closed/unmerged issues/PRs, causal roots, supersession and 7/21/90-day temporal edges | Stable cohort IDs, typed edges and source hashes | Candidate |

No score across rows compensates for a red in another row. Stop specifically completed local W75/W64/W81/W82 expansion while retaining these independent blockers.
