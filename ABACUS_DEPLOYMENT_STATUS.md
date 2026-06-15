# ABACUS Deployment Status

Date: 2026-06-11

## Status definitions

- **Active:** workflow file is directly under `.github/workflows/` and has an `on:` trigger.
- **Disabled / pending:** workflow file is outside `.github/workflows/`, such as `.github/workflows-pending/`.
- **Deprecated:** workflow file is retained under `.github/workflows/legacy/` or superseded by an active workflow.

## Deployment, release, pages, and artifact workflows

| Workflow | Trigger | Active | Purpose |
| -------- | ------- | ------ | ------- |
| `.github/workflows/cd.yml` | `push`, `pull_request`, daily `schedule`, `workflow_dispatch` | Yes | DMAIC V3.3 CD pipeline; runs `DMAIC_V3.dmaic_v3_engine`, builds book/GLOOB artifacts, and uploads CD artifacts. |
| `.github/workflows/cd-unified.yml` | `push`, tag push, `pull_request`, daily `schedule`, `workflow_dispatch` | Yes | Unified DOW + Recursive DMAIC CD with lint, CI, DMAIC full cycle, artifact build, and release jobs. |
| `.github/workflows/deployment-enforcement.yml` | `workflow_dispatch` with environment input | Yes | DELTA_1 deployment governance gates for dev/stage/prod. |
| `.github/workflows/delta-1-deploy.yml` | `workflow_dispatch` | Yes | DELTA_1 deployment scaffold/workflow. |
| `.github/workflows/dow-main-cicd.yml` | `pull_request`, `push`, six-hour `schedule` | Yes | DOW main CI/CD; runs tests and `DMAIC_V3/full_pipeline_orchestrator.py`. |
| `.github/workflows/dow-scheduled.yml` | six-hour `schedule`, `workflow_dispatch` | Yes | Scheduled DOW pipeline execution; uploads execution logs. |
| `.github/workflows/gbogeb-abacus-integration-ci-cd.yml` | `push`, `pull_request`, `workflow_dispatch` | Yes, but path-stale | GBOGEB/ABACUS ↔ DOW integration; references root-level bridge files that do not match the located `staging/` bridge path. |
| `.github/workflows/release.yml` | tag push `v*`, `workflow_dispatch` | Yes | Release and package workflow with `contents: write` and Pages permissions. |
| `.github/workflows/delta-1-release.yml` | `workflow_dispatch` | Yes | DELTA_1 release workflow scaffold. |
| `.github/workflows/pages.yml` | `push` to `main` with runtime/pages paths, `workflow_dispatch` | Yes | QPLANT Pages runtime publish using Pages artifact upload/deploy actions. |
| `.github/workflows/deploy-docs.yml` | `push` to `main` for docs/dashboard paths, `workflow_dispatch` | Yes | Documentation deployment to GitHub Pages. |
| `.github/workflows/book-build.yml` | Markdown/book/script `push`, `pull_request`, `workflow_dispatch` | Yes | Builds DMAIC V3 book and uploads artifacts. |
| `.github/workflows/export-docs.yml` | docs/global index `push`, `workflow_dispatch` | Yes | Exports docs artifacts. |
| `.github/workflows/reports.yml` | daily `schedule`, `workflow_dispatch`, selected `push` | Yes | Generates and uploads project reports. |
| `.github/workflows/dmaic-commit-metrics.yml` | `push`, docs deploy `workflow_run`, `workflow_dispatch` | Yes | Per-commit metrics and post-deploy signal collection. |
| `.github/workflows/inventory.yml` | weekly `schedule`, `workflow_dispatch` | Yes | Repository inventory and audit artifacts. |
| `.github/workflows/review-artifact-validation.yml` | selected docs/SSOT `push` | Yes | Review artifact validation. |
| `.github/workflows/runtime-verification.yml` | `workflow_dispatch`, successful deployment enforcement `workflow_run` | Yes | Runtime readiness verification after deployment enforcement. |
| `.github/workflows/runtime-governance.yml` | `workflow_dispatch` | Yes | Runtime governance validation scaffold. |
| `.github/workflows/legacy/cd.yml.old` | legacy `on:` block retained in `.old` file | No | Deprecated CD workflow superseded by active `.github/workflows/cd.yml`. |
| `.github/workflows/legacy/dow-integration-ci-cd.yml.old` | legacy file under `.github/workflows/legacy/` | No | Deprecated DOW integration CI/CD workflow. |
| `.github/workflows-pending/deploy-docs.yml` | pending copy outside active workflow directory | No | Pending/disabled docs deploy copy. |
| `.github/workflows-pending/release.yml` | pending copy outside active workflow directory | No | Pending/disabled release copy. |
| `.github/workflows-pending/dashboard-health.yml` | pending copy outside active workflow directory | No | Pending/disabled dashboard health copy. |
| `DMAIC_V3/.github/workflows/cd-main.yml` | nested workflow path | Not active at repo root | DMAIC_V3 nested CD lineage; not counted as root GitHub Actions execution. |
| `DMAIC_V3/.github/workflows/release.yml` | nested workflow path | Not active at repo root | DMAIC_V3 nested release lineage; not counted as root GitHub Actions execution. |

## Active workflow summary

The active deployment surface is complete but overlapping: root workflows cover CD, release, Pages, reports/artifacts, DOW scheduled execution, and runtime verification. Deprecated workflows are isolated under `.github/workflows/legacy/`. Pending workflows are outside the active `.github/workflows/` directory. The only deployment blocker identified here is path drift in `gbogeb-abacus-integration-ci-cd.yml`.
