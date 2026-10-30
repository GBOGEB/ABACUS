# 🚀 Quick Reference Guide - CI/CD Tracking System

## 📋 Common Commands

### CI Monitoring (Tests)

```bash
# Check CI status for PR
python ci_monitor_local.py --pr 15

# Watch CI continuously
python ci_monitor_local.py --pr 15 --watch

# Create issues for failures
python ci_monitor_local.py --pr 15 --create-issues
```

### CD Monitoring (Deployments)

```bash
# View all deployments
python cd_monitor.py

# Filter by environment
python cd_monitor.py --environment production

# Check deployment health
python cd_monitor.py --health-check 12345

# Generate report
python cd_monitor.py --report --save-report cd_report.json
```

### PR Tracking

```bash
# Sync PR from GitHub
python github_tracking_manager.py --sync-pr 15

# Sync CI runs
python github_tracking_manager.py --sync-ci 15

# Analyze for missed opportunities
python github_tracking_manager.py --analyze 15

# Generate PR report
python github_tracking_manager.py --report --pr 15
```

### Workflow Analysis

```bash
# Analyze last 30 days
python workflow_analyzer.py

# Analyze last 90 days
python workflow_analyzer.py --days 90

# Save report
python workflow_analyzer.py --save-report analysis.json
```

### PowerShell (Windows)

```powershell
# CI monitoring
.\ci_cd_automation.ps1 -PR 15

# CD monitoring
.\ci_cd_automation.ps1 -MonitorCD -Environment production

# Track PR
.\ci_cd_automation.ps1 -PR 15 -Track

# Analyze
.\ci_cd_automation.ps1 -Analyze -Days 30

# Generate reports
.\ci_cd_automation.ps1 -Report

# Combined
.\ci_cd_automation.ps1 -PR 15 -Track -Analyze -Report
```

---

## 🎯 Workflow Scenarios

### Scenario 1: New PR Created

```bash
# 1. Create PR
gh pr create --title "feat: New Feature" --body "Description"

# 2. Start tracking
python github_tracking_manager.py --sync-pr 15

# 3. Monitor CI
python ci_monitor_local.py --pr 15 --watch
```

### Scenario 2: CI Failure

```bash
# 1. Check status
python ci_monitor_local.py --pr 15

# 2. Create issues
python ci_monitor_local.py --pr 15 --create-issues

# 3. Update tracking
python github_tracking_manager.py --sync-ci 15
```

### Scenario 3: PR Merged

```bash
# 1. Sync final state
python github_tracking_manager.py --sync-pr 15
python github_tracking_manager.py --sync-ci 15

# 2. Analyze
python github_tracking_manager.py --analyze 15

# 3. Check deployments
python cd_monitor.py --environment staging
```

### Scenario 4: Weekly Review

```bash
# 1. Analyze workflows
python workflow_analyzer.py --days 7

# 2. Review feedback
python github_tracking_manager.py --review-feedback

# 3. Generate reports
python github_tracking_manager.py --report
python cd_monitor.py --report
```

---

## 📊 State Files

### JSON (Machine-Readable)
```bash
cat github_tracking_state.json
```

### YAML (Human-Readable)
```bash
cat github_tracking_state.yaml
```

### Structure
```yaml
metadata:
  version: "1.0.0"
  repository: "GBOGEB/ABACUS"

pull_requests:
  "15":
    status: "merged"
    ci_runs: [...]
    cd_deployments: [...]
    copilot_feedback: [...]

issues:
  "16":
    status: "open"
    sub_issues: [17, 18]

ci_cd_history:
  ci_runs: [...]
  cd_deployments: [...]
  missed_opportunities: [...]

copilot_feedback_queue: [...]
action_items: [...]
```

---

## 🔧 Authentication

### Setup (One-Time)
```bash
gh auth login
```

### Verify
```bash
gh auth status
```

### Get Token
```bash
gh auth token
```

---

## 📁 File Structure

```
.
├── ci_monitor_local.py              # CI monitoring
├── cd_monitor.py                    # CD monitoring
├── github_tracking_manager.py       # Tracking system
├── workflow_analyzer.py             # Workflow analysis
├── ci_cd_automation.ps1             # PowerShell wrapper
├── github_tracking_state.json       # State (JSON)
├── github_tracking_state.yaml       # State (YAML)
├── GITHUB_TRACKING_README.md        # Full documentation
├── CI_CD_AUTOMATION_README.md       # CI/CD docs
└── .github/
    ├── workflows/
    │   └── ci_monitor_and_issue_creator.yml
    └── scripts/
        └── create_issues_from_failures.py
```

---

## 🎨 Output Examples

### CI Status
```
🔍 Checking CI status for PR #15...
✅ CI Status: success
📊 Check Runs: 3
   ✅ build - success
   ✅ test - success
   ✅ lint - success
```

### CD Status
```
📦 Deployment Status
════════════════════════════════════════
🌍 Environment: production
   ✅ abc1234 - success
   Created: 2024-12-16T10:00:00Z
   By: github-actions
```

### Tracking Report
```
📊 GitHub CI/CD Tracking Report
════════════════════════════════════════
📊 PR #15: feat: New Feature
   Status: merged
   Branch: feature/new-feature
   CI Runs: 5
   Issues Created: 0
   Copilot Feedback: 2
```

### Workflow Analysis
```
📊 GitHub Workflow Analysis Report
════════════════════════════════════════
📈 Summary (30 days):
   Total Runs: 150
   Total Failures: 10
   Failure Rate: 6.7%

🎯 Missed Opportunities (3):
🟡 workflow_optimization (medium)
   Description: Workflow runtime could be optimized
   Recommendation: Consider caching dependencies
```

---

## 🆘 Troubleshooting

### Issue: "No tracking state found"
```bash
python github_tracking_manager.py --sync-pr 15
```

### Issue: "Cannot sync CI runs"
```bash
# Check if PR has CI runs
gh pr checks 15

# Sync manually
python github_tracking_manager.py --sync-ci 15
```

### Issue: "Authentication failed"
```bash
# Re-authenticate
gh auth login

# Verify
gh auth status
```

### Issue: "Deployment not found"
```bash
# Check if deployments exist
gh api repos/GBOGEB/ABACUS/deployments
```

---

## 💡 Tips

1. **Sync regularly** - Run tracking after every PR update
2. **Review feedback daily** - Check `--review-feedback`
3. **Analyze weekly** - Run `workflow_analyzer.py` weekly
4. **Commit state files** - Track changes in Git
5. **Use watch mode** - Monitor CI in real-time with `--watch`

---

## 📞 Quick Help

```bash
# CI Monitor
python ci_monitor_local.py --help

# CD Monitor
python cd_monitor.py --help

# Tracking Manager
python github_tracking_manager.py --help

# Workflow Analyzer
python workflow_analyzer.py --help

# PowerShell
.\ci_cd_automation.ps1
```

---

**Version:** 1.0.0
**Last Updated:** December 16, 2024
