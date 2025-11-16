# 🤖 CI/CD Automation System

**Complete automation for GitHub CI/CD with automatic issue creation for test failures**

## 🎯 Overview

This system provides **semi-automated** CI/CD management with clear separation between:
- **Code Side (Local/MCP):** Git operations, test execution, issue creation
- **GitHub Side:** PR management, CI/CD checks, merge operations

### Key Features

✅ **Automated CI Monitoring** - Real-time status tracking  
✅ **Auto Issue Creation** - GitHub issues for every test failure  
✅ **Parallel Workflows** - MCP copilot (GitHub) + MCP local (Git)  
✅ **Smart Merge** - Only merge when all checks pass  
✅ **Release Automation** - Automatic tagging and release creation  
✅ **User Control** - Manual approval points for critical operations

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
- Real-time CI status monitoring
- Fetching test results
- Creating issues from local machine
- Watch mode for continuous monitoring

### 4. PowerShell Automation
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

### Prerequisites

```bash
# Install required packages
pip install PyGithub requests pytest pytest-json-report

# Set GitHub token
export GITHUB_TOKEN="your_github_token"  # Linux/Mac
$env:GITHUB_TOKEN="your_github_token"    # Windows PowerShell

# Optional: Install GitHub CLI
# https://cli.github.com/
```

### Basic Usage

#### 1. Monitor CI Status
```bash
# Python (cross-platform)
python ci_monitor_local.py --pr 15

# PowerShell (Windows)
.\ci_automation.ps1 status -PRNumber 15
```

#### 2. Watch CI Continuously
```bash
# Python
python ci_monitor_local.py --pr 15 --watch

# PowerShell
.\ci_automation.ps1 monitor -PRNumber 15 -Watch
```

#### 3. Create Issues for Failures
```bash
# Python
python ci_monitor_local.py --pr 15 --create-issues

# PowerShell
.\ci_automation.ps1 create-issues -PRNumber 15
```

#### 4. Complete Roundtrip
```powershell
# PowerShell - Full automation
.\ci_automation.ps1 roundtrip -AutoMerge -CreateIssues
```

---

## 📋 Workflows

### Workflow 1: Manual Control (Recommended)

```bash
# 1. Create PR (done via GitHub web interface)

# 2. Monitor CI locally
python ci_monitor_local.py --pr 15 --watch

# 3. If failures, create issues
python ci_monitor_local.py --pr 15 --create-issues

# 4. Fix issues (work on fixes locally)

# 5. Push fixes
git add .
git commit -m "fix: resolve CI failures"
git push

# 6. Monitor again
python ci_monitor_local.py --pr 15 --watch

# 7. Merge via GitHub web interface when ready

# 8. Tag release locally
.\github_roundtrip.ps1 tag
```

### Workflow 2: Semi-Automated

```powershell
# PowerShell - monitors, creates issues, waits for CI, then merges
.\ci_automation.ps1 roundtrip -AutoMerge -CreateIssues -PRNumber 15
```

### Workflow 3: GitHub Actions (Fully Automated)

The GitHub Actions workflow automatically:
1. Runs on every PR update
2. Executes tests
3. Creates issues for failures
4. Comments on PR with summary

**No local action required!**

---

## 🔧 Configuration

### Environment Variables

```bash
# Required
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
export GITHUB_REPOSITORY="GBOGEB/ABACUS"

# Optional
export PR_NUMBER="15"
```

### GitHub Token Permissions

Your token needs:
- `repo` - Full repository access
- `workflow` - Workflow access
- `write:discussion` - Issue/PR comments

Create token at: https://github.com/settings/tokens

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

### Issue: "GITHUB_TOKEN not found"
```bash
# Set token
export GITHUB_TOKEN="your_token"  # Linux/Mac
$env:GITHUB_TOKEN="your_token"    # Windows
```

### Issue: "Repository not found"
```bash
# Specify explicitly
python ci_monitor_local.py --pr 15 --repo GBOGEB/ABACUS
```

### Issue: "PR not found"
```bash
# Check PR number
gh pr list

# Use correct number
python ci_monitor_local.py --pr <correct_number>
```

### Issue: "Cannot create issue - already exists"
This is normal! The system prevents duplicates.

### Issue: "Timeout waiting for CI"
```bash
# Increase timeout or check manually
gh pr checks 15
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
