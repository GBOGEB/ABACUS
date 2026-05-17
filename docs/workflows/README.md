# GitHub Actions Workflow Templates

> **Status:** ✅ All 5 workflows installed to `.github/workflows/` on 2026-05-18

These workflow files are CI/CD automation templates for the ABACUS project. They have been **installed** (copied) to `.github/workflows/` where GitHub Actions can execute them. The copies here serve as reference documentation.

---

## Installed Workflows

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| 🏥 Dashboard Health Check | [`dashboard-health.yml`](../../.github/workflows/dashboard-health.yml) | Daily cron (06:00 UTC), manual | Validates all dashboard HTML files exist, checks JS/CSS references, reports broken internal links, auto-opens issues on failure |
| 📄 Deploy Documentation | [`deploy-docs.yml`](../../.github/workflows/deploy-docs.yml) | Push to main (docs/**), manual | Validates HTML, deploys docs to GitHub Pages, verifies deployment |
| 📊 DMAIC Commit Metrics | [`dmaic-commit-metrics.yml`](../../.github/workflows/dmaic-commit-metrics.yml) | Push to main, post-deploy, manual | Collects per-commit DMAIC phase health metrics, generates Plotly charts, escalates on quality regression |
| 🚀 Release & Package | [`release.yml`](../../.github/workflows/release.yml) | Tag push (v*), manual | Validates critical files, runs syntax checks, packages dashboards, creates GitHub Release |
| 📝 Update Documentation | [`update-docs.yml`](../../.github/workflows/update-docs.yml) | Push to main (Python files), manual | Extracts module docstrings, updates API docs, generates deployment matrix, creates auto-PR |

---

## Active Workflow Location

```
.github/workflows/        ← Active (executed by GitHub Actions)
docs/workflows/           ← Reference templates (this directory)
```

---

## How to Monitor

1. **GitHub Actions tab:** [GBOGEB/ABACUS Actions](https://github.com/GBOGEB/ABACUS/actions)
2. **DMAIC Metrics Dashboard:** Available at `docs/api/dmaic_metrics_chart.html` after first run
3. **Dashboard Health:** Check daily run results in Actions tab

---

## Installation Log

See [INSTALLATION.md](./INSTALLATION.md) for detailed installation status and verification results.

---

## Original Installation Command

```bash
cp docs/workflows/*.yml .github/workflows/
```

> **Note:** Workflows in `docs/workflows/` are templates only. They must be in `.github/workflows/` to execute.
