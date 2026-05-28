# DMAIC Repository Cleanup Methodology

**A reusable, iteration-based playbook for transforming scattered repositories into production-ready, governed, continuously-validated systems.**

> Derived from the GBOGEB/ABACUS cleanup that delivered v4.4.0 (95% completion, 92.5/100 quality, 558 commits analyzed, 39 active workflows, GitHub Pages live).

---

### Introduction

#### Purpose

Provide a deterministic, repeatable framework for taking *any* messy software repository — legacy monorepo, abandoned research code, multi-version analytics project, half-documented prototype — and ending up with:

- A clean, navigable structure.
- Full version lineage and history traceability.
- Production-grade CI/CD automation.
- A documentation site (handover book + topic dashboards).
- Governance (templates, contribution rules, branch protection).
- Continuous quality metrics.

#### When to use it

- A repository has > 50 files at the root with no clear hierarchy.
- Multiple parallel versions exist with unclear lineage (`v1`, `v2.1`, `legacy`, `final-final`).
- The README either doesn't exist, is empty, or contradicts the code.
- CI/CD is missing, broken, or partially configured.
- Stakeholders disagree on what the repo is, who owns it, or what state it's in.
- An audit, handover, or production release is approaching.

#### Expected outcomes

- **Quality score ≥ 90 / 100** on the repository health scorecard.
- **Documentation completeness ≥ 95%** of code surface.
- **CI/CD coverage** of every code path (test, lint, build, deploy).
- **Public landing page** (e.g., GitHub Pages) with topic dashboards.
- **Governance pack** (issue/PR templates, contributing guide, branch protection, release template).
- A **handover book** that a new contributor can read in one sitting.

#### Time estimates

| Repo size                         | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | **Total** |
| --------------------------------- | ------: | ------: | ------: | ------: | ------: | --------: |
| Small (< 100 files, < 50 commits) |   0.5 d |   1.0 d |   0.5 d |   1.0 d |   0.5 d |   3.5 days |
| Medium (100–500 files, < 200 commits) | 1 d |   2 d   |   1 d   |   3 d   |   1 d   |   8 days   |
| Large (500–2 000 files, < 1 000 commits) | 2 d | 3 d  |  2 d   |   5 d   |   2 d   |  14 days   |
| ABACUS-scale (2 000+ files, 600+ commits) | 3 d | 4 d | 3 d  |   7 d   |   2 d   |  19 days   |

These are *focused-engineer-days*; calendar elapsed time is typically 2–3× higher because of reviews and stakeholder loops.

---

### Phase 0 — Pre-Analysis Preparation

Goal: get a clean workspace and an honest baseline before touching anything.

| Step | Action                                                                                     |
| ---: | ------------------------------------------------------------------------------------------ |
| 0.1  | `git clone --no-single-branch <repo>` into a dedicated workspace.                          |
| 0.2  | `git fetch --all --tags` to pull every branch and tag.                                     |
| 0.3  | Take a **read-only snapshot** (`git tag pre-cleanup-snapshot && git push origin --tags`).  |
| 0.4  | Run `scripts/analyze_repo.py` (see `repo_analysis_toolkit/`) to produce a baseline JSON.   |
| 0.5  | Open an inventory issue: *"DMAIC cleanup — baseline assessment for `<repo>`."*             |
| 0.6  | Identify stakeholders (CODEOWNERS, last 5 committers, anyone on the README).               |
| 0.7  | Define success criteria with stakeholders (target score, target deadline, must-haves).     |
| 0.8  | Create branch `dmaic/phase-1-define`.                                                      |

Deliverables: `pre-cleanup-snapshot` tag, baseline JSON, GitHub inventory issue, stakeholder list.

---

### Phase 1 — DEFINE — Repository Assessment

> DMAIC Define phase: *Clearly state what we're working on, who cares, and what "done" looks like.*

#### 1.1 Initial scan

Use `repo_analysis_toolkit/analyze_repo.py` and capture:

