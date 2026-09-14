# ABACUS CI Runner Snapshot + Statistical Gate Design Proposal

**Status:** mixed historical evidence + design proposal; no authority transfer.

**Source routing:** curated from QPS W192 raw-text intake and assigned to `GBOGEB/ABACUS` because the raw capture contains ABACUS Actions/job-log evidence and a proposed ABACUS CI observability/statistics extension.

**Raw provenance alias:** `Pasted text (2)(2).txt`  
**Raw SHA256:** `954f2fec27d0f8810c41cd6e9cea5bb1956ab9c317727793c65d25e2f1ceee37`

## Context / Objective

The source is a mixed transcript containing two materially different things: real GitHub Actions runner/job-log observations and an embedded design proposal for statistical CI reliability. The useful content is separated here so historical execution evidence is not conflated with unimplemented architecture.

## Current State / Observed Execution Evidence

The captured ABACUS job-log material shows:

- a hosted runner materialized on Ubuntu 24.04.4;
- checkout cleanup included git safe-directory handling and cleanup of SSH/GitHub HTTP authorization configuration;
- the captured workflow emitted a warning about Node.js 20 action-runtime deprecation and migration toward Node.js 24.

These observations are historical. Their applicability to current ABACUS workflows must be verified against current action versions and runner images.

## Evidence

The raw transcript contains actual Actions/job-log text, including runner image information, git configuration/cleanup commands, and action-runtime warnings. QPS W192 intake retained the raw bytes and SHA as provenance; this curated copy does not replace those raw bytes.

## Proposed Design / Interpretation

The same transcript proposes a CI observability/statistics layer with these candidate elements:

- append-only `logs/ci-runs.jsonl` as a CI-performance event stream;
- `tools/ci_stats.py` for per-gate runtime statistics and SPC diagnostics;
- `tools/gate_rollup.py` for identifying the first failed gate per PR;
- a consolidated modular pull-request template carrying governance and runtime-statistics fields;
- optional dashboard views for runtime distributions, SPC and first-failure rollups.

This is a **design proposal only**, not implementation evidence.

## What Must Not Be Inferred

- that the proposed statistics tooling exists on current `main`;
- that the proposed thresholds are suitable for every gate;
- that a short-running failure is necessarily environmental/configuration rather than logic;
- that branch protection or required checks were changed;
- that a new telemetry SSOT is needed if current ABACUS/QPS metrics already satisfy the requirement.

## Risks / Open Questions

1. Existing metrics/receipt surfaces may already overlap the proposed event stream.
2. Statistical baselines can be misleading if heterogeneous runner families or workflow versions are mixed.
3. Runtime duration is evidence, not a root-cause classifier.
4. Action-runtime migration warnings may already be resolved in current workflow versions.

## Actions / Next Gate

1. Inspect current ABACUS workflows and action versions before applying any Node-runtime repair.
2. Inventory existing ABACUS/CODEX/QPS metrics, receipts and first-red reporting before adding new CI telemetry.
3. If a measurable gap remains, extend the existing controlled metrics surface instead of creating a parallel SSOT.
4. Preserve first-causal-red semantics when adding runtime statistics or rollups.

## Provenance / Authority Boundary

This document is a **human-curated candidate** derived from immutable raw-text provenance. The observed log material is historical evidence; the statistical tooling is a proposal. Neither section overrides current ABACUS workflows, release gates, governance, or CI results.

**Disposition:** `HISTORICAL_LOG_CURRENTNESS_CHECK + DESIGN_CANDIDATE`.
