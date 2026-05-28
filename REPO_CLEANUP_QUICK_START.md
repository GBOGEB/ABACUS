# Repository Cleanup — Quick Start Guide

**A day-by-day execution plan for applying the [DMAIC Repository Cleanup Methodology](./DMAIC_REPO_CLEANUP_METHODOLOGY.md) to a new repository.**

> Total: ~3 weeks of focused-engineer-time for a medium repo. Scale up or down using the time-estimate table in the main methodology doc.

---

### Day 1 — Initial Assessment  (2–4 hours)

| Step | Action                                                                                  | Tool / output                                    |
| ---: | --------------------------------------------------------------------------------------- | ------------------------------------------------ |
| 1.1  | `git clone --no-single-branch <repo>` into `~/repos/<name>`.                            | Local checkout.                                  |
| 1.2  | `git fetch --all --tags`.                                                               | All history pulled.                              |
| 1.3  | `git tag pre-cleanup-snapshot && git push origin pre-cleanup-snapshot`.                 | Safety net.                                      |
| 1.4  | `python repo_analysis_toolkit/analyze_repo.py --repo . --out reports/baseline.json`     | `reports/baseline.json`                          |
| 1.5  | Open `REPO_ASSESSMENT_INITIAL.md` and fill from the JSON.                               | Initial assessment.                              |
| 1.6  | Identify top 3 pain points (READ the JSON, then ask the team).                          | One-line per pain point.                         |
| 1.7  | Create GitHub issue **"DMAIC cleanup — baseline for `<repo>`"** and paste the summary.  | Public commitment.                               |

**Checklist**
- [ ] Repo cloned with full history.
- [ ] `pre-cleanup-snapshot` tag pushed.
- [ ] `baseline.json` produced and reviewed.
- [ ] Top 3 pain points written down.
- [ ] Baseline issue opened.

**Success criteria:** anyone can read the baseline issue in 5 minutes and understand the starting state.

**Common pitfalls**
- Skipping the tag step — you *will* want to roll back something.
- Running scripts on a shallow clone — git history will be incomplete.

---

### Days 2–3 — Deep Analysis  (1–2 days)

| Step | Action                                                                                            |
| ---: | ------------------------------------------------------------------------------------------------- |
| 2.1  | `python repo_analysis_toolkit/generate_lineage.py --repo . --out reports/lineage.md`              |
| 2.2  | `python repo_analysis_toolkit/classify_artifacts.py --repo . --out reports/classification.csv`    |
| 2.3  | Walk the CSV with a maintainer. Validate the Stale / Redundant / Corrupted columns.               |
| 2.4  | Write `LINEAGE_ANALYSIS.md`, `INTEGRATION_MAP.md`, and `ARTIFACT_CLASSIFICATION_MATRIX.csv`.      |
| 2.5  | `python repo_analysis_toolkit/create_dashboard.py --reports reports/ --out reports/dashboard.html`|
| 2.6  | Commit reports to a new branch `dmaic/phase-2-measure`.                                           |

**Checklist**
- [ ] Lineage diagram generated.
- [ ] Every file classified (no Unknowns left).
- [ ] Integration map complete (all external surfaces listed).
- [ ] Dashboard HTML reviewable in a browser.

**Required tools:** Python 3.11+, `git`, `pandas`, `plotly`, `networkx`.

**Common pitfalls**
- Auto-classifying without a maintainer review — the script gets ~80% right; the remaining 20% is the *important* 20%.
- Not deduplicating renamed-but-identical files (use the SHA-1 column in the CSV).

---

### Days 4–5 — Planning  (1 day)

| Step | Action                                                                                                 |
| ---: | ------------------------------------------------------------------------------------------------------ |
| 3.1  | Draft `TARGET_STRUCTURE.md` (see the ABACUS template in `repo_analysis_toolkit/templates/`).           |
| 3.2  | Draft `CLEANUP_PLAN.md` — break into 8–15 PRs, each ≤ 50 file moves.                                   |
| 3.3  | Hold a 30-min review with stakeholders. Adjust.                                                        |
| 3.4  | Set milestones in GitHub: `Phase-4-Improve-PR1`, `…-PR2`, … (one milestone per planned PR).            |
| 3.5  | Define a target score: ≥ 90 / 100 on `REPO_HEALTH_SCORECARD.md`.                                       |

**Checklist**
- [ ] Target structure agreed.
- [ ] Cleanup PR sequence defined.
- [ ] Milestones created.
- [ ] Score target written down.

**Common pitfalls**
- Planning one giant PR — *don't*. It is unreviewable and will block for weeks.
- Skipping the stakeholder review — surprises in Improve are 10× more expensive than surprises in Plan.