- File / directory counts.
- Language breakdown.
- Total commits, contributors, first-commit and last-commit dates.
- Branch and tag list.
- Documentation presence (any `README*`, `docs/`, `*.md`).
- Workflow presence (`.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, etc.).
- License + security files (`SECURITY.md`, `CODE_OF_CONDUCT.md`).

#### 1.2 Stakeholder requirements

Interview each stakeholder for 15 minutes. Capture in `REPO_ASSESSMENT_INITIAL.md`:

- What is this repo *supposed* to do?
- Who actually uses it (people, services, downstream repos)?
- Top 3 pain points right now?
- What would "ideal" look like in 3 months?
- Any constraints (compliance, deadlines, frozen branches)?

#### 1.3 Current state documentation

Produce a one-page **State of the Repo** in `REPO_ASSESSMENT_INITIAL.md`:

- Purpose (1 sentence).
- Entry points (files actually executed in production).
- External dependencies (pip / npm / system).
- Main vs. auxiliary components.
- Top 5 risks.

#### Phase 1 deliverables

- `REPO_ASSESSMENT_INITIAL.md`
- Issue tracking sheet (one row per known problem)
- Stakeholder requirements doc
- A signed-off **success criteria** statement

---

### Phase 2 — MEASURE — Deep Analysis

> DMAIC Measure phase: *Quantify everything before changing anything.*

#### 2.1 Quantitative analysis

Run `repo_analysis_toolkit/classify_artifacts.py`:

- Lines of code per directory.
- Commit frequency per timeframe (daily, weekly, monthly).
- Contributor concentration (bus-factor).
- File age distribution.
- Duplicate / near-duplicate file detection (hash + fuzzy match).
- Largest files and largest directories.

#### 2.2 Version lineage

Run `repo_analysis_toolkit/generate_lineage.py`:

- Walk `git log --all` and tag every version.
- Build a Mermaid / Graphviz diagram of branch ancestry.
- Map feature evolution: when did each major capability appear?
- Mark abandoned branches (no commits in ≥ 6 months, no merge into `main`).
- Emit `LINEAGE_ANALYSIS.md`.

#### 2.3 Artifact classification

Every file gets one of five tags (matrix in `ARTIFACT_CLASSIFICATION_MATRIX.csv`):

| Tag        | Rule of thumb                                                                                 |
| ---------- | --------------------------------------------------------------------------------------------- |
| Active     | Touched in last 90 days *or* referenced by a current entry point.                             |
| Archived   | Not active, but referenced by docs / historical decisions; valuable.                          |
| Stale      | Not active, not referenced, but may contain patterns worth keeping; review before deleting.   |
| Redundant  | Duplicate of an Active file or superseded by a newer version; safe to delete after diff.      |
| Corrupted  | Zero-byte, broken, partial, unparseable; mark for deletion.                                   |

#### 2.4 Integration points

Map external surface in `INTEGRATION_MAP.md`:

- External APIs called.
- Databases / message buses connected to.
- Downstream consumers (who imports / fetches us?).
- CI/CD secrets used.
- Cloud resources provisioned.

#### Phase 2 deliverables

- `LINEAGE_ANALYSIS.md` (+ Mermaid / SVG diagram)
- `ARTIFACT_CLASSIFICATION_MATRIX.csv`
- `INTEGRATION_MAP.md`
- Baseline metrics JSON (committed to `docs/api/`)

---

### Phase 3 — ANALYZE — Root Cause & Pattern Recognition

> DMAIC Analyze phase: *Understand why the repo got into its current state so we don't recreate the mess.*

#### 3.1 Identify contradictions

For each contradiction found, log in `CONTRADICTION_REPORT.md`:

- Conflicting documentation (e.g., README says v2, code is v3).
- Version mismatches between modules.
- Duplicate functionality (two cleanup scripts that do the same thing differently).
- Dead code paths (functions never called).

#### 3.2 Root cause analysis

For the top 5 contradictions, run a 5-Whys in `ROOT_CAUSE_ANALYSIS.md`:

- Why did this artifact go stale?
- What caused fragmentation across versions?
- Why are versions unclear?
- What process gap let this in?

#### 3.3 Pattern recognition

Capture **patterns** (positive and negative) in `ROOT_CAUSE_ANALYSIS.md`:

- Common file structures already used (good — adopt them as the standard).
- Naming conventions (or lack thereof — define one).
- Documentation patterns (where docs *do* exist, what do they look like?).
- Development workflows (who branches how, who reviews what).

#### 3.4 Gap analysis

Produce `GAP_ANALYSIS.md`:

- Missing documentation (per directory).
- Missing tests (per module).
- Missing CI/CD (per pipeline stage).
- Missing version control (uncommitted patterns, tags that don't match versions).
- Missing governance (templates, contributing, branch protection).

#### Phase 3 deliverables

- `CONTRADICTION_REPORT.md`
- `ROOT_CAUSE_ANALYSIS.md`
- `GAP_ANALYSIS.md`
- A prioritized **Improve backlog**

---

### Phase 4 — IMPROVE — Cleanup & Organization

> DMAIC Improve phase: *Execute the plan. This is where 60–70% of the calendar time goes.*

#### 4.1 Create target structure

Capture in `TARGET_STRUCTURE.md` the ideal layout. ABACUS adopted:

```
<repo>/
├── .github/                  # CI/CD, templates, governance
├── docs/                     # Public-facing site (GitHub Pages)
├── docs_versioned/           # Historical versions preserved
├── <core-engine>/            # Main runtime code
├── <agent-or-service>/       # Optional auxiliary services
├── scripts/                  # Operational tooling
├── README.md                 # Single canonical entry
├── CHANGELOG.md
├── CONTRIBUTING.md
└── SECURITY.md
```

Adapt naming to your domain; keep the *shape*.

#### 4.2 Cleanup actions

Captured in `CLEANUP_PLAN.md`, executed in small, reviewable PRs:

1. Move files to logical locations (one PR per directory).
2. Archive old versions to `docs_versioned/` or `legacy/`.
3. Delete confirmed Redundant + Corrupted artifacts.
4. Standardize naming (`SCREAMING_SNAKE.md`, `kebab-case.yml`, `snake_case.py`).
5. Add front-matter / file-level docstrings to every Active file.

> Rule: **no PR may delete more than 50 files without an explicit reviewer sign-off.**

#### 4.3 Documentation creation

Captured in `DOCUMENTATION_OUTLINE.md`:

- Main `README.md` — what / why / how to run / how to contribute.
- Section READMEs for every top-level directory.
- API documentation (auto-generated from docstrings when possible).
- User guide and developer guide.
- Version migration guides between major versions.
- A **Handover Book** (12 chapters or fewer) as `docs/handover_book.html`.

#### 4.4 Automation setup

Install these baseline workflows (templates in `repo_analysis_toolkit/workflow_templates/`):

| Workflow              | Purpose                                                       |
| --------------------- | ------------------------------------------------------------- |
| `ci.yml`              | Lint, unit tests, build on every push & PR.                   |
| `deploy-docs.yml`     | Auto-deploy `docs/` to GitHub Pages.                          |
| `dashboard-health.yml`| Daily validation of HTML dashboards.                          |
| `release.yml`         | Tag-driven release with packaged artifacts + auto notes.      |
| `update-docs.yml`     | Auto-PR documentation refresh when code changes.              |
| `dmaic-metrics.yml`   | Per-commit quality metric calculation + chart.                |
| `inventory.yml`       | Weekly repo inventory snapshot.                               |

#### Phase 4 deliverables

- `TARGET_STRUCTURE.md`
- `CLEANUP_PLAN.md` (with PR-by-PR breakdown)
- `DOCUMENTATION_OUTLINE.md`
- 7+ active workflows
- New `docs/` site live

---

### Phase 5 — CONTROL — Governance & Maintenance

> DMAIC Control phase: *Lock in the gains so the repo cannot regress.*

#### 5.1 Establish governance

Add / configure:

- `CONTRIBUTING.md` (workflow, code style, review expectations).
- `CODE_OF_CONDUCT.md`.
- `.github/PULL_REQUEST_TEMPLATE.md`.
- `.github/ISSUE_TEMPLATE/` — at minimum `bug_report.md`, `feature_request.md`, `documentation_improvement.md`, `question.md`.
- `.github/RELEASE_TEMPLATE.md`.
- **Branch protection** on `main` (require PR review, status checks, no force-push, include admins).
- `CODEOWNERS`.

#### 5.2 Monitoring setup

- Quality metrics tracked on a public dashboard (`docs/dmaic-metrics.html`).
- Automated health checks (`dashboard-health.yml`, broken-link checker).
- Documentation freshness check (warn if any `docs/**/*.md` is > 90 days older than the code it documents).
- Dependency updates (Dependabot / Renovate).

#### 5.3 Continuous improvement

- Quarterly cleanup pass (re-run the artifact classifier).
- Version deprecation process (announce 1 minor release ahead).
- Documentation review cycle (every 6 months).
- Metrics review monthly with the maintainers.

#### Phase 5 deliverables

- `CONTRIBUTING.md`
- `GOVERNANCE_FRAMEWORK.md`
- `MAINTENANCE_SCHEDULE.md`
- Branch protection enabled
- Dependabot live

---

### Cross-cutting principles

1. **One change, one PR.** Never mix structural moves with content edits.
2. **Tag before you touch.** `pre-cleanup-snapshot`, `phase-1-baseline`, `phase-2-measure`, etc.
3. **Measure twice, cut once.** No deletions before classification is complete.
4. **Documentation is a deliverable, not a follow-up.** A workflow without docs counts as 0% done.
5. **Automate the next iteration.** Every manual step you do twice becomes a script in `repo_analysis_toolkit/`.
6. **Stakeholder loops.** End each phase with a 15-minute review with the originally-interviewed stakeholders.

---

### Phase checklists (quick reference)

#### Phase 1 — Define
- [ ] Repo cloned with all branches + tags
- [ ] `pre-cleanup-snapshot` tag pushed
- [ ] `analyze_repo.py` baseline JSON produced
- [ ] Stakeholders interviewed
- [ ] `REPO_ASSESSMENT_INITIAL.md` written
- [ ] Success criteria signed off

#### Phase 2 — Measure
- [ ] `classify_artifacts.py` run; CSV produced
- [ ] `generate_lineage.py` run; diagram produced
- [ ] `LINEAGE_ANALYSIS.md` written
- [ ] `INTEGRATION_MAP.md` written
- [ ] Metrics committed to `docs/api/`

#### Phase 3 — Analyze
- [ ] `CONTRADICTION_REPORT.md` written
- [ ] `ROOT_CAUSE_ANALYSIS.md` written
- [ ] `GAP_ANALYSIS.md` written
- [ ] Improve backlog prioritized

#### Phase 4 — Improve
- [ ] `TARGET_STRUCTURE.md` agreed
- [ ] Moves executed (one PR per dir)
- [ ] Redundant + Corrupted artifacts removed
- [ ] All top-level + section READMEs written
- [ ] Handover book published
- [ ] 7+ workflows active
- [ ] GitHub Pages live

#### Phase 5 — Control
- [ ] Contributing guide live
- [ ] All issue + PR templates live
- [ ] Branch protection enabled
- [ ] Dependabot / Renovate live
- [ ] Quality dashboard live
- [ ] Maintenance schedule published

---

### Companion artefacts

| File                                       | Purpose                                                |
| ------------------------------------------ | ------------------------------------------------------ |
| `REPO_CLEANUP_QUICK_START.md`              | Day-by-day execution guide for new repositories.       |
| `REPO_HEALTH_SCORECARD.md`                 | Scoring rubric (out of 100).                           |
| `EXAMPLE_DRY_RUN.md`                       | Worked example on a fictional repo.                    |
| `repo_analysis_toolkit/`                   | Five reusable Python scripts + YAML config.            |
| `repo_analysis_toolkit/templates/`         | Pre-built phase templates (`PHASE1_*`, `PHASE2_*`, …). |

Apply this methodology to any repository, in any language, of any size. The DMAIC structure is invariant; only the contents of each deliverable change.
