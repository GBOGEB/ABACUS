# GitHub Actions Workflow Templates

> **Status:** ⏳ 5 workflow templates documented here; matching activation copies are staged in `workflows-to-install/` pending manual move to `.github/workflows/`.

These workflow files are CI/CD automation templates for the ABACUS project. The documentation copies live in `docs/workflows/`, and the activation bundle lives in `workflows-to-install/`. GitHub Actions will only execute them after they are manually moved into `.github/workflows/`.

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
workflows-to-install/     ← Staged activation bundle
docs/workflows/           ← Reference templates (this directory)
```

---

## How to Activate

```bash
cp workflows-to-install/*.yml .github/workflows/
rm -rf workflows-to-install/
git add -A && git commit -m "ci: activate workflows"
```

## How to Monitor

1. **GitHub Actions tab:** [GBOGEB/ABACUS Actions](https://github.com/GBOGEB/ABACUS/actions)
2. **DMAIC Metrics Dashboard:** Available at `docs/api/dmaic_metrics_chart.html` after first run
3. **Dashboard Health:** Check daily run results in Actions tab

---

## Installation Log

See [INSTALLATION.md](./INSTALLATION.md) for the staged activation status and verification results.

---

## Original Staging Command

```bash
cp docs/workflows/*.yml workflows-to-install/
```

> **Note:** Workflows in `docs/workflows/` are templates only. Files in `workflows-to-install/` are the staged copies to move into `.github/workflows/`.
