# BDQ three-pulse QA bridge

**Authority:** ABACUS #1929 is the canonical root census owner.
ABACUS #1860 owns admission. The queue authority remains
`triage/ABACUS_BD_QUEUE_CURRENT.yaml` (historical 2026-09-26).
This is an additive consumer, not another source of truth.

## Three pulse execution (3PC / N to N+3)

- N+1: receive three validated canonical join outputs on distinct exact SHAs.
  Reject duplicate heads, malformed denominators, and fabricated approval.
- N+2: compare source-qualified statement and branch numerators only when
  configurations and eligible denominators match. Otherwise report null.
- N+3: record terminal native test and artifact receipts, first-red roots,
  security dispositions, independent review and authority controls.
  Admission remains HOLD until every gate is satisfied.

Run:

```sh
python scripts/bd_three_pulse_bridge.py \
  --inputs N1.json N2.json N3.json --out receipt.json
```

Inputs must come from `scripts/bd_ldab_join_census.py`.
Any optional coverage enrichment needs independent native source proof.
Matching config and denominator alone never establish coverage acceptance.

## Numbered backlog J01-J09

- **J01 - Evidence identities.** Preserve source scope and commit SHA.
  Need real run, job, artifact, and digest attestations.
- **J02 - Bandit disjoint ownership.** Consume canonical validated B2-B5.
  Need fresh full and configured scan census.
- **J03 - Root/first-red signatures.** Preserve source-owned root IDs.
  Need reviewed first failed commands and native log links.
- **J04 - LDAB/LLDB sessions.** Report null worker launches by default.
  Need authenticated runner, session, debugger, port and REX receipts.
- **J05 - Comparable debt.** Preserve existing comparator authority.
  Need same scanner, rules, version, path scope and source receipts.
- **J06 - Coverage and throughput.** Compute only on eligible scopes.
  Need native source-bound numerator, denominator and runtime evidence.
- **J07 - Determinism.** Add negative controls and stable JSON emission.
  Need terminal exact-head CI and artifact-byte verification.
- **J08 - Governance.** Maintain HOLD and zero credited formal closures.
  Need effective ruleset, CI, security and independent human review.
- **J09 - Repeated statistical quality.** Three-pulse observation is not
  sufficient for population reliability; need comparable repeated cycles.

## First-red and continuity ownership

- ABACUS PR #2135 received the isolated report-assertion correction.
  Commit: `64a49a340dd89811879927ed8bd75494c2d306bd`.
  Native CI checks must be read separately to classify the outcome.
- ABACUS #2026 owns the Matplotlib compatibility root.
- ABACUS PR #2133 owns changed-workflow YAML line-length issues.
- ABACUS #1995 and #2041 own governance/inventory convergence.
- Dashboard #1885 retains 53 historical broken href manifestations:
  50 MYRRHA, two reports, and one dynamic expression.
  Six historically closed duplicate alert tickets are housekeeping.
  None qualifies as accepted engineering-root closure.
- CODEX PR #975 merged in CODEX only. CODEX #977 still requires
  authenticated ABACUS-local dispatch evidence and owner approval.

## Operator return / next admissible action

1. Verify current head SHA against terminal native jobs and artifacts.
2. Classify each failing first step under an actual source owner.
3. Reject mismatched heads, changed source populations, and unknown scope.
4. Update the existing BD queue and deduplicated root owner with receipts.
5. Require human/security/governance admission before any main merge.

No inferred Crew launch, CI success, human approval or waiver.
`MERGE_ADMISSION=HOLD`, `AUTHORITY_TRANSFER=false`,
`SECURITY_WAIVER=false`. Root closures need independent proof.
