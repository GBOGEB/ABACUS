<!-- markdownlint-disable MD013 -->

# CODE PURPLE — evidence-linked workflow graph, LDAB and admission architecture

Status: **read-only architecture prototype**. Owner: ABACUS execution evidence. CODEX MissionControl remains orchestration-only. No authority transfer, security waiver or inferred worker dispatch.

## Views and evidence contract

- `docs/code_purple_execution_graph.html`: responsive dark/light workflow lane viewer. Click nodes for source URLs, timing, dependency and guarded next action; focus ABACUS Matrix, MIP, or admission; QA overlay. Its default screenshots-inspired job statuses are explicitly **historical examples**, not verified live state.
- ABACUS Matrix: `ci-abacus.yml`, planner → 3-job matrix → proof completeness → compatibility. MIP: B0 census → 8-job proposal-worker matrix / report-only admission. A green GitHub Actions *job* is a runner execution, not an authenticated CODEX crew launch.
- Admission: exact-head first red → authenticated local crew dispatch → REX receipt → gate → merge readback. These are separate governed evidence types; defaults **UNKNOWN**.
- Existing authority: [ABACUS #1860](https://github.com/GBOGEB/ABACUS/issues/1860), [CODEX #977](https://github.com/GBOGEB/CODEX/issues/977), [CODEX #975](https://github.com/GBOGEB/CODEX/pull/975), [ABACUS LDAB](https://github.com/GBOGEB/ABACUS/blob/main/MIP/README.md). Existing CODEX graph viewer and producer must not be replaced.

## Typed evidence and first-red algorithm (follow-on implementation contract)

A governed producer shall emit pinned JSON with schema version, `observed_at`, repository, PR, `head_sha`, `main_sha`, `run_id`, `workflow_id`, `job_id`, `conclusion`, `started_at`, `completed_at`, `source_url` and producer identity. Nodes: WORKFLOW, JOB, MATRIX_CELL, CHECK, REVIEW, DISPATCH, WORKER, RECEIPT, ROOT_CAUSE, BD_ITEM, COVERAGE. Edges: NEEDS, PRODUCES, BLOCKS, DISPATCHES, VERIFIED_BY, TRACKED_AS, REPLACES. Do not infer edge causality from vertical proximity or screenshots; mark derived vs source-authored edges.
1. Ingest Actions workflow-run/job/steps for exact head and `needs` from parsed workflow YAML. Distinguish `success`, `failure`, `cancelled`, `skipped`, `pending`, and `unknown`. Deduplicate matrix cells by workflow run + job ID.
2. First-red is earliest failing job/step reachable after satisfied dependencies; mark cascading downstream failures separately and retain source URLs. Do not call skipped optional canary a failure. If actual job logs/steps are missing, the first-red is UNKNOWN.
3. Prompt/dispatch suggestion is inert until a CODEX #977 authenticated ABACUS-local executor has been separately promoted (exact head, principal, action/path allowlist, dry-run, approval, replay guard, locks). Only issued worker run ID plus trusted REX receipt constitutes launch/completion evidence. Viewer does **not** mutate or launch.
4. PR admission requires terminal **required** checks, exact-head review + security evidence, zero unresolved material threads, and strict ruleset; green matrix/MIP alone is not admission. Use no implicit break-glass.
5. Coverage: separately report measured `main` and PR broad and PR diff, with numerator/denominator, source receipt SHA and baseline SHA. Historical baselines: main 36.85% (2026-10-11); PR 36.92% broad, 51% diff (2026-10-12). Never present them as new readings.
6. LDAB: ingest `MIP/receipts/repo_self_index.json#/assessments/repo_self_assess_debug_ldab` and diagnostic/trace provenance; report error category, severity, recurring signature, open/closed root cause, noisy-versus-unique finding, duration to resolve, and evidence link.
7. Top 7/14/21: rank independent root-cause signatures by severity × recurrence × number of blocked dependents, with windows and timestamps explicit. Do not mix root-cause, BD-item and PR populations. Unknown denominators display UNKNOWN, never 0.
8. Trigger CODE PURPLE review on measured first-red change, new admitted merge, coverage gain, or material TODO completion; emit delta + next admissible action into governed BD queue and doctor/historian REX lane. Alerts are suggestions, not authenticated dispatch.
9. Publish to Pages only after successful exact-head CI, owner review, approved deployment workflow and content-identity readback. No automatic Pages publication in this PR.

## Definition of done

- Regression fixture: matrix dependencies, MIP fan-out, failed predecessor, cancelled/skipped jobs, missing logs, stale head, absent REX, coverage null vs zero, review pending, no fake admission.
- Playwright dark/light, responsive, keyboard focus and evidence-link QA; fail closed on invalid JSON.
- Source registry pins CODEX execution graph and ABACUS producer separately; no competing SSOT.
- Execute real ingest/CI and verify new main SHA and coverage only after gated merge.

This PR establishes a navigable **architecture and source contract**, not an operational production telemetry service.
