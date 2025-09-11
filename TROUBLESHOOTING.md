# Troubleshooting GitHub Permission Issues

This guide helps diagnose and fix common GitHub permission problems with ABACUS.

## Quick Diagnosis

Run the automated test to identify issues:
```bash
./test_permissions.sh
```

## Common Error Messages and Solutions

### 1. "Permission Denied: Resource not accessible by personal access token"

**Cause**: Your GitHub token lacks sufficient permissions.

**Solutions**:
1. **Check token scopes**:
   - Go to [GitHub Settings > Personal access tokens](https://github.com/settings/tokens)
   - Find your token and verify it has `repo` scope checked
   
2. **Regenerate token with correct scopes**:
   ```bash
   # Delete old token in GitHub settings
   # Generate new token with 'repo' scope
   # Update environment variable
   export GITHUB_TOKEN=your_new_token
   ```

3. **Test the new token**:
   ```bash
   ./test_permissions.sh
   ```

### 2. "fatal: could not read Username for 'https://github.com'"

**Cause**: Git credential helper not configured for token authentication.

**Solution**: Configure git to use token authentication:
```bash
# Configure credential helper to use GITHUB_TOKEN
git config credential.helper "!f() { test \"\$1\" = get && echo \"password=\$GITHUB_TOKEN\"; }; f"

# Or set up credential helper globally
git config --global credential.helper "!f() { test \"\$1\" = get && echo \"password=\$GITHUB_TOKEN\"; }; f"
```

### 3. "Repository not found" (404 error)

**Possible causes**:
- Repository is private and token lacks access
- Token doesn't have `repo` scope
- Repository name is incorrect

**Solutions**:
1. **Verify repository exists and you have access**:
   ```bash
   curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/repos/GBOGEB/ABACUS
   ```

2. **Check if repository is private**:
   - Private repos require `repo` scope (not just `public_repo`)
   - Organization repos may need admin approval

### 4. "Bad credentials" (401 error)

**Causes**:
- Token is invalid or expired
- Token is not properly set in environment

**Solutions**:
1. **Verify token is set**:
   ```bash
   echo $GITHUB_TOKEN  # Should show your token
   ```

2. **Test token directly**:
   ```bash
   curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
   ```

3. **Generate new token if needed**

### 5. Organization Repository Issues

**Issue**: Token works for personal repos but not organization repos.

**Solution**: 
1. Check if organization requires token approval:
   - Go to organization settings
   - Check "Third-party application access policy"
   
2. Request approval from organization admin:
   - Admin must approve your personal access token
   - Or organization must enable token access

## Token Scope Requirements

### Minimum Required Scopes
For basic ABACUS functionality:
- ✅ `repo` - Full repository access
- ✅ `workflow` - GitHub Actions (if using CI/CD)

### Recommended Additional Scopes
For enhanced functionality:
- `write:packages` - Package registry access
- `read:packages` - Package downloads
- `user:email` - Access to email addresses

### Fine-grained Token Permissions
If using fine-grained tokens:
- **Repository access**: Selected repositories or all repositories
- **Contents**: Read and write
- **Metadata**: Read
- **Pull requests**: Write (if creating PRs)
- **Issues**: Write (if creating issues)

## Environment Setup Verification

### 1. Check Environment Variables
```bash
# Verify all required variables are set
echo "GITHUB_TOKEN: ${GITHUB_TOKEN:0:10}..." 
echo "GITHUB_USER: $GITHUB_USER"
echo "GITHUB_REPO: $GITHUB_REPO"
```

### 2. Check Git Configuration
```bash
# View current git configuration
git config --list | grep -E "(user|credential|remote)"

# Check remote URL
git remote -v
```

### 3. Test Repository Access
```bash
# Test read access
git ls-remote origin

# Test write access (safe - doesn't change anything)
git push --dry-run origin HEAD
```

## Advanced Troubleshooting

### Enable Git Debug Output
```bash
# Enable verbose git operations
export GIT_CURL_VERBOSE=1
export GIT_TRACE=1

# Try git operation with debug info
git push origin main
```

### Check Token Scopes via API
```bash
# Get detailed token information
curl -i -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

# Look for 'X-OAuth-Scopes' header in response
```

### Network/Proxy Issues
```bash
# Test direct GitHub API access
curl -v https://api.github.com/

# Check if proxy is interfering
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
```

## Prevention Tips

1. **Use token with appropriate lifetime**: Set reasonable expiration dates
2. **Regular token rotation**: Update tokens before expiration
3. **Least privilege principle**: Only grant necessary scopes
4. **Monitor token usage**: Check token usage in GitHub settings
5. **Secure storage**: Never commit tokens to repositories

## Getting Help

If issues persist:

1. **Run diagnostics**:
   ```bash
   ./test_permissions.sh > diagnostics.txt 2>&1
   ```

2. **Create an issue** with:
   - Error message (without token details)
   - Output of diagnostic script
   - Steps you've already tried

3. **Include environment info**:
   - Operating system
   - Git version: `git --version`
   - curl version: `curl --version`

## Emergency Recovery

If you've accidentally committed a token:

1. **Immediately revoke the token** in GitHub settings
2. **Remove from git history**:
   ```bash
   # Use git-filter-branch or BFG Repo-Cleaner
   # This is complex - consider creating new repository if needed
   ```
3. **Generate new token** with proper scopes
4. **Update all systems** using the old token

Remember: Prevention is better than recovery - use `.env` files and `.gitignore` properly!