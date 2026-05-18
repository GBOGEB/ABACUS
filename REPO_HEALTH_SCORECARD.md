# Repository Health Scorecard

**A 100-point rubric for assessing the health of any software repository at a glance.**

> Use after Phase 1 (baseline), after Phase 4 (improve), and quarterly in Control. Anything < 60 is *critical*; anything ≥ 90 is *excellent*.

---

### Scoring overview

| Category          | Points |
| ----------------- | -----: |
| Documentation    |     25 |
| Organization     |     25 |
| Automation       |     25 |
| Governance       |     25 |
| **Total**         | **100** |

| Band      | Score    | Meaning                                                                    |
| --------- | -------- | -------------------------------------------------------------------------- |
| Excellent | 90 – 100 | Production-ready. Minor polish only.                                       |
| Good      | 75 – 89  | Healthy. Targeted improvements will get to Excellent.                      |
| Needs improvement | 60 – 74 | Functional but fragile. Plan a focused cleanup sprint.            |
| Critical  | < 60     | Apply the full DMAIC cleanup methodology. Do not ship critical changes.    |

---

### 1. Documentation  (0 – 25 points)

| Criterion                                                              | Points |
| ---------------------------------------------------------------------- | -----: |
| Top-level `README.md` exists and answers what / why / how-to-run / how-to-contribute. |  5 |
| Section READMEs in every top-level directory.                         |     5  |
| API documentation exists (auto-generated or hand-written).             |    5  |
| User guide + developer guide exist.                                    |    5  |
| Documentation is **up-to-date** (no `docs/**/*.md` > 90 days older than the code it describes). | 5 |
| **Subtotal**                                                           | **25** |

#### How to measure

- Run `python repo_analysis_toolkit/validate_cleanup.py --check docs`.
- Spot-check 3 random source files: does the doc still describe them correctly?

---

### 2. Organization  (0 – 25 points)

| Criterion                                                       | Points |
| --------------------------------------------------------------- | -----: |
| Clear directory structure (≤ 15 top-level entries, logical grouping). |   5  |
| Logical file placement (every file lives where its name suggests).    |   5  |
| Consistent naming (one convention per file type, applied 95%+).       |   5  |
| Version management (semver tags + `CHANGELOG.md` + `docs_versioned/` for major versions). | 5 |
| No redundancy (zero duplicate files in `classify_artifacts.py` output). |   5  |
| **Subtotal**                                                          | **25** |

#### How to measure

- `find . -maxdepth 1 -type d | wc -l` should be ≤ 15.
- Re-run `classify_artifacts.py`; "Redundant" column must be empty.
- `git tag --list "v*" | tail -5` should match the latest 5 entries of `CHANGELOG.md`.

---

### 3. Automation  (0 – 25 points)

| Criterion                                                | Points |
| -------------------------------------------------------- | -----: |
| CI/CD workflows in place (lint, build, test, deploy).    |    10  |
| Automated testing (unit + integration; coverage tracked). |    5  |
| Automated documentation (docs build / deploy on every change to `docs/`). | 5 |
| Health monitoring (daily dashboard check, broken-link check, dependency check). | 5 |
| **Subtotal**                                             | **25** |

#### How to measure

- Count workflows in `.github/workflows/` — should be ≥ 7.
- `gh workflow list --all` — all workflows last run within 30 days.
- Open `docs/index.html` — every linked dashboard returns 200.

---

### 4. Governance  (0 – 25 points)

| Criterion                                            | Points |
| ---------------------------------------------------- | -----: |
| `CONTRIBUTING.md` exists and is current.            |    5  |
| Issue + PR templates installed (≥ 4 issue templates, 1 PR template). |  5 |
| Branch protection on `main` (required reviews, required status checks, no force-push, includes admins). | 5 |
| Code review process documented and followed (PR approval rule enforced). | 5 |
| Maintenance plan published (`MAINTENANCE_SCHEDULE.md`). | 5 |
| **Subtotal**                                         | **25** |

#### How to measure

- `gh api repos/:owner/:repo/branches/main/protection` returns enforcement.
- `.github/ISSUE_TEMPLATE/*.md` count ≥ 4.
- Last 10 merged PRs all have ≥ 1 review approval.

---

### Scoring example — ABACUS v4.4.0

| Category       | Points earned | Notes                                                                |
| -------------- | ------------: | -------------------------------------------------------------------- |
| Documentation  |        24/25  | All criteria met; minor freshness gaps on some `v0.31` files.        |
| Organization   |        24/25  | 95+ artifacts classified; one duplicate cleanup script flagged Stale. |
| Automation     |        25/25  | 39 active workflows; DMAIC metrics live; daily health checks green.  |
| Governance     |        19/25  | All templates + contributing + maintenance live; **branch protection pending** (admin action). |
| **Total**      |     **92/25** | Wait — let's redo that.                                              |

**ABACUS total: 92 / 100 → Excellent.** Branch-protection is the single 5-point ceiling lift remaining.

---

### Quick template (copy into `REPO_HEALTH_SCORECARD_RESULTS.md`)

```markdown
# Repo Health Scorecard — <repo name>

Date: YYYY-MM-DD
Phase: 1 / 4 / Control

## Documentation (___ / 25)

- [ ] Top-level README (5)
- [ ] Section READMEs (5)
- [ ] API docs (5)
- [ ] User + developer guides (5)
- [ ] Docs are current (5)

## Organization (___ / 25)

- [ ] Clear top-level structure (5)
- [ ] Logical file placement (5)
- [ ] Consistent naming (5)
- [ ] Version management (5)
- [ ] No redundancy (5)

## Automation (___ / 25)

- [ ] CI/CD workflows (10)
- [ ] Automated testing (5)
- [ ] Automated docs (5)
- [ ] Health monitoring (5)

## Governance (___ / 25)

- [ ] Contributing guide (5)
- [ ] Issue + PR templates (5)
- [ ] Branch protection (5)
- [ ] Code review process (5)
- [ ] Maintenance plan (5)

**Total: ___ / 100**

### Top 3 things blocking the next 10 points
1.
2.
3.
```

---

### Re-scoring schedule

- Immediately after Phase 1 — baseline.
- Immediately after Phase 4 — improvement.
- Quarterly thereafter — drift detection.

Track the trend over time on `docs/dmaic-metrics.html` (or your equivalent dashboard).
