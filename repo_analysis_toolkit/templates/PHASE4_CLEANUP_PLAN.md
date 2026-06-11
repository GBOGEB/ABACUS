# Cleanup Plan — `<repo-name>`

**Phase:** 4 — DMAIC Improve
**Date:** YYYY-MM-DD

Break Phase 4 into a sequence of small, reviewable PRs. **No PR removes more than 50 files without explicit reviewer sign-off.**

---

### PR roadmap

| PR # | Title                                                       | Files touched | Risk  | Status |
| ---: | ----------------------------------------------------------- | ------------- | ----- | ------ |
|    1 | Add `.github/` skeleton (templates only)                   |               | Low   |        |
|    2 | Archive historical versions to `docs_versioned/`           |               | Med   |        |
|    3 | Remove Redundant + Corrupted files                          |               | High  |        |
|    4 | Reorganize main code into target structure                  |               | Med   |        |
|    5 | Rewrite top-level `README.md`                               |               | Low   |        |
|    6 | Add section READMEs                                         |               | Low   |        |
|    7 | Add `docs/index.html` + topic pages                         |               | Low   |        |
|    8 | Add handover book                                           |               | Low   |        |
|    9 | Install CI workflows                                        |               | Med   |        |
|   10 | Install health + metrics workflows                          |               | Low   |        |
|   11 | Wire Dependabot / Renovate + first dependency upgrade pass |               | Med   |        |
|   12 | Final fix-up (links, references, scorecard)                 |               | Low   |        |

---

### Per-PR checklist (apply to every entry above)

- [ ] One purpose only (no mixed structural + content changes).
- [ ] CI green before merge.
- [ ] Stakeholder reviewer added.
- [ ] Linked to the relevant Gap Analysis row.
- [ ] Updated `CHANGELOG.md`.

---

### Tags & rollback strategy

- Tag each merged PR with `phase-4-pr<N>`.
- If a regression is found, `git revert <merge-commit>` and open a follow-up issue.
- Final tag: `phase-4-complete`.
