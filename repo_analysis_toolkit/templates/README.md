# DMAIC Phase Templates

Ready-to-fill Markdown templates aligned with the **DMAIC Repo Cleanup Methodology**. Copy each template into your repo (e.g., `docs/governance/` or `audit/`), fill in the placeholders, and ship as living governance documents.

---

## 📋 Template Index

| # | Template | Phase | When to use |
|---|----------|-------|-------------|
| 1 | `PHASE1_REPO_ASSESSMENT_INITIAL.md` | **Define / Measure** | Baseline audit: counts, ages, owners, current state |
| 2 | `PHASE2_INTEGRATION_MAP.md` | **Measure / Analyze** | Map external integrations, APIs, workflows |
| 3 | `PHASE2_LINEAGE_ANALYSIS.md` | **Measure / Analyze** | Document version history, branches, tags |
| 4 | `PHASE3_CONTRADICTION_REPORT.md` | **Analyze** | Surface conflicts between docs, code, configs |
| 5 | `PHASE3_GAP_ANALYSIS.md` | **Analyze** | Identify missing docs, tests, governance |
| 6 | `PHASE3_ROOT_CAUSE_ANALYSIS.md` | **Analyze** | Trace failures/debt to systemic root causes |
| 7 | `PHASE4_CLEANUP_PLAN.md` | **Improve** | Action plan: what to delete, archive, refactor |
| 8 | `PHASE4_TARGET_STRUCTURE.md` | **Improve** | Define the target directory layout post-cleanup |
| 9 | `PHASE5_CONTRIBUTING.md` | **Control** | Contributor guide enforcing the new standards |
| 10 | `PHASE5_GOVERNANCE_FRAMEWORK.md` | **Control** | Long-term governance: review cadence, ownership |
| 11 | `PHASE5_MAINTENANCE_SCHEDULE.md` | **Control** | Recurring tasks: audit cadence, deprecation policy |

---

## 🛠️ Usage Pattern

```bash
# 1. Pick the template for your current phase
cp repo_analysis_toolkit/templates/PHASE1_REPO_ASSESSMENT_INITIAL.md \
   docs/governance/01_baseline_assessment.md

# 2. Fill placeholders (search for [TODO], [DATE], [OWNER], etc.)
$EDITOR docs/governance/01_baseline_assessment.md

# 3. Commit alongside the toolkit script outputs
git add docs/governance/01_baseline_assessment.md baseline.json
git commit -m "audit: complete phase 1 baseline assessment"
```

---

## 🧭 Workflow Alignment

Templates pair with the toolkit scripts:

| Script | Companion Templates |
|--------|---------------------|
| `analyze_repo.py` → `baseline.json` | `PHASE1_REPO_ASSESSMENT_INITIAL.md` |
| `classify_artifacts.py` → `classification.csv` | `PHASE3_GAP_ANALYSIS.md`, `PHASE4_CLEANUP_PLAN.md` |
| `generate_lineage.py` → `LINEAGE.md` | `PHASE2_LINEAGE_ANALYSIS.md` |
| `create_dashboard.py` → `dashboard.html` | `PHASE2_INTEGRATION_MAP.md` |
| `validate_cleanup.py` → `scorecard.json` | `PHASE5_GOVERNANCE_FRAMEWORK.md`, `PHASE5_MAINTENANCE_SCHEDULE.md` |

---

## 📐 Conventions

All templates follow the same pattern:

1. **Frontmatter** — Repo name, phase, date, owner, version
2. **Executive summary** — 3–5 sentences, key numbers
3. **Detailed findings / actions** — Tabular wherever possible
4. **Risks & assumptions** — Explicit
5. **Sign-off** — Reviewer + approver fields

---

## 🔗 Related Documents

- 📘 [DMAIC Methodology](../../DMAIC_REPO_CLEANUP_METHODOLOGY.md) — full playbook
- ⏱️ [Quick Start Guide](../../REPO_CLEANUP_QUICK_START.md) — day-by-day execution
- 📊 [Health Scorecard](../../REPO_HEALTH_SCORECARD.md) — 100-point rubric
- 🎬 [Example Dry-Run](../../EXAMPLE_DRY_RUN.md) — end-to-end walkthrough
