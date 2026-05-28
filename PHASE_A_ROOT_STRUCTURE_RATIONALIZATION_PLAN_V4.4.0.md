# Phase A — Root Structure Rationalization Plan (v4.4.0)

**Execution Slot:** Sprint 1 / Wave 2 / Phase A  
**Date:** 2026-05-28

## Baseline

- Root files at repository top-level: **363**
- Root directories at repository top-level: **46**
- Root `.md` files: **293**
- Root `.py` files: **33**

## Goal

Reduce top-level file sprawl without changing runtime behavior by moving non-runtime artifacts into stable versioned/documentation zones.

## Batch Plan

### Batch A1 (safe, docs-only)
- Move historical session/report markdown files from repo root into:
  - `docs_versioned/handover/`
  - `docs_versioned/v4.4/` (new, if needed)
  - `handover/` where applicable
- Keep root-level pointers only (`README.md`, release summaries, essential navigation docs).

### Batch A2 (archive-heavy)
- Move legacy quick references and execution summaries not required by active workflows into:
  - `docs_versioned/v2.2_archived/`
  - `docs_versioned/v2.3/`
  - `docs_versioned/v3.3/`

### Batch A3 (script organization)
- Consolidate operational scripts to:
  - `scripts/` for utilities
  - `DMAIC_V3/` for DMAIC runtime tools
- Keep root-level executable entry points only where referenced by workflows.

## Guardrails

- Do not move files directly referenced by active workflows until path references are updated.
- Preserve currently referenced root scripts (example: `run_deployment_test_system.py`, `cicd_github_orchestrator.py`) during Phase A planning.
- Run these validations after each batch:
  - `bash scripts/verify_workflows.sh`
  - `python scripts/validate_docs_links.py`
  - `python -m pytest DMAIC_V3/tests -q`

## Exit Criteria for Phase A

- Rationalization batches and target destinations documented (this file).
- Candidate move classes identified with no runtime-path breakage introduced.
- Ready to execute Batch A1 in Sprint 2 / Wave 3.
