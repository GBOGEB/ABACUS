# CODE PURPLE / MIP Floating-Code Programme — execution contract

Version: 2026-10-19 / owner: ABACUS source governance / status: PROPOSAL, NOT ADMISSION.
Reference source: W104 DOW floating-anchor census, ANCHOR_COVERAGE_PENETRATION and W46_HIGH_YIELD_COVERAGE_HANDOVER.
Exact initial main reference: cf27dba3b6826a364c2467a49104a115feab99f1.

## Six stages (MIP / DMAIC)

1. **Baseline / Define and Measure.** Freeze source HEAD, instrumentor, measured cohort (including statement/branch denominators), configuration, B0 run/job/attempt, and SHA256 of raw artifacts. Anchor names and path heuristics are candidates, never verified semantic links. Report unknowns separately. W46 measured 9430/28014 combined, 18584 missing, 114/223 zero-covered paths; no fresh gain is attributed to this programme.
2. **Classify / Investigate.** Partition into F01 active-uncovered, F02 floating capability, F03 dormant subsystem, F04 cross-repo utility, F05 possible duplicate, F06 legacy/dead candidate, F07 unsafe/unstable. Add UNKNOWN class until runtime consumers and provenance are inspected. Path name and missing coverage alone never authorize orphan or removal classification. Score by missed opportunities, independent graph evidence, risk, size and cross-repo reuse, keeping each feature distinct.
3. **Construct evidence DAG / Analyze.** Nodes: path, symbol, module, registry declaration, CI/CLI entrypoint, runtime call, artifact producer/consumer, contract, test, owner, commit, receipt. Typed edges distinguish DECLARED, STATIC, DYNAMIC_OBSERVED, CONTRACT, ARTIFACT, NEGATIVE_SEARCH and UNKNOWN, each with source SHA and evidence reference. Search dynamic import, plugins, reflection, scripts, workflows, external and periodic callers before declaring orphan. Map golden threads from user need to entrypoint to behavior to receipt.
4. **Incubate / Improve.** First no-side-effect smoke and import isolation, then contracts, negative/reverse/property/metamorphic tests, fault/replay stress and mock external effects. For F05 run differential tests of equivalent interfaces, including mutation/side-effect comparison. Dispositions: RETAIN_TEST, BRIDGE, ORCHESTRATE, FEDERATE, SNIP_CONSOLIDATE, PRUNE, QUARANTINE, DEFER_UNKNOWN. Require explicit owner decision and rollback path. PRUNE only when no justified consumer is established, approved, and removal regressions pass.
5. **Telemetry / Prove.** Measure separate functional numerator gains on matched denominator and structural denominator shifts; never credit source deletion as newly tested behavior. Each pulse stores UTC timestamp, repository, exact HEAD, scope and instrumentor hashes, statement and branch counts, candidate reconciliation, deduplicated root cohort, disjoint workers, queue/execute times, native test artifacts, current admission. Unknown means null, not zero. Use tools/triage/mip_pulse_rollup.py for descriptive histories: per-pulse counts, p95 latency, N->N+1 comparable changes, root delta and conservative local plateau. Cross-branch scopes require matching instrumentation and population fingerprints. Authenticate supplied JSON, artifact hashes and CI provenance separately; the rollup itself is NOT an attestation.
6. **Scale / Control.** Assign file-ownership leases and separate branches. Independent worker families: A census+graph (read only), B duplicate semantic comparison, C six priority source-test modules by disjoint path, D federation/consumers (read only), E telemetry and QA. No shared-file parallel writes. Each worker produces proposal SHA, tests, run/job/attempt, context, first RED, deduplicated root, changed covered opportunities, and scoped regression evidence. Serial admission only after effective required statuses, approved reviewer, resolved threads, no unapproved bypass and a fresh head check.

## Wave scheduling

- **N=0**, measured historical W46 baseline; record source / run / matched denominator and verify artifact provenance; W104 candidate findings remain path heuristics.
- **N=1**, three disjoint read-only discovery lanes for executable call graph, registry/entrypoint/consumer graph, differential duplicate map. Produce unknown and exclusion populations.
- **N=2**, six disjoint test incubation owners, scoped to their own paths, without dispatch side effects; run identical-source before/after and audit flags.
- **N=3**, disposition lanes and bridge integration tests for retained capability, then independent review and serialized CI proof.
- **N>=4**, dynamically reprioritize based on qualified marginal gains, roots removed, risk and p95 queue latency. Do not set expected gain equal to theoretical saturation.

## Convergence controls

Stop a locally saturated module once statement+branch opportunities are exhausted (on fixed source). Stop a stalled *local* lane after three consecutive terminal comparable pulses with <=0.05 percentage-point gain, no increase in disposition resolution, and no net root closure, **only** when fixed-cohort root telemetry is available. Reroute workers to another source family. A lack of data or mismatched denominator must be tagged NOT_COMPARABLE, never STABLE. Formal release readiness is governed by separate CI, security, review and provenance gates; no auto-merge, acceptance or security waiver.

## Minimum telemetry JSON

```json
{
  "schema": "codepurple.mip.floating-pulse.v1",
  "repository": "GBOGEB/ABACUS",
  "head_sha": "<40-lowercase-hex>",
  "population_sha256": "<64-lowercase-hex>",
  "instrumentation_sha256": "<64-lowercase-hex>",
  "observed_at": "2026-10-19T12:00:00Z",
  "coverage": {
    "statements": {"covered": 7779, "eligible": 22456},
    "branches": {"covered": 1651, "eligible": 5558}
  },
  "triage": null,
  "root_reds_open": null,
  "workers": [],
  "governance": {"merge_admission": "HOLD", "security_waiver": false}
}
```

Do not treat this example as a live pulse until population and instrumentation hashes have been computed from actual matching assets. Command: `python tools/triage/mip_pulse_rollup.py pulse0.json pulse1.json --out mip_rollup.json`. Run `python -m unittest discover -s tests -p test_mip_pulse_rollup.py` for focused synthetic tests.

## Disjoint worker path ownership

- MIP-T / telemetry: `tools/triage/mip_pulse_rollup.py`, `tests/test_mip_pulse_rollup.py`.
- MIP-G / method: `triage/MIP_FLOATING_CODE_CONVERGENCE.md`.
- MIP-C / census extension: future `tools/triage/` paths excluding MIP-T paths; new branch and PR required.
- MIP-R / runtime tests: future `tests/` names specific to each owner/module; ensure no overlapping files or fixture modifications.

Evidence status: No new native B0, merge approval, coverage gain, semantic orphan count, review or safety waiver is asserted here. MERGE_ADMISSION = HOLD.
