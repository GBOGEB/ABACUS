# Workflow Installation Status

**Last Updated:** 2026-05-18  
**Installed By:** PR #397 (staged for manual activation)

---

## Installation Status

| # | Workflow | File | Status | Updated |
|---|---------|------|--------|-----------|
| 1 | Dashboard Health Check | `dashboard-health.yml` | ⏳ STAGED | 2026-05-18 |
| 2 | Deploy Documentation | `deploy-docs.yml` | ⏳ STAGED | 2026-05-18 |
| 3 | DMAIC Commit Metrics | `dmaic-commit-metrics.yml` | ⏳ STAGED | 2026-05-18 |
| 4 | Release & Package | `release.yml` | ⏳ STAGED | 2026-05-18 |
| 5 | Update Documentation | `update-docs.yml` | ⏳ STAGED | 2026-05-18 |

---

## Installation Details

All 5 workflow files have been copied from `docs/workflows/` to `workflows-to-install/`. They still need a manual move into `.github/workflows/` before GitHub Actions can discover and execute them.

### Source → Staging

```
docs/workflows/dashboard-health.yml      → workflows-to-install/dashboard-health.yml
docs/workflows/deploy-docs.yml           → workflows-to-install/deploy-docs.yml
docs/workflows/dmaic-commit-metrics.yml  → workflows-to-install/dmaic-commit-metrics.yml
docs/workflows/release.yml               → workflows-to-install/release.yml
docs/workflows/update-docs.yml           → workflows-to-install/update-docs.yml
```

### Originals Preserved

The original files in `docs/workflows/` are kept as reference templates. The staged copies in `workflows-to-install/` are ready for a maintainer to move into `.github/workflows/`.

---

## Verification

- [x] All YAML files pass syntax validation
- [x] Workflow permissions are correctly scoped
- [x] Trigger conditions verified
- [x] No path reference conflicts with existing workflows
- [x] No duplicate workflow names with existing workflows

---

## Manual Activation

```bash
cp workflows-to-install/*.yml .github/workflows/
rm -rf workflows-to-install/
git add -A && git commit -m "ci: activate workflows"
```

| Workflow | Activation After Move | First Run |
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
