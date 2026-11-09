# Stack tools

PowerShell 7 tools that rebuild stacked PR branches (bottom → top) onto the
latest base branch and auto-resolve the conflicts they hit. They were written
during the ABACUS stacked-PR conflict work in October 2026.

| File | What it does |
|---|---|
| `Stack-Tools.cmd` | Double-click menu for everything below |
| `Fix-AllStacks.ps1` | Finds every open PR stack with conflicts, rebuilds each one, reports READY / REVIEW / SKIPPED, then asks before pushing |
| `Rebase-Stack.ps1` | Rebuilds one stack, found from any PR number or given as `-Branches bottom,...,top` |
| `Stack-Helper.ps1` | Menu: pick a repo, clone and stack; copies the `Rebase-Stack.ps1` command to the clipboard |

Requires `pwsh` (`winget install Microsoft.PowerShell`), `git` and `python`
(with PyYAML, for the syntax check). Set `GITHUB_TOKEN` for a higher GitHub
API limit; it is optional.

## Which repo

`-Repo <clone>` wins. Without it, the scripts use the `STACK_REPO`
environment variable. If that is unset too, they use the clone the scripts
live in (`git rev-parse --show-toplevel` from `tools/stack`). The working
tree must be clean: the scripts check out and rewrite branches in it.

## Entry points

**Double-click:** run `Stack-Tools.cmd`.

1. List stacks with conflicts (changes nothing)
2. Fix all conflicting stacks (report, asks before pushing)
3. Same as 2, plus `pytest` on each stack's top branch
4. Pick a repo or stack from a menu (`Stack-Helper.ps1`)
5. Fix one stack by PR number

**By PR number:** any PR in the stack works. The whole chain is looked up on GitHub.

```powershell
.\Rebase-Stack.ps1 2145                  # rebuild locally and report; no push
.\Rebase-Stack.ps1 2145 -Push            # push if nothing was auto-resolved
.\Rebase-Stack.ps1 2145 -Push -AcceptAuto   # push after you reviewed the auto-resolved files
.\Rebase-Stack.ps1 2145 -Manual          # pause on every conflict instead
```

`-Mode Auto` (the default) merges when any branch in the stack already has
merge commits, so no force-push is needed. Otherwise it rebases.

## Conflict rule

The rule runs per conflicting file, unless you pass `-Manual`:

- **Both sides only added lines** in a hunk → keep both, skipping lines that
  are already present. This applies only to prose and list files: `.md`,
  `.txt`, `.rst`, `.yml`/`.yaml`, `.toml`, `.cfg`, `.ini` and `.gitignore`.
- **A line was changed or deleted** → the side whose last change to that file
  (author date) is newer wins the hunk. If the newer change deleted the file,
  the deletion wins.
- **Code and every other file type** → the newer side always wins. `.py`,
  `.yml`/`.yaml` and `.json` results then get a syntax check. If "keep both"
  produced invalid syntax, the file is redone with the newer side for every
  hunk. If it still fails, the script prints a warning.

Non-conflicting hunks from both sides are always kept. `git rerere` is
switched on (with `autoUpdate`), so a resolution is replayed the next time the
same hunk shows up, in this stack or any other.

## Push gating

Nothing is pushed without `-Push`. The push is atomic, with
`--force-with-lease` pinned to the remote SHAs seen at the start.

`-Push` refuses when any conflict was auto-resolved, either by the rule above
or by a replayed rerere resolution. The script lists those files instead.
Review each one, then re-run with `-Push -AcceptAuto`.

Before any push, verification also stops the run when:

- a branch is not on top of the one below it,
- conflict markers are left in the top branch,
- the update added a duplicated Markdown heading.

`Fix-AllStacks.ps1` marks a stack REVIEW instead of READY when it has
warnings or replayed rerere resolutions, or when its tests fail. Only READY
stacks are offered for pushing.

## Refs the scripts leave behind

- `refs/stack-backup/<timestamp>/<branch>`: the original remote tip of every
  branch, taken before anything is rewritten.
  `refs/stack-backup/<timestamp>/local/<branch>` holds a differing local tip.
  To undo: `git branch -f <branch> refs/stack-backup/<timestamp>/<branch>`.
- `refs/stack-result/<branch>`: what the last run produced.
  `Fix-AllStacks.ps1` normally skips branches with unpushed local commits.
  A branch that still equals its `stack-result` ref is the script's own
  output, so it may be rebuilt.

Clean up old ones with
`git for-each-ref --format="%(refname)" refs/stack-backup | ForEach-Object { git update-ref -d $_ }`.

## Known pitfalls

These come from ABACUS #2156, 2026-10-20.

- **Newest-wins reverted real logic.** In
  `.github/workflows/g3a-n15-python-matrix.yml` the lower branch's only newer
  change was an actions `@v4 → @v7` bump. Newest-wins therefore threw away
  the substantive W16 workflow logic from the other side. A timestamp says
  nothing about which side holds the intent. add/add workflow files are the
  worst case.
- **rerere replayed the bad resolution.** A later `-Push` run replayed it from
  rerere and pushed it. That is why `-Push` now needs `-AcceptAuto`.
- **"Keep both" duplicated a Markdown section** in `MIP/EXECUTION.md`. This
  is now caught by the duplicated-heading check.

What to do:

- **Review every auto-resolved yml or workflow file 3-way.** Diff
  `merge-base → ours` and `merge-base → theirs`, then combine both intents.
  For example, keep the logic side and re-apply the version bump.
  ```powershell
  git diff $(git merge-base <a> <b>) <a> -- <file>
  git diff $(git merge-base <a> <b>) <b> -- <file>
  ```
- **Fix a bad replay** with `git rerere forget <file>` while the conflict is
  checked out, then resolve it again by hand. Otherwise rerere keeps
  reapplying it in every later run and stack.
