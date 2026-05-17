# GitHub Actions Workflow Templates

These workflow files are ready to be copied to `.github/workflows/` to enable CI/CD automation.

## Included Workflows

| File | Purpose | Trigger |
|------|---------|---------|
| `deploy-docs.yml` | Deploy docs to GitHub Pages | Push to main (docs/**), manual |
| `update-docs.yml` | Auto-update API docs on code changes | Push to main (DMAIC_V3/**, local_mcp/**) |
| `dashboard-health.yml` | Daily dashboard health checks | Cron (06:00 UTC daily), manual |
| `release.yml` | Build and publish releases | Tag creation (v*), manual |

## Installation

```bash
# Copy all workflows to the active directory
cp docs/workflows/*.yml .github/workflows/
git add .github/workflows/
git commit -m "ci: enable GitHub Actions workflows"
git push
```

> **Note:** Workflows placed in `docs/workflows/` are templates only. They must be in `.github/workflows/` to execute.
