<!-- markdownlint-disable MD013 MD060 -->

# MIP / 3P* SIPOC-DAG reuse contract

Status: advisory engineering design; not admission evidence.

## SIPOC

| Supplier | Input | Process | Output | Customer |
|---|---|---|---|---|
| PR author / GitHub | Exact SHA, changed paths, test node IDs | Unique inventory, category classification, impact planning | Deterministic census and risk plan | MIP B0 |
| Canonical CI / scanners | JUnit, coverage XML, Bandit and static reports | Parallel B0, B1, static/DAB, report-only, matrix | Source-bound evidence and first-red queue | Independent reviewer |
| LDAB / 3P workers | Runner, OS, Python, timing and hashes | Repeat comparable experiments and reconcile drift | p50/p95, critical path, stability receipts | CI owner, non-authoritative consumers |

## Reusable execution DAG

```mermaid
flowchart TD
  A[Exact SHA and diff] --> B[Inventory and taxonomy]
  B --> C[SIPOC: risk and impact analysis]
  C --> D{Critical failure?}
  D -->|Yes| E[Escalate affected family]
  D -->|No| F[Parallel evidence]
  E --> F
  F --> G[B0 canonical JUnit and coverage]
  F --> H[B1 false-green]
  F --> I[Static DAB and Bandit]
  F --> J[Report-only and Python matrix]
  G --> K[Exact-head evidence join]
  H --> K
  I --> K
  J --> K
  K --> L{Terminal and complete?}
  L -->|No| M[Root-specific repair and remeasure]
  M --> C
  L -->|Yes| N[3P stability and time comparison]
  N --> O[Independent protected admission]
  O --> P[Consumer feedback and new baseline]
  P -.->|Next iteration only| B
```

## Evidence contract

1. Count unique collected node IDs once; category membership can overlap.
2. Measure collected, passed, failed, skipped, xfailed, test seconds, setup seconds, queue seconds and total wall time separately.
3. Bind JUnit, coverage and scanner evidence to exact SHA, interpreter, runner, dependency/configuration identity and artifact hash.
4. Report covered and eligible changed lines; UNKNOWN rather than an inferred percentage if artifacts are missing.
5. Classify complexity 1-5 only from measured duration, dependencies, environment and history. Otherwise UNMEASURED.
6. Fast diagnostics never substitute for required B0, security or governance admission.
7. Python 3.9 source-only proof is not package compatibility where pyproject requires Python >=3.11.
8. Escalate security reds to affected negative tests and scanner; compatibility reds to the relevant interpreter; runner outages to queue diagnostics.
9. Retire legacy workflows only after equivalence and branch-protection owner approval; preserve useful quick-start paths.
10. Reuse canonical workflows; do not manually modify generated docs/ci/WORKFLOW_RATIONALIZATION.md.

## Waves

- W1: taxonomy and advisory planning, PR #1921.
- W2: full collect-only census and source-to-test contexts.
- W3: JUnit timing and complexity distribution.
- W4: bounded 3P* repeatability and trigger escalation.
- W5: measured redundant workflow deprecation candidates.
- W6: independent admission and cross-repository consumer rollout.

Authority transfer = false; engineering credit = 0 until independently accepted.

## GCA-3: wave/pulse terminology and governed N→N+3 advance

Adopt [GCA-3 terminology and execution protocol](../../MIP/GCA3_GLOSSARY_AND_PROTOCOL.md) as an operational naming overlay without changing this canonical SIPOC/DAG or the historical W1–W6 list. **Wave** (`W[N+i]`) = independently receipted, bounded delivery increment; **pulse** (`Uj`) = observe/diagnose/change-or-no-change/verify loop *within* a wave; **3P\*** P1/P2/P3 = methodology stages, not a pulse count. `GCA-3` = three attempted waves, default ≤3 pulses per wave, accepted index advances only by contiguous engineering DoV PASS. Independent branch/reviewer/security/A10/governance gates never inherit PASS from engineering tests.

```mermaid
flowchart LR
  A[Freeze accepted N and exact evidence] --> B[W N+1]
  B --> U1[U1..U3 bounded pulses]
  U1 --> G1{Engineering DoV?}
  G1 -->|PASS| C[W N+2]
  G1 -->|HOLD| X[Keep accepted index N; route safe disjoint lane]
  C --> U2[U1..U3 bounded pulses]
  U2 --> G2{Engineering DoV?}
  G2 -->|PASS| D[W N+3]
  G2 -->|HOLD| X
  D --> U3[U1..U3 bounded pulses]
  U3 --> G3{Engineering DoV?}
  G3 -->|PASS| Z[Accepted N+3 engineering scope]
  G3 -->|HOLD| X
  Z --> R[Independent release admission remains separate]
  X --> Q[Return attempted vs accepted and blocker receipts]
```

The completed response shall return the wave receipts, first-red/BDQ root reconciliation, metrics before/after with matched scope, jobs/attempts, owner leases, and acceptance-vector/HOLD status. A source-head CI run that has merely been queued does not count as wave acceptance. No background execution is implied.
