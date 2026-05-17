# Branch Protection Recommendations

## Overview

This document recommends branch protection rules for the `main` branch of GBOGEB/ABACUS to ensure code quality and prevent accidental changes.

## Recommended Rules for `main` Branch

### 1. Require Pull Request Reviews Before Merging

| Setting | Recommended Value |
|---------|-------------------|
| Required approving reviews | 1 |
| Dismiss stale PR reviews | ✅ Enabled |
| Require review from code owners | Optional (enable if CODEOWNERS file is added) |

**Why**: Ensures at least one person reviews all changes before they reach `main`. Particularly important for the DMAIC engine (`DMAIC_V3/`) and integration bridges (`staging/`).

### 2. Require Status Checks to Pass

| Check | Source |
|-------|--------|
| Python syntax validation | `ci.yml` workflow |
| HTML validation | `validate_docs.yml` workflow |
| Dashboard health | `dashboard-health.yml` workflow |

**Why**: Prevents broken code from being merged. The CI/CD workflows in `docs/workflows/` can be installed to `.github/workflows/` to provide these checks.

### 3. Require Branches to Be Up to Date

| Setting | Recommended Value |
|---------|-------------------|
| Require branches to be up to date before merging | ✅ Enabled |

**Why**: Ensures PRs are tested against the latest `main` branch, preventing integration conflicts.

### 4. Include Administrators

| Setting | Recommended Value |
|---------|-------------------|
| Include administrators | ✅ Enabled |

**Why**: Even repository admins should follow the same review process to maintain consistency.

### 5. Additional Recommendations

| Setting | Recommended Value | Reason |
|---------|-------------------|--------|
| Restrict push access | Enabled | Only allow merges through PRs |
| Allow force pushes | ❌ Disabled | Prevent history rewriting on `main` |
| Allow deletions | ❌ Disabled | Prevent accidental branch deletion |
| Require signed commits | Optional | Adds verification layer |
| Require linear history | Optional | Cleaner git history |

## How to Enable

1. Go to **Settings** → **Branches** → **Branch protection rules**
2. Click **Add rule**
3. Branch name pattern: `main`
4. Configure the settings above
5. Click **Create** / **Save changes**

Direct link: https://github.com/GBOGEB/ABACUS/settings/branches

## Priority

- **Phase 1** (Now): Enable PR review requirement + status checks
- **Phase 2** (After CI/CD installed): Add workflow status checks
- **Phase 3** (When team grows): Add CODEOWNERS and signed commits
