# CODE PURPLE / GoGREEN / EVERRED scheduled DAG — 17 October 2026

Status: DRAFT. Read-only, non-admitting, inactive until admitted onto main.
The canonical BD/LDAB ledger stays at ABACUS issue #1929. P0 recovery is #1860.
CODEX Mission Control #975 and execution gate #977 remain independent.

## Operating cadence, UTC

The proposal uses one GitHub Actions cron: 05:23 UTC Monday–Saturday.
Brussels wall time is 07:23 during CEST, 06:23 during CET.
Queue delays may change the actual start. The workflow runs on the admitted
default branch only; merely opening this PR does NOT activate the schedule.

| Days | Method | Stage selection | Execution |
| --- | --- | --- | --- |
| Monday, Wednesday, Friday | GoGREEN | N0 + N3 | Native negative and reverse tests if capacity eligible |
| Tuesday, Thursday | EVERRED | N0 + N1 + N2 | Four-read-only-scout, 253-run metadata census; gg_MATH handoff |
| Saturday | CODE PURPLE | N0 + N4 | Review-only P0 receipt and test checks; never self-approval |
| Sunday | None | None | No scheduled workflow |
| Explicit manual input | GoGREEN, EVERRED, CODE PURPLE | Named partial slice | Same capacity and source checks |
| Explicit manual input and full acknowledgement | Full | N0..N5 | Read-only all slices; no merge or security waiver |

Full mode is never automatically scheduled. Manual full acknowledges an
expensive observational testflight, NOT waiver, reviewer or merge authority.

## Capacity and retry rule

Acquire GitHub repo queued and in-progress counts through the Actions API;
the two reads are not atomic. The maximum allowed queue is 40 and the
maximum running count is 12. If either exceeds the cap, or either is
unavailable, emit a cold plan and skip native/test work. UNKNOWN does not
mean zero. This is conservative under the observed 653 queued/8 running
snapshot reported by PR #2097, which is historical, not a live recensus.

Source mutation workers without a lease: 0.
Read-only native reader bound: 4.
No automatic rerun-failed, rerun-all, branch rebasing, ruleset modification,
review approval, canonical ledger write, or main merge is performed.
Rerun scheduling belongs to the separately governed #2097 planner.

## Directed graph

The graph JSON and HTML projection include:

N0 Exact-source census -> N1 EVERRED native first-red -> N2 gg_MATH handoff
N0 Exact-source census -> N3 GoGREEN negative and reverse testing
N1 and N3 -> N4 CODE PURPLE independent admission review
N4 -> N5 protected main and recurrence verification

N4 is a READ-ONLY reviewer preparation stage even when N1 or N3 have
outstanding evidence. The unmet prerequisite must remain visible, and the
stage cannot confer PASS. N5 is a reserved, non-admitting evidence stage.

## SIPOC and source ownership

S: native GitHub source/attempt/job metadata; canonical EVERRED evidence.
I: exact source SHA, UTC date, non-atomic queue, selected mode and run IDs.
P: N0 first-page census, N1 full-page paginated metadata, N2 math provider
handoff, N3 positive/negative/reverse tests, N4 non-compensating review,
N5 exact-main recurrence after a separately authorized merge.
O: hashed immutable plan, typed DAG nodes and edges, SIPOC JSON, user-facing
review HTML, and a ledger PROPOSAL that cannot acquire root authority.
C: BD/LDAB #1929, DOW, gg_MATH, Mission Control, admission #1860.

## gg_MATH provider bridge and mathematical interpretation

The bridge produces a GBOGEB/gg_MATH worker envelope using the canonical
gbogeb.skill.invoke.v1 schema, with math/PCA/ADVANCED, exact input matrix
digest, and authority_transfer=false. It does not claim the gg_MATH runner
was launched or that a new PCA fit was accepted.

Exploratory historical offline projection from 16 October N0:
73 proxy source-head groups with at least one sampled failed association,
19 workflow dimensions, p/n = 0.2603. Mean-centered PC1 explained 22.47%;
PC2 14.65%; PC3 13.96%. PC1's strongest positive loadings were ABACUS v032
and the ABACUS Python matrix. Effective rank was approximately 10.03.
In a deterministic 500-resample head-proxy bootstrap, PC1 absolute loading
congruence had median 0.925, 5th percentile 0.745. Those are descriptive
sensitivity diagnostics, not independently calibrated confidence intervals.

The historical input is a non-atomic first-page PR sample. Correlated workflow
fan-out and source-head aliases compromise independent-trial inference.
No PCA component is a proved shared causal root. Standardized correlation PCA
has different loadings and must be assessed as a sensitivity check.

## Outputs and verification

The scheduler writes pulse-plan.json, pulse-dag.json, pulse-sipoc.json,
review.html and sha256.json, plus ledger-proposal.jsonl with explicit
NOT_CANONICAL_EVENT. The gg_MATH bridge emits incidence matrix, worker request,
status with provider_executed=false, and SHA hashes. The GitHub workflow uploads
these files as read-only artifacts. Raw private security job logs are excluded.

Positive, reverse and negative tests cover queue saturation, unavailable
capacity, forged security/approval, mismatched source SHA, manual-full guard,
no misleading zero, dependency graph, deterministic receipts and false root
promotion. Full main and diff coverage remain separately UNKNOWN until their
actual native numerator and denominator are observed.

Three distinct gates must pass independently before eventual default-branch
deployment: technical exact-head CI and negative tests; native queue/load
control and source owner lease; P0 governance, A10, Safety/Bandit, effective
branch protection and independent review. New workflow policy registration
must be performed by its authorized governance owner. No threshold is relaxed.

Entry points:
- GitHub schedule (only after governed merge of this PR chain)
- workflow_dispatch with selected partial mode or acknowledged full
- Local read-only Python script cbd_scheduled_pulse.py
- Canonical provider handoff cbd_ggmath_bridge.py

Disposition: ADMISSION_HOLD; authority_transfer=false; security_waiver=false.
