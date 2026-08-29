# QPS RTM/OFFER — DMAIC coverage and completion scorecard

Status: **CONTROL / IMPROVEMENT CHECKPOINT — NO REQUIREMENT CLOSURE**

## Purpose

Drive the lowest-scoring programme dimensions upward together instead of continuing isolated five-RTM batches.

## Baseline at start of this wave

| Dimension | Baseline | Primary defect | Wave-1 target |
|---|---:|---|---:|
| Canonical SSOT / authority integrity | 97/100 | Minor presentation/state propagation gaps | >=97 |
| BT/PCA prioritisation | 90/100 | Rank used too narrowly as review boundary | >=92 |
| Bidirectional RTM<->OFFER propagation | ~50/100 | Seed review did not consistently fan out to full canonical neighbourhood | >=75 |
| Governed manual RTM coverage | 169/722 = 23.4% minimum | Lower-ranked dependent items under-used | >=25% via graph-aware review |
| Live-state completeness | 23 individually visible | Earlier T0 work absent | Backfill all 43 dedicated T0 items |
| Granular Contractor evidence disposition | Early/intermediate | Positive evidence missing, especially LKT | Increase by neighbourhood, not isolated row |
| Closure readiness | Low | Evidence/disposition not yet transformed into closure-ready packs | Define explicit readiness fields |
| Formal requirement closure | 0 claimed | Intentionally conservative | Remains evidence-driven; no numeric target |
| End-to-end programme completion | ~37/100 | Propagation/evidence/closure lag governance engine | >=42 after cross-cutting waves |

## DMAIC

### Define

The review unit is no longer a single ranked RTM. It is a **governed dependency neighbourhood** initiated by a ranked RTM seed.

### Measure

Maintain separate counters for:

1. canonical population;
2. individually governed/reviewed RTMs;
3. dependency-neighbourhood covered RTMs;
4. granular Contractor-evidence dispositions;
5. Owner dispositions;
6. verification-ready requirements;
7. formally closed requirements.

Never collapse these into one misleading percentage.

### Analyse

Highest-value defects identified this session:

- T0 work was governed but absent from the live state;
- RTM->OFFER lookup was performed, but OFFER->all-linked-RTM fan-out was incomplete;
- same-family / parent-child engineering dependencies were not consistently propagated;
- absence of bidder exception could visually resemble compliance if not explicitly controlled;
- BT/PCA rank was incorrectly acting as a review boundary rather than a seed selector;
- closure readiness was not separately measured from review/evidence coverage.

### Improve — ordered waves

**Wave 1 — graph + T0 backfill + metrics**
- backfill 43 dedicated T0 items;
- establish canonical direct/supporting and separately-labelled derived dependency edges;
- expose OFFER neighbourhoods;
- add explicit programme metrics and scorecard.

**Wave 2 — dependency-expanded evidence review**
- take the next exact-v24 ranked seed;
- fan out through all canonical OFFER neighbours and relevant same-family RTMs;
- review both bidders against the Owner baseline;
- dispose several lower-ranked items in the same engineering pass.

**Wave 3 — positive-evidence recovery**
- prioritize `NE`, `PE`, `NO_EXCEPTION_ON_FILE`, and conditional-equivalence states;
- bind exact LKT/ALAT proposal, compliance, FAT/SAT and product evidence;
- reduce low-information states without weakening authority.

**Wave 4 — closure-readiness packs**
- per requirement: Owner baseline, exact Contractor commitment, deviation disposition, objective evidence, verification method, residual action, owner, due/gate;
- mark `READY_FOR_GOVERNED_CLOSURE_REVIEW` only when all required fields exist;
- formal closure remains a separate governed decision.

**Wave 5 — control / live HTML**
- display individually governed vs dependency-covered vs evidence-complete vs closure-ready separately;
- show OFFER neighbourhood and edge class;
- show BT rank/PCA dimension as prioritisation metadata only;
- prevent green/compliant rendering from missing exception data.

### Control

Acceptance criteria for future waves:

- every ranked seed performs bidirectional RTM<->OFFER fan-out before manual scope is frozen;
- canonical and derived edges are never conflated;
- lower-ranked dependent RTMs can be reviewed early but retain their exact-v24 rank metadata;
- bidder evidence never changes requirement wording;
- no requirement closure from ranking, grouping, missing exceptions or review coverage;
- live coverage is monotonic unless a governed supersession explicitly removes/reclassifies an item;
- accepted-release HOLD remains independent.

## Headline KPIs

Use two headline scores:

- **Governance / analytical engine maturity** — baseline ~89/100.
- **End-to-end evidence-to-closure programme completion** — baseline ~37/100.

The purpose of the next waves is to raise the second score without degrading the first.
