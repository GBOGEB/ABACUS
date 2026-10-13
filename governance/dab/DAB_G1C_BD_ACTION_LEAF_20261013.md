# DAB-G1-C — Burndown and Action Companion (pilot)

Status: **IN PROGRESS; DoD partial; DoV pending**. This document is a branch-local evidence leaf, **not** a promotion or merge authorization.

## Source authority

- Repository: GBOGEB/ABACUS; exact source main SHA: `efdd1ec49ae5dacd9db1a68e9faf944fc5a81239`.
- [DAB census run 38381405952](https://github.com/GBOGEB/ABACUS/actions/runs/38381405952), [artifact 11802689708](https://github.com/GBOGEB/ABACUS/actions/runs/38381405952/artifacts/11802689708).
- Full red total: **2973**; E999: **0**; compatible proposal envelopes: **890**; active G1 threshold `<3000`, numeric G1 met, **companion pending**.
- G2 threshold `<2500`: requires >=474 verified net reductions from this baseline. G3 threshold `<2000`: >=974 net reductions.
- Existing classification authority: [DAB-HARD issue #1488](https://github.com/GBOGEB/ABACUS/issues/1488); recovery/admission: [#1860](https://github.com/GBOGEB/ABACUS/issues/1860).

## Action ledger — single-writer discipline

| ID | Action | Owner | Status | Evidence / acceptance |
|---|---|---|---|---|
| G1C-01 | Freeze exact source census and proposed queue | DAB reader | COMPLETE (run receipt only) | 38381405952; artifact 11802689708 |
| G1C-02 | Inspect all 890 proposal envelopes and classify by rule/path/risk/authority/duplicate | DAB scout | **PENDING** | Actual binary proposal JSON inspection needed; 890 is not 890 accepted fixes |
| G1C-03 | Freeze disjoint file ownership and select bounded safe cohort | DAB planner | **PARTIAL** | Single-file exploratory pilot below; membership in the 890 candidate envelopes **NOT VERIFIED** |
| G1C-04 | Execute one bounded pilot source mutation on independent branch | Single mutation writer | COMMITTED | `tools/generic_3pm_burndown.py`: delete unused `math` import; existing earlier CI Pylint log recorded unused import; current census matching pending |
| G1C-05 | Exact-head lint, syntax, regression and full DAB recensus | Verifier | **PENDING** | Verify on pilot commit with actual run, compare identical scan commands and tool versions |
| G1C-06 | G1 companion DoV, code review, and protection/admission | Independent reviewer / repo admin | **HOLD** | Current effective main protection missing; no PR created or merge attempted |
| G2-01 | Industrialized disjoint batches from verified compatible subset | DAB coordinator | **BLOCKED by G1-C DoV** | >=474 verified net findings removed; no waivers |
| G3-01 | Semantic/hard cause remediation and sustainable reduction | DAB-HARD owner | **NOT STARTED** | >=974 verified net findings removed; tests and unchanged governance |

## Exploratory pilot (not yet counted as reduction)

- File: `tools/generic_3pm_burndown.py`, one deletion: `import math`.
- Prior CI Pylint evidence identified `unused-import` for this path (historical, not proof of current Flake8 census membership).
- Disjoint source ownership: exactly one touched file; no other writer may edit it before evidence reconciliation.
- Requires: `python -m py_compile tools/generic_3pm_burndown.py`, targeted tests/consumers, applicable style/security checks, DAB census against pilot SHA, and exact before/after findings for same source/tool/config.
- **Expected/measured improvement: UNKNOWN**. Do not infer a Flake8 F401 count or subtract one; this prior evidence was Pylint only. No claimed coverage delta.

## Companion DoV and promotion rules

Each future batch shall record `source_sha`, `pilot_sha`, touched file set, rule-specific before/after, introduced findings, test receipts, scanner versions, review provenance and approved single mutation writer. Maintain `UNKNOWN` instead of zero when artifacts or tests are unavailable. G1 static pass does not close G1-C; G2 may be planned but not promoted until G1-C is independently verified. Governance remains `authority_transfer=false`, `security_waiver=false`, `formal_credit_delta=0`, `engineering_credit_delta=0`.
