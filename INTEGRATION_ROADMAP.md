# ABACUS Integration Roadmap

_Last updated: 2026-06-07_

This document outlines a phased plan for federating the **ABACUS** analysis
repository with the wider QPLANT cryogenics ecosystem (the
`cryo_leak_rate_dashboard` and related tooling). It is a planning artifact, not
a commitment — phases can be re-ordered or de-scoped as priorities shift.

## Context

- **ABACUS** holds engineering analyses authored as version-controlled
  documents. The first published analysis is the MYRRHA warm-compressor
  comparison (PR #400, merged), which compares the ALaT FSD 575 SFC and LKT
  FSD 475 SFC skids against requested mass-flow targets.
- The **cryo_leak_rate_dashboard** repository hosts the live status tooling,
  GitHub Pages dashboard, and the ecosystem status / PR-tracking documents.
- Today these live as independent repositories. The goal of this roadmap is a
  predictable, low-risk path toward shared data, cross-linking, and reusable
  visualization components.

## Guiding principles

1. **Engineering data is contract-critical.** Numeric values from applicant
   pre-studies and datasheets are never transformed silently. Any derived value
   keeps a visible reference trail to its source document.
2. **GitHub-renderable first.** Every analysis must read fully on GitHub without
   relying on `<script>`/`<style>` (which GitHub strips). Interactive views are
   published as standalone HTML pages and linked from the Markdown.
3. **Small, reviewable PRs.** Each phase lands through one or more pull requests;
   nothing is pushed straight to `main`.
4. **No hard coupling.** Cross-repo integration prefers data contracts and
   static artifacts over tight runtime dependencies.

## Phase 1 — Repository hygiene & conventions (foundation)

**Goal:** make ABACUS a predictable home for analyses.

- [x] Establish the `analyses/<domain>/` directory convention
      (e.g. `analyses/compressors/`).
- [x] Standalone interactive views live under
      `analyses/<domain>/visualizations/` and are linked from the Markdown.
- [ ] Add a top-level `README.md` index that lists each analysis, its status,
      and the source PR.
- [ ] Document the authoring conventions (H1 title, Markdown pipe tables,
      explicit colours in standalone HTML) in a `CONTRIBUTING.md`.

## Phase 2 — Visualization component library

**Goal:** stop hand-porting chart code per analysis.

- [ ] Extract the shared chart primitives (capacity bars, per-skid frequency
      bars, status table, model switcher) into a small reusable JS/CSS bundle
      under `analyses/_shared/viz/`.
- [ ] Parameterise the bundle with a JSON data contract
      (`{ targets, models }`) so a new analysis only supplies data.
- [ ] Use explicit, self-contained theme tokens (no host-app CSS variables) so
      pages render identically inside and outside GitHub.

## Phase 3 — Shared data contracts

**Goal:** a single source of truth for skid/utility figures.

- [ ] Define a versioned JSON/CSV schema for compressor skid specifications
      (per-skid flow, frequency, package power, cooling water, heat rejection).
- [ ] Store canonical datasets under `data/` with provenance metadata
      (source document, page reference, date confirmed).
- [ ] Generate the analysis tables and the interactive views from the same
      dataset to eliminate copy drift.

## Phase 4 — Cross-repo linking with the dashboard

**Goal:** make ABACUS analyses discoverable from the live dashboard.

- [ ] Publish an analysis manifest (machine-readable index) from ABACUS.
- [ ] Have the `cryo_leak_rate_dashboard` GitHub Pages site consume the manifest
      and surface links to each ABACUS analysis.
- [ ] Add reciprocal links from each ABACUS analysis back to the relevant
      dashboard view.

## Phase 5 — CI validation

**Goal:** keep the conventions enforced automatically.

- [ ] Markdown lint + link checker (catch broken relative links such as the
      HTML visualization path and in-document anchors).
- [ ] Numeric-integrity check: assert that figures in the Markdown tables match
      the canonical dataset within tolerance.
- [ ] HTML smoke test: load each standalone visualization headless and confirm
      it renders without console errors.

## Phase 6 — Publication & federation

**Goal:** a unified, browsable ecosystem.

- [ ] Optionally publish ABACUS analyses to GitHub Pages with the standalone
      visualizations served directly.
- [ ] Federated search/index across ABACUS and the dashboard.
- [ ] Release tagging so each analysis can be cited at a fixed version.

## Status snapshot

| Phase | Title | Status |
|---|---|---|
| 1 | Repository hygiene & conventions | In progress |
| 2 | Visualization component library | Planned |
| 3 | Shared data contracts | Planned |
| 4 | Cross-repo linking with the dashboard | Planned |
| 5 | CI validation | Planned |
| 6 | Publication & federation | Planned |

> This roadmap is intentionally incremental. Phase 1 conventions are already
> partially realised by the compressor analysis polish work; later phases are
> proposals to be confirmed before implementation.
