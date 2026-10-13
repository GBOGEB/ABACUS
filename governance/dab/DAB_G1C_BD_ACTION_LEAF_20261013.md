# DAB-G1-C — Burndown and Action Companion (pilot)

Status: **IN PROGRESS; DoD partial; DoV pending**. This document is a
branch-local evidence leaf, **not** a promotion or merge authorization.

## Source authority

- Repository: GBOGEB/ABACUS; exact source main SHA:
  `efdd1ec49ae5dacd9db1a68e9faf944fc5a81239`.
- [DAB census run 38381405952][dab-run]; artifact 11802689708.
  This receipt is linked from the run's Artifacts section.
- Full red total: **2973**; E999: **0**; compatible proposal envelopes:
  **890**; active G1 threshold `<3000`, numeric G1 met, **companion pending**.
- G2 threshold `<2500`: requires >=474 verified net reductions from this
  baseline. G3 threshold `<2000`: >=974 net reductions.
- Existing classification authority: [DAB-HARD #1488][dab-hard].
  Recovery and merge admission: [ABACUS #1860][abacus-admission].

## Action ledger — single-writer discipline

### Governed action records

- **G1C-01 — Freeze exact source census and proposed queue**
  - Owner: DAB reader
  - Status: COMPLETE (run receipt only)
  - Evidence / acceptance: 38381405952; artifact 11802689708

- **G1C-02 — Inspect all 890 proposal envelopes and classify by
  rule/path/risk/authority/duplicate**
  - Owner: DAB scout
  - Status: **PENDING**
  - Evidence / acceptance: Actual binary proposal JSON inspection needed; 890
    is not 890 accepted fixes

- **G1C-03 — Freeze disjoint file ownership and select bounded safe cohort**
  - Owner: DAB planner
  - Status: **PARTIAL**
  - Evidence / acceptance: Single-file exploratory pilot below; pilot matched
    to exact proposal F401-153; further cohort selection pending

- **G1C-04 — Execute one bounded pilot source mutation on independent branch**
  - Owner: Single mutation writer
  - Status: COMMITTED
  - Evidence / acceptance: `tools/generic_3pm_burndown.py`: delete unused
    `math` import; existing earlier CI Pylint log recorded unused import;
    source proposal F401-153 confirmed from archived queue

- **G1C-05 — Exact-head lint, syntax, regression and full DAB recensus**
  - Owner: Verifier
  - Status: **PENDING**
  - Evidence / acceptance: Verify on pilot commit with actual run, compare
    identical scan commands and tool versions

- **G1C-06 — G1 companion DoV, code review, and protection/admission**
  - Owner: Independent reviewer / repo admin
  - Status: **HOLD**
  - Evidence / acceptance: Current effective main protection missing; no PR
    created or merge attempted

- **G2-01 — Industrialized disjoint batches from verified compatible subset**
  - Owner: DAB coordinator
  - Status: **BLOCKED by G1-C DoV**
  - Evidence / acceptance: >=474 verified net findings removed; no waivers

- **G3-01 — Semantic/hard cause remediation and sustainable reduction**
  - Owner: DAB-HARD owner
  - Status: **NOT STARTED**
  - Evidence / acceptance: >=974 verified net findings removed; tests and
    unchanged governance

## Exploratory pilot (not yet counted as reduction)

- File: `tools/generic_3pm_burndown.py`, one deletion: `import math`.
- Exact source DAB proposal `DAB-efdd1ec49ae5-F401-153` identifies line 8
  `F401 'math' imported but unused` (1 finding).
- Disjoint source ownership: exactly one touched file; no other writer may edit
  it before evidence reconciliation.
- Requires: `python -m py_compile tools/generic_3pm_burndown.py`, targeted
  tests/consumers, applicable style/security checks, DAB census against pilot
  SHA, and exact before/after findings for same source/tool/config.
- **Expected local F401 resolution: 1; measured full-repository improvement
  UNKNOWN** pending equal-tool exact-head recensus. This was a confirmed
  current-census proposal; no reduction may be credited yet. No claimed
  coverage delta.

## Companion DoV and promotion rules

Each future batch shall record `source_sha`, `pilot_sha`, touched file set,
rule-specific before/after, introduced findings, test receipts, scanner
versions, review provenance and approved single mutation writer. Maintain
`UNKNOWN` instead of zero when artifacts or tests are unavailable. G1 static
pass does not close G1-C; G2 may be planned but not promoted until G1-C is
independently verified. Governance remains `authority_transfer=false`,
`security_waiver=false`, `formal_credit_delta=0`, `engineering_credit_delta=0`.

## 2026-10-13 artifact-level census reconciliation and Mission Control reuse

Actual archive 11802689708 from [run 38381405952][dab-run] was
inspected: **890/890** proposal envelopes parsed; **750 MEDIUM**,
**140 LOW_MECHANICAL**, **0 HIGH_OR_PROTECTED** envelopes. Value lanes:
**268 P2_MAINTAINABILITY**, **622 P3_STYLE**. Unique proposal-affected
files: **369**. These are classifications, not 890 repairs or 890
independent files. All envelopes bind the frozen source SHA. Counts
apply only to this receipt.

Measured high-volume families (proposal envelopes / enumerated findings): F401
**155 / 330**, F541 **113 / 295**, E402 **211 / 612**, E501 **95 / 943**, E305
**36 / 108**. One file may have more than one family; grouping MUST intersect
all `scope.paths` first. Style E501 dominates raw volume but not engineering
value; prioritisations follow `governance/dab/DAB_FULL_RED_GATES.json` rather
than number-only optimization. `E999=0` is a source census, not a safety
approval.

### Reused assets, not recreated

- **MissionControl dispatch:** [CODEX #977][codex-977] requires an
  authenticated ABACUS-local principal, exact-head lease, allowlisted
  paths, dry-run, idempotency and replay/path locks. CODEX remote mutation
  is **disabled**. Read-only GitHub analysis is not an authenticated
  Crew launch.
- **REX return:** use CODEX
  `federation/rex/REPO_REX_RETURN_TEMPLATE_v1.yaml` and
  [CODEX #989][codex-989], with signature+authority-scope merge. Search
  historical REX first; update recurrence and verification receipts
  rather than minting duplicate signatures.
- **Proposal contract:**
  `governance/proposals/PROPOSAL_COMPATIBILITY_CONTRACT.json`; no new
  schema/producer or parallel Pages deployment.
- **Governed security:** ABACUS [#1860][abacus-admission],
  hard semantic [#1488][dab-hard]; P0 branch enforcement
  remains independent.

### Proposed disjoint worker sets — PLAN ONLY, no dispatch or fix credit

### Proposed disjoint workstream records

- **T0 / pilot — F401 one-file receipt**
  - Representative first path: `tools/generic_3pm_burndown.py`
  - Priority / required action: Verify exact-head F401-153 disappears; syntax,
    targeted test and full census

- **T1 / maintainability — F401 unused imports**
  - Representative first path: `ABACUS-v032/bulk_resolve_github_issues.py`
  - Priority / required action: Confirm import use and dynamic consumers;
    bounded one-file change

- **T2 / maintainability — F541 needless f-string markers**
  - Representative first path: `.github/scripts/security_dashboard.py`
  - Priority / required action: Examine templating intent before mechanical
    rewrite

- **T3 / structure — E402 module-level import placement**
  - Representative first path:
    `ABACUS-v032/execute_full_dmaic_phases_0_to_9_v033.py`
  - Priority / required action: Inspect import side effects/boot order; do not
    bulk move imports

- **T4 / mechanical — E305 blank-line normalization**
  - Representative first path:
    `ABACUS_V21_DEPLOYMENT_PACKAGE/local_deployment_runner.py`
  - Priority / required action: Mechanical max 12 findings / 3 files, but start
    one-file proof

- **R1 / integration — Ruff and Black/isort overlapping paths**
  - Representative first path: Read-only cross-tool delta
  - Priority / required action: Freeze per-file combined lint/tool semantics
    before assigning any write

These representative paths are **different**, but full path-set disjointness
for expansion is not proven. A planner shall assign a unique per-path lock
across all families and existing workers; one serial mutation writer across the
campaign. A read-only Crew/Scout can report a proposal; it cannot publish
execution evidence for an unlaunched worker.

### Preconfiguration → test flight → DoV → REX

1. **Preconfig:** confirm source SHA, executable/test versions, exact DAB
   policy, source receipt digest, dry-run plan, file locks,
   side-effect/authority class and intended REX signature. Record any source
   drift and stop.
2. **Preflight:** use existing DAB proposal compatibility validation; verify no
   duplicate/in-flight BD ownership, no unsafe import/semantic transforms, no
   protected E999 regression, and exact file allowlist. Distinguish Ruff
   (possibly overlapping rules), selected Flake8 CI critical surface, full
   Flake8 debt census, and Black/isort scanners.
3. **Testflight:** `python -m py_compile` on touched Python, selected unit
   tests, command-equivalent Flake8 on frozen baseline and candidate, Ruff
   where configured, Black/isort where applicable, Bandit for material semantic
   changes, Python 3.10/3.11/3.12 roles and recorded skips. Do not waive
   failures.
4. **Measurement:** compare per-rule/per-path before/after + introduced
   findings, same scanner/config/version, current exact SHA, branch coverage
   and diff coverage when meaningful. For mechanical-only changes, explicit
   verified NON_REGRESSION or justified NOT_APPLICABLE rather than invented
   numeric gains.
5. **DoV/REX:** bind run/job/step/artifact and reviewer evidence; update
   existing REX signature if one exists. Only then close BD action. Admit G2
   only after G1-C companion proof and effective protected-main admission; no
   automatic merge.

**Pilot status at this update:** source F401 = 1 confirmed; actual target
full-census delta = UNKNOWN; targeted regression = NOT RUN; Crew authenticated
launch = NOT PROVEN; G1-C DoV pending; G2 on HOLD.

### Evidence links

[dab-run]: https://github.com/GBOGEB/ABACUS/actions/runs/38381405952
[dab-hard]: https://github.com/GBOGEB/ABACUS/issues/1488
[abacus-admission]: https://github.com/GBOGEB/ABACUS/issues/1860
[codex-977]: https://github.com/GBOGEB/CODEX/issues/977
[codex-989]: https://github.com/GBOGEB/CODEX/issues/989
