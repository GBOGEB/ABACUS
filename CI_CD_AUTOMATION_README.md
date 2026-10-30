# 🤖 CI/CD Automation System

**Complete automation for GitHub CI/CD with automatic issue creation for test failures**

## 🎯 Overview

This system provides **semi-automated** CI/CD management with clear separation between:
- **Code Side (Local/MCP):** Git operations, test execution, issue creation
- **GitHub Side:** PR management, CI/CD checks, merge operations

### Key Features

✅ **Automated CI Monitoring** - Real-time status tracking for tests
✅ **Automated CD Monitoring** - Deployment tracking and health checks
✅ **Auto Issue Creation** - GitHub issues for every test failure
✅ **Parallel Workflows** - MCP copilot (GitHub) + MCP local (Git)
✅ **Smart Merge** - Only merge when all checks pass
✅ **Release Automation** - Automatic tagging and release creation
✅ **User Control** - Manual approval points for critical operations
✅ **Complete Tracking** - JSON/YAML state files for PR lifecycle

---

## 📦 Components

### 1. GitHub Actions Workflow
**File:** `.github/workflows/ci_monitor_and_issue_creator.yml`

Automatically triggered on:
- PR creation/update
- CI workflow completion

**Actions:**
- Runs tests
- Parses results
- Creates issues for failures
- Comments on PR with summary

### 2. Issue Creator Script
**File:** `.github/scripts/create_issues_from_failures.py`

Python script that:
- Parses pytest JSON reports
- Creates detailed GitHub issues
- Links issues to PRs
- Assigns labels and priorities
- Avoids duplicates

### 3. Local CI Monitor
**File:** `ci_monitor_local.py`

Local Python script for:
- Real-time CI status monitoring (tests)
- Watch mode for continuous updates
- Issue creation from local environment
- Integration with GitHub CLI

### 4. Local CD Monitor
**File:** `cd_monitor.py`

Local Python script for:
- Deployment status monitoring
- Environment tracking (staging, production)
- Health checks for deployments
- Deployment history and reports

### 5. GitHub Tracking Manager
**File:** `github_tracking_manager.py`

Comprehensive tracking system for:
- PR lifecycle tracking
- CI/CD run history
- Copilot feedback capture
- Missed opportunity detection
- Sub-issue management
- State persistence (JSON + YAML)

### 6. Workflow Analyzer
**File:** `workflow_analyzer.py`

Analyzes past workflows for:
- Failure pattern detection
- Missed CI/CD opportunities
- Actionable recommendations
- Historical trend analysis

### 7. PowerShell Automation
**File:** `ci_automation.ps1`

Complete automation script:
- PR status checking
- CI monitoring
- Issue creation
- Auto-merge (when CI passes)
- Release tagging
- Complete roundtrip

---

## 🚀 Quick Start

### 1. One-Time Setup

```bash
# Install and authenticate GitHub CLI
gh auth login

# Verify authentication
gh auth status
```

### 2. Basic Usage

#### Monitor CI Status
```bash
# Check current status
python ci_monitor_local.py --pr 15

# Watch continuously (updates every 30 seconds)
python ci_monitor_local.py --pr 15 --watch
```

#### Create Issues for Failures
```bash
# Automatically create GitHub issues for failing tests
python ci_monitor_local.py --pr 15 --create-issues
```

#### PowerShell Automation (Windows)
```powershell
# Check status
.\ci_automation.ps1 status -PRNumber 15

# Monitor with auto-issue creation
.\ci_automation.ps1 monitor -PRNumber 15 -Watch -CreateIssues

# Full roundtrip (monitor → create issues → auto-merge when green)
.\ci_automation.ps1 roundtrip -PRNumber 15 -AutoMerge -CreateIssues
```

---

## 📋 Workflows

### Workflow 1: Manual Control (Recommended)

```bash
# 1. Create PR (via GitHub web interface or gh CLI)
gh pr create --title "feat: My Feature" --body "Description"

# 2. Monitor CI locally (auto-authenticated via gh CLI)
python ci_monitor_local.py --pr 15 --watch

# 3. If failures occur, create issues automatically
python ci_monitor_local.py --pr 15 --create-issues

# 4. Fix issues locally
# ... make your fixes ...

# 5. Push fixes
git add .
git commit -m "fix: resolve CI failures"
git push

# 6. Monitor again until green
python ci_monitor_local.py --pr 15 --watch

# 7. Merge when ready
gh pr merge 15 --squash

# 8. Tag release
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

### Workflow 2: Semi-Automated (PowerShell)

```powershell
# One command to rule them all:
# - Monitors CI continuously
# - Creates issues for failures
# - Auto-merges when all checks pass
.\ci_automation.ps1 roundtrip -PRNumber 15 -AutoMerge -CreateIssues
```

### Workflow 3: GitHub Actions (Fully Automated)

The GitHub Actions workflow automatically:
1. ✅ Runs on every PR update
2. ✅ Executes all tests
3. ✅ Creates issues for failures
4. ✅ Comments on PR with summary
5. ✅ Links issues to PR

**No local action required!** Just push your code and the automation handles the rest.

---

## 🔧 Configuration

## Authentication

The scripts use **GitHub CLI authentication** which is more secure than manual tokens:

### ✅ Recommended: GitHub CLI (Automatic)
```bash
# One-time setup
gh auth login

