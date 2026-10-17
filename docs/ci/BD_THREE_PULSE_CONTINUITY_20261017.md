# BDQ three-pulse QA bridge — execution contract

**Authority:** canonical queue `triage/ABACUS_BD_QUEUE_CURRENT.yaml`; root/census owner [#1929](https://github.com/GBOGEB/ABACUS/issues/1929); admission [#1860](https://github.com/GBOGEB/ABACUS/issues/1860). This additive consumer must never supersede the queue or invent a new census SSOT.

## Three pulses (3PC / N to N+3)

| Pulse | Slice | Expected test/receipt | Admission |
|---|---|---|---|
| N+1 | Canonical three distinct SHA joins | Three valid `bd.ldab.joined.census.v1` inputs; reject duplicates/missing provenance | HOLD |
| N+2 | Comparable root and coverage telemetry | Same scope/config/denominator or null; issue housekeeping excluded | HOLD |
| N+3 | Terminal native testflight + REX | Exact-head run/job/artifacts, disjoint path owner, human review | HOLD until all required gates |

Use `python scripts/bd_three_pulse_bridge.py --inputs N1.json N2.json N3.json --out receipt.json`.
Inputs must originate from `scripts/bd_ldab_join_census.py` and retain immutable source heads. The `coverage` field is an optional **separately source-verified** enrichment, never an inferred legacy conversion. A matching config and denominator is necessary but not sufficient: native artifacts and source membership must be verified independently.

## Numbered backlog J01–J09

| Item | Scope | This slice | Completion evidence still needed |
|---|---|---|---|
| J01 | SHA/run/job/artifact identities | Preserve canonical scope in each pulse | Live native exact-head attachment |
| J02 | Bandit exclusive B2/B3/B4/B5 ownership | Consume canonical validated join | Fresh full/configured native census |
| J03 | DAB/CI first-red signatures | Preserve canonical root IDs; no relabeling | Root-owner reviewed signatures and logs |
| J04 | LDAB/LLDB real sessions | Null launches by default | Authenticated runner/session/port receipts |
| J05 | Comparable debt burndown | Carry canonical comparable delta without promotion | Same scanner/tool/config before/after |
| J06 | Coverage and throughput | Numeric delta only on same eligible denom/config | Native source-matched numerator/denominator |
| J07 | Determinism and projection | Deterministic JSON consumer + negative tests | Terminal exact-head CI and artifact hashes |
| J08 | Governed admission | Permanent HOLD output and zero formal credit | Human/security/ruleset review + checks |
| J09 | Repeated statistical quality | Three-pulse sequence without invented trend | >=2 independent comparable actual cycles |

## Live first-red handoff

- Source repair: [#2135](https://github.com/GBOGEB/ABACUS/pull/2135), case-insensitive report assertion fix committed as `64a49a340dd89811879927ed8bd75494c2d306bd`; native workflow executions are separate and nonterminal until readback proves completion.
- Existing unrelated blockers: [#2026](https://github.com/GBOGEB/ABACUS/pull/2026) Matplotlib compatibility; [#2133](https://github.com/GBOGEB/ABACUS/pull/2133) YAML length violations; [#1995](https://github.com/GBOGEB/ABACUS/issues/1995)/[#2041](https://github.com/GBOGEB/ABACUS/issues/2041) governance. Never credit these as repaired by this PR.
- [#1885](https://github.com/GBOGEB/ABACUS/issues/1885): 53 historical href manifestations (50 MYRRHA, 2 report, 1 dynamic). Six historical alert issue closures were duplicate/housekeeping, not accepted engineering-root closures.
- CODEX [#975](https://github.com/GBOGEB/CODEX/pull/975) is a historical CODEX merge, not ABACUS admission; [#977](https://github.com/GBOGEB/CODEX/issues/977) executor dispatch remains unproven.

## Next admissible operator sequence

1. Watch current exact head for terminal native lint/test/security checks; classify each first failed step.
2. Before claiming coverage growth, verify both source SHAs and native job/artifact eligibility.
3. Obtain authentic ABACUS-local launch identities before reporting a crew or runner as launched (native CI is not Crew dispatch).
4. Update existing owner/root inventory once verified. Do not close tickets or merge without independent governance.

`MERGE_ADMISSION=HOLD`; `AUTHORITY_TRANSFER=false`; `SECURITY_WAIVER=false`; no synthetic worker launches.
