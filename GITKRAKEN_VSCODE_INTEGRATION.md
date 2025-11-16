# GitKraken + VS Code + GitHub Integration Guide

## 🎯 Complete Integration Setup

This guide sets up full integration between GitKraken, VS Code, GitHub, and CI/CD workflows.

---

## 📦 Prerequisites

### 1. Install Required Tools

```bash
# GitHub CLI
winget install GitHub.cli

# GitKraken (if not installed)
winget install Axosoft.GitKraken

# VS Code (if not installed)
winget install Microsoft.VisualStudioCode
```

### 2. Verify Installations

```bash
gh --version
git --version
code --version
```

---

## 🔐 Authentication Setup

### 1. GitHub CLI Authentication

```bash
# Login to GitHub
gh auth login

# Select:
# - GitHub.com
# - HTTPS
# - Login with a web browser

# Verify
gh auth status
```

### 2. GitKraken Authentication

1. Open GitKraken
2. Click **File** → **Preferences** → **Authentication**
3. Click **Connect** next to GitHub
4. Authorize GitKraken in browser
5. Verify connection shows ✅

### 3. VS Code GitHub Authentication

1. Open VS Code
2. Press `Ctrl+Shift+P`
3. Type: `GitHub: Sign In`
4. Authorize in browser
5. Verify: Look for GitHub icon in Activity Bar

---

## 🔧 VS Code Extensions Setup

### Automatic Installation

The repository includes `.vscode/extensions.json` which will prompt you to install:

**Core Extensions:**
- GitHub Pull Requests and Issues
- GitHub Copilot
- GitHub Copilot Chat
- GitHub Actions
- GitLens
- GitKraken Authentication

**Supporting Extensions:**
- Python
- Pylance
- Jupyter
- YAML
- Docker

### Manual Installation

```bash
# Install all recommended extensions
code --install-extension github.vscode-pull-request-github
code --install-extension github.copilot
code --install-extension github.copilot-chat
code --install-extension github.vscode-github-actions
code --install-extension eamodio.gitlens
code --install-extension gitkraken.gitkraken-authentication
code --install-extension ms-vscode.vscode-github-issue-notebooks
code --install-extension github.remotehub
code --install-extension ms-vscode-remote.remote-repositories
code --install-extension ms-python.python
code --install-extension redhat.vscode-yaml
```

---

## 🚀 VS Code Tasks Integration

The repository includes `.vscode/tasks.json` with pre-configured tasks:

### Run Tasks

Press `Ctrl+Shift+P` → `Tasks: Run Task` → Select:

1. **Push to GitHub** - Push current branch
2. **Create PR** - Create pull request
3. **Check CI Status** - Check CI for PR
4. **Watch CI** - Monitor CI in real-time
5. **Check CD Status** - Check deployments
6. **Track PR** - Update tracking state
7. **Analyze Workflows** - Analyze past workflows
8. **Generate Reports** - Generate all reports
9. **Full CI/CD Check** - Complete check (PowerShell)
10. **Run Tests** - Execute pytest
11. **Validate YAML** - Validate workflow files
12. **GitHub Auth Status** - Check authentication

### Keyboard Shortcuts

Add to `.vscode/keybindings.json`:

```json
[
  {
    "key": "ctrl+shift+g p",
    "command": "workbench.action.tasks.runTask",
    "args": "Push to GitHub"
  },
  {
    "key": "ctrl+shift+g c",
    "command": "workbench.action.tasks.runTask",
    "args": "Check CI Status"
  },
  {
    "key": "ctrl+shift+g r",
    "command": "workbench.action.tasks.runTask",
    "args": "Generate Reports"
  }
]
```

---

## 🎨 GitKraken Integration

### 1. Open Repository in GitKraken

```bash
# From VS Code terminal
gitkraken --path .
```

Or:
1. Open GitKraken
2. **File** → **Open Repo** → Select repository

### 2. Configure GitKraken

**Preferences** → **General**:
- ✅ Auto-fetch every 5 minutes
- ✅ Show commit graph
- ✅ Enable GitFlow

**Preferences** → **Integrations**:
- ✅ GitHub (connected)
- ✅ Enable PR creation
- ✅ Enable issue tracking

### 3. GitKraken Workflows

**Create PR from GitKraken:**
1. Push branch
2. Right-click branch → **Create Pull Request**
3. Fill details → **Create Pull Request**

**View CI/CD Status:**
1. Click on commit
2. View **Checks** tab
3. See CI/CD status

---

## 🔄 Complete Workflow Integration

### Scenario 1: Create Feature Branch and PR

**In VS Code:**

```bash
# 1. Create branch
git checkout -b feature/new-feature

# 2. Make changes and commit
git add .
git commit -m "feat: Add new feature"

# 3. Push (use VS Code task)
# Ctrl+Shift+P → Tasks: Run Task → Push to GitHub

# 4. Create PR (use VS Code task)
# Ctrl+Shift+P → Tasks: Run Task → Create PR
```

**In GitKraken:**

1. Create branch (right-click main → **Create branch**)
2. Make commits
3. Push branch (click **Push** button)
4. Create PR (right-click branch → **Create Pull Request**)

### Scenario 2: Monitor CI/CD

**In VS Code:**

```bash
# Watch CI in real-time
# Ctrl+Shift+P → Tasks: Run Task → Watch CI

# Or use PowerShell
.\ci_cd_automation.ps1 -PR 15 -Watch
```

