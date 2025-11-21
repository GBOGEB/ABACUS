# GitHub Bulk Issue/PR Resolution Guide
# ======================================

## Quick Start

### 1. Install Dependencies
```bash
pip install PyGithub
```

### 2. Set GitHub Token
```bash
# Windows PowerShell
$env:GITHUB_TOKEN="your_github_token_here"

# Windows CMD
set GITHUB_TOKEN=your_github_token_here

# Linux/Mac
export GITHUB_TOKEN=your_github_token_here
```

### 3. Check for Duplicates (Safe - No Changes)
```bash
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action check
```

### 4. Close Duplicates (Dry Run First)
```bash
# Dry run (shows what would be closed)
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action close --dry-run

# Actual execution (requires confirmation)
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action close
```

### 5. Export Report
```bash
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action export --output duplicate_report.json
```

## Features

### Duplicate Detection
- ✅ Detects duplicate issues based on test name patterns
- ✅ Detects duplicate PRs based on title patterns
- ✅ Groups duplicates by test name
- ✅ Identifies oldest issue/PR to keep

### Resolution Strategy
- **Keep**: Oldest issue/PR (first created)
- **Close**: All newer duplicates
- **Comment**: Adds explanation and reference to kept issue/PR

### Safety Features
- ✅ Dry run mode (--dry-run)
- ✅ Confirmation prompt before closing
- ✅ Detailed reporting before action
- ✅ Export to JSON for review

## Usage Examples

### Example 1: Check Only
```bash
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action check
```

**Output:**
```
✅ Connected to repository: GBOGEB/ABACUS

🔍 Scanning for duplicate issues...
✅ Found 5 groups with duplicate issues
   Total duplicate issues: 12

🔍 Scanning for duplicate pull requests...
✅ Found 3 groups with duplicate PRs
   Total duplicate PRs: 8

======================================================================
DUPLICATE DETECTION REPORT
======================================================================

📋 DUPLICATE ISSUES:
----------------------------------------------------------------------

🔴 Test: test_dmaic_phase_1
   Duplicates: 3 issues
   [KEEP (oldest)] #123: CI Failure: test_dmaic_phase_1
      Created: 2025-11-17 08:00:00
      URL: https://github.com/GBOGEB/ABACUS/issues/123
   [CLOSE (duplicate)] #145: CI Failure: test_dmaic_phase_1
      Created: 2025-11-17 09:00:00
      URL: https://github.com/GBOGEB/ABACUS/issues/145
   [CLOSE (duplicate)] #167: CI Failure: test_dmaic_phase_1
      Created: 2025-11-17 10:00:00
      URL: https://github.com/GBOGEB/ABACUS/issues/167

======================================================================
SUMMARY:
  Issues to close: 12
  PRs to close: 8
  Total to close: 20
======================================================================
```

### Example 2: Close Duplicates (Dry Run)
```bash
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action close --dry-run
```

**Output:**
```
⚠️  DRY RUN MODE - No changes will be made

[Shows same report as check, but indicates what would be closed]
```

### Example 3: Close Duplicates (Actual)
```bash
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action close
```

**Output:**
```
⚠️  Are you sure you want to close these duplicates? (yes/no): yes

🔧 Closing duplicate issues and PRs...
✅ Closed issue #145: CI Failure: test_dmaic_phase_1
✅ Closed issue #167: CI Failure: test_dmaic_phase_1
✅ Closed PR #156: [WIP] Fix CI failure for test_dmaic_phase_1
...

✅ Successfully closed 20 duplicates
```

### Example 4: Add Comment to All
```bash
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action comment --message "Investigating root cause. Will update soon."
```

### Example 5: Export Report
```bash
python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action export --output my_report.json
```

## How It Works

### Duplicate Detection Logic

1. **Issue Grouping**:
   - Extracts test name from issue title
   - Groups issues with same test name
   - Identifies groups with 2+ issues

2. **PR Grouping**:
   - Extracts test name from PR title
   - Groups PRs with same test name
   - Identifies groups with 2+ PRs

3. **Resolution Strategy**:
   - Sort by creation date (oldest first)
   - Keep oldest issue/PR
   - Close all newer duplicates
   - Add comment with reference to kept item

### Title Patterns Detected

**Issues:**
- `CI Failure: test_name`
- `CI/CD test failure for test_name`
- `CI/CD test failure in test_name`

**PRs:**
- `[WIP] Fix CI failure for test_name`
- `[WIP] Fix CI test_name`

## Troubleshooting

### Error: GitHub token not found
```bash
# Set token environment variable
export GITHUB_TOKEN=your_token_here
```

### Error: PyGithub not installed
```bash
pip install PyGithub
```

### Error: Failed to connect to repository
- Check repository name format: `OWNER/REPO`
- Verify token has correct permissions
- Ensure repository exists and is accessible

## Best Practices

1. **Always run check first**:
   ```bash
   python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action check
   ```

2. **Use dry-run before closing**:
   ```bash
   python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action close --dry-run
   ```

3. **Export report for review**:
   ```bash
   python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action export
   ```

4. **Review exported JSON before closing**:
   ```bash
   cat duplicate_report.json
   ```

## Preventing Future Duplicates

### Update CI/CD Workflow

Add duplicate check before creating issues:

```yaml
- name: Check for existing issue
  id: check_issue
  run: |
    EXISTING=$(gh issue list --label "ci-failure" --search "test_${{ matrix.test }}" --json number --jq '.[0].number')
    if [ -n "$EXISTING" ]; then
      echo "exists=true" >> $GITHUB_OUTPUT
      echo "issue_number=$EXISTING" >> $GITHUB_OUTPUT
    else
      echo "exists=false" >> $GITHUB_OUTPUT
    fi

- name: Create or update issue
  if: steps.check_issue.outputs.exists == 'false'
  run: |
    gh issue create --title "CI Failure: test_${{ matrix.test }}" --body "..."

- name: Comment on existing issue
  if: steps.check_issue.outputs.exists == 'true'
  run: |
    gh issue comment ${{ steps.check_issue.outputs.issue_number }} --body "Test still failing..."
```

## Support

For issues or questions:
1. Check the script output for error messages
2. Verify GitHub token permissions
3. Review the exported JSON report
4. Check GitHub API rate limits

## License

Part of ABACUS v033.1 - CANONICAL ALIGNED
