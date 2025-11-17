#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/git_github_roundtrip.sh "roundtrip/update-handover" "chore: roundtrip handover artifacts"
BRANCH_NAME="${1:-roundtrip/$(date -u +%Y%m%d_%H%M%S)}"
COMMIT_MSG="${2:-chore(roundtrip): update handover artifacts and reports}"

# Preflight
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not in a git repository."
  exit 1
fi

# Ensure dependencies for builds (best-effort)
echo ">>> Running optional builds (PDF, GLOOB, convergence)..."
if [ -f "scripts/build_handover_book.sh" ]; then
  bash scripts/build_handover_book.sh || echo "PDF build skipped/failed"
fi
if [ -f "scripts/build_handover_bundle.py" ]; then
  python scripts/build_handover_bundle.py || echo "GLOOB build skipped/failed"
fi
if [ -f "scripts/check_convergence.py" ]; then
  python scripts/check_convergence.py || echo "Convergence check skipped/failed"
fi

# Branch
echo ">>> Creating branch: ${BRANCH_NAME}"
git fetch --all --prune
git switch -c "${BRANCH_NAME}"

# Stage typical roundtrip artifacts
echo ">>> Staging changes"
git add \
  DMAIC_V3_OUTPUT/reports || true
git add handover/DMAIC_V3_3_HANDOVER_BOOK.pdf || true
git add handover/DMAIC_V3_3_HANDOVER_GLOOB.zip || true
git add DMAIC_V3_CANONICAL_HANDOVER_BOOK.md || true
git add .github/workflows/*.yml || true
git add scripts/*.py scripts/*.sh || true
git add knowledge_packages/* || true

# Commit if any changes
if git diff --cached --quiet; then
  echo "No staged changes to commit."
else
  git commit -m "${COMMIT_MSG}"
fi

# Push
echo ">>> Pushing branch"
git push --set-upstream origin "${BRANCH_NAME}"

# Open PR if GitHub CLI is available
if command -v gh >/dev/null 2>&1; then
  echo ">>> Creating pull request via gh"
  gh pr create \
    --title "${COMMIT_MSG}" \
    --body "Automated roundtrip: build artifacts (PDF/GLOOB) and reports. Trigger validations and CD." \
    --base main \
    --head "${BRANCH_NAME}" || echo "PR creation skipped/failed"
else
  echo "gh CLI not found. Create a PR here:"
  REPO_URL=$(git config --get remote.origin.url | sed 's/.git$//')
  echo "Repository: ${REPO_URL}"
  echo "Branch: ${BRANCH_NAME}"
fi

echo "✅ Roundtrip complete."
