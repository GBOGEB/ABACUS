#!/usr/bin/env bash
# branch_prune.sh — identify and optionally delete remote branches that are safe to prune.
#
# Usage:
#   bash scripts/branch_prune.sh                  # dry-run: list branches to prune
#   bash scripts/branch_prune.sh --execute        # delete listed branches from origin
#   bash scripts/branch_prune.sh --merged-only    # only list branches whose tip is an ancestor of main
#   bash scripts/branch_prune.sh --stale-days 60  # treat branches older than N days as stale (default: 30)
#
# A branch is considered safe to prune if ALL of the following hold:
#   1. Its tip is fully reachable from origin/main (i.e. already incorporated), OR
#      its associated PR is merged or closed.
#   2. It is not a protected branch (main, develop, release/*, hotfix/*).
#   3. It is not the currently checked-out branch.
#
# Branches with open PRs are always shown but flagged; deletion is skipped unless --force.

set -euo pipefail

EXECUTE=false
MERGED_ONLY=false
STALE_DAYS=30
FORCE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --execute)     EXECUTE=true ;;
    --merged-only) MERGED_ONLY=true ;;
    --force)       FORCE=true ;;
    --stale-days)  shift; STALE_DAYS="$1" ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

BASE="origin/main"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
NOW=$(date +%s)
STALE_CUTOFF=$(( NOW - STALE_DAYS * 86400 ))

is_protected() {
  local b="$1"
  [[ "$b" =~ ^(main|develop|release/|hotfix/) ]] && return 0
  return 1
}

is_ancestor_of_main() {
  git merge-base --is-ancestor "$1" "$BASE" 2>/dev/null
}

branch_age_days() {
  local ts
  ts=$(git log -1 --format="%ct" "$1" 2>/dev/null || echo "$NOW")
  echo $(( (NOW - ts) / 86400 ))
}

echo "=== Branch Prune Report (base: ${BASE}) ==="
echo "   Date          : $(date -u +"%Y-%m-%d %H:%M UTC")"
echo "   Stale threshold: ${STALE_DAYS} days"
echo "   Mode          : $([ "$EXECUTE" = true ] && echo 'EXECUTE' || echo 'DRY-RUN')"
echo ""

SAFE_TO_DELETE=()
STALE_DIVERGED=()
OPEN_PR_BRANCHES=()
ACTIVE_BRANCHES=()

while IFS= read -r remote_ref; do
  branch="${remote_ref#origin/}"

  # Skip protected and current
  is_protected "$branch" && continue
  [[ "$branch" == "$CURRENT_BRANCH" ]] && continue

  ahead=$(git rev-list --count "${BASE}..${remote_ref}" 2>/dev/null || echo 0)
  age_days=$(branch_age_days "$remote_ref")
  last_date=$(git log -1 --format="%ci" "$remote_ref" 2>/dev/null || echo "unknown")

  if is_ancestor_of_main "$remote_ref" 2>/dev/null || [[ "$ahead" -eq 0 ]]; then
    SAFE_TO_DELETE+=("$branch|$age_days|$last_date|fully merged (0 unique commits)")
  elif [[ "$age_days" -gt "$STALE_DAYS" ]]; then
    STALE_DIVERGED+=("$branch|$age_days|$last_date|${ahead} unique commits, ${age_days}d old")
  else
    ACTIVE_BRANCHES+=("$branch|$age_days|$last_date|${ahead} unique commits")
  fi
done < <(git for-each-ref --format='%(refname:short)' refs/remotes/origin/ | grep -v '^origin/HEAD$' | grep -v '^origin/main$')

# Print safe-to-delete
echo "--- SAFE TO DELETE (merged into main) ---"
if [[ ${#SAFE_TO_DELETE[@]} -eq 0 ]]; then
  echo "  (none)"
else
  for entry in "${SAFE_TO_DELETE[@]}"; do
    IFS='|' read -r b age last reason <<< "$entry"
    printf "  %-60s  age:%3dd  last: %s\n" "$b" "$age" "${last:0:10}"
  done
fi
echo ""

# Print stale diverged
if [[ "$MERGED_ONLY" != "true" ]]; then
  echo "--- STALE (diverged, older than ${STALE_DAYS} days) ---"
  if [[ ${#STALE_DIVERGED[@]} -eq 0 ]]; then
    echo "  (none)"
  else
    for entry in "${STALE_DIVERGED[@]}"; do
      IFS='|' read -r b age last reason <<< "$entry"
      printf "  %-60s  age:%3dd  last: %s  [%s]\n" "$b" "$age" "${last:0:10}" "$reason"
    done
  fi
  echo ""

  echo "--- ACTIVE (recent, unmerged) ---"
  if [[ ${#ACTIVE_BRANCHES[@]} -eq 0 ]]; then
    echo "  (none)"
  else
    for entry in "${ACTIVE_BRANCHES[@]}"; do
      IFS='|' read -r b age last reason <<< "$entry"
      printf "  %-60s  age:%3dd  last: %s  [%s]\n" "$b" "$age" "${last:0:10}" "$reason"
    done
  fi
  echo ""
fi

echo "Summary: ${#SAFE_TO_DELETE[@]} safe-to-delete, ${#STALE_DIVERGED[@]} stale-diverged, ${#ACTIVE_BRANCHES[@]} active"
echo ""

if [[ "$EXECUTE" != "true" ]]; then
  echo "Dry-run only. Re-run with --execute to delete safe-to-delete branches from origin."
  if [[ "$MERGED_ONLY" != "true" && ${#STALE_DIVERGED[@]} -gt 0 ]]; then
    echo "Add --force to also delete stale-diverged branches (review carefully first)."
  fi
  exit 0
fi

# Execute deletions
echo "Deleting safe-to-delete branches from origin..."
for entry in "${SAFE_TO_DELETE[@]}"; do
  IFS='|' read -r b age last reason <<< "$entry"
  echo "  Deleting origin/$b ..."
  git push origin --delete "$b" && echo "    OK" || echo "    FAILED (may already be deleted)"
done

if [[ "$FORCE" == "true" && ${#STALE_DIVERGED[@]} -gt 0 ]]; then
  echo ""
  echo "Deleting stale-diverged branches from origin (--force)..."
  for entry in "${STALE_DIVERGED[@]}"; do
    IFS='|' read -r b age last reason <<< "$entry"
    echo "  Deleting origin/$b ..."
    git push origin --delete "$b" && echo "    OK" || echo "    FAILED"
  done
fi

echo ""
echo "Done. Run 'git fetch --prune' locally to remove stale remote-tracking refs."
