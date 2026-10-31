# Phase 1 Lessons Learned — Process Improvement Insights

> **Project:** MYRRHA QPLANT Cryogenic Dashboard v4.0.0  
> **Phase:** 1 — Stabilization & Alignment  
> **Date:** 2026-05-12  

---

## Executive Summary

Phase 1 revealed systemic issues in configuration management, version control, and build orchestration. While all 6 tasks were completed successfully (22/22 tests, 9.7/10.0 compliance), the root causes point to practices that, if unaddressed, will recur in future development cycles.

---

## Key Lessons

### Lesson 1: SSoT Must Be Enforced, Not Optional

**What happened:** `config.yaml` and `config_loader.py` existed as the Single Source of Truth, but two major generators (`build_dense_slides.py`, `build_v3_1.py`) contained hardcoded values that diverged from SSoT.

**Root cause:** No enforcement mechanism ensured all generators consumed SSoT. Developers could bypass it without triggering any warning or test failure.

**Impact:** 5 stale configuration values propagated to user-facing HTML pages, undermining data accuracy for engineering decisions.

**Recommendation:**
- Add build-time assertion: every generator must import `config_loader` and use SSoT values
- Create a linting rule that flags numeric literals matching known engineering parameters
- Consider Jinja2 templates where SSoT values are injected at render time

---

### Lesson 2: Version Labels Require Automated Injection

**What happened:** 26 version labels across 8 files were outdated — some by two major versions (v2.1.0 → v4.0.0).

**Root cause:** Version strings were hardcoded in HTML templates. Updating `VERSION.json` did not propagate to generated pages.

**Impact:** Users saw conflicting version indicators, creating confusion about which data was current.

**Recommendation:**
- All generators should read version from `cfg.version` (SSoT)
- Add a post-build check: `grep -r "v[0-9]\+\.[0-9]\+\.[0-9]\+" docs/*.html` and validate against current version
- Consider a `<meta name="dashboard-version">` tag for machine-readable version detection

---

### Lesson 3: Build Fragmentation Creates Invisible Drift

**What happened:** 7+ Python scripts needed to be run in a specific order. Developers ran subsets, causing partial builds and inconsistent output states.

**Root cause:** Each visualization module was developed independently with no orchestration layer.

**Impact:** Pages generated at different times reflected different configurations. No way to verify a complete, consistent build.

**Recommendation:**
- Always use `build_all.sh` for production builds (now created)
- Individual scripts should remain callable for development but marked as "dev-only"
- Add build timestamp and source script metadata to every generated page

---

### Lesson 4: Tests Validate Logic, Not Data Alignment

**What happened:** All 22 tests passed throughout Phase 1, even when configuration values were wrong. Tests checked math correctness but not whether the correct input values were used.

**Root cause:** Tests used fixed test inputs rather than validating against SSoT values in generated output.

**Impact:** False sense of security — green tests did not mean correct output.

**Recommendation:**
- Add integration tests that parse generated HTML and verify SSoT values appear
- Create a "config drift" test that reads key values from HTML and compares to `config.yaml`
- Separate unit tests (math) from integration tests (output correctness)

---

### Lesson 5: TODO Fragmentation Leads to Lost Work

**What happened:** 29 TODO items were scattered across 5 different sources (backlog.json, SLIDE_PACKAGES_STATUS.md, VISUAL_CATALOG.md, code comments, analysis findings).

**Root cause:** No single, authoritative task tracking system. Each contributor used their preferred tracking method.

**Impact:** Duplicate tracking, lost items, and no visibility into overall project health.

**Recommendation:**
- Maintain `phase1_consolidated_todos.md` as the single task tracker
- Add a script to scan for new TODO/FIXME comments and append to tracker
- Regular (weekly) review and prioritization of remaining items

---

### Lesson 6: Compliance Scoring Catches What Tests Miss

**What happened:** The triage compliance checker (`verify_triage.py`) identified requirement gaps that unit tests did not cover.

**Root cause:** Compliance checking evaluates against external requirements (SoR matrix, standards), while tests validate internal logic.

**Impact:** 9.7/10.0 score revealed 2 unmet requirements that were invisible to the test suite.

**Recommendation:**
- Run compliance check as part of every build (now included in `build_all.sh` step 7)
- Set minimum acceptable compliance threshold (recommended: 9.0/10.0)
- Track compliance score trend over time

---

## What Worked Well

| Practice | Why It Worked |
|----------|---------------|
| `config_loader.py` singleton pattern | Modules that used it had correct values automatically |
| Manifest with SHA256 hashes | Enables detection of unauthorized file changes |
| Plotly chart generation | Reproducible, data-driven visualizations |
| Test suite structure | Clear test file per module, easy to extend |
| Build log in `dist/build_all.log` | Full audit trail of build process |

## What Needs Improvement

| Area | Current State | Desired State |
|------|--------------|---------------|
| Template engine | Inline HTML in Python | Jinja2 or equivalent |
| Config enforcement | Optional import | Mandatory, validated |
| Version propagation | Manual, per-file | Automated, single-source |
| CI/CD | None | GitHub Actions or equivalent |
| Cross-referencing | None | Automated link registry |
| Monitoring | Static HTML reports | Real-time dashboard |

## Anti-Patterns to Avoid

1. **Copy-paste engineering values into HTML strings** — Always use config_loader
2. **Running individual build scripts in production** — Always use build_all.sh
3. **Skipping tests with `--skip-tests`** — Tests are a safety net, not optional
4. **Editing generated HTML files directly** — Edit the generator, then rebuild
5. **Adding TODO comments without updating the tracker** — Use the consolidated file

---

## Action Items from Lessons Learned

| # | Action | Owner | Priority | Phase |
|---|--------|-------|----------|-------|
| LL-1 | Refactor generators to use SSoT exclusively | Dev Team | 🔴 Critical | Phase 2 |
| LL-2 | Add version injection from config_loader to all generators | Dev Team | 🟡 High | Phase 2 |
| LL-3 | Create config drift detection test | QA | 🟡 High | Phase 2 |
| LL-4 | Implement pre-commit hooks for value validation | DevOps | 🟢 Medium | Phase 3 |
| LL-5 | Set up CI/CD pipeline | DevOps | 🟢 Medium | Phase 3 |
| LL-6 | Migrate to Jinja2 templates | Dev Team | 🟢 Medium | Phase 3 |
| LL-7 | Create real-time monitoring dashboard | Dev Team | 🟡 High | Phase 2 |

---

*Phase 1 Lessons Learned — Generated 2026-05-12*
