# Branch Retirement Runbook

This runbook turns the branch-triage methodology into a repeatable process for ABACUS and sibling repositories. It is intentionally conservative: active PR branches, protected branch names, the selected base branch, and branches without reliable PR metadata are preserved until review is complete.

## Safety invariants

- The selected `--base` branch is always `KEEP`, even if it is a custom name such as `trunk`.
- A closed-but-unmerged PR with unique commits is **not** auto-deleted; it is classified `CHERRY-PICK THEN DELETE` for manual preservation/review.
- Generated delete commands use an option terminator and shell-quote repository-controlled branch names.
- Missing PR metadata remains conservative unless `--force-stale` is explicitly supplied.
- The generated deletion script is an operator-reviewed artifact; it is not executed by this tool.

## Recommended ABACUS command

```bash
python3 scripts/branch_retirement_report.py \
  --repo /workspace/ABACUS \
  --protect-pr 932
```

Add other open/critical PRs with repeated `--protect-pr` flags when needed.

## Recommended CODEX command

```bash
python3 scripts/branch_retirement_report.py \
  --repo /workspace/CODEX \
  --protect-pr <active-pr-number>
```

## Output files

The command writes three files under `reports/branch-retirement/` in the target repository:

- `branch-retirement-report.md` — human-readable summary and inventory.
- `branch-retirement-inventory.csv` — branch-by-branch review export.
- `branch-delete-commands.sh` — commands only for branches classified `DELETE`.

## Classification policy

| Classification | Meaning | Default action |
| --- | --- | --- |
| `KEEP` | Selected base, protected branch, open/protected PR, or insufficient metadata on a recent branch. | Do not delete. |
| `MERGE` | PR metadata exists and unique branch work remains. | Review and merge/squash before cleanup. |
| `CHERRY-PICK THEN DELETE` | Unique commits may remain, including closed unmerged PRs or stale branches without PR metadata. | Preserve/review needed commits, then delete only after operator decision. |
| `DELETE` | Tip is reachable from base, PR is merged, or stale/no-PR branch is explicitly forced. | Review the generated command before execution. |

## Preconditions for a complete report

1. The target checkout has an `origin` remote.
2. `git fetch --prune origin` succeeds unless `--no-fetch` is intentionally used.
3. GitHub CLI (`gh`) is installed/authenticated if PR metadata should be included.
4. Active/critical PRs are supplied using `--protect-pr` where required.

If a precondition is missing, the report records the limitation and stays conservative.
