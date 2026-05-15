#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/merge_dormancy_order.sh
#   bash scripts/merge_dormancy_order.sh --execute
#
# Notes:
# - Dry-run by default: prints the merge queue in dormancy-safe order.
# - --execute will merge queued branches into the current checked-out branch.
# - This script follows the approved ordering strategy:
#   merged cleanup -> 1 ahead -> 2 ahead -> 3 ahead -> high divergence -> final branch.

EXECUTE=false
if [[ "${1:-}" == "--execute" ]]; then
  EXECUTE=true
fi

BASE_BRANCH="origin/main"

cleanup_branches=(
  "origin/copilot/fix-ci-test-multiple-iterations"
  "origin/copilot/fix-ci-test-phase4-output"
  "origin/copilot/fix-run-deployment-test-system"
  "origin/copilot/inspect-branches-for-merging"
  "origin/roundtrip/20251117_042931"
)

one_ahead_branches=(
  "origin/copilot/fix-ci-test-file-saved-correctly"
  "origin/copilot/fix-ci-test-output-structure-yet-again"
  "origin/copilot/fix-ci-test-phase2-measure-again"
  "origin/copilot/fix-test-file-saved-correctly-again"
  "origin/copilot/fix-test-multiple-iterations"
)

high_divergence_branches=(
  "origin/copilot/fix-ci-test-phase3-output"
  "origin/copilot/fix-test-calculate-statistics-failure"
  "origin/copilot/fix-full-deployment-test-issues"
)

final_branch="origin/feature/dow-integration"

contains() {
  local value="$1"
  shift
  local item
  for item in "$@"; do
    if [[ "$item" == "$value" ]]; then
      return 0
    fi
  done
  return 1
}

ahead_count() {
  local branch="$1"
  local counts
  counts="$(git rev-list --left-right --count "${BASE_BRANCH}...${branch}")"
  echo "${counts#* }"
}

is_merged_into_base() {
  local branch="$1"
  git merge-base --is-ancestor "${branch}" "${BASE_BRANCH}"
}

print_branch_with_ahead() {
  local branch="$1"
  if git rev-parse --verify -q "$branch" >/dev/null; then
    echo "- ${branch} ($(ahead_count "${branch}") ahead)"
  else
    echo "- ${branch} (missing)"
  fi
}

echo "=== Dormancy-safe merge plan (base: ${BASE_BRANCH}) ==="
echo
echo "1) Immediate cleanup (already merged)"
for branch in "${cleanup_branches[@]}"; do
  if git rev-parse --verify -q "$branch" >/dev/null && is_merged_into_base "$branch"; then
    echo "- ${branch} [merged]"
  else
    echo "- ${branch} [not merged or missing]"
  fi
done
echo

echo "2) Merge next (smallest pending)"
for branch in "${one_ahead_branches[@]}"; do
  print_branch_with_ahead "$branch"
done
echo

exclude_branches=(
  "${cleanup_branches[@]}"
  "${one_ahead_branches[@]}"
  "${high_divergence_branches[@]}"
  "${final_branch}"
)

two_ahead=()
three_ahead=()

while IFS= read -r branch; do
  contains "$branch" "${exclude_branches[@]}" && continue
  [[ "$branch" == origin/copilot/* ]] || continue
  count="$(ahead_count "$branch")"
  if [[ "$count" == "2" ]]; then
    two_ahead+=("$branch")
  elif [[ "$count" == "3" ]]; then
    three_ahead+=("$branch")
  fi
done < <(git for-each-ref --format='%(refname:short)' refs/remotes/origin/copilot)

echo "3) Merge low-risk batch (2 ahead)"
for branch in "${two_ahead[@]}"; do
  print_branch_with_ahead "$branch"
done
echo

echo "4) Merge medium batch (3 ahead)"
for branch in "${three_ahead[@]}"; do
  print_branch_with_ahead "$branch"
done
echo

echo "5) Merge high-divergence batch"
for branch in "${high_divergence_branches[@]}"; do
  print_branch_with_ahead "$branch"
done
echo

echo "6) Merge last (most divergent)"
print_branch_with_ahead "$final_branch"
echo

echo "7) Ongoing rule"
echo "- Merge in ascending ahead count (1 -> 2 -> 3 -> 4+)."
echo "- Prune merged branches weekly."
echo

merge_queue=(
  "${one_ahead_branches[@]}"
  "${two_ahead[@]}"
  "${three_ahead[@]}"
  "${high_divergence_branches[@]}"
  "${final_branch}"
)

if [[ "${EXECUTE}" != "true" ]]; then
  echo "Dry-run only. Re-run with --execute to merge queue into current branch."
  exit 0
fi

echo "Executing merges into current branch: $(git rev-parse --abbrev-ref HEAD)"
for branch in "${merge_queue[@]}"; do
  if git rev-parse --verify -q "$branch" >/dev/null; then
    echo "Merging ${branch}..."
    git merge --no-ff --no-edit "$branch"
  else
    echo "Skipping missing branch ${branch}"
  fi
done

echo "Done. Run tests, then push your branch and open/update PR."