# The scripts will automatically use gh CLI credentials
python ci_monitor_local.py --pr 15
```

### 🔧 Alternative: Environment Variable (CI/CD)
For GitHub Actions workflows, the token is automatically provided:
```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

For local development with environment variables:
```bash
# Linux/macOS
export GITHUB_TOKEN=$(gh auth token)

# Windows PowerShell
$env:GITHUB_TOKEN = gh auth token

# Windows CMD
set GITHUB_TOKEN=%gh auth token%
```

**Note:** The scripts will automatically try these methods in order:
1. GitHub CLI authentication (`gh auth token`)
2. `GITHUB_TOKEN` environment variable
3. `--token` command line argument (for advanced users)

### Environment Variables

```bash
# Optional - usually auto-detected
export GITHUB_REPOSITORY="GBOGEB/ABACUS"
export PR_NUMBER="15"
```

### Required Permissions

When using `gh auth login`, ensure you grant these scopes:
- `repo` - Full repository access
- `workflow` - Workflow access
- `write:discussion` - Issue/PR comments

The GitHub CLI will request appropriate permissions during login.

---

## 📊 Issue Creation

### Automatic Issue Format

When a test fails, an issue is automatically created with:

**Title:** `🔴 CI Failure: test_function_name`

**Labels:**
- `ci-failure` - Identifies CI failures
- `automated` - Auto-created issue
- `priority:high/medium` - Based on test type
- `integration-test` or `unit-test` - Test category

**Content:**
- Test name and file
- Failure message
- Investigation steps
- Fix checklist
- Links to PR and CI logs

### Duplicate Prevention

The system checks for existing issues before creating new ones, preventing duplicate issues for the same test.

---

## 🎯 Use Cases

### Use Case 1: PR Created, CI Fails

```bash
# Scenario: You create PR #15, CI fails

# Step 1: Check what failed
python ci_monitor_local.py --pr 15

# Output:
# ❌ FAILED
# Total Checks: 3
# ✅ Passed: 2
# ❌ Failed: 1
# Check Details:
#   ❌ pytest: failure

# Step 2: Create issues
python ci_monitor_local.py --pr 15 --create-issues

# Output:
# ✅ Created issue #16: 🔴 CI Failure: test_integration

# Step 3: Fix the issue
# (work on fix locally)

# Step 4: Push fix
git add .
git commit -m "fix: resolve test_integration failure"
git push

# Step 5: Verify
python ci_monitor_local.py --pr 15 --watch
# ✅ All checks passed!
```

### Use Case 2: Continuous Monitoring

```bash
# Watch CI in real-time
python ci_monitor_local.py --pr 15 --watch --create-issues

# This will:
# 1. Check CI status every 30s
# 2. Display updates
# 3. Create issues if failures detected
# 4. Stop when CI completes (success or failure)
```

### Use Case 3: Complete Automation

```powershell
# Full roundtrip with auto-merge
.\ci_automation.ps1 roundtrip -AutoMerge -CreateIssues

# This will:
# 1. Monitor CI
# 2. Create issues for failures
# 3. Wait for CI to pass
# 4. Merge PR automatically
# 5. Tag release
# 6. Create GitHub release
```

---

## 🔍 Monitoring Output

### Status Display

```
======================================================================
🔍 CI/CD Status for PR #15
======================================================================
Title: feat: Complete DMAIC + DOW Integration with Live Demonstration
Commit: e963a8a
Status: ✅ SUCCESS

📊 Summary:
   Total Checks: 3
   ✅ Passed: 3
   ❌ Failed: 0
   ⏳ Pending: 0

🔧 Check Details:
   ✅ pytest: success
   ✅ lint: success
   ✅ type-check: success
======================================================================
```

### Issue Creation Output

```
🤖 CI/CD Issue Creator - Starting
======================================================================

📊 Test Summary:
   Total: 10
   ✅ Passed: 8
   ❌ Failed: 2

🔍 Processing 2 failing test(s)...

✅ Created issue #16: 🔴 CI Failure: test_integration
✅ Created issue #17: 🔴 CI Failure: test_validation

======================================================================
✅ Created 2 issue(s)
   Issue numbers: #16, #17
======================================================================
```

---

## 🛠️ Advanced Usage

### Custom Watch Interval

```bash
# Check every 60 seconds instead of 30
python ci_monitor_local.py --pr 15 --watch --interval 60
```

### Specify Repository

