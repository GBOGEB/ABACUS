# MissionControl Lossless Handover — 2026-10-03

## Purpose

This is a fresh repository-native lossless restart cut for the live MissionControl execution frontier.

It does not replace, rewrite, or reinterpret the historical W80 handover. W80 remains an immutable closed-subject checkpoint.

## Authority snapshot

- ABACUS exact main: `fd5cad73fbee0c3d46eaa45484ef47385930a206`
- CODEX exact main: `c8bdedd2912ceb456f4582988ab9aa72eea844de`
- CODEX open PRs at refresh: none
- Restart policy: repository authority only
- Cross-SHA evidence substitution: forbidden

## Historical restart chain preserved

The W80 chain remains valid historical evidence:

```text
handover/mc2/W80_CURRENT.json
-> handover/mc2/W80_LOSSLESS_HANDOVER_20260918.md
-> handover/mc2/W80_DROPIN.md
-> architecture/w80/W80_3PSTAR_MIP_CLOSEOUT_RECEIPT_v0.3.json
-> architecture/w80/W80_V03_PUBLICATION_ATTESTATION_v0.1.json
```

The W232 receiver also remains pointer-only analytical restart evidence. It must not be treated as live child authority without refreshing the child/current repository.

## Live ABACUS execution frontier

### Primary lane — PR #1732

- PR: `#1732 ci: parallelize MIP B0 evidence producers`
- Base main: `fd5cad73fbee0c3d46eaa45484ef47385930a206`
- Exact head: `dea25f536d93136030d8950a643f7be6b9b21040`
- Merge state: open / unmerged
- MIP B0 run `37115520578`: in progress at snapshot
- CI Matrix run `37115520654`: in progress at snapshot
- qps-canonicalization run `37115520697`: GREEN
- Smoke run `37115520664`: GREEN

Earliest completed attributable red:

```text
CI Workflow Governance
run 37115520651
job 111181483152
exact head dea25f536d93136030d8950a643f7be6b9b21040
result FAILURE

first red:
generated governance report is stale:
docs/ci/WORKFLOW_RATIONALIZATION.md
```

The governance job uploaded exact-head diagnostic artifact `11271344036` with SHA-256
`23d70e50317384218478f5be64a0c6c217dd28e5a6c8f64b6407e1a29f30222e`.

A later completed failure also exists:

```text
Validate Docs
run 37115520636
job 111181483121
MD047 single-trailing-newline
docs/ci/WORKFLOW_RATIONALIZATION.md
```

That later observation is retained but not promoted as a second repair residual before the first-red repair and recensus.

### Parallel lane — PR #1731

- PR: `#1731 governance: continuous DAB G1-G3 and compatible proposal proof`
- Base main: `fd5cad73fbee0c3d46eaa45484ef47385930a206`
- Exact head: `bd1608fb34f1047714b03a351d10ae2580a01e5e`
- DAB Flake8 Census run `37115644282`: GREEN
- DAB job `111181826679`: >0-step GREEN
- DAB artifact `11271234872`
- DAB artifact SHA-256: `df7e437a53d0984e6ee1ca300b3d190aaa9f4c12627d9fad065009284489799d`
- qps-canonicalization run `37115644208`: GREEN
- MIP B0 run `37115644162`: in progress at snapshot
- CI Matrix run `37115644244`: in progress at snapshot

No DAB residual count from another SHA is substituted into this exact-head record.

### Older pending lane — PR #1730

- PR: `#1730 ci: govern advisory checks in bootstrap pipeline`
- Base main: `fd5cad73fbee0c3d46eaa45484ef47385930a206`
- Exact head: `d7539ba6bda902fb2444295873285381526a5bab`
- MIP B0 run `37113888399`: GREEN
- CI Matrix run `37113888378`: GREEN
- Bootstrap Statistics CI/CD run `37113888437`: completed failure

The bootstrap failure must be classified on its own exact head before merge. It is not used to overwrite the #1732 first-red chain.

## Current measured residual

For the primary lane, the current material residual is:

```text
CI_GOVERNANCE_DERIVED_INVENTORY_STALE
path = docs/ci/WORKFLOW_RATIONALIZATION.md
source = #1732 exact head dea25f536d93136030d8950a643f7be6b9b21040
run = 37115520651
job = 111181483152
```

## Next legal transition

```text
refresh ABACUS main + CODEX main
-> confirm #1732 exact head unchanged
-> repair only the stale generated governance report
-> rerun exact-head governance/docs/MIP/Matrix surfaces
-> classify chronological first completed attributable red only
-> merge #1732 iff admissible
-> exact-main readback
-> fresh MIP/DAB recensus
-> only then consume another measured residual
```

PR #1731 may continue independently on its own exact-head evidence. Do not use its DAB evidence to satisfy #1732.

## Invariants

```text
authority_transfer=false
formal_credit_delta=0
engineering_credit_delta=0
repository authority > chat memory
no cross-SHA evidence substitution
first completed attributable red only
no second residual before recensus
historical W80 handover immutable
```

## Restart rule

On restart, read `handover/mc2/MISSIONCONTROL_CURRENT.json` first, then refresh both live repositories before acting. If any exact SHA, PR head, workflow state, or measured residual has changed, the refreshed repository state supersedes this snapshot without invalidating this historical handover cut.