---

### Week 2 — Implementation  (3–5 days)

Execute the cleanup PRs in order. Recommended sequence:

| PR #  | Goal                                                                       |
| ----: | -------------------------------------------------------------------------- |
| PR 1  | Add `.github/` skeleton (templates only; no workflows yet).                |
| PR 2  | Move historical versions into `docs_versioned/`.                           |
| PR 3  | Delete Redundant + Corrupted artifacts (after a final diff).               |
| PR 4  | Reorganize main code into target structure.                                |
| PR 5  | Add / rewrite the main `README.md`.                                        |
| PR 6  | Add section READMEs (one per top-level directory).                         |
| PR 7  | Add `docs/index.html` launcher and topic landing pages.                    |
| PR 8  | Add handover book (`docs/handover_book.html`).                             |
| PR 9  | Install CI workflows (`ci.yml`, `deploy-docs.yml`, `release.yml`, …).      |
| PR 10 | Install quality + health workflows (`dashboard-health.yml`, `dmaic-metrics.yml`). |
| PR 11 | Wire Dependabot / Renovate.                                                |
| PR 12 | Final pass: fix any links, broken pages, missing references.               |

**Checklist**
- [ ] All PRs merged in order.
- [ ] No PR contains > 50 file moves without explicit sign-off.
- [ ] Every PR has a green CI status before merge.
- [ ] GitHub Pages successfully deploys after PR 7.

**Common pitfalls**
- Combining moves and edits in the same PR — reviewers can't see what changed.
- Letting workflows run before the structure is fixed — you'll spend hours debugging false-positive CI failures.

---

### Week 3 — Governance  (2 days)

| Step | Action                                                                                       |
| ---: | -------------------------------------------------------------------------------------------- |
| 5.1  | Enable branch protection on `main` (require PR review + status checks + include admins).    |
| 5.2  | Add `CODEOWNERS` (per-directory ownership).                                                  |
| 5.3  | Tag a `v1.0.0` (or appropriate first clean version) and let `release.yml` build the release. |
| 5.4  | Publish a one-page **launch announcement** + link to the new docs site.                      |
| 5.5  | Train the team: 30-min walk-through of the new structure + workflows.                        |
| 5.6  | Add the repo to your portfolio of "DMAIC-cleaned" repos (track the score).                   |
| 5.7  | Set a maintenance schedule (quarterly cleanup pass, monthly metrics review).                 |

**Checklist**
- [ ] Branch protection live.
- [ ] CODEOWNERS in place.
- [ ] First clean release tagged.
- [ ] Team trained.
- [ ] Maintenance schedule published.

**Required tools:** GitHub admin access (for branch protection), the team's calendar.

**Common pitfalls**
- Skipping the training session — the cleanest repo regresses fastest when contributors don't know the new rules.
- Enabling branch protection too early (Day 1 of Implementation) — it will block legitimate cleanup PRs.

---

### Total time

| Phase                | Engineer-time |
| -------------------- | ------------- |
| Initial assessment   | 2–4 hours     |
| Deep analysis        | 1–2 days      |
| Planning             | 1 day         |
| Implementation       | 3–5 days      |
| Governance           | 2 days        |
| **Total**            | **~3 weeks**  |

Calendar elapsed time: 4–6 weeks with normal review cycles.

---

### Required tools

- `git` ≥ 2.30
- Python ≥ 3.11
- Python packages: `pandas`, `plotly`, `networkx`, `pyyaml`, `markdown`, `jinja2`
- GitHub CLI (`gh`)
- A modern browser for visual verification
- Optional: `pre-commit`, `dependabot`, `renovate`

---

### Success criteria (overall)

- Repository health score ≥ 90 / 100 (see `REPO_HEALTH_SCORECARD.md`).
- All Improve PRs merged.
- GitHub Pages live.
- All baseline pain points closed in GitHub issues.
- A new contributor can clone, install, run, and submit a first PR in under 60 minutes.

---

### Common pitfalls — universal list

1. **Skipping the snapshot tag.** *Always* tag before touching.
2. **Auto-deleting without a maintainer review.** Even a 99% accurate classifier deletes the wrong file eventually.
3. **One giant PR.** Use small, reviewable PRs.
4. **Workflows before structure.** Fix the layout first; install CI second.
5. **No stakeholder loop.** Cleanup is 30% engineering and 70% expectation management.
6. **Forgetting branch protection.** The whole effort regresses within a quarter without it.
7. **Treating docs as optional.** Every workflow, every module, every script needs a one-paragraph explanation.

Apply the same playbook to every repository. The patterns repeat; the deliverables compound.
