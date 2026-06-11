# Phase C — Deployment Activation Checklist (v4.4.0)

**Execution Slot:** Sprint 1 / Wave 2 / Phase C  
**Date:** 2026-05-28

## Objective

Start deployment activation from existing CI/CD by using already-present workflows and environment gates.

## Workflow Evidence

- `.github/workflows/deploy-docs.yml`
  - Deploy job uses environment `github-pages`
  - Uses `actions/deploy-pages@v5`
- `.github/workflows/deployment-enforcement.yml`
  - Manual governance gate for `dev`, `stage`, `prod` environments
- `.github/workflows/main.yml`
  - Includes deployment readiness check
- `.github/workflows/dow-integration.yml`
  - Includes deploy job on `main` push

## Activation Checklist

### C1 — Repository environment readiness
- [ ] Confirm GitHub environment exists for `github-pages`
- [ ] Confirm environment protections for `dev`, `stage`, `prod`
- [ ] Confirm required reviewers/secrets per environment policy

### C2 — Workflow permissions and triggers
- [ ] Confirm `deploy-docs.yml` permissions (`pages: write`, `id-token: write`) remain enabled
- [ ] Confirm branch triggers map to intended deployment branches
- [ ] Confirm manual trigger paths (`workflow_dispatch`) for controlled deploys

### C3 — Deployment validation path
- [ ] Run `deploy-docs.yml` manually and validate post-deploy HTTP check
- [ ] Run `deployment-enforcement.yml` for `dev` then `stage`
- [ ] Validate `main.yml` deployment-check signal on latest main commit
- [ ] Validate DOW integration deploy path on controlled main push

### C4 — Governance closeout
- [ ] Record deployment run IDs and outcomes in execution tracker/session log
- [ ] Document failures and rollback actions if any
- [ ] Mark deployment activation complete when all checks are green

## Current State

Checklist started; execution of C1-C4 continues in Sprint 2 / Wave 3 and Sprint 3 / Wave 5.
