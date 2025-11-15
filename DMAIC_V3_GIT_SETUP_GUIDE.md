# DMAIC V3.0 - Git & GitHub Setup Guide

**Version:** 3.0.0  
**Date:** 2024  
**Status:** Complete

---

## 🎯 QUICK START

### 1. Initialize Git Repository

```bash
cd DMAIC_V3
git init
git add .
git commit -m "feat(init): initial DMAIC V3.0 modular architecture"
```

### 2. Create GitHub Repository

```bash
# Using GitHub CLI
gh repo create dmaic-v3 --public --description "DMAIC V3.0 - Modular Idempotent Architecture"

# Or manually on GitHub.com
# Then connect:
git remote add origin https://github.com/YOUR_USERNAME/dmaic-v3.git
git branch -M main
git push -u origin main
```

### 3. Set Up Branch Protection

```bash
# Using GitHub CLI
gh api repos/YOUR_USERNAME/dmaic-v3/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["CI Status Check"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1}' \
  --field restrictions=null
```

### 4. Configure Secrets

```bash
# Add secrets for CI/CD
gh secret set PYPI_API_TOKEN --body "your-pypi-token"
gh secret set CODECOV_TOKEN --body "your-codecov-token"
gh secret set SLACK_WEBHOOK --body "your-slack-webhook"
```

### 5. Test CI/CD

```bash
# Make a change and push
git checkout -b feature/test-ci
echo "# Test" >> README.md
git add README.md
git commit -m "docs(readme): test CI pipeline"
git push origin feature/test-ci

# Create PR
gh pr create --title "Test CI Pipeline" --body "Testing CI/CD setup"
```

---

## 📋 DETAILED SETUP

### Step 1: Initialize Git

```bash
cd DMAIC_V3

# Initialize repository
git init

# Add all files
git add .

# Initial commit
git commit -m "feat(init): initial DMAIC V3.0 modular architecture

- Modular phase architecture
- Idempotency system with state management
- Phase 0 setup and validation
- Centralized configuration
- Cross-platform setup scripts
- Comprehensive documentation
- CI/CD pipelines
- Version management"

# Create develop branch
git checkout -b develop
git checkout main
```

### Step 2: Create GitHub Repository

#### Option A: Using GitHub CLI

```bash
# Install GitHub CLI if needed
# Windows: winget install GitHub.cli
# Mac: brew install gh
# Linux: See https://github.com/cli/cli#installation

# Login
gh auth login

# Create repository
gh repo create dmaic-v3 \
  --public \
  --description "DMAIC V3.0 - Modular Idempotent Architecture for Process Improvement" \
  --homepage "https://github.com/YOUR_USERNAME/dmaic-v3"

# Connect and push
git remote add origin https://github.com/YOUR_USERNAME/dmaic-v3.git
git branch -M main
git push -u origin main
git push origin develop
```

#### Option B: Manual Setup

1. Go to https://github.com/new
2. Repository name: `dmaic-v3`
3. Description: "DMAIC V3.0 - Modular Idempotent Architecture"
4. Public/Private: Choose based on needs
5. Don't initialize with README (we already have one)
6. Click "Create repository"

```bash
# Connect repository
git remote add origin https://github.com/YOUR_USERNAME/dmaic-v3.git
git branch -M main
git push -u origin main
git push origin develop
```

### Step 3: Configure Repository Settings

#### Branch Protection Rules

**Main Branch:**

```bash
gh api repos/YOUR_USERNAME/dmaic-v3/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["CI Status Check","Phase 0 - CI Status"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true,"require_code_owner_reviews":false}' \
  --field required_linear_history=false \
  --field allow_force_pushes=false \
  --field allow_deletions=false \
  --field restrictions=null
```

**Develop Branch:**

```bash
gh api repos/YOUR_USERNAME/dmaic-v3/branches/develop/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["CI Status Check"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews=null \
  --field restrictions=null
```

#### Labels

