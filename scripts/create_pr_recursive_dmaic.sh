#!/bin/bash

# Create Pull Request for Recursive DMAIC v0.4.0 CI/CD Integration
# Based on DOW PR creation tools
# Note: GitHub CLI is not available in this organization

set -e

echo "=========================================="
echo "🚀 Create Pull Request"
echo "Recursive DMAIC v0.4.0 CI/CD Integration"
echo "=========================================="
echo ""

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
echo "📌 Current branch: $CURRENT_BRANCH"
echo ""

# Verify we're on the correct branch
if [[ "$CURRENT_BRANCH" != "cicd/recursive-dmaic-v0.4.0" ]]; then
    echo "⚠️  WARNING: Expected branch 'cicd/recursive-dmaic-v0.4.0' but on '$CURRENT_BRANCH'"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Aborted"
        exit 1
    fi
fi

# Get remote URL
REMOTE_URL=$(git remote get-url origin)
echo "🔗 Remote: $REMOTE_URL"
echo ""

# Extract repo info
if [[ $REMOTE_URL =~ github\.com[:/]([^/]+)/([^/.]+) ]]; then
    OWNER="${BASH_REMATCH[1]}"
    REPO="${BASH_REMATCH[2]}"
    
    PR_URL="https://github.com/$OWNER/$REPO/compare/main...$CURRENT_BRANCH?expand=1"
    
    echo "=========================================="
    echo "📝 Pull Request URL:"
    echo "$PR_URL"
    echo "=========================================="
    echo ""
    echo "🌐 Opening PR in browser..."
    echo ""
    
    # Try to open in browser
    if command -v start &> /dev/null; then
        start "$PR_URL"
        echo "✅ Browser opened successfully"
    elif command -v open &> /dev/null; then
        open "$PR_URL"
        echo "✅ Browser opened successfully"
    elif command -v xdg-open &> /dev/null; then
        xdg-open "$PR_URL"
        echo "✅ Browser opened successfully"
    else
        echo "⚠️  Could not open browser automatically"
        echo "Please open this URL manually:"
        echo "$PR_URL"
    fi
    
    echo ""
    echo "=========================================="
    echo "📋 PR Details to Use:"
    echo "=========================================="
    echo ""
    echo "Title:"
    echo "feat: Add automated PR creation script (browser-based)"
    echo ""
    echo "Description:"
    echo "Copy from: .github/PULL_REQUEST_TEMPLATE.md"
    echo ""
    echo "Or use this quick summary:"
    cat << 'EOF'

## 🎉 Recursive DMAIC v0.4.0 CI/CD Integration

### Summary
Complete integration of Recursive DMAIC v0.4.0 CI/CD workflows with the existing DOW (DMAIC + ABACUS) pipeline.

### ✅ What's Included

#### New Workflows (5)
- ✅ **cd-unified.yml** - Unified CD pipeline
- ✅ **ci-enhanced.yml** - Enhanced CI pipeline
- ✅ **ci-abacus.yml** - ABACUS-specific CI
- ✅ **ci-codex.yml** - CODEX-specific CI
- ✅ **dow-scheduled.yml** - Scheduled execution

#### Documentation (7)
- ✅ Comprehensive workflow documentation
- ✅ Integration plan and strategy
- ✅ Implementation status tracking

### 🎯 Key Features
- Multi-platform validation (Ubuntu + RHEL 8 + RHEL 9)
- Gated deployment
- FIPS compliance support
- Comprehensive testing

### 📊 Status
- Files created: 11
- Workflows: 5 production workflows
- Documentation: 7 comprehensive documents
- YAML syntax: ✅ Validated

**Status**: ✅ PRODUCTION-READY

See full details in `.github/PULL_REQUEST_TEMPLATE.md`
EOF
    
    echo ""
    echo ""
    echo "Labels to add:"
    echo "- enhancement"
    echo "- ci/cd"
    echo "- integration"
    echo "- documentation"
    echo ""
    echo "=========================================="
    echo "📚 Documentation Available:"
    echo "=========================================="
    echo "- PR_CREATION_GUIDE.md"
    echo "- INTEGRATION_FINAL_SUMMARY.md"
    echo "- .github/PULL_REQUEST_TEMPLATE.md"
    echo "- .github/workflows/README.md"
    echo "- DOW_CICD_INTEGRATION_PLAN.md"
    echo "- DOW_CICD_IMPLEMENTATION_STATUS.md"
    echo "- DOW_CICD_INTEGRATION_COMPLETE.md"
    echo ""
    echo "=========================================="
    echo "📋 After Creating the PR:"
    echo "=========================================="
    echo "1. ✅ Check Actions tab for workflow runs"
    echo "2. ✅ Monitor CI execution (10-15 minutes)"
    echo "   - ci-enhanced.yml"
    echo "   - ci-abacus.yml"
    echo "   - cd-unified.yml (validation)"
    echo "3. ✅ Review PR checks and logs"
    echo "4. ✅ Request team review"
    echo "5. ✅ Merge when all checks pass"
    echo "6. ✅ Create release tag:"
    echo "   git tag -a v0.4.0 -m 'Release: Recursive DMAIC v0.4.0'"
    echo "   git push origin v0.4.0"
    echo "7. ✅ Monitor CD execution (20-25 minutes)"
    echo "8. ✅ Verify GitHub Release creation"
    echo ""
    echo "=========================================="
    echo "🎯 Success Criteria:"
    echo "=========================================="
    echo "✅ All linting checks pass"
    echo "✅ All tests pass on Ubuntu"
    echo "✅ RHEL tests pass (if runners available)"
    echo "✅ Smoke tests pass"
    echo "✅ Integration tests pass"
    echo "✅ No breaking changes"
    echo "✅ Team approval obtained"
    echo ""
    echo "=========================================="
    echo "🚀 Ready to Ship!"
    echo "=========================================="
    echo ""
    
    # Copy PR template to clipboard if possible
    if [ -f .github/PULL_REQUEST_TEMPLATE.md ]; then
        if command -v clip &> /dev/null; then
            cat .github/PULL_REQUEST_TEMPLATE.md | clip
            echo "✅ PR description copied to clipboard!"
            echo ""
        elif command -v pbcopy &> /dev/null; then
            cat .github/PULL_REQUEST_TEMPLATE.md | pbcopy
            echo "✅ PR description copied to clipboard!"
            echo ""
        elif command -v xclip &> /dev/null; then
            cat .github/PULL_REQUEST_TEMPLATE.md | xclip -selection clipboard
            echo "✅ PR description copied to clipboard!"
            echo ""
        else
            echo "💡 TIP: Copy PR description from .github/PULL_REQUEST_TEMPLATE.md"
            echo ""
        fi
    else
        echo "⚠️  WARNING: .github/PULL_REQUEST_TEMPLATE.md not found. Skipping clipboard copy."
        echo "💡 TIP: Ensure the PR template exists or copy your PR description manually."
        echo ""
    fi
    
else
    echo "❌ ERROR: Could not parse GitHub URL"
    echo "Expected format: github.com/OWNER/REPO"
    exit 1
fi
