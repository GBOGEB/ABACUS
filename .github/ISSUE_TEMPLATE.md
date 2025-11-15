---
name: GitHub Permission Issue
about: Report GitHub token permission problems
title: "[PERMISSIONS] "
labels: permissions, github-token
---

## GitHub Permission Issue

**Describe the problem**
A clear description of the permission error you're experiencing.

**Error message**
```
Paste the exact error message here
```

**Token Configuration**
- [ ] I have a GitHub Personal Access Token
- [ ] Token has `repo` scope enabled
- [ ] Token has `workflow` scope enabled  
- [ ] Token is set as `GITHUB_TOKEN` environment variable

**Repository Access**
- Repository: GBOGEB/ABACUS
- Access type: [ ] Public [ ] Private [ ] Organization
- Role: [ ] Owner [ ] Collaborator [ ] Outside collaborator

**Environment**
- OS: [e.g. Windows, macOS, Linux]
- Tool: [e.g. git CLI, GitHub Desktop, VS Code]
- Token type: [ ] Classic [ ] Fine-grained

**Troubleshooting Steps Tried**
- [ ] Regenerated GitHub token
- [ ] Verified token scopes in GitHub settings
- [ ] Tested token with `curl` command
- [ ] Checked organization token approval (if applicable)

**Additional context**
Add any other context about the problem here.

---

**Quick Fix Checklist:**
1. Go to [GitHub Token Settings](https://github.com/settings/tokens)
2. Generate new token with `repo` scope
3. Update `GITHUB_TOKEN` environment variable
4. Test with: `git push origin main`

See [GITHUB_SETUP.md](../GITHUB_SETUP.md) for detailed setup instructions.