# W37 — Exact reviewer union and coverage pulse

The W36 fail-closed hold can now be resolved at RTM-ID level.

## Exact union

The prior human-review cohort contains 39 RDA RTMs plus 13 GBO review-presence RTMs, with 7 RDA↔GBO overlaps: **45 unique RTMs**. DKO contributes seven RTMs — RTM-437, 438, 439, 441, 442, 443 and 447 — and none overlap the RDA or GBO cohorts.

| Metric | Before DKO | W37 exact union | Delta |
|---|---:|---:|---:|
| Unique human-reviewed RTMs | 45 | **52** | **+7** |
| Global RTM review coverage | 6.23% | **7.20%** | **+0.97 pp** |
| Relative coverage uplift | — | **+15.56%** | versus 45-node baseline |
| Reviewer→RTM evidence edges | 52 | **59** | **+7** |
| Formal engineering closure | 70/90 | **70/90** | 0 |
| Negotiation resolution | 0/20 | **0/20** | 0 |

The edge count remains larger than the unique-node count because RDA and GBO legitimately coexist on seven RTMs. Multi-reviewer evidence is preserved; only the population numerator is deduplicated.

## DKO domain effect

The DKO RTM family is in **Design & Fabrication**, whose current controlled denominator is **35 RTMs**. DKO alone now provides named source-supported review evidence on **7/35 = 20.0%** of that domain.

This is deliberately described as the **DKO share** of Design & Fabrication, not total human-review coverage for the domain. The earlier 45-node cohort still needs to be projected through the same domain taxonomy before total per-domain coverage can be stated.

## Coverage interpretation

Global human-review coverage has genuinely moved, but remains sparse: **52/722 = 7.20%**. This is a review/evidence metric, not a compliance metric. The strongest new concentration is CAD/model/spatial integration; the largest remaining denominator fronts are Subsystems (202), Control & Interlock (86), Acceptance Testing (66), Buildings & Utilities (53), Process & Functional (49), Quality Assurance & Control (45), Technical Documentation (28) and Global Design Criteria (24).

Those domains are **next projection targets**, not yet ranked as least-reviewed: their exact reviewed numerators must be calculated before making that claim.

## PCA / BT consequence

DKO materially enriches the Design & Fabrication feature space but the global reviewer-feature coverage is only 7.20%, far below the 60% reviewer/explicit-hold readiness control target. Do not recompute the reviewer/compliance PCA yet.

BT should instead use the exact-union result to drive the next catch-up wave: project all 52 reviewed RTMs through the domain taxonomy, calculate domain coverage/gap, and prioritize high-denominator low-density fronts while retaining the DKO P1 negotiation gates.

## Control rule

**Reviewed ≠ compliant.** No formal engineering or negotiation score moves from W37. Closure requires supplier/owner evidence and canonical re-entry.