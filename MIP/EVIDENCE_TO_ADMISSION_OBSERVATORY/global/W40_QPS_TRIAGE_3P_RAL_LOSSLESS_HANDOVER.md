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

