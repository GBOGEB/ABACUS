# GitHub Push Summary — MINERVA P&ID (W001–W005)

## Repository
- **Target:** https://github.com/GBOGEB/ABACUS  (default branch `main`)
- **Authenticated as:** `GBOGEB` (push/admin access confirmed)
- **Pull request:** [#546 — MINERVA QCELL/RFCELL P&ID subproject (W001–W005)](https://github.com/GBOGEB/ABACUS/pull/546)
- **PR state:** `open`, `mergeable: true`, base `main` ← head `minerva-pid-w001-w005`

## Scope decision (confirmed by user)
- **Option B — combined PR1 = W001–W005** (all work to date), single review unit.

## What was pushed
The full MINERVA project was nested as a **self-contained subproject under `MINERVA_PID/`**
(matching how `ABACUS` already holds sibling projects such as `ABACUS-UNIFIED`, `ABACUS-v031`).

| Item | Value |
| --- | --- |
| Files added (all under `MINERVA_PID/`) | **423** (source-of-record only) |
| Commits in PR | 1 (squashed subproject import) |
| Derived artifacts tracked | **0** — all git-ignored |

## Two branches on the remote
| Branch | Purpose |
| --- | --- |
| `minerva-pid-w001-w005` | **PR #546** into `main` — clean, conflict-free subdir addition |
| `pr1-w001-w005` | Standalone branch preserving the **granular wave-by-wave commit history** (15 commits) |

> The `ABACUS` `main` branch is a large multi-project monorepo that shares **no history** with the
> MINERVA work, so a flat PR into `main` was impossible. Nesting under `MINERVA_PID/` produces a
> clean, mergeable PR while the original per-wave history remains on `pr1-w001-w005`.

## Repo hygiene actions
1. **Removed `*_preview/` office-doc preview artifacts from the entire git history** (`git filter-repo`)
   — derived files; one contained a base64 PPTX media blob that tripped GitHub secret-scanning push
   protection (false positive, **not** a live credential). Added `*_preview/` to `.gitignore`.
2. **Force-added** the source-of-record tree under `MINERVA_PID/` to override the parent monorepo's
   aggressive root `.gitignore` (which ignores `*.json`, `*.pdf`, `reports/`, `output/`) so that
   essential source files (configs, segmentation data, W005 reports, `wave_status.json`) are tracked.

## Verification
- ✅ All derived outputs excluded from git (`data/model/`, `data/pemo/`, `data/excel/`, `output_v6/`, `publish/`, `reports/*.xlsx`)
- ✅ `make.sh` regeneration tested — exit 0
- ✅ 31/31 tests passing (integration 5 + colour 5 + W003/W004 10 + W005 11)
- ✅ Every changed file in the PR is under `MINERVA_PID/` (0 stray paths; no collision with existing `main` content)
- ✅ PR reports `mergeable: true`

## Next steps
1. Review PR #546 on GitHub.
2. Merge when approved (kept open — **not** auto-merged, per governance).
3. Optionally tag a release after merge, e.g. `minerva-pid/v1.0-w001-w005`.

---
*Subproject readme:* `MINERVA_PID/README.md` · *Full PR description:* `MINERVA_PID/docs/PR1_DESCRIPTION_COMBINED.md`
