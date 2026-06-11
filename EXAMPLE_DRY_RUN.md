# Example Dry Run — "Legacy-Dashboard-Project"

**A worked end-to-end example of the [DMAIC Repository Cleanup Methodology](./DMAIC_REPO_CLEANUP_METHODOLOGY.md) applied to a fictional but representative repository.**

> All commands shown are real. Outputs shown are illustrative of what a typical small-to-medium legacy repo produces.

---

### 0. The starting state

Fictional repo: `acme-internal/Legacy-Dashboard-Project`.

What we found on Day 0:

- 327 files at the repo root (mostly `.py`, `.md`, a few `.ipynb`).
- 3 partial `README` files (`README.md`, `README_old.md`, `README_NEW.md`) with conflicting instructions.
- 4 "version" directories: `v1/`, `v2/`, `v2_final/`, `latest/`.
- Two CI workflows in `.github/workflows/` — one broken since 2024, one disabled.
- No `CONTRIBUTING.md`, no issue templates, no `CODEOWNERS`.
- 184 commits total, 6 contributors, last commit 11 months ago, last *meaningful* commit ~18 months ago.
- Dashboard runs locally but only on one engineer's laptop; nobody knows the exact dependency tree.

Top 3 pain points captured:

1. "I can never tell which version is the real one."
2. "The dashboard breaks every time someone touches it because nothing is tested."
3. "Onboarding takes a week because there's no README that actually works."

---

### Phase 0 — Pre-Analysis Preparation

Commands run:

```bash
mkdir -p ~/repos/legacy-dashboard-cleanup
cd ~/repos/legacy-dashboard-cleanup

git clone --no-single-branch \
  https://github.com/acme-internal/Legacy-Dashboard-Project.git
cd Legacy-Dashboard-Project

git fetch --all --tags
git tag pre-cleanup-snapshot
git push origin pre-cleanup-snapshot

git checkout -b dmaic/phase-1-define
```

Output:

```
Cloning into 'Legacy-Dashboard-Project'...
remote: Counting objects: 4382, done.
Receiving objects: 100% (4382/4382), 28.6 MiB | 6.4 MiB/s, done.
 * [new tag]         pre-cleanup-snapshot -> pre-cleanup-snapshot
Switched to a new branch 'dmaic/phase-1-define'
```

Stakeholder list (collected in 30 minutes):

- @alice — original author, partial owner.
- @bob — current de-facto maintainer (writes most recent commits).
- @carol — data-science consumer; reads dashboard daily.
- @dave — platform engineer; cares about CI/security.

---

### Phase 1 — DEFINE — Repository Assessment

#### Command

```bash
python ~/tools/repo_analysis_toolkit/analyze_repo.py \
  --repo . \
  --out reports/baseline.json
```

#### Output (excerpt)

```
ANALYZE_REPO   v1.0
repo:        Legacy-Dashboard-Project
files:       1 247
top-level:   327 files / 11 dirs
commits:     184
contributors:    6
languages:   Python 71%, Markdown 18%, Jupyter 8%, YAML 2%, other 1%
readmes:     3 candidates  (README.md, README_old.md, README_NEW.md)
workflows:   2 in .github/workflows (1 active, 1 disabled)
tags:        12   (last: v2.0-rc4, 14 months ago)
branches:    9    (4 stale, last activity > 6 months)
license:     none detected
security:    no SECURITY.md detected
issue_templates: 0
pr_template:    none
docs_dir:    no /docs directory
score_estimate: 38 / 100
```

#### Filled-in `REPO_ASSESSMENT_INITIAL.md`

```markdown
# Repo Assessment — Legacy-Dashboard-Project

**Date:** 2026-05-18
**Branch:** dmaic/phase-1-define

## What this repo is supposed to do
Provide an internal real-time KPI dashboard for the acme-data team.

## Who uses it
- Data-science consumers (5 daily users).
- One downstream pipeline that hits `/api/kpi`.

## Top 3 pain points
1. Which version is real?
2. Nothing is tested; every change breaks the dashboard.
3. Onboarding takes a week.

## Entry points
- `app.py`  (Flask) — current production entry, port 8080.
- `legacy_app.py` — old version, still served on port 8081 by mistake.
- `notebooks/build_kpi.ipynb` — manual data preparation.

## Dependencies
- Python 3.9 (only — newer versions break `pandas==0.25`).
- Postgres 12 (read replica).
- Internal `acme-auth` library v0.4.

## Top 5 risks
1. Production runs `legacy_app.py` *and* `app.py`. Nobody knows which is authoritative.
2. `pandas==0.25` is 5 years old and CVE-flagged.
3. No tests — any change is a roll of the dice.
4. CI is disabled.
5. The single engineer who knows the dependency tree is leaving in 60 days.

## Success criteria (signed off by Alice + Bob + Carol + Dave)
- One canonical entry point.
- ≥ 80% test coverage on critical paths.
- CI green on every PR.
- Dependency upgrade plan to Python 3.11.
- New onboarding doc that gets a contributor running in < 60 minutes.
- Target score ≥ 85 / 100 within 3 weeks.
```

