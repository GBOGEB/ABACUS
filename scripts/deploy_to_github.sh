#!/bin/bash

# DMAIC_V3 GitHub Enterprise Deployment Script
# Version: 0.4.1
# Date: 2025-01-15

echo "=========================================="
echo "DMAIC_V3 GitHub Enterprise Deployment"
echo "Version: 0.4.1"
echo "=========================================="
echo ""

# Step 1: Verify we're in the right directory
echo "[1/7] Verifying directory..."
if [ ! -f ".github/workflows/dmaic-enterprise-ci.yml" ]; then
    echo "ERROR: Not in the correct directory. Please run from Master_Input root."
    exit 1
fi
echo "✓ Directory verified"
echo ""

# Step 2: Verify workflows
echo "[2/7] Verifying workflows..."
if [ -f "scripts/verify_workflows.sh" ]; then
    bash scripts/verify_workflows.sh
    if [ $? -ne 0 ]; then
        echo "ERROR: Workflow verification failed"
        exit 1
    fi
else
    echo "WARNING: Verification script not found, skipping..."
fi
echo ""

# Step 3: Check git status
echo "[3/7] Checking git status..."
git status --short
echo ""

# Step 4: Get GitHub repository URL
echo "[4/7] GitHub Repository Setup"
echo ""
echo "Please provide your GitHub repository URL:"
echo "Examples:"
echo "  - GitHub.com: https://github.com/GBOGEB/DMAIC_V3.git"
echo "  - GitHub Enterprise: https://github.enterprise.company.com/GBOGEB/DMAIC_V3.git"
echo ""
read -p "Enter GitHub repository URL: " REPO_URL

if [ -z "$REPO_URL" ]; then
    echo "ERROR: No repository URL provided"
    exit 1
fi

echo "Repository URL: $REPO_URL"
echo ""

# Step 5: Configure remote
echo "[5/7] Configuring git remote..."

# Remove existing origin if it exists
git remote remove origin 2>/dev/null

# Add new origin
git remote add origin "$REPO_URL"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to add remote"
    exit 1
fi

echo "✓ Remote configured"
git remote -v
echo ""

# Step 6: Push to GitHub
echo "[6/7] Pushing to GitHub..."
echo ""
echo "Current branch: $(git branch --show-current)"
echo ""
read -p "Push to this branch? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Deployment cancelled"
    exit 0
fi

echo ""
echo "Pushing to GitHub..."
git push -u origin $(git branch --show-current)

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Push failed"
    echo ""
    echo "Common issues:"
    echo "1. Repository doesn't exist - Create it on GitHub first"
    echo "2. Authentication failed - Check your credentials"
    echo "3. Permission denied - Check repository access"
    echo ""
    echo "To create a repository:"
    echo "  - Go to https://github.com/new (or your GitHub Enterprise URL)"
    echo "  - Create a new repository named 'DMAIC_V3'"
    echo "  - Do NOT initialize with README, .gitignore, or license"
    echo "  - Then run this script again"
    exit 1
fi

echo ""
echo "✓ Push successful!"
echo ""

# Step 7: Verify workflows
echo "[7/7] Verifying deployment..."
echo ""
echo "✓ Code pushed to GitHub"
echo "✓ Workflows should now be visible in the Actions tab"
echo ""
echo "Next steps:"
echo "1. Open your repository on GitHub"
echo "2. Go to the 'Actions' tab"
echo "3. You should see 17 workflows listed"
echo "4. Workflows will trigger automatically on push"
echo "5. Monitor the workflow runs"
echo ""
echo "Repository URL: $REPO_URL"
echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Documentation:"
echo "  - Workflow Status: handover/GITHUB_WORKFLOWS_STATUS.md"
echo "  - Deployment Guide: handover/DEPLOYMENT_CHECKLIST.md"
echo "  - Release Notes: RELEASE_NOTES_v0.4.1.md"
echo ""
