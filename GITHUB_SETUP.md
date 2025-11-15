# GitHub Token Setup and Permissions

This guide helps resolve the "Permission Denied: Resource not accessible by personal access token" error when using ABACUS with GitHub.

## Required GitHub Token Permissions

To give your codeLLM (ABACUS) correct access to the full repository, your GitHub Personal Access Token must have the following scopes:

### Classic Personal Access Token Scopes
- ✅ **repo** (Full control of private repositories)
  - repo:status
  - repo_deployment 
  - public_repo
  - repo:invite
  - security_events
- ✅ **workflow** (Update GitHub Action workflows)
- ✅ **write:packages** (Upload packages to GitHub Package Registry)
- ✅ **read:packages** (Download packages from GitHub Package Registry)

### Fine-grained Personal Access Token Permissions
If using fine-grained tokens, ensure these repository permissions are granted:
- **Contents**: Read and write
- **Metadata**: Read
- **Pull requests**: Read and write
- **Issues**: Read and write
- **Actions**: Read and write
- **Security events**: Read and write

## Setting Up Your GitHub Token

### Step 1: Create a Personal Access Token
1. Go to GitHub Settings > Developer settings > Personal access tokens
2. Choose either "Tokens (classic)" or "Fine-grained tokens" 
3. Click "Generate new token"
4. Set appropriate expiration date
5. Select the required scopes listed above

### Step 2: Configure Token for ABACUS
Set the token as an environment variable:
```bash
export GITHUB_TOKEN=your_token_here
```

Or add it to your shell profile:
```bash
echo 'export GITHUB_TOKEN=your_token_here' >> ~/.bashrc
source ~/.bashrc
```

### Step 3: Test Token Permissions
Verify your token has correct permissions:
```bash
# Test repository access
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user/repos

# Test specific repository access
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/repos/GBOGEB/ABACUS
```

## Troubleshooting Common Issues

### "Resource not accessible by personal access token"
- **Cause**: Token missing `repo` scope permissions
- **Solution**: Regenerate token with full `repo` scope

### "Bad credentials"  
- **Cause**: Invalid or expired token
- **Solution**: Generate new token and update environment variable

### "Not Found" errors
- **Cause**: Token lacks access to private repositories
- **Solution**: Ensure `repo` scope includes private repository access

### Organization repositories
- **Additional requirement**: Organization may require token approval
- **Solution**: Contact organization admin to approve your token

## Security Best Practices

1. **Use minimal required permissions**: Only grant necessary scopes
2. **Set token expiration**: Use shortest reasonable expiration time
3. **Store securely**: Never commit tokens to code repositories
4. **Regular rotation**: Rotate tokens periodically
5. **Monitor usage**: Review token usage in GitHub settings

## Environment Variable Configuration

For persistent configuration, add to your environment:

```bash
# ~/.bashrc or ~/.zshrc
export GITHUB_TOKEN="ghp_your_token_here"
export GITHUB_USER="your_username"
export GITHUB_REPO="GBOGEB/ABACUS"
```

## Testing Repository Access

Use this script to verify full repository access:

```bash
#!/bin/bash
# Test GitHub token permissions
echo "Testing GitHub token permissions..."

# Test basic authentication
echo "1. Testing authentication..."
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user | jq -r '.login // "Authentication failed"'

# Test repository access
echo "2. Testing repository access..."
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/GBOGEB/ABACUS | jq -r '.full_name // "Repository access failed"'

# Test push permissions (check if token can create issues)
echo "3. Testing write permissions..."
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  -X GET https://api.github.com/repos/GBOGEB/ABACUS/collaborators | \
  jq -r 'if type == "array" then "Write access confirmed" else "Limited access" end'

echo "Permission test complete."
```

Save as `test_permissions.sh` and run with: `chmod +x test_permissions.sh && ./test_permissions.sh`