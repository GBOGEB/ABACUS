#!/bin/bash
# GitHub Setup Script for Git Bash/Linux/Mac
# This script helps set up Git-GitHub integration

set -e

REPO_URL=""
SKIP_GITIGNORE=false
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --repo-url)
            REPO_URL="$2"
            shift 2
            ;;
        --skip-gitignore)
            SKIP_GITIGNORE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=== GitHub Setup Script ==="
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "✗ Git is not installed. Please install Git first."
    echo "  Download from: https://git-scm.com/downloads"
    exit 1
fi

GIT_VERSION=$(git --version)
echo "✓ Git installed: $GIT_VERSION"

# Check current git status
echo ""
echo "Current Git Status:"
git status --short

# Check if remote exists
if git remote get-url origin &> /dev/null; then
    EXISTING_REMOTE=$(git remote get-url origin)
    echo ""
    echo "✓ Remote 'origin' already configured:"
    echo "  $EXISTING_REMOTE"
    
    read -p "Do you want to update it? (y/N): " response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        if [ "$DRY_RUN" = false ]; then
            git remote remove origin
            echo "✓ Removed existing remote"
        fi
    else
        echo "Keeping existing remote configuration"
        exit 0
    fi
fi

# Get repository URL if not provided
if [ -z "$REPO_URL" ]; then
    echo ""
    echo "Please create a GitHub repository first:"
    echo "  1. Go to https://github.com/new"
    echo "  2. Create repository (DO NOT initialize with README)"
    echo "  3. Copy the repository URL"
    echo ""
    read -p "Enter your GitHub repository URL (e.g., https://github.com/username/repo.git): " REPO_URL
fi

if [ -z "$REPO_URL" ]; then
    echo "✗ Repository URL is required"
    exit 1
fi

# Validate URL format
if [[ ! "$REPO_URL" =~ ^https://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+\.git$ ]] && \
   [[ ! "$REPO_URL" =~ ^git@github\.com:[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+\.git$ ]]; then
    echo "⚠ Warning: URL format may be incorrect"
    echo "  Expected: https://github.com/username/repo.git"
    echo "  Got: $REPO_URL"
    read -p "Continue anyway? (y/N): " continue
    if [[ ! "$continue" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Add remote
echo ""
echo "Adding remote 'origin'..."
if [ "$DRY_RUN" = false ]; then
    if git remote add origin "$REPO_URL"; then
        echo "✓ Remote added successfully"
    else
        echo "✗ Failed to add remote"
        exit 1
    fi
else
    echo "[DRY RUN] Would execute: git remote add origin $REPO_URL"
fi

# Verify remote
echo ""
echo "Verifying remote configuration:"
git remote -v

# Create/update .gitignore
if [ "$SKIP_GITIGNORE" = false ]; then
    echo ""
    echo "Checking .gitignore..."
    if [ -f ".gitignore" ]; then
        echo "✓ .gitignore already exists"
    else
        echo "⚠ .gitignore not found"
        echo "  Please create .gitignore before committing"
    fi
fi

# Show next steps
echo ""
echo "=== Next Steps ==="
echo ""
echo "1. Review and stage your changes:"
echo "   git status"
echo "   git add DMAIC_V3/ deployment/ .gitignore"
echo ""
echo "2. Commit your changes:"
echo "   git commit -m 'feat: Add DOW integration and deployment'"
echo ""
echo "3. Push to GitHub:"
echo "   git push -u origin feature/dow-integration"
echo ""
echo "4. Create Pull Request on GitHub:"
REPO_WEB_URL="${REPO_URL%.git}"
echo "   Visit: ${REPO_WEB_URL}/pulls"
echo ""

# Optional: Check if gh CLI is installed
if command -v gh &> /dev/null; then
    echo "✓ GitHub CLI (gh) is installed"
    echo "  You can use: gh pr create"
else
    echo "ℹ GitHub CLI (gh) not installed"
    echo "  Install for easier PR management: https://cli.github.com/"
fi

echo ""
echo "Setup complete! 🚀"
