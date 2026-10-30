#!/bin/bash

# GitHub Token Permission Test Script
# This script verifies that your GitHub token has the necessary permissions for ABACUS

set -e

echo "🔍 Testing GitHub Token Permissions for ABACUS..."
echo "=================================================="

# Check if GITHUB_TOKEN is set
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ ERROR: GITHUB_TOKEN environment variable is not set"
    echo "   Please set your GitHub token: export GITHUB_TOKEN=your_token_here"
    echo "   See GITHUB_SETUP.md for detailed instructions"
    exit 1
fi

echo "✅ GITHUB_TOKEN environment variable is set"

# Test 1: Basic Authentication
echo ""
echo "1️⃣  Testing basic authentication..."
RESPONSE=$(curl -s -w "%{http_code}" -H "Authorization: token $GITHUB_TOKEN" \
    https://api.github.com/user -o /tmp/auth_test.json)

if [ "$RESPONSE" = "200" ]; then
    USERNAME=$(jq -r '.login' /tmp/auth_test.json 2>/dev/null || echo "unknown")
    echo "✅ Authentication successful - logged in as: $USERNAME"
else
    echo "❌ Authentication failed (HTTP $RESPONSE)"
    echo "   Check if your token is valid and not expired"
    exit 1
fi

# Test 2: Repository Access
echo ""
echo "2️⃣  Testing repository access..."
REPO_RESPONSE=$(curl -s -w "%{http_code}" -H "Authorization: token $GITHUB_TOKEN" \
    https://api.github.com/repos/GBOGEB/ABACUS -o /tmp/repo_test.json)

if [ "$REPO_RESPONSE" = "200" ]; then
    REPO_NAME=$(jq -r '.full_name' /tmp/repo_test.json 2>/dev/null || echo "GBOGEB/ABACUS")
    echo "✅ Repository access successful - can access: $REPO_NAME"
else
    echo "❌ Repository access failed (HTTP $REPO_RESPONSE)"
    if [ "$REPO_RESPONSE" = "404" ]; then
        echo "   Repository not found or token lacks access permissions"
    elif [ "$REPO_RESPONSE" = "403" ]; then
        echo "   Access forbidden - token may lack 'repo' scope"
    fi
fi

# Test 3: Write Permissions (check collaborators endpoint)
echo ""
echo "3️⃣  Testing write permissions..."
WRITE_RESPONSE=$(curl -s -w "%{http_code}" -H "Authorization: token $GITHUB_TOKEN" \
    https://api.github.com/repos/GBOGEB/ABACUS/collaborators -o /tmp/write_test.json)

if [ "$WRITE_RESPONSE" = "200" ]; then
    echo "✅ Write permissions confirmed - can manage repository"
elif [ "$WRITE_RESPONSE" = "403" ]; then
    echo "⚠️  Limited access - read-only permissions detected"
    echo "   Your token may lack full 'repo' scope permissions"
else
    echo "❌ Write permission test failed (HTTP $WRITE_RESPONSE)"
fi

# Test 4: Token Scopes
echo ""
echo "4️⃣  Checking token scopes..."
SCOPES_RESPONSE=$(curl -s -I -H "Authorization: token $GITHUB_TOKEN" \
    https://api.github.com/user | grep -i "x-oauth-scopes:" || echo "")

if [ -n "$SCOPES_RESPONSE" ]; then
    SCOPES=$(echo "$SCOPES_RESPONSE" | cut -d: -f2- | tr -d ' \r\n')
    echo "✅ Token scopes: $SCOPES"

    # Check for required scopes
    if echo "$SCOPES" | grep -q "repo"; then
        echo "✅ 'repo' scope detected - full repository access available"
    else
        echo "❌ Missing 'repo' scope - this will cause push failures"
        echo "   Regenerate your token with 'repo' scope enabled"
    fi

    if echo "$SCOPES" | grep -q "workflow"; then
        echo "✅ 'workflow' scope detected - GitHub Actions access available"
    else
        echo "⚠️  Missing 'workflow' scope - may limit GitHub Actions integration"
    fi
else
    echo "⚠️  Unable to determine token scopes"
fi

# Test 5: Git Push Simulation
echo ""
echo "5️⃣  Testing Git configuration..."
GIT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "not configured")
echo "📍 Git remote URL: $GIT_REMOTE"

if [[ "$GIT_REMOTE" == *"github.com"* ]]; then
    echo "✅ GitHub remote configured correctly"

    # Check git credential configuration
    GIT_HELPER=$(git config credential.helper 2>/dev/null || echo "not configured")
    if [[ "$GIT_HELPER" == *"GITHUB_TOKEN"* ]]; then
        echo "✅ Git credential helper configured for GITHUB_TOKEN"
    else
        echo "⚠️  Git credential helper may not be configured for GITHUB_TOKEN"
        echo "   Current helper: $GIT_HELPER"
    fi
else
    echo "⚠️  Git remote not pointing to GitHub or not configured"
fi

# Summary
echo ""
echo "📋 SUMMARY"
echo "=========="

# Clean up temp files
rm -f /tmp/auth_test.json /tmp/repo_test.json /tmp/write_test.json

# Final recommendations
if [ "$RESPONSE" = "200" ] && [ "$REPO_RESPONSE" = "200" ]; then
    if [ "$WRITE_RESPONSE" = "200" ]; then
        echo "🎉 All tests passed! Your GitHub token is properly configured for ABACUS."
    else
        echo "⚠️  Basic access works, but write permissions may be limited."
        echo "   Recommendation: Ensure your token has full 'repo' scope permissions."
    fi
else
    echo "❌ Configuration issues detected. Please review the errors above."
    echo ""
    echo "🔧 Quick Fix Steps:"
    echo "   1. Go to https://github.com/settings/tokens"
    echo "   2. Generate new token with 'repo' scope"
    echo "   3. Update: export GITHUB_TOKEN=your_new_token"
    echo "   4. Run this test again"
    echo ""
    echo "📚 For detailed instructions, see: GITHUB_SETUP.md"
fi

echo ""
echo "For more help, see GITHUB_SETUP.md or create an issue with the test results."
