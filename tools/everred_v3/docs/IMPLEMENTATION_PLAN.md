# EVERRED V3 · implementation register

## Implementation boundary

The local build has a functioning event ledger, derived KPIs, vector diagrams and self-contained HTML. It does **not** have a live authenticated GitHub poll, server-side distributed lease service, human reviewer attestation, new confirmed causal roots, a running LDAB fleet, or approved merge authority.

## Next controlled implementation slices

| ID | Owner lane | Required work | Verifiable acceptance |
|---|---|---|---|
| V3-A1 | A observer | Native GitHub Actions/JUnit/Bandit/coverage fetch adapter with caching, pagination and exact-source checks | Read-only authenticated receipt tests; no guessed fields |
| V3-A2 | B RCA | Canonical signature normalization + root candidate graph with counterfactual contracts | Same signature can split into two causes; several signatures can join one cause, with recorded evidence |
| V3-A3 | C canonical repair | Repository-wide lease coordinator (CAS, TTL, role validation, idempotency; non-overlapping ownership) | Two simultaneous writers on same path cannot both acquire; stale SHA rejected |
| V3-A4 | D replay | Immutable worktree / Docker snapshot consumer testflight | Synthetic replay explicitly not mislabelled native exact-head PASS |
| V3-A5 | E security | Fingerprint normalization, B101 intent-classification and Safety exit-64 diagnosis | Identical scanner/rule/config before/after; opened/resolved/persisting counts |
| V3-A6 | F runtime | LDAB/LLDB/RHEL8-9/UBI/Docker launcher and typed receipts | Real signed job/session/port, runtime, logs and source binding |
| V3-A7 | G governance | Independent protection+review verifier; merge done outside local engine | Server readback of branch protection; eligible reviewer; all native P5 checks |
| V3-A8 | H federation | CODEX Mission Control/REX accepted-receipt contract | Read-only aggregation without authority propagation |
| V3-A9 | Observability | Snapshot federation and history, KPI trend windows, rate denominators and alert thresholds | Two or more comparable census runs; UNKNOWN preserved |

## Disjoint wave approach

A can run with E and F (read-only) in parallel. B may classify independently while C waits for confirmed root ownership. D may fan out immutable replays in parallel; only after verified canonical repair. G owns admission separately. H consumes *accepted* typed evidence without modifying the canonical registry.

## DMAIC / DoV / DoD

**Define:** exact failure intent, scope, blocked consumer and authority. **Measure:** run/job/sha/test IDs plus comparable denominators. **Analyze:** counterfactual main-vs-PR-vs-env, downstream first-red dependencies. **Improve:** bounded canonical repair, negative regression and disjoint replay. **Control:** effective protection, independent approval, exact-main verification and recurrence sentinel.

**Technical DoV:** reproduce + repair original behavior; negative controls fail closed; exact-head producer proof; attribution and permitted paths logged.

**Global DoD:** authorized protected merge, eligible independent security review, exact-main proof, known consumer reconciliation, recurrence observation and final typed release receipt. A locally passing producer remains `TECHNICALLY_VERIFIED / ADMISSION_HOLD` until all global gates pass.

## Current-main integration finding (14 October 2026 connector readback)

The original #1914 dashboard numbers remain an immutable **historical case study**. A newer GitHub main SHA was observed as `b45cf45eaad8303c6c4287616492895be4638f56`, 52 commits ahead of the case study's `02cca5020d59cc339cea486ed38857f53eea3e88`. The current repo contains `scripts/bd_ldab_join_census.py` (schema `bd.ldab.joined.census.v1`) and tracking issue #1929. Do not republish #1914 metrics as current-main security or coverage levels.

EVERRED's new `scripts/ingest_bd_ldab_join.py` consumes the current main joiner's explicit output without changing its producer or converting its BD/CI group IDs to confirmed causal roots.