```bash
# If not auto-detected
python ci_monitor_local.py --pr 15 --repo GBOGEB/ABACUS
```

### Use with Different Token

```bash
# Use specific token
python ci_monitor_local.py --pr 15 --token ghp_xxxxxxxxxxxx
```

---

## 📚 Integration with MCP

### MCP Copilot (GitHub Side)

The GitHub Actions workflow acts as the "MCP copilot" on GitHub:
- Monitors all PRs
- Runs tests automatically
- Creates issues
- Comments on PRs

### MCP Local (User Git Side)

The local scripts act as "MCP local" on your machine:
- Monitor CI from local environment
- Create issues from local machine
- Control merge timing
- Manage releases

### Parallel Operation

Both systems work in parallel:
- **GitHub Actions:** Automatic, always running
- **Local Scripts:** On-demand, user-controlled

This provides:
- ✅ Redundancy
- ✅ Flexibility
- ✅ User control
- ✅ Automation

---

## 🎯 Best Practices

### 1. Always Monitor Before Merge
```bash
python ci_monitor_local.py --pr 15
```

### 2. Create Issues Early
```bash
# Don't wait - create issues immediately
python ci_monitor_local.py --pr 15 --create-issues
```

### 3. Use Watch Mode for Long CI
```bash
# For CI that takes >5 minutes
python ci_monitor_local.py --pr 15 --watch
```

### 4. Review Issues Before Fixing
- Check all created issues
- Prioritize by label
- Fix high-priority first

### 5. Verify Locally Before Push
```bash
# Run tests locally first
pytest -v

# Then push
git push
```

---

## 🔧 Troubleshooting

### Authentication Issues

#### Issue: "GitHub authentication required"
```bash
# Solution 1: Use GitHub CLI (recommended)
gh auth login

# Verify it worked
gh auth status

# Test the script
python ci_monitor_local.py --pr 15
```

#### Issue: "gh: command not found"
```bash
# Install GitHub CLI first
# Windows
winget install --id GitHub.cli

# macOS
brew install gh

# Linux (Debian/Ubuntu)
sudo apt install gh

# Then authenticate
gh auth login
```

#### Issue: "Token invalid or expired"
```bash
# Re-authenticate with GitHub CLI
gh auth logout
gh auth login

# Verify
gh auth status

# If using environment variable, refresh it
export GITHUB_TOKEN=$(gh auth token)  # Linux/Mac
$env:GITHUB_TOKEN = gh auth token     # Windows PowerShell
```

### Repository Issues

#### Issue: "Repository not found"
```bash
# Specify repository explicitly
python ci_monitor_local.py --pr 15 --repo GBOGEB/ABACUS

# Or set environment variable
export GITHUB_REPOSITORY=GBOGEB/ABACUS  # Linux/Mac
$env:GITHUB_REPOSITORY = "GBOGEB/ABACUS"  # Windows PowerShell
```

#### Issue: "PR not found"
```bash
# List all PRs to find the correct number
gh pr list

# Use the correct PR number
python ci_monitor_local.py --pr <correct_number>
```

### CI/CD Issues

#### Issue: "Cannot create issue - already exists"
✅ This is normal! The system prevents duplicate issues.

#### Issue: "Timeout waiting for CI"
```bash
# Check CI status manually
gh pr checks 15

# Increase watch interval
python ci_monitor_local.py --pr 15 --watch --interval 60
```

#### Issue: "No test results found"
```bash
# Ensure tests are running in CI
gh pr checks 15

# Check workflow logs
gh run view --log
```

### Permission Issues

#### Issue: "Permission denied to create issues"
```bash
# Ensure your GitHub token has the right scopes
gh auth refresh -s repo -s write:discussion

# Verify permissions
gh auth status
```

---

## 📞 Support

### Quick Commands

```bash
# Check PR status
gh pr view 15

# Check CI status
gh pr checks 15

# List issues
gh issue list --label ci-failure

# View issue
gh issue view 16
```

### Files

- **Workflow:** `.github/workflows/ci_monitor_and_issue_creator.yml`
- **Issue Creator:** `.github/scripts/create_issues_from_failures.py`
- **Local Monitor:** `ci_monitor_local.py`
- **Automation:** `ci_automation.ps1`
- **This README:** `CI_CD_AUTOMATION_README.md`

---

## 🎉 Summary

This CI/CD automation system provides:

✅ **Semi-Automated Workflow** - User control with automation
✅ **Automatic Issue Creation** - Never miss a failing test
✅ **Parallel Operation** - GitHub + Local working together
✅ **Real-Time Monitoring** - Know CI status immediately
✅ **Smart Merging** - Only merge when ready
✅ **Complete Roundtrip** - From PR to release

**Result:** Efficient, controlled, and reliable CI/CD process!

---

**Version:** 1.0.0
**Date:** December 16, 2024
**Status:** ✅ Production Ready
