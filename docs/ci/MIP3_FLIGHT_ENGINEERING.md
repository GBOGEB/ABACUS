# MIP3 — Local-to-CI flight engineering and postflight method refinement

## Mission

Convert MIP2 method qualification into an attributable, repeatable local-first
  flight system. Preserve separate decisions for (1) testflight, (2) method
  qualification, (3) root resolution, (4) integration eligibility, and (5)
  merge admission.

## SIPOC

- Supplier: developer, scanner and CI.
- Input: exact SHA, configuration, test corpus and tool versions.
- Process: preflight -> seeded testflight -> postflight.
- Output: evidence receipt, JUnit and artifact hashes.
- Consumer: method registry, Mission Control and owner.

## Flight stages

1. **F0 discovery:** enumerate Python, OS, tools, versions, executable paths,
  pinned configuration; missing != failed test.
2. **F1 preflight:** exact Git HEAD, syntax compilation, schema validation,
  dirty-tree check (future), source/config hashes, dependency capability.
3. **F2 fast testflight:** contract and syntax checks; JSON telemetry; fail
  closed.
4. **F3 full testflight:** seeded Black/isort, Bandit, coverage tests; JUnit,
  durations and failures.
5. **F4 postflight:** match local receipt SHA to HEAD, parse JUnit, require
  nonzero tests, zero failures/errors/skips, verify actual bytes and SHA256.
6. **F5 native CI:** independent GitHub runner executes same contracts on exact
  PR head; no local receipt grants merge.
7. **F6 method admission:** measured TP/FP/FN, stability, diagnostic accuracy,
  repair yield and rollback evidence.
8. **F7 repository federation:** compatibility pilot in CODEX and
  cryoplant-project, separately verified.

## Method engineering DMAIC + 3P*

For **each** scanner or repair method: DEFINE intended rule/defect class and
  repair envelope; MEASURE paired corpus precision, recall, runtime and
  duplicate rate; ANALYZE missed/false/duplicate roots and first-red
  attribution; IMPROVE pinned configuration, adapters and repair algorithm;
  CONTROL seeded positive and negative tests plus semantic invariants; PREPARE
  baseline/candidate pairs; PROVE native reproducibility; PROPAGATE contracts
  to applicable repositories with rollback.

## KPIs and evidence fields

## Statistical plan

- Record paired baseline/candidate results on identical labeled cases;
  bootstrap confidence intervals only with adequate observations.
- Wilson intervals for binary detection/repair outcomes, with denominators
  disclosed.
- Pareto by unique root family and wasted verification time; avoid counting
  correlated workflows as independent defects.
- PCA only after sufficient repeated method-by-repository observations,
  missing-data handling and standardized features. Never infer causality from
  PCA.
- Control charts on repeatable per-method runtimes, failure rates and root
  yield after stable baselines.

## First-red and overflow treatment

Keep governance producer, governance admission, docs lint, A10 and formatting
  as separately attributed streams until logs prove shared roots. An unexpected
  error becomes an overflow finding with repo, exact SHA, run/job, signature,
  owner, evidence and UNKNOWN classification; no silent drop.

## Acceptance and release

- Local F1/F3/F4 PASS on same SHA; 4/4 seeded tests must actually execute and
  produce JUnit.
- CI F5 PASS on the **new** SHA and uploaded artifact bytes validated.
- First-reds repaired at source; no check disablement, weakened security,
  self-approval or premature merge.
- MIP3 method pilot success is not equivalent to resolving the eight historical
  BD roots.
- Re-run after each method improvement; record before/after values and preserve
  rollback.

## Known baseline (historical, not current-head admission)

MIP2 exact head 2f8de7b: 4/4 seeded tests PASS in 0.93 s, JUnit artifact
  11929400523 (455 bytes); 33 workflows, later 21 success, five failure, seven
  nonterminal. Subsequent local tooling commits 52c0b10 and 06b449d had not
  received completed native proof at last prior inspection.

## Follow-on implementation backlog

- MIP3-01: unify local and CI receipt schemas; enforce tool versions and
  dependency lock.
- MIP3-02: prevent pre-commit recursion and add staged-file syntax scope;
  handle dirty tree.
- MIP3-03: executable seeded corpus per method with true-positive/negative
  labels.
- MIP3-04: detect false greens by intentionally failing negative-control
  fixtures.
- MIP3-05: reproducible environment via pinned Python toolchain and optional
  Docker.
- MIP3-06: coverage risk-ranked branch selection and comparable denominators.
- MIP3-07: scanner fingerprint federation, LDAB joins, root IDs, overflow
  queue.
- MIP3-08: runtime LLDB/Docker session receipts and debugger crash signatures.
- MIP3-09: paired statistical experiment runner, confidence intervals, Pareto
  and PCA readiness.
- MIP3-10: method promotion and rollback by independent repository proof.

