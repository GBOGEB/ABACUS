# GitHub Setup Guide - Git & GitHub Bridge

## Current Status
- ✅ Local Git repository initialized
- ✅ Feature branch `feature/dow-integration` created
- ❌ No GitHub remote configured
- ❌ Cannot push/pull/PR without remote

## Setup Steps

### Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository settings:
   - **Name**: `Master_Input` (or your preferred name)
   - **Description**: "DMAIC V3 - DOW Integration & Process Management"
   - **Visibility**: Private (recommended) or Public
   - **DO NOT** initialize with README, .gitignore, or license (we already have content)
3. Click "Create repository"

### Step 2: Configure Git Remote

After creating the repository, GitHub will show you the repository URL. Use it below:

```bash
# Add the remote (replace YOUR_USERNAME and YOUR_REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Verify remote was added
git remote -v
```

### Step 3: Create .gitignore (Important!)

Before pushing, we need to exclude unnecessary files:

```bash
# Create .gitignore from the provided template
cp .gitignore.template .gitignore

# Or manually create it with essential exclusions
```

### Step 4: Stage and Commit Changes

```bash
# Check current status
git status

# Add all deployment files
git add DMAIC_V3/
git add deployment/
git add .gitignore

# Commit the changes
git commit -m "feat: Add DOW integration and deployment configuration"
```

### Step 5: Push to GitHub

```bash
# Push the feature branch to GitHub
git push -u origin feature/dow-integration

# This will:
# - Upload your code to GitHub
# - Set up tracking between local and remote branch
# - Enable pull/push operations
```

### Step 6: Create Pull Request (PR)

1. Go to your GitHub repository
2. You'll see a banner: "feature/dow-integration had recent pushes"
3. Click "Compare & pull request"
4. Fill in PR details:
   - **Title**: "feat: DOW Integration and Deployment System"
   - **Description**: Add details from DEPLOY_NOW.md
5. Click "Create pull request"

### Step 7: Merge to Main (After Review)

```bash
# Option A: Merge via GitHub UI (recommended)
# - Click "Merge pull request" on GitHub
# - Then locally:
git checkout main
git pull origin main

# Option B: Merge locally
git checkout main
git merge feature/dow-integration
git push origin main
```

## GitHub Workflow - Ongoing Usage

### Making Changes
```bash
# 1. Create new feature branch
git checkout -b feature/new-feature

# 2. Make changes, then commit
git add .
git commit -m "feat: description of changes"

# 3. Push to GitHub
git push -u origin feature/new-feature

# 4. Create PR on GitHub
# 5. Review and merge
```

### Pulling Latest Changes
```bash
# Update main branch
git checkout main
git pull origin main

# Update feature branch with latest main
git checkout feature/your-branch
git merge main
```

### Syncing with Remote
```bash
# Fetch all remote changes
git fetch origin

# See all branches (local and remote)
git branch -a

# Pull changes from remote branch
git pull origin branch-name
```

## GitHub CLI (Optional but Recommended)

Install GitHub CLI for easier GitHub operations:

### Windows Installation
```powershell
# Using winget
winget install --id GitHub.cli

# Or download from: https://cli.github.com/
```

### After Installing gh CLI
```bash
# Authenticate
gh auth login

# Create repo directly from CLI
gh repo create Master_Input --private --source=. --remote=origin

# Create PR from CLI
gh pr create --title "feat: DOW Integration" --body "See DEPLOY_NOW.md"

# View PRs
gh pr list

# Merge PR
gh pr merge 1 --merge
```

## Quick Reference Commands

```bash
# Check remote status
git remote -v

# Check branch status
git status

# See commit history
git log --oneline --graph --all

# Push current branch
git push

# Pull latest changes
git pull

# Create and switch to new branch
git checkout -b feature/branch-name

# Switch branches
git checkout branch-name

# Delete local branch
git branch -d branch-name

# Delete remote branch
git push origin --delete branch-name
```

## Troubleshooting

### "fatal: remote origin already exists"
```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
```

### "Updates were rejected because the remote contains work"
```bash
# Pull first, then push
git pull origin branch-name --rebase
git push origin branch-name
```

### "Permission denied (publickey)"
```bash
# Use HTTPS instead of SSH, or set up SSH keys
# See: https://docs.github.com/en/authentication/connecting-to-github-with-ssh
```

### Large files causing issues
```bash
# Add to .gitignore, then:
git rm --cached path/to/large/file
git commit -m "Remove large file from tracking"
```

## Next Steps

1. ✅ Create GitHub repository
2. ✅ Add remote origin
3. ✅ Create .gitignore
4. ✅ Commit changes
5. ✅ Push to GitHub
6. ✅ Create Pull Request
7. ✅ Review and merge

Once complete, you'll have full Git-GitHub integration with:
- ✅ Push/Pull capabilities
- ✅ Pull Request workflow
- ✅ Branch management
- ✅ Collaboration features
- ✅ Version control history
