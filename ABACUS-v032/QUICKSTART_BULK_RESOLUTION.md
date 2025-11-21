# Quick Start: Resolve Duplicate GitHub Issues/PRs
# ==================================================

## Step 1: Get Your GitHub Token

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name: "ABACUS Bulk Resolution"
4. Select scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `public_repo` (Access public repositories)
5. Click "Generate token"
6. **COPY THE TOKEN** (you won't see it again!)

## Step 2: Set the Token (Choose One Method)

### Method A: Environment Variable (Recommended)
```powershell
# PowerShell
$env:GITHUB_TOKEN="ghp_your_token_here"

# Then run the script
cd ABACUS-v032
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action check
```

### Method B: Pass Token Directly
```powershell
cd ABACUS-v032
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action check --token ghp_your_token_here
```

### Method C: Create .env File
```powershell
# Create .env file in ABACUS-v032 directory
echo "GITHUB_TOKEN=ghp_your_token_here" > .env
```

## Step 3: Check for Duplicates (Safe - No Changes)

```powershell
cd ABACUS-v032
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action check
```

**Expected Output:**
```
✅ Connected to repository: GBOGEB/ABACUS

🔍 Scanning for duplicate issues...
✅ Found X groups with duplicate issues
   Total duplicate issues: Y

🔍 Scanning for duplicate pull requests...
✅ Found X groups with duplicate PRs
   Total duplicate PRs: Y

======================================================================
DUPLICATE DETECTION REPORT
======================================================================
[Detailed list of duplicates]
```

## Step 4: Export Report (Optional)

```powershell
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action export --output duplicates.json
```

## Step 5: Close Duplicates (Dry Run First!)

```powershell
# Dry run (shows what would be closed, but doesn't actually close)
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action close --dry-run

# If everything looks good, run for real
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action close
```

**You will be asked to confirm:**
```
⚠️  Are you sure you want to close these duplicates? (yes/no): yes
```

## What the Script Does

### Detection Logic
1. **Finds duplicate issues** with same test name
2. **Finds duplicate PRs** with same test name
3. **Groups them** by test name
4. **Identifies oldest** issue/PR to keep

### Resolution Strategy
- **KEEPS**: Oldest issue/PR (first created)
- **CLOSES**: All newer duplicates
- **ADDS COMMENT**: Explains closure and references kept issue/PR

### Example Comment Added
```
This issue is a duplicate of #123 and is being automatically closed.

**Reason**: Multiple issues were created for the same test failure.
**Action**: Keeping the oldest issue (#123) and closing duplicates.

If this test failure is still occurring, please comment on #123.
```

## Troubleshooting

### Error: "GitHub token not found"
```powershell
# Set the token
$env:GITHUB_TOKEN="ghp_your_token_here"
```

### Error: "Failed to connect to repository"
- Check repository name: `GBOGEB/ABACUS` (case-sensitive)
- Verify token has correct permissions
- Ensure repository exists and is accessible

### Error: "PyGithub not installed"
```powershell
pip install PyGithub
```

## Safety Features

✅ **Dry Run Mode**: Test before making changes
✅ **Confirmation Prompt**: Asks before closing anything
✅ **Detailed Report**: Shows exactly what will be closed
✅ **Export to JSON**: Review duplicates offline
✅ **Keeps Oldest**: Preserves original issue/PR
✅ **Adds Comments**: Explains why items were closed

## Complete Example Session

```powershell
# 1. Set token
$env:GITHUB_TOKEN="ghp_your_token_here"

# 2. Check for duplicates
cd ABACUS-v032
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action check

# 3. Export report for review
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action export

# 4. Review the report
cat duplicate_report.json

# 5. Dry run to see what would be closed
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action close --dry-run

# 6. If everything looks good, close for real
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action close
```

## Preventing Future Duplicates

Add this to your CI/CD workflow to check for existing issues before creating new ones:

```yaml
- name: Check for existing issue
  id: check_issue
  run: |
    EXISTING=$(gh issue list --label "ci-failure" --search "in:title ${{ matrix.test }}" --json number --jq '.[0].number')
    if [ -n "$EXISTING" ]; then
      echo "Issue #$EXISTING already exists for this test"
      echo "exists=true" >> $GITHUB_OUTPUT
      echo "issue_number=$EXISTING" >> $GITHUB_OUTPUT
    else
      echo "exists=false" >> $GITHUB_OUTPUT
    fi

- name: Create new issue
  if: steps.check_issue.outputs.exists == 'false'
  run: |
    gh issue create --title "CI Failure: ${{ matrix.test }}" --body "..."

- name: Comment on existing issue
  if: steps.check_issue.outputs.exists == 'true'
  run: |
    gh issue comment ${{ steps.check_issue.outputs.issue_number }} --body "Test still failing in run ${{ github.run_number }}"
```

## Need Help?

Run the script with `--help`:
```powershell
python bulk_resolve_github_issues.py --help
```

---

**Part of ABACUS v033.1 - CANONICAL ALIGNED**