```bash
# Create labels
gh label create "phase:0" --color "0E8A16" --description "Phase 0: Setup"
gh label create "phase:1" --color "1D76DB" --description "Phase 1: Define"
gh label create "phase:2" --color "5319E7" --description "Phase 2: Measure"
gh label create "phase:3" --color "E99695" --description "Phase 3: Analyze"
gh label create "phase:4" --color "F9D0C4" --description "Phase 4: Improve"
gh label create "phase:5" --color "FEF2C0" --description "Phase 5: Control"
gh label create "phase:6" --color "C2E0C6" --description "Phase 6: Knowledge"

gh label create "type:bug" --color "D73A4A" --description "Bug report"
gh label create "type:feature" --color "A2EEEF" --description "New feature"
gh label create "type:enhancement" --color "84B6EB" --description "Enhancement"
gh label create "type:documentation" --color "0075CA" --description "Documentation"

gh label create "priority:high" --color "B60205" --description "High priority"
gh label create "priority:medium" --color "FBCA04" --description "Medium priority"
gh label create "priority:low" --color "0E8A16" --description "Low priority"

gh label create "status:in-progress" --color "FBCA04" --description "In progress"
gh label create "status:review" --color "0E8A16" --description "In review"
gh label create "status:blocked" --color "D73A4A" --description "Blocked"

gh label create "good-first-issue" --color "7057FF" --description "Good for newcomers"
gh label create "help-wanted" --color "008672" --description "Help wanted"
```

#### Milestones

```bash
gh api repos/YOUR_USERNAME/dmaic-v3/milestones \
  --method POST \
  --field title="v3.0.0 - Foundation" \
  --field description="Complete foundation with Phase 0" \
  --field state="open"

gh api repos/YOUR_USERNAME/dmaic-v3/milestones \
  --method POST \
  --field title="v3.1.0 - Phase 1" \
  --field description="Implement Phase 1: Define" \
  --field state="open"

gh api repos/YOUR_USERNAME/dmaic-v3/milestones \
  --method POST \
  --field title="v3.2.0 - Phase 2" \
  --field description="Implement Phase 2: Measure" \
  --field state="open"

gh api repos/YOUR_USERNAME/dmaic-v3/milestones \
  --method POST \
  --field title="v3.3.0 - All Phases" \
  --field description="Complete all phases implementation" \
  --field state="open"
```

### Step 4: Configure Secrets

```bash
# PyPI token (for publishing packages)
gh secret set PYPI_API_TOKEN

# Codecov token (for code coverage)
gh secret set CODECOV_TOKEN

# Slack webhook (for notifications)
gh secret set SLACK_WEBHOOK

# Docker credentials (if using Docker)
gh secret set DOCKER_USERNAME
gh secret set DOCKER_PASSWORD
```

### Step 5: Enable GitHub Features

#### Enable Issues

```bash
gh api repos/YOUR_USERNAME/dmaic-v3 \
  --method PATCH \
  --field has_issues=true
```

#### Enable Projects

```bash
# Create project board
gh project create --title "DMAIC V3.0 Development" --body "Main development board"
```

#### Enable Discussions (Optional)

```bash
gh api repos/YOUR_USERNAME/dmaic-v3 \
  --method PATCH \
  --field has_discussions=true
```

### Step 6: Set Up Webhooks (Optional)

```bash
# Slack webhook
gh api repos/YOUR_USERNAME/dmaic-v3/hooks \
  --method POST \
  --field name="web" \
  --field active=true \
  --field events[]="push" \
  --field events[]="pull_request" \
  --field events[]="release" \
  --field config='{"url":"YOUR_SLACK_WEBHOOK","content_type":"json"}'
```

---

## 🔄 WORKFLOW EXAMPLES

### Creating a Feature Branch

