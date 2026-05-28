# GitHub Actions Workflow Templates

> **Status:** ✅ 5 workflow templates documented here; matching active copies are installed in `.github/workflows/`.

These workflow files are CI/CD automation templates for the ABACUS project. The documentation copies live in `docs/workflows/`, and the active workflow copies live in `.github/workflows/`. The historical activation bundle remains in `workflows-to-install/` for traceability.

---

## Workflow Templates

| Workflow | Template | Trigger | Purpose |
|----------|----------|---------|---------|
| 🏥 Dashboard Health Check | [`dashboard-health.yml`](./dashboard-health.yml) | Daily cron (06:00 UTC), manual | Validates all dashboard HTML files exist, checks JS/CSS references, reports broken internal links, auto-opens issues on failure |
| 📄 Deploy Documentation | [`deploy-docs.yml`](./deploy-docs.yml) | Push to main (docs/**), manual | Validates HTML, deploys docs to GitHub Pages, verifies deployment |
| 📊 DMAIC Commit Metrics | [`dmaic-commit-metrics.yml`](./dmaic-commit-metrics.yml) | Push to main, post-deploy, manual | Collects per-commit DMAIC phase health metrics, generates Plotly charts, escalates on quality regression |
| 🚀 Release & Package | [`release.yml`](./release.yml) | Tag push (v*), manual | Validates critical files, runs syntax checks, packages dashboards, creates GitHub Release |
| 📝 Update Documentation | [`update-docs.yml`](./update-docs.yml) | Push to main (Python files), manual | Extracts module docstrings, updates API docs, generates deployment matrix, creates auto-PR |

---

## Activation Locations

```
.github/workflows/        ← Active location (executed by GitHub Actions)
docs/workflows/           ← Reference templates (this directory)
workflows-to-install/     ← Historical activation bundle
```

---

## Activation Status

```bash
cp workflows-to-install/*.yml .github/workflows/
git add -A && git commit -m "ci: activate workflows"
```

Activation completed on 2026-05-20. Use the copies in `.github/workflows/` for active automation.

## How to Monitor

1. **GitHub Actions tab:** [GBOGEB/ABACUS Actions](https://github.com/GBOGEB/ABACUS/actions)
2. **DMAIC Metrics Dashboard:** Available at `docs/api/dmaic_metrics_chart.html` after first run
3. **Dashboard Health:** Check daily run results in Actions tab

---

## Installation Log

See [INSTALLATION.md](./INSTALLATION.md) for the installed workflow status and verification results.

---

## Original Staging Command

```bash
cp docs/workflows/*.yml workflows-to-install/
```

> **Note:** Workflows in `docs/workflows/` are templates only. GitHub Actions executes the installed copies in `.github/workflows/`.
