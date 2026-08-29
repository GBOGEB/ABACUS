# QPS Wave 2 — graph multiplication and backlog evidence harvest

Status: **DEPENDENCY EXPANSION + EXISTING-EVIDENCE HARVEST — NO REQUIREMENT CLOSURE**

## Multiplication metric

The exact-v24 frontier seed is **RTM-197**. Under the corrected review method, BT/PCA chooses the entry point only; it does not cap the manual-review scope.

Depth-controlled canonical expansion gives:

1. Seed: RTM-197 — **1 RTM**.
2. First-hop OFFERs: OFFER-17 direct and OFFER-13 broad/contextual.
3. OFFER-13 canonical RTM neighbourhood: RTM-141..152, RTM-193..197, RTM-236..257, RTM-263..267 — **44 unique RTMs**.
4. Second-hop narrow OFFERs reached inside that neighbourhood include OFFER-15, OFFER-16, OFFER-17, OFFER-19 and OFFER-20.
5. OFFER-20 adds supporting/context RTM-258..262 — **5 additional unique RTMs**.

Therefore the depth-2 canonical reach is **49 unique RTMs from one ranked seed**.

**Coverage multiplication factor = 49 / 1 = 49× graph reach.**

This is *reach*, not compliance, review completion or closure.

## Existing-evidence harvest

Returned evidence summaries already exist for five narrower canonical families within this 49-RTM neighbourhood:

| Family | Canonical RTMs | Unique RTMs | Existing returned evidence | Immediate flagged backlog |
|---|---|---:|---|---|
| OFFER-15 Compressor Noise | RTM-141..147 | 7 | ALAT: 13 matched matrix rows; LKT exception lane contains no flagged exception | ALAT: RTM-142 Suggestion; RTM-146 Suggestion + Deviations; RTM-147 Deviation |
| OFFER-16 Compressor Configuration / Limits | RTM-148..152 | 5 | ALAT: 10 matched rows; LKT has explicit clarification/deviation | ALAT: RTM-148 Deviation; RTM-149/150/152 Suggestions. LKT: compressor-scope clarification + turndown deviation |
| OFFER-17 Preliminary 3D Layout | RTM-193..197 | 5 | ALAT: 31 matched rows; LKT no flagged exception in exception-only lane | ALAT: RTM-194, RTM-195, RTM-197 Suggestions |
| OFFER-19 WSH Design / Layout | RTM-239..248 | 10 | ALAT: 40 matched rows; LKT no flagged exception in exception-only lane | ALAT: RTM-239, RTM-240 and RTM-247 Suggestions |
| OFFER-20 Helium Leak / Loss | RTM-252..262 | 11 | ALAT direct-family rows + explicit flags; LKT has explicit deviations | ALAT: RTM-252/253 Suggestions; RTM-254 Deviations. LKT: no warranty of unverifiable leak rates; EN 13185 replacement position; refusal of specified Table-16 leak rates |

These five evidence-bearing families cover **38 unique RTMs** of the 49-RTM graph neighbourhood.

**Evidence-harvest ratio = 38 / 49 = 77.6%.**

This means more than three quarters of the graph-reached neighbourhood already has bidder-returned evidence summaries available for manual disposition; it should not remain dormant backlog waiting for individual scalar BT priority.

## Immediate backlog execution order

### A. High-value explicit deviations first

Promote these to individual Owner disposition immediately because the returned evidence already contains a substantive Contractor delta:

- RTM-146 and RTM-147 — compressor noise/vibration family;
- RTM-148 — compressor configuration/operating limit;
- RTM-254 — helium leak detection/standard basis;
- RTM-255/Table-16 family via LKT leak-rate refusal where the exact requirement relationship is confirmed;
- OFFER-20 family-level standards-equivalence issue: EN 13185 vs ISO 20485 must be treated as a governed technical equivalence question, not silent substitution.

### B. Clarification / suggestion backlog next

- RTM-142;
- RTM-149, RTM-150, RTM-152;
- RTM-194, RTM-195, RTM-197;
- RTM-239, RTM-240, RTM-247;
- RTM-252, RTM-253.

These are not automatically deviations, but each already has returned evidence and therefore qualifies for Owner disposition now.

### C. Evidence-present but no exception flagged

All other RTMs inside the five evidence-bearing families move from generic `DEPENDENCY_COVERED_PENDING_DISPOSITION` to:

`RETURNED_EVIDENCE_PRESENT / POSITIVE_SUBSTANTIATION_REVIEW_PENDING`.

For LKT, `NO_EXCEPTION_ON_FILE` remains lower-information evidence and can never be promoted to compliance merely because the exception-only register is silent.

## Remaining uncovered 11 RTMs

Within the 49-RTM depth-2 neighbourhood, the following are not yet represented by one of the five narrow evidence summaries above:

- RTM-236..238;
- RTM-249..251;
- RTM-263..267.

These remain `DEPENDENCY_COVERED_PENDING_EVIDENCE_RECOVERY` and become the targeted evidence-recovery backlog after the 38 already-evidenced items are harvested.

## DMAIC effect

### Define
Review scope is now the governed dependency neighbourhood, not the scalar rank row.

### Measure
- ranked seed: 1;
- graph reach: 49;
- evidence-bearing RTMs already available: 38;
- evidence-harvest ratio: 77.6%;
- uncovered targeted recovery: 11.

### Analyse
The previous bottleneck was not absence of evidence but **failure to propagate already-existing evidence through the canonical crosswalk**. This created artificial backlog.

### Improve
Disposition the 38 evidence-bearing RTMs family-by-family, starting with explicit deviations; only then spend effort recovering evidence for the remaining 11.

### Control
Keep five distinct states:

1. `DEPENDENCY_COVERED_PENDING_EVIDENCE_RECOVERY`;
2. `RETURNED_EVIDENCE_PRESENT_REVIEW_PENDING`;
3. `GOVERNED_INDIVIDUAL`;
4. `EVIDENCE_COMPLETE / CLOSURE_READY`;
5. `CLOSED`.

Graph expansion or evidence presence never implies compliance or closure.

## Authority boundary

Contract/Addendum II remains authoritative; RTM remains the governed numbered projection; OFFER remains an evidence interface; bidder statements do not redefine the requirement; derived dependencies remain labelled derived; accepted-release HOLD is unchanged and independent.