---

### Phase 2 — MEASURE — Deep Analysis

#### Commands

```bash
python ~/tools/repo_analysis_toolkit/generate_lineage.py \
  --repo . \
  --out reports/lineage.md \
  --diagram reports/lineage.svg

python ~/tools/repo_analysis_toolkit/classify_artifacts.py \
  --repo . \
  --out reports/classification.csv \
  --dedup
```

#### Lineage output (excerpt)

```
LINEAGE
v0.1 (2021-02-04)  →  v0.9 (2021-09-12)  →  v1.0 (2022-03-08)
   │
   ├── feature/multi-tenant   (abandoned, last commit 2023-04, never merged)
   ├── feature/api-rewrite     (merged into v1.0)
   └── refactor/python311      (open, 8 months stale)

v1.0  →  v2.0-rc1 (2023-08)  →  v2.0-rc4 (2024-03, current latest tag)

Branches with no recent activity (≥ 6 months):
- feature/multi-tenant
- feature/legacy-export
- bugfix/auth-2023
- experimental/streamlit-attempt
```

#### Classification CSV (top of file)

```csv
path,size_bytes,age_days,last_author,tag,confidence
app.py,18342,42,bob,Active,0.99
legacy_app.py,21551,488,alice,Stale,0.92
README.md,2104,512,alice,Stale,0.88
README_old.md,1108,1023,alice,Redundant,0.97
README_NEW.md,3210,42,bob,Active,0.95
v1/dashboard.py,17890,720,alice,Archived,0.91
v2/dashboard.py,18012,520,bob,Redundant,0.94
v2_final/dashboard.py,18342,42,bob,Active,0.98
latest/dashboard.py,0,7,bob,Corrupted,1.00
notebooks/build_kpi.ipynb,84512,140,carol,Active,0.93
...
```

Aggregate counts (from the dashboard generator):

| Tag         | Files |
| ----------- | ----: |
| Active      |   118 |
| Archived    |    47 |
| Stale       |    73 |
| Redundant   |    62 |
| Corrupted   |     4 |
| Unclassified |    23 |

After a 90-minute review with @alice and @bob, all 23 Unclassified entries get a tag.

---

### Phase 3 — ANALYZE — Root Cause & Patterns

#### `CONTRADICTION_REPORT.md` (excerpt)

```markdown
1. README.md and README_NEW.md describe different startup commands.
2. v2_final/dashboard.py and v2/dashboard.py are byte-identical except for whitespace.
3. requirements.txt pins pandas==0.25.0; setup.py says pandas>=1.0.
4. CI workflow expects Python 3.9; Dockerfile installs Python 3.11.
5. /api/kpi is documented in README_old.md but no code path serves it (regression!).
```

#### `ROOT_CAUSE_ANALYSIS.md` (excerpt — 5-whys for #1)

```
Q: Why are there two READMEs?
A: README_NEW.md was added but the old one was never deleted.

Q: Why was it not deleted?
A: The author was unsure if anyone still linked to it.

Q: Why was there no way to know who linked to it?
A: No inventory tooling. No CODEOWNERS. No deprecation process.

Q: Why no deprecation process?
A: No CONTRIBUTING.md or maintenance schedule.

Q: Why none of those?
A: The repo was inherited without a formal handover.

→ ROOT CAUSE: No governance pack from day one.
```

#### `GAP_ANALYSIS.md` (counts)

| Gap                  | Count |
| -------------------- | ----: |
| Missing docstrings   |   211 |
| Missing tests        |   118 |
| Missing CI stages    |     4 |
| Missing templates    |     5 |
| Missing branch protection | 1 |

---

### Phase 4 — IMPROVE — Cleanup & Organization

#### Target structure

```
Legacy-Dashboard-Project/
├── .github/
│   ├── workflows/      # ci, deploy-docs, release, dashboard-health
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── docs/
│   ├── index.html
│   ├── handover_book.html
│   ├── api/
│   └── versions/
├── docs_versioned/
│   ├── v1.0/
│   └── v2.0/
├── dashboard/        # was app.py and friends
├── tests/
├── scripts/
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
└── SECURITY.md
```

