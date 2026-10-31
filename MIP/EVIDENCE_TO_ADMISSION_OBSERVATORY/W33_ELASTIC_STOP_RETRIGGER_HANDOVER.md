# CODE PURPLE W33 — Elastic scaling, local stop and evidence-bound retrigger

**Authority:** engineering candidate on isolated branch, **not** merger/admission authority.  
**Restart source:** \`MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/w33_verified_focused_input.json\`.  
**Implementation:** \`elastic_wave_governor.py\` + \`test_elastic_wave_governor.py\`.  
**Native proof source:** [W31/W32 exact-head Actions run 39159837402](https://github.com/GBOGEB/ABACUS/actions/runs/39159837402).  
**Associated issues:** [coverage #1991](https://github.com/GBOGEB/ABACUS/issues/1991), [causal roots #1929](https://github.com/GBOGEB/ABACUS/issues/1929), [governance #2087](https://github.com/GBOGEB/ABACUS/issues/2087).

## Verified N baseline, not a claim for W33 tests

At \`dccefcd7bffc39b75224f3c6ec0afd60768c417c\`, the two native Ubuntu Python 3.10/3.12 jobs passed 118/118 each (236 successful executions). Both strict evidence-upload steps succeeded; corresponding artifact IDs: 12148546623 and 12148119116.

**Focused four-source module numerator/denominator (not B0):**

| Family | Covered | Eligible | Remaining | Measured scope |
| --- | ---: | ---: | ---: | --- |
| W75 stability | 219 | 221 | 2 | Python 3.10 and 3.12 |
| W64 reverse pressure | 123 | 125 | 2 | Python 3.10 and 3.12 |
| W81 repair outcomes | 154 | 162 | 8 | Python 3.10 and 3.12 |
| W82 semantic diversity | 164 | 215 | 51 | Python 3.10 and 3.12 |
| **Total** | **660** | **723** | **63** | **91.29% focused** |

Interpretation: W75, W64, W81 each satisfy the **95% local coverage-expansion target**; W82 needs at least **205/215** covered opportunities for that target, i.e. **+41** over its current numerator on the identical denominator. W82 is the next source family, not an invitation to run a huge new matrix.

**New W33 testflight candidate:** reuse the **existing** two-Python-cell W29–W32 workflow, appending existing canonical W82 tests and the new elastic-controller tests. No new workflow file, gate exclusion or production-logic change. Source is written to a branch only; no PR is opened while the effective protection rule lacks required reviews/checks and prior draft PRs have been merged before all native checks completed. Thus **W33 native test result = UNKNOWN** and no W33 coverage gain is credited.

## Scale controller as a finite-state machine

Unit of progress = **distinct terminal exact-head source-changing engineering pulse** (full SHA, run/attempt, hashed artifact, independent test slice, fixed cohort/config, native receipt). A repeated GET, rerun of the same unchanged code, or polling is **not** a new wave.

**Fast response** (descriptive AIMD/hysteresis, not inferred probabilistic performance):

| Condition | Read-only lanes | Native proposal |
| --- | --- | --- |
| Job population or fresh queue p95 UNKNOWN | 1 | 0 |
| Queue p95 >900s | max(1, floor(previous/2)) | 0 |
| Artifact evidence yield <100% | max(1, floor(previous/2)) | 0 |
| Queue p95 in (600,900]s | hold prior lane limit | At most available owner/runner slots |
| Queue p95 <=600s AND 2 fresh, comparable, positive coverage transitions AND new source/run | double prior lanes up to 8 | min(capacity, disjoint leases, owners, active families) |
| A capacity-recovery retrigger | do not ramp directly to 8 | 1 pilot maximum |

**Caps are proposals**, not permissions to start agents or relax branch rules. Source-owner writes remain separately authorized; automatic dispatch and automatic merge are always false. Unknown available slots, outstanding jobs or source lease count imply no native proposal. A source with a terminal first-red is routed to a targeted repair before scale.

**Local stop** occurs when local coverage >=95%, or when 3 consecutive exact-cohort zero-gain **transitions** are proven from 4 distinct qualified source-changing pulses. Target stop -> local CONTROL monitoring; plateau below target -> pivot to another source/angle, NOT global completion or Six Sigma.

**Local re-entry** is event-driven and idempotent. The eligible event kinds are critical new first-red, measured coverage regression, genuinely new eligible opportunities, change in acceptance contract, capacity recovery and proven governance repair. A source family is reopened only for a material family-specific event; queue recovery and governance repair alone do **not** reopen already-covered source families. Events must carry exact SHA, causal fingerprint and native terminal proof; a matched opportunity change must have a signed nonzero delta. Consumed fingerprints suppress repeated retries and A->B->A aliases. The first re-entry is one small negative-path pilot, never immediately 8 runners.

**Global stop** is **not** the conjunction of high local percentages alone. Require all declared families at target; explicit 0 **accepted** critical roots remaining (not ordinary issue closure); 100% required evidence artifacts; attestation for every declared repository; correctly enforced required checks, eligible human independent review, blocked RED canary and security; >=8 independent stable control observations with no detected special cause. This is a *provisional operational-control gate*, not a six-sigma process-capability calculation. In the current input the global gate is **false**, governance HOLD and root denominator UNKNOWN.

## Reproducible W33 execution

\`\`\`bash
python MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/elastic_wave_governor.py \
  --input MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/w33_verified_focused_input.json \
  --out /tmp/code-purple-w33-elastic-decision.json

python -m pytest -q MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/test_elastic_wave_governor.py

python -m pytest -q \
  tests/test_w82_semantic_diversity_diagnostic.py \
  tests/test_w32_w82_semantic_permutation.py \
  MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/test_elastic_wave_governor.py
\`\`\`

The existing \`.github/workflows/w29-disjoint-frontier-coverage.yml\` now includes the canonical W82 and governor test files in its existing two native matrix jobs; it retains fail-closed JUnit JSON/XML/hash checks. Exact W33 native proof is required before a coverage increment or completion receipt.

## Next legitimate pulses (stop early if unsafe)

1. **W33-P1 selective W82:** verify the union with existing canonical tests and whether 51 uncovered W82 opportunities decrease. Require both Python jobs, same full commit SHA, coverage JSON/XML, JUnit and manifest. If no new covered element, do not increase runners for an identical selector.
2. **W33-P2 policy qualification:** evaluate the controller with fresh, *complete* run/job population clocks and true 100%-yield receipts. Exercise 1->2->4->8 by independent synthetic tests only until real matching terminal pulses justify an actual higher lane recommendation. Never count synthetic evidence as native execution.
3. **W33-P3 differentiated next frontier:** upon accepted W82 target/plateau, switch from source coverage to governance first-red, federation provenance or new independent untested artifact type. Preserve independent source leases, parent/child receipts and repository main / PR denominator separation.
4. **CONTROL re-entry:** trigger only for a genuinely new SHA/frontier/root, passed governance/queue recovery with pending work, security regression, or externally changed acceptance contract. A quiet control period is not a job request.

**Current guard:** \`MERGE_ADMISSION=HOLD\`, \`AUTOMATIC_DISPATCH=false\`, \`GLOBAL_CONTROL=false\`. Remaining governance: effective ruleset 24494381 previously read with required approvals 0 and no required status checks; authorization, negative canary and review not demonstrated. No waiver, root closure, CODEX Crew launch, REX or merge claim.

## Progress receipt and handover fields

For every new pulse preserve \`family, source_sha, base_sha, run_id, attempt, job_ids, first_red_signature, source_slice, cohort_digest, configuration_digest, covered, eligible, missing, test_passed, test_failed, test_skipped, artifact_ids, artifact_sha256, queue_population_count, queue_p95, evidence_yield, independent_lease, root_disposition, admission_status, previous_wave, predicted_next_bounds, actual_delta, stop_reason, retrigger_key\`. If missing, write \`null\` and retain source URL. Do not silently substitute zero, reuse an old main SHA, or classify a queued run as a negative outcome.

## G3A / MIP scope accounting

- **N−1** = original W29 test-only positive assertions but coverage receipt failure (128/128 assertions; both jobs FAIL); no coverage credit.
- **N** = W29 repaired exact head, 128/128 success, 342/346 focused, distinct two-family source cohort.
- **N+1** = W31/W32 four-family observed head, 236/236 success, 660/723 focused; **not directly comparable to 342/346 for delta**.
- **N+2 candidate** = W33 small W82 canonical-test union and elastic governor branch, **not yet native qualified**.
- Next source wave only if actual fresh receipt and capacity checks pass; stay at one readonly observation lane otherwise.


### W33 controller hardening after initial staging

Fresh scaling requires **A->B->A stable current source identity** and a **complete queue job population bound to that same exact terminal run ID and source SHA**; neither is assumed from the older W31/W32 run. Geometric growth may only arise from an *active, not already-target-reached* source family's two new comparable gain transitions. A stale queue population or repeated evaluation cannot double the budget.

Global CONTROL additionally requires exact-current-main canonical B0, complete native artifact-type and downstream-consumer attestations, and the independently governed rules/negative canary/security/roots/repo-stability conditions. The W33 source-type receipt illustrates 4 types x 2 native cells = 8 native-file observations, but consumer attestation is UNKNOWN; 8/8 native ≠ federation acceptance.

\`wave_metrics.py\` now appends \`elastic_controller\` to the pre-existing observatory receipt, with \`measurement_freshness=HISTORICAL_FOCUSED_SOURCE_HEAD_NOT_EXACT_CURRENT_MAIN\`. This is not an execution/replacement of the legacy measured B0 signal.

## W34/W35 terminal local-stop checkpoint (18 Oct 2026)

After the W33 staged controller, the explicitly bounded single-cell branch testflight [run 39161484760](https://github.com/GBOGEB/ABACUS/actions/runs/39161484760) found one implementation root (artifact count shadowed artifact-census object), producing three failed tests. Source-owner correction at `c51e6b9d112fb9a4e5fecd55189f94680b832503` passed [run 39161560713](https://github.com/GBOGEB/ABACUS/actions/runs/39161560713) 201/201 cases, focused four-module 697/723. W35 two CLI negative/canonical cases at tested head `6f51404c121283c56c92cfbabd064f0e63815883` passed [run 39161760486](https://github.com/GBOGEB/ABACUS/actions/runs/39161760486) 203/203, four-source **707/723 (97.79%)**; W82 **211/215 (98.14%)**, plus +47 vs W31 W82 164/215. Thus W75 219/221, W64 123/125, W81 154/162, W82 211/215 are **4/4 >=95% local target** and broad same-slice test expansion STOPS.

`w33_verified_focused_input.json` now pins this W35 terminal source head (not current main), exact run identity, artifact ZIP hash, four native artifact-file families and 203 true test cases. The observatory's controller should return `next_pilot=null`, 4 local coverage CONTROL decisions, 1 read-only observation lane and 0 native scale proposals while A->B->A main/head and complete queue p95 remain UNKNOWN. Global CONTROL/REX/accepted-root/merger admissions remain HOLD. A material new failed source path or scoped regression alone reopens a *single* targeted pilot. Separate governance-only W36 branch `code-purple/w36-governance-seven-workflow-census-20261018` addresses 7/198 otherwise unclassified workflow definitions; its native report and inherited first-reds remain independent.

The four-source 707/723 measurement is focused, not canonical ABACUS main coverage; 1-cell W35 evidence is not retrospective 2-cell current-head acceptance.
