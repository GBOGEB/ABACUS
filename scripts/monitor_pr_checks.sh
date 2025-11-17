#!/bin/bash

# Monitor PR Checks Status
# Usage: ./scripts/monitor_pr_checks.sh [PR_NUMBER]

PR_NUMBER=${1:-9}
REPO="GBOGEB/ABACUS"

echo "🔍 Monitoring PR #${PR_NUMBER} checks..."
echo "Repository: ${REPO}"
echo ""

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "⚠️  GitHub CLI (gh) not found. Install from: https://cli.github.com/"
    echo ""
    echo "📱 View checks in browser:"
    echo "   https://github.com/${REPO}/pull/${PR_NUMBER}/checks"
    exit 1
fi

# Get PR checks status
echo "Fetching checks status..."
gh pr checks ${PR_NUMBER} --repo ${REPO}

echo ""
echo "📊 Summary:"
gh pr view ${PR_NUMBER} --repo ${REPO} --json statusCheckRollup --jq '.statusCheckRollup[] | "\(.context): \(.state)"'

echo ""
echo "🔗 View full details:"
echo "   https://github.com/${REPO}/pull/${PR_NUMBER}"
echo "   https://github.com/${REPO}/actions"
