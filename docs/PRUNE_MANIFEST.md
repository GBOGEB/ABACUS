<!-- markdownlint-disable MD013 -->
# Prune Manifest — ABACUS (list-only, nothing deleted)

> Federation actions **P4/P7** from [`INTEGRATION_REPORT.md`](INTEGRATION_REPORT.md)
> §4 items 6 & 7. **Safety:** this pass deletes nothing — no directory removed, no
> branch deleted, no force-push. Each item is a *candidate* for a future dedicated,
> reviewable PR. Verify independently before acting.

## 1. Stale snapshot directories (candidates to archive/remove)

Verified present on `main` at the time of writing:

| Directory | Size | Rationale | Recommended action |
|-----------|------|-----------|--------------------|
| `ABACUS-v031/` | 708K | Frozen version snapshot superseded by current tree | Archive out-of-tree, then remove in a dedicated PR |
| `ABACUS-v032/` | 968K | Frozen version snapshot superseded by current tree | Archive, then remove |
| `ABACUS_V21_DEPLOYMENT_PACKAGE/` | 56K | Old deployment package | Archive, then remove |
| `DELTA_1/` | 48K | Superseded delta snapshot | Confirm not referenced, then remove |
| `DMAIC_V3_OUTPUT/` | 160K | Generated output committed to the tree | Move to artifacts/ignore; remove from VCS |
| `demo_workspace/` | 12K | Scratch/demo workspace | Remove if unused |

**Before removing any of the above:** run `git grep -n "<dir-name>"` to confirm no
live code, workflow, or docs reference it, and check it is not an input to a CI job.

## 2. Stale remote branches (candidates to retire)

Observed remote branch count: **456**. Of these, **121** match
`auto/update-docs-YYYYMMDD-*` — automation branches that are typically merged or
obsolete.

| Pattern | Count | Recommended action |
|---------|------:|--------------------|
| `auto/update-docs-*` | 121 | Retire branches whose commits are already in `main` (merged) |
| merged feature branches | (audit) | Delete after confirming merge via `git branch -r --merged origin/main` |

Suggested audit (read-only; lists merged branches safe to retire):

```bash
git fetch origin --prune
# branches fully merged into main (safe-to-delete candidates):
git branch -r --merged origin/main | grep 'origin/auto/update-docs-' | sed 's# *origin/##'
# delete ONLY after review, one dedicated PR/cleanup window, e.g.:
#   git push origin --delete <branch>      # (NOT run by this pass)
```

## 3. DMAIC metrics auto-commit (noise reduction)

The DMAIC metrics auto-commit workflow re-triggers CI on every metrics push.
Recommended: append `[skip ci]` to that commit's message (federation item 8) so
metric bumps don't consume CI minutes. Not changed in this pass — flagged for the
workflow owner.

---
*No deletions, renames, or force-pushes were performed to produce this manifest.*
