# ABACUS
CodeLLM and Deep Agent place to view and drop all files

## Quick Start

ABACUS provides a centralized workspace for CodeLLM integration with full repository access.

### GitHub Token Setup
To avoid "Permission Denied" errors when pushing to GitHub, ensure your token has proper permissions:

👉 **[Complete Setup Guide](GITHUB_SETUP.md)** - Follow this guide to configure GitHub token permissions

### Required Permissions
Your GitHub Personal Access Token needs:
- ✅ **repo** scope (full repository access)
- ✅ **workflow** scope (for GitHub Actions)
- ✅ **write:packages** scope (for package operations)

### Quick Fix
```bash
# Set your GitHub token with repo permissions
export GITHUB_TOKEN=your_token_with_repo_scope
```

## Quick Setup Test
Run the automated permission test:
```bash
./test_permissions.sh
```

## Troubleshooting
- **"Permission Denied"** → Check token has `repo` scope in [GitHub Settings](https://github.com/settings/tokens)
- **"Resource not accessible"** → Regenerate token with full repository permissions
- **Organization repos** → May require admin approval for token access

## Documentation
- 📖 [Complete Setup Guide](GITHUB_SETUP.md) - Detailed GitHub token configuration
- 🔧 [Troubleshooting Guide](TROUBLESHOOTING.md) - Fix common permission issues  
- 📋 [Configuration Example](.env.example) - Environment variable template
- 🧪 [Permission Test Script](test_permissions.sh) - Automated validation tool

## Files Overview
- `GITHUB_SETUP.md` - Comprehensive token setup instructions
- `TROUBLESHOOTING.md` - Common issues and solutions
- `test_permissions.sh` - Automated permission validation
- `.env.example` - Environment configuration template
- `.github/ISSUE_TEMPLATE.md` - Issue template for permission problems
- `.github/workflows/validate-setup.yml` - CI validation workflow