#### PR sequence executed

| PR | Description                                                         | LOC moved | Status |
| -: | ------------------------------------------------------------------- | --------: | ------ |
| 1  | Add `.github/` skeleton (templates only)                            |         0 | Merged |
| 2  | Move `v1/`, `v2/` into `docs_versioned/v1.0/`, `docs_versioned/v2.0/` |  +0 / -812 (renames) | Merged |
| 3  | Delete Redundant + Corrupted files (62 + 4 = 66 files)              |     -3104 | Merged |
| 4  | Reorganize `app.py` + `legacy_app.py` into `dashboard/` (single entry point) |  +18 / -91 | Merged |
| 5  | Rewrite `README.md`                                                |       +160 | Merged |
| 6  | Add section READMEs                                                |       +420 | Merged |
| 7  | Add `docs/index.html` + topic pages                                |       +680 | Merged |
| 8  | Add 6-chapter handover book                                        |     +1 240 | Merged |
| 9  | Install `ci.yml`, `deploy-docs.yml`, `release.yml`                 |       +380 | Merged |
| 10 | Install `dashboard-health.yml`, `dmaic-metrics.yml`                |       +290 | Merged |
| 11 | Wire Dependabot + first dependency upgrades                        |      +1 700 | Merged |
| 12 | Final fix-up: links, references, scorecard                         |       +110 | Merged |

After PR 12: dashboard runs on Python 3.11, all tests green, CI runs in 7 minutes, GitHub Pages live at `https://acme-internal.github.io/Legacy-Dashboard-Project/`.

---

### Phase 5 — CONTROL — Governance

Actions:

```bash
gh api -X PUT repos/acme-internal/Legacy-Dashboard-Project/branches/main/protection \
  --input branch-protection.json

gh release create v3.0.0 --notes-file RELEASE_NOTES.md
```

Maintenance schedule published in `MAINTENANCE_SCHEDULE.md`:

- Monthly: metrics review (Dave + Bob).
- Quarterly: re-run `classify_artifacts.py`; address all new Stale > 3.
- Annually: dependency upgrade pass.

---

### Before / after comparison

| Metric                              | Before        | After             |
| ----------------------------------- | ------------- | ----------------- |
| Files at root                       | 327           | 14                |
| READMEs                             | 3 (conflicting) | 1 (canonical)   |
| Version directories at root         | 4             | 0 (moved to `docs_versioned/`) |
| Tests                               | 0             | 184 (87% coverage) |
| Active workflows                    | 1             | 7                 |
| Docs site                           | None          | GitHub Pages live |
| Issue templates                     | 0             | 4                 |
| PR template                         | None          | Present           |
| Branch protection                   | Off           | On                |
| Onboarding time (clone → first PR)  | ~1 week       | 47 minutes (timed) |
| Health scorecard                    | **38 / 100**  | **91 / 100**      |

---

### Final deliverables produced

- `REPO_ASSESSMENT_INITIAL.md`
- `LINEAGE_ANALYSIS.md` + `lineage.svg`
- `ARTIFACT_CLASSIFICATION_MATRIX.csv`
- `INTEGRATION_MAP.md`
- `CONTRADICTION_REPORT.md`
- `ROOT_CAUSE_ANALYSIS.md`
- `GAP_ANALYSIS.md`
- `TARGET_STRUCTURE.md`
- `CLEANUP_PLAN.md`
- `DOCUMENTATION_OUTLINE.md`
- New `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md`
- `docs/` (index, handover book, topic pages)
- `docs_versioned/v1.0/`, `docs_versioned/v2.0/`
- 7 active workflows
- `MAINTENANCE_SCHEDULE.md`
- `GOVERNANCE_FRAMEWORK.md`
- `REPO_HEALTH_SCORECARD_RESULTS.md` (38 → 91)
- v3.0.0 release tag + GitHub Release

---

### Lessons learned (applicable to every repo)

1. **The biggest payoff is in Phase 2 (Measure).** Classification is what unlocks every later decision.
2. **A messy repo is a *governance* problem before it is an engineering problem.** Fix the templates first; the rest follows.
3. **Stakeholder loops are the difference between a cleanup that sticks and one that regresses in 6 months.**
4. **Tag often.** `pre-cleanup-snapshot`, `phase-2-measure`, `phase-4-improve-pr3`, etc.
5. **Automate every manual step you do twice.** The scripts in `repo_analysis_toolkit/` paid for themselves in the 3rd PR.

Apply the same playbook to every repository. The pattern repeats; the deliverables compound; the score climbs.
