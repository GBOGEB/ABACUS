---
title: Project documentation index
shortTitle: Docs index
---

# ABACUS Documentation Hub

This docs site now centers on a repository navigation view for **GBOGEB/ABACUS**.

## HTML navigation

- [Repository navigation hub](index.html)
- [Repository metrics dashboard](dashboard.html)

## Documentation articles

- [Docs content index](content/)
- Conceptual documentation is available in the `docs/content/` article set.
- Procedural documentation is available in the `docs/content/` article set.
- Reference documentation is available in the `docs/content/` article set.
- [Runtime reconstruction and continuity flow](content/runtime-reconstruction-continuity.md)

## Navigation focus

- Main repo hierarchy: `DMAIC_V3/`, `src/dmaic/`, `local_mcp/`, `scripts/`, `handover/`, `.github/workflows/`
- Functions and entry points: orchestrator, deployment runner, global index generator, metrics collectors, workflow analyzer
- Links and indexes: master indexes, handover indexes, workflow docs, repository roots
- Metrics and maturity: file inventory plus `maturity_assessment.json`
- Change logs: root and DMAIC V3 changelog families
- Bridge and self-smoke: bridge implementation, smoke workflow, bridge tests, maturity tracker
- Canonical artefacts by type: canonical index code, JSON/YAML registries, markdown indexes, dashboards, notebook assets

## Main repositories and bridges

- [GBOGEB/ABACUS](https://github.com/GBOGEB/ABACUS) — main repository
- [GBOGEB/CODEX](https://github.com/GBOGEB/CODEX) — linked standards repository
- [GBOGEB/morris.js](https://github.com/GBOGEB/morris.js) — linked charting reference

### ABACUS interconnect flow (upstream/downstream)

| Component | Upstream | Downstream | Shared source |
|---|---|---|---|
| Tuple metadata validation | `.github/workflows/ci.yml` | `DMAIC_V3_OUTPUT/tuple_metadata.validated.json` | `scripts/validate_tuple_metadata.py` |
| Interactive handover tracker | `docs/api/final_handover_tracker.json` | `docs/FINAL_HANDOVER.html` | `scripts/build_final_handover_tracker.py` |
| Phase-2 reconstruction manifest | `docs/api/phase2_reconstruction_manifest.json` | `DMAIC_V3_OUTPUT/reconstruction_manifest.validated.json` | `scripts/validate_reconstruction_manifest.py` |
| CODEX bridge | `GBOGEB/CODEX` policy/workflow patterns | ABACUS workflow checks + docs/workflows | `.github/workflows/ci-codex.yml` |
| Visualization bridge | `GBOGEB/morris.js` charting patterns | ABACUS HTML dashboards in `docs/` | `docs/assets` + dashboard pages |

## Manifest and packaging

- [manifest.yml](manifest.yml)
- Root packaging helper: `make docs-zip`
