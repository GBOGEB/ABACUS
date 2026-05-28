# Maintenance Schedule — `<repo-name>`

**Phase:** 5 — DMAIC Control
**Date:** YYYY-MM-DD

The recurring tasks that keep the repository healthy after the cleanup.

---

### Weekly

| Task                                                      | Owner | Tool / workflow             |
| --------------------------------------------------------- | ----- | --------------------------- |
| Review Dependabot / Renovate PRs                          |       | `dependabot.yml`            |
| Confirm `dashboard-health.yml` green                       |       | `.github/workflows/dashboard-health.yml` |

### Monthly

| Task                                                      | Owner | Tool / workflow             |
| --------------------------------------------------------- | ----- | --------------------------- |
| Review DMAIC quality metrics trend                         |       | `docs/dmaic-metrics.html`   |
| Sign off on the metrics in the team channel                |       |                             |
| Triage stale issues (no activity > 90 days)                |       | GitHub UI                   |

### Quarterly

| Task                                                      | Owner | Tool / workflow             |
| --------------------------------------------------------- | ----- | --------------------------- |
| Re-run `classify_artifacts.py` and address new Stale/Redundant |    | `repo_analysis_toolkit/`    |
| Re-run `validate_cleanup.py` and confirm score ≥ target    |       | `repo_analysis_toolkit/`    |
| Review and update section READMEs for accuracy             |       |                             |

### Annually

| Task                                                      | Owner | Tool / workflow             |
| --------------------------------------------------------- | ----- | --------------------------- |
| Major dependency upgrade pass                              |       |                             |
| Re-baseline the methodology (refresh templates)            |       |                             |
| Archive obsolete versions to `docs_versioned/`             |       |                             |

---

### Deprecation process

1. Announce deprecation in `CHANGELOG.md` under "Deprecated".
2. Add deprecation warnings in code.
3. Wait at least **one minor release**.
4. Remove the deprecated API in the next major release.
5. Move corresponding docs to `docs_versioned/`.

### Versioning rules

- SemVer enforced by `release.yml`.
- `CHANGELOG.md` updated **before** every tag.
- Tags pushed only after CI is green on `main`.

---

### Escalation

If the quality score regresses below **75 / 100** in any monthly review, open a tracking issue tagged `regression` and assign to the maintainer. Run a Phase 2 + Phase 4 mini-cleanup within 30 days.
