# ABACUS — CI/CD Workflow Catalog

> **37 active workflows** · Last updated: 2026-05-18

## 📋 Overview

This directory contains all active GitHub Actions workflows for the ABACUS project.
Workflows are organized by function: core CI/CD, documentation, monitoring, DMAIC execution, and maintenance.

---

## 🔄 Workflow Catalog

### Core CI/CD Pipelines

| Workflow | File | Triggers | Description |
|----------|------|----------|-------------|
| ABACUS v032 CI/CD | `abacus-cicd.yml` | push, PR, manual | Main ABACUS CI/CD pipeline |
| Main CI/CD | `main.yml` | push, PR, manual | Primary CI/CD entry point |
| CI — ABACUS Matrix | `ci-abacus.yml` | push, PR, manual | Matrix-based CI for ABACUS modules |
| CI — CODEX Matrix | `ci-codex.yml` | push, PR, manual | Matrix-based CI for CODEX modules |
| CI Enhanced | `ci-enhanced.yml` | push, PR, manual | DOW + Recursive DMAIC enhanced CI |
| CI — Test System Bridge | `ci.yml` | push, PR | DMAIC V3 bridge integration tests |
| CD Pipeline | `cd.yml` | push, PR, schedule, manual | DMAIC V3.3 continuous deployment |
| CD Unified | `cd-unified.yml` | push, PR, schedule, manual | Unified CD with multi-platform validation |
| V2.3 Agent CI/CD | `v23-cicd.yml` | push, PR, manual | V2.3 agent-specific pipeline |

### DMAIC Execution & Metrics

| Workflow | File | Triggers | Description |
|----------|------|----------|-------------|
| DMAIC Enterprise CI | `dmaic-enterprise-ci.yml` | push, PR, manual | Enterprise-grade DMAIC CI |
| DMAIC Phase Execution | `dmaic-phase-execution.yml` | manual | Execute specific DMAIC phases |
| DMAIC Commit Metrics | `dmaic-commit-metrics.yml` | push, workflow_run, manual | Per-commit quality tracking with Plotly charts |
| Bridge CI | `bridge-ci.yml` | push, PR, manual | DMAIC V3 bridge integration tests with manual dispatch support |

### DOW Integration

| Workflow | File | Triggers | Description |
|----------|------|----------|-------------|
| DOW Integration | `dow-integration.yml` | push, PR, manual, schedule | DOW integration pipeline |
| DOW Main CI/CD | `dow-main-cicd.yml` | push, PR | Main DOW CI/CD pipeline |
| DOW Monitoring | `dow-monitoring.yml` | schedule, manual | DOW monitoring dashboard |
| DOW Scheduled | `dow-scheduled.yml` | schedule, manual | Scheduled DOW pipeline execution |
| GBOGEB/ABACUS ↔ DOW | `gbogeb-abacus-integration-ci-cd.yml` | push, PR, manual | Cross-repo DOW integration |

### Documentation & Deployment

| Workflow | File | Triggers | Description |
|----------|------|----------|-------------|
| Deploy Docs | `deploy-docs.yml` | push (docs/), manual | Deploy documentation to GitHub Pages |
| Update Docs | `update-docs.yml` | push (*.py), manual | Auto-extract docstrings and update API docs |
| Export Docs | `export-docs.yml` | push, manual | Export documentation artifacts |
| Validate Docs | `validate_docs.yml` | push, PR | Validate Markdown, YAML, and JSON |
| Book Build | `book-build.yml` | push, PR, manual | Build DMAIC V3 handbook |

### Monitoring & Health

| Workflow | File | Triggers | Description |
|----------|------|----------|-------------|
| Dashboard Health | `dashboard-health.yml` | daily 06:00 UTC, manual | Validate HTML dashboards and links |
| CI/CD Monitor | `ci_monitor_and_issue_creator.yml` | workflow_run, PR | Monitor CI runs and auto-create issues |
| Inventory Scan | `inventory.yml` | weekly, manual | Repository inventory and audit |
| Reports | `reports.yml` | weekly, manual, push | Generate project reports |

### Release & Packaging

| Workflow | File | Triggers | Description |
|----------|------|----------|-------------|
| Release & Package | `release.yml` | tag push (v*), manual | Build release artifacts and create GitHub Release |

### Quality & Formatting

| Workflow | File | Triggers | Description |
|----------|------|----------|-------------|
| Format Check | `format-check.yml` | push, PR, manual | Code formatting validation |
| Smoke Test | `smoke-test.yml` | PR, manual | Quick smoke tests for PRs |
| Tooling CI | `tooling-ci.yml` | push, PR, manual | Validate tooling and scripts |
| Validate Setup | `validate-setup.yml` | manual | Validate ABACUS environment setup |

### Maintenance & Automation

| Workflow | File | Triggers | Description |
|----------|------|----------|-------------|
| Branch Analysis | `branch-analysis.yml` | PR, manual | Auto-review and branch analysis |
| Branch Pruner | `branch-pruner.yml` | manual | Clean up stale branches |
| Copilot PR Creator | `copilot-pr-creator.yml` | manual | Create PRs from Copilot branches |
| Sprint Trigger | `sprint-trigger.yml` | schedule, manual | Sprint automation trigger |
| Recursive Build | `recursive-build.yml` | push, manual | Recursive documentation build |

---

## 📁 Legacy Workflows

Deprecated workflows are preserved in `.github/workflows/legacy/`:

| File | Notes |
|------|-------|
| `cd.yml.old` | Replaced by `cd-unified.yml` |
| `dow-integration-ci-cd.yml.old` | Replaced by `dow-integration.yml` |

---

## 🔒 Security Notes

- All workflows should specify least-privilege `permissions` blocks
- Actions are pinned to major versions (e.g., `@v4`)
- Dependabot monitors action version updates (`.github/dependabot.yml`)
- See `BRANCH_PROTECTION_RECOMMENDATIONS.md` for required status checks

---

## 📝 Adding New Workflows

1. Create the `.yml` file in this directory
2. Follow naming convention: `kebab-case.yml`
3. Include a `name:` field, `permissions:` block, and `concurrency:` group
4. Add the workflow to this README catalog
5. Test with `workflow_dispatch` before enabling automatic triggers
6. Update `CODEOWNERS` if the workflow covers new paths

---

## 📊 Workflow Templates

Reusable workflow templates are available in:
- `docs/workflows/` — Reference templates for the 5 newest workflows
- `repo_analysis_toolkit/workflow_templates/` — Generic CI/deploy/analysis templates
