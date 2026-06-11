# GitHub Pages Deployment Guide

> **Generated:** 2026-05-16 22:34

## GitHub Pages-Ready Assets

| File | Size | Has JS | Has CSS | Needs Backend | GH Pages? |
|------|------|--------|---------|---------------|----------|
| `docs/FINAL_HANDOVER.html` | 647B | ✅ | ❌ | ❌ | Yes |
| `docs/dashboard.html` | 1,371B | ❌ | ✅ | ❌ | Yes |
| `docs/index.html` | 1,725B | ❌ | ✅ | ❌ | Yes |
| `docs/deep_analysis_dashboard.html` | 21,060B | ✅ | ✅ | ❌ | Yes |
| `docs/handover_book.html` | 42,186B | ✅ | ✅ | ❌ | Yes |
| `cryo_dashboard_v0_3_0/index.html` | 34,824B | ✅ | ✅ | ❌ | Yes |

## Deployment Steps

### Option 1: Deploy `docs/` directory
1. Go to repository Settings → Pages
2. Source: Deploy from branch → `main` → `/docs` folder
3. All HTML dashboards in `docs/` will be served automatically

### Option 2: GitHub Actions Deployment
```yaml
# .github/workflows/deploy-pages.yml
name: Deploy to GitHub Pages
on:
  push:
    branches: [main]
    paths: ['docs/**']
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v4
      - uses: actions/upload-pages-artifact@v3
        with:
          path: docs/
      - uses: actions/deploy-pages@v4
```

### Recommended Dashboard Hosting

| Dashboard | Recommended Hosting | Notes |
|-----------|-------------------|-------|
| `docs/deep_analysis_dashboard.html` | GitHub Pages ✅ | Fully static, no API calls |
| `docs/index.html` | GitHub Pages ✅ | Landing page |
| `docs/FINAL_HANDOVER.html` | GitHub Pages ✅ | Static document |
| `docs/dashboard.html` | GitHub Pages ✅ | Static dashboard |
| `cryo_dashboard_v0_3_0/index.html` | GitHub Pages ✅ | Static visualization |
| `docs/handover_book.html` | GitHub Pages ✅ | This handover book |