**In GitKraken:**

1. Click on commit
2. View **Checks** tab
3. See real-time CI/CD status

**In GitHub (via VS Code):**

1. Open **GitHub Pull Requests** view
2. Click on PR
3. View **Checks** section

### Scenario 3: Track and Analyze

**In VS Code:**

```bash
# Full tracking and analysis
# Ctrl+Shift+P → Tasks: Run Task → Full CI/CD Check

# Or manually
python github_tracking_manager.py --sync-pr 15
python github_tracking_manager.py --sync-ci 15
python github_tracking_manager.py --analyze 15
python github_tracking_manager.py --report --pr 15
```

---

## 🎯 GitHub Codespaces Integration

### 1. Open in Codespaces

```bash
# From GitHub repository
gh codespace create --repo GBOGEB/ABACUS

# Or click "Code" → "Codespaces" → "Create codespace"
```

### 2. Codespaces Configuration

The repository includes `.devcontainer/devcontainer.json` (if needed):

```json
{
  "name": "ABACUS Development",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "features": {
    "ghcr.io/devcontainers/features/github-cli:1": {},
    "ghcr.io/devcontainers/features/git:1": {}
  },
  "customizations": {
    "vscode": {
      "extensions": [
        "github.vscode-pull-request-github",
        "github.copilot",
        "github.vscode-github-actions",
        "eamodio.gitlens"
      ]
    }
  },
  "postCreateCommand": "pip install -r requirements.txt",
  "remoteUser": "vscode"
}
```

---

## 📊 VS Code GitHub Integration Features

### 1. Pull Requests View

- View all PRs in sidebar
- Create/review/merge PRs
- View CI/CD status
- Comment on PRs

### 2. Issues View

- View/create/close issues
- Filter by labels
- Assign issues
- Link to PRs

### 3. GitHub Actions View

- View workflow runs
- See logs
- Re-run workflows
- View artifacts

### 4. Copilot Integration

- Code suggestions
- Chat assistance
- PR descriptions
- Commit messages

---

## 🔧 Configuration Files

### `.vscode/extensions.json`
Recommends required extensions

### `.vscode/settings.json`
Configures GitHub, GitLens, Copilot, YAML validation

### `.vscode/tasks.json`
Pre-configured tasks for CI/CD operations

### `.vscode/launch.json` (Optional)
Debug configurations for Python scripts

---

## 🎨 GitKraken Features

### 1. Visual Commit Graph
- See branch history
- View merges
- Track PRs

### 2. PR Management
- Create PRs
- Review code
- Merge PRs
- View CI/CD status

### 3. Issue Tracking
- View issues
- Create issues
- Link to commits

### 4. GitFlow Support
- Feature branches
- Release branches
- Hotfix branches

---

## 🚀 Quick Commands

### VS Code Command Palette (`Ctrl+Shift+P`)

```
GitHub: Sign In
GitHub: Create Pull Request
GitHub: View Pull Requests
GitHub: View Issues
GitHub Actions: View Workflows
GitLens: Show Commit Graph
Tasks: Run Task
```

### VS Code Terminal

```bash
# Push and create PR
git push origin feature/new-feature
gh pr create --title "feat: New Feature" --body "Description"

# Check CI
python ci_monitor_local.py --pr 15 --watch

# Track PR
python github_tracking_manager.py --sync-pr 15

# Full check
.\ci_cd_automation.ps1 -PR 15 -Track -Analyze -Report
```

### GitKraken

- `Ctrl+P` - Push
- `Ctrl+Shift+P` - Pull
- `Ctrl+N` - New branch
- `Ctrl+M` - Merge

---

## 🔍 Troubleshooting

### Issue: "Not authenticated"

```bash
# Re-authenticate GitHub CLI
gh auth login

# Re-authenticate VS Code
# Ctrl+Shift+P → GitHub: Sign In

# Re-authenticate GitKraken
# File → Preferences → Authentication → Reconnect
```

### Issue: "Extensions not working"

```bash
# Reload VS Code
# Ctrl+Shift+P → Developer: Reload Window

# Reinstall extensions
code --install-extension github.vscode-pull-request-github --force
```

### Issue: "Tasks not found"

```bash
# Verify .vscode/tasks.json exists
ls .vscode/tasks.json

# Reload tasks
# Ctrl+Shift+P → Tasks: Run Task
```

---

## 📈 Best Practices

### 1. Use VS Code for Development
- Code editing
- Running tests
- Monitoring CI/CD
- Creating PRs

### 2. Use GitKraken for Git Operations
- Visual commit history
- Branch management
- Merge conflict resolution
- PR reviews

### 3. Use GitHub CLI for Automation
- Scripting
- CI/CD integration
- Batch operations

### 4. Use GitHub Copilot
- Code suggestions
- Documentation
- Test generation
- PR descriptions

---

## 🎉 Summary

You now have complete integration between:

✅ **VS Code** - Development environment with GitHub integration  
✅ **GitKraken** - Visual Git client with PR management  
✅ **GitHub CLI** - Command-line automation  
✅ **GitHub Copilot** - AI-powered coding assistance  
✅ **CI/CD Tracking** - Automated monitoring and analysis  
✅ **YAML Workflows** - Validated and executable  

**Result:** Seamless workflow from code to deployment!

---

**Version:** 1.0.0  
**Date:** December 16, 2024  
**Status:** ✅ Production Ready
