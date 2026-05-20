# Workflow Installation Status

**Last Updated:** 2026-05-20  
**Installed By:** Post-merge activation sync

---

## Installation Status

| # | Workflow | File | Status | Updated |
|---|---------|------|--------|-----------|
| 1 | Dashboard Health Check | `dashboard-health.yml` | ✅ ACTIVE | 2026-05-20 |
| 2 | Deploy Documentation | `deploy-docs.yml` | ✅ ACTIVE | 2026-05-20 |
| 3 | DMAIC Commit Metrics | `dmaic-commit-metrics.yml` | ✅ ACTIVE | 2026-05-20 |
| 4 | Release & Package | `release.yml` | ✅ ACTIVE | 2026-05-20 |
| 5 | Update Documentation | `update-docs.yml` | ✅ ACTIVE | 2026-05-20 |

---

## Installation Details

All 5 workflow files are now present in `.github/workflows/`, so GitHub Actions can discover and execute them. The `docs/workflows/` copies remain the reference templates, and `workflows-to-install/` is retained only as a historical activation bundle.

### Source → Active

```
docs/workflows/dashboard-health.yml      → .github/workflows/dashboard-health.yml
docs/workflows/deploy-docs.yml           → .github/workflows/deploy-docs.yml
docs/workflows/dmaic-commit-metrics.yml  → .github/workflows/dmaic-commit-metrics.yml
docs/workflows/release.yml               → .github/workflows/release.yml
docs/workflows/update-docs.yml           → .github/workflows/update-docs.yml
```

### Reference Copies Preserved

The original files in `docs/workflows/` are kept as reference templates. The historical copies in `workflows-to-install/` are preserved for traceability, while `.github/workflows/` is the live execution location.

---

## Verification

- [x] All YAML files pass syntax validation
- [x] Workflow permissions are correctly scoped
- [x] Trigger conditions verified
- [x] No path reference conflicts with existing workflows
- [x] No duplicate workflow names with existing workflows

---

## Activation Command Used

```bash
cp workflows-to-install/*.yml .github/workflows/
git add -A && git commit -m "ci: activate workflows"
```

| Workflow | Active Trigger | First Run |
|----------|-----------------------|-----------|
| `dashboard-health.yml` | Automatic (cron: daily 06:00 UTC) + manual | Next 06:00 UTC or manual dispatch |
| `deploy-docs.yml` | Automatic on push to `main` (docs/**) | Next push modifying docs/ |
| `dmaic-commit-metrics.yml` | Automatic on push to `main` | Immediately after activation push |
| `release.yml` | Manual or on tag push (`v*`) | Manual dispatch or `git tag v*` |
| `update-docs.yml` | Automatic on push to `main` (Python files) | Next push modifying Python code |

---

## Related

- **PR:** Phase 4 Final: Install Remaining CI/CD Workflows
- **Issue:** [#388 — Install CI/CD Workflows](https://github.com/GBOGEB/ABACUS/issues/388)
- **Issue:** [#394 — Phase 4 Tracking](https://github.com/GBOGEB/ABACUS/issues/394)
