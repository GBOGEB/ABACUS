# Workflow templates

Baseline GitHub Actions workflows that a DMAIC-cleaned repository should ship with. Copy any of these into your target repo's `.github/workflows/` and adjust the language-specific steps.

| File                  | Purpose                                                       |
| --------------------- | ------------------------------------------------------------- |
| `ci.yml`              | Lint + tests + coverage on every push and PR.                 |
| `repo-analysis.yml`   | Run the DMAIC toolkit; uploads reports as artifacts.          |
| `deploy-docs.yml`     | Auto-deploy `docs/` to GitHub Pages on every push to `main`.  |

### Installation

```bash
mkdir -p .github/workflows
cp repo_analysis_toolkit/workflow_templates/*.yml .github/workflows/
git add .github/workflows/
git commit -m "ci: install baseline DMAIC workflows"
```

### Required repository settings

For `deploy-docs.yml` to work:

1. Settings → Pages → Source: **GitHub Actions**.
2. Settings → Actions → General → Workflow permissions: **Read and write**.

For `repo-analysis.yml`:

- Schedule runs weekly — adjust the cron line as needed.
- Reports are kept 30 days; download from the Actions tab.