```bash
# From develop
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/phase1-implementation

# Make changes
# ... edit files ...

# Commit with conventional commit
git add .
git commit -m "feat(phase1): implement artifact scanning

- Add file system scanner
- Implement pattern matching
- Add progress tracking
- Update tests"

# Push to GitHub
git push origin feature/phase1-implementation

# Create PR
gh pr create \
  --base develop \
  --title "feat(phase1): Implement artifact scanning" \
  --body "Implements artifact scanning for Phase 1

## Changes
- File system scanner
- Pattern matching
- Progress tracking

## Testing
- Unit tests added
- Integration tests passing

Closes #123"
```

### Creating a Bug Fix

```bash
# From develop
git checkout develop
git pull origin develop

# Create bugfix branch
git checkout -b bugfix/phase0-disk-check

# Fix bug
# ... edit files ...

# Commit
git add .
git commit -m "fix(phase0): correct disk space calculation

- Fix MB to GB conversion
- Add proper error handling
- Update tests

Fixes #456"

# Push and create PR
git push origin bugfix/phase0-disk-check
gh pr create --base develop
```

### Creating a Release

```bash
# Ensure you're on main
git checkout main
git pull origin main

# Use version manager
python version_manager.py bump minor

# Or manually trigger release workflow
gh workflow run release.yml \
  --field version_bump=minor

# Check release
gh release list
gh release view v3.1.0
```

---

## 🧪 TESTING CI/CD

### Test Main CI Pipeline

```bash
# Make a change
git checkout -b test/ci-pipeline
echo "# Test" >> README.md
git add README.md
git commit -m "test(ci): verify CI pipeline"
git push origin test/ci-pipeline

# Create PR and watch CI
gh pr create --base develop
gh pr checks
```

### Test Phase 0 CI

```bash
# Modify Phase 0
git checkout -b test/phase0-ci
echo "# Test" >> phases/phase0_setup.py
git add phases/phase0_setup.py
git commit -m "test(phase0): verify Phase 0 CI"
git push origin test/phase0-ci

# Watch CI
gh run list --workflow=ci-phase0.yml
gh run watch
```

### Test CD Pipeline

```bash
# Create a test tag
git tag -a v3.0.1-test -m "Test CD pipeline"
git push origin v3.0.1-test

# Watch CD
gh run list --workflow=cd-main.yml
gh run watch

# Clean up test tag
git tag -d v3.0.1-test
git push origin :refs/tags/v3.0.1-test
```

---

## 📊 MONITORING

### View CI/CD Status

```bash
# List recent runs
gh run list

# Watch specific run
gh run watch RUN_ID

# View logs
gh run view RUN_ID --log

# Download artifacts
gh run download RUN_ID
```

### View Repository Status

```bash
# Repository info
gh repo view

# Issues
gh issue list

# Pull requests
gh pr list

# Releases
gh release list
```

---

## 🔧 TROUBLESHOOTING

### CI Pipeline Fails

```bash
# View failed run
gh run view --log

# Re-run failed jobs
gh run rerun RUN_ID

# Re-run only failed jobs
gh run rerun RUN_ID --failed
```

### Branch Protection Issues

```bash
# Check protection status
gh api repos/YOUR_USERNAME/dmaic-v3/branches/main/protection

# Temporarily disable (admin only)
gh api repos/YOUR_USERNAME/dmaic-v3/branches/main/protection \
  --method DELETE
```

### Secret Issues

```bash
# List secrets
gh secret list

# Update secret
gh secret set SECRET_NAME

# Remove secret
gh secret remove SECRET_NAME
```

---

## 📚 ADDITIONAL RESOURCES

- [GitHub CLI Documentation](https://cli.github.com/manual/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)

---

## ✅ SETUP CHECKLIST

- [ ] Git repository initialized
- [ ] GitHub repository created
- [ ] Remote origin configured
- [ ] Main and develop branches pushed
- [ ] Branch protection rules set
- [ ] Labels created
- [ ] Milestones created
- [ ] Secrets configured
- [ ] CI/CD pipelines tested
- [ ] First release created
- [ ] Documentation updated
- [ ] Team members added

---

**DMAIC V3.0 - Git & GitHub Setup Complete** ✅
