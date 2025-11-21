# DOW + Recursive DMAIC - CI/CD Workflows

## 📋 Overview

This directory contains the unified CI/CD workflows that integrate the DOW (DMAIC + ABACUS) pipeline with Recursive DMAIC v0.4.0 features.

## 🔄 Workflow Structure

### Production Workflows

#### 1. **cd-unified.yml** - Unified CD Pipeline
**Purpose**: Main continuous deployment pipeline with multi-platform validation

**Triggers**:
- Push to `main` or `develop` branches
- Pull requests to `main`
- Tags matching `v*.*.*`
- Daily schedule at 2 AM UTC
- Manual dispatch

**Jobs**:
1. **lint-and-validate** - Code quality checks
2. **ci-ubuntu** - Ubuntu CI validation
3. **ci-rhel-8** - RHEL 8 validation (self-hosted)
4. **ci-rhel-9** - RHEL 9 validation (self-hosted)
5. **dmaic-full-cycle** - Complete DMAIC execution (Phases 0-6)
6. **build-artifacts** - Generate release artifacts
7. **release** - Create GitHub Release (tags only)

**Features**:
- ✅ Multi-platform validation (Ubuntu + RHEL 8 + RHEL 9)
- ✅ DMAIC full cycle execution
- ✅ Knowledge package initialization
- ✅ PDF handover book generation
- ✅ GLOOB bundle creation
- ✅ Universal archives (.zip, .tar.gz)
- ✅ Automated GitHub Release
- ✅ FIPS compliance checks
- ✅ Private PyPI support

#### 2. **ci-enhanced.yml** - Enhanced CI Pipeline
**Purpose**: Comprehensive continuous integration for all branches

**Triggers**:
- Push to any branch
- Pull requests to `main` or `develop`
- Manual dispatch

**Jobs**:
1. **lint** - Code quality (ruff, black, pylint, mypy, pre-commit)
2. **test-ubuntu** - Ubuntu tests (Python 3.11, 3.12)
3. **test-rhel-8** - RHEL 8 tests (self-hosted)
4. **test-rhel-9** - RHEL 9 tests (self-hosted)
5. **smoke-tests** - Quick validation tests
6. **integration-tests** - DOW integration tests
7. **summary** - CI results summary

**Features**:
- ✅ Comprehensive linting
- ✅ Multi-platform testing
- ✅ Code coverage reporting
- ✅ FIPS mode validation
- ✅ Parallel test execution
- ✅ Artifact collection

#### 3. **ci-abacus.yml** - ABACUS-Specific CI
**Purpose**: ABACUS project-specific testing

**Triggers**:
- Push/PR to main/develop/feature branches
- Manual dispatch

**Conditions**:
- Only runs if `github.repository == 'GBOGEB/ABACUS'`

**Matrix**:
- OS: Ubuntu
- Python: 3.10, 3.11, 3.12

#### 4. **ci-codex.yml** - CODEX-Specific CI
**Purpose**: CODEX project-specific testing

**Triggers**:
- Push/PR to main/develop/feature branches
- Manual dispatch

**Conditions**:
- Only runs if `github.repository == 'GBOBEB/CODEX'`

**Matrix**:
- OS: Ubuntu, Windows
- Python: 3.11, 3.12

#### 5. **dow-scheduled.yml** - Scheduled Execution
**Purpose**: Periodic DOW pipeline execution

**Triggers**:
- Schedule: Every 6 hours
- Manual dispatch

**Features**:
- ✅ Automated pipeline execution
- ✅ Test execution
- ✅ Log collection
- ✅ Failure notifications

### Legacy Workflows (Archived)

The following workflows have been archived to `legacy/`:
- `cd.yml.old` - Original DMAIC V3.3 CD
- `dow-integration-ci-cd.yml.old` - Original DOW integration CI/CD
- `dow-main-cicd.yml.old` - Original DOW main CI/CD

## 🚀 Usage

### Running CI on Feature Branches

```bash
git checkout -b feature/my-feature
git push origin feature/my-feature
```

This triggers:
- `ci-enhanced.yml` (lint + Ubuntu tests)
- `ci-abacus.yml` (if ABACUS repo)
- `ci-codex.yml` (if CODEX repo)

### Creating a Release

```bash
git tag v1.0.0
git push origin v1.0.0
```

This triggers:
- `cd-unified.yml` with full validation and release creation

### Manual Workflow Dispatch

Go to Actions → Select workflow → Run workflow

## 🔧 Configuration

### Required Secrets

**Optional (for private PyPI)**:
- `PIP_INDEX_URL` - Private PyPI mirror URL
- `PIP_EXTRA_INDEX_URL` - Additional PyPI sources
- `PIP_TRUSTED_HOST` - Trusted hosts for PyPI
- `PIP_CERT` - CA certificate path

**Optional (for FIPS)**:
- `REQUIRE_FIPS` - Set to enable FIPS compliance checks

### Self-Hosted Runners

**RHEL 8 Runner**:
- Labels: `[self-hosted, linux, x64, rhel-8]`
- Python: 3.11+
- Packages: `python3-devel`, `gcc`, `git`

**RHEL 9 Runner**:
- Labels: `[self-hosted, linux, x64, rhel-9]`
- Python: 3.11+
- Packages: `python3-devel`, `gcc`, `git`

## 📊 Workflow Dependencies

```
cd-unified.yml:
  lint-and-validate
    ↓
  ci-ubuntu + ci-rhel-8 + ci-rhel-9
    ↓
  dmaic-full-cycle
    ↓
  build-artifacts
    ↓
  release (tags only)

ci-enhanced.yml:
  lint
    ↓
  test-ubuntu + test-rhel-8 + test-rhel-9
    ↓
  smoke-tests + integration-tests
    ↓
  summary
```

## 🎯 Success Criteria

### CI Pipeline
- ✅ All linting checks pass
- ✅ Tests pass on Ubuntu (Python 3.11, 3.12)
- ✅ Tests pass on RHEL 8 (if available)
- ✅ Tests pass on RHEL 9 (if available)
- ✅ Smoke tests pass
- ✅ Integration tests pass

### CD Pipeline
- ✅ All CI checks pass
- ✅ DMAIC full cycle completes
- ✅ All artifacts generated
- ✅ Release created (for tags)

## 📈 Monitoring

### GitHub Actions UI
- View workflow runs: Actions tab
- Check job status: Click on workflow run
- Download artifacts: Artifacts section in workflow run

### Workflow Badges

Add to README.md:

```markdown
![CI](https://github.com/GBOGEB/ABACUS/workflows/DOW%20+%20Recursive%20DMAIC%20-%20Enhanced%20CI/badge.svg)
![CD](https://github.com/GBOGEB/ABACUS/workflows/DOW%20+%20Recursive%20DMAIC%20-%20Unified%20CD%20Pipeline/badge.svg)
```

## 🐛 Troubleshooting

### RHEL Runners Not Available
If RHEL runners are not configured, the workflows will skip RHEL-specific jobs. Ubuntu jobs will still run.

### FIPS Mode Issues
If FIPS mode is required but not enabled:
1. Check `/proc/sys/crypto/fips_enabled`
2. Enable FIPS on the runner
3. Restart the runner service

### Private PyPI Issues
If private PyPI is not accessible:
1. Verify secrets are configured
2. Check network connectivity
3. Verify CA certificate if using HTTPS

### Artifact Upload Failures
If artifacts fail to upload:
1. Check file paths exist
2. Verify artifact size limits
3. Check workflow permissions

## 📚 Additional Documentation

- [Integration Plan](../../DOW_CICD_INTEGRATION_PLAN.md)
- [Implementation Status](../../DOW_CICD_IMPLEMENTATION_STATUS.md)
- [CICD Setup Guide](../../CICD_SETUP_GUIDE.md)
- [Quick Reference](../../CICD_QUICK_REFERENCE.md)

## 🔄 Migration from Legacy Workflows

### What Changed

1. **cd.yml** → **cd-unified.yml**
   - Added multi-platform validation
   - Added gated deployment
   - Enhanced artifact generation

2. **dow-integration-ci-cd.yml** → **ci-enhanced.yml**
   - Added comprehensive linting
   - Added multi-platform testing
   - Added coverage reporting

3. **dow-main-cicd.yml** → **dow-scheduled.yml**
   - Focused on scheduled execution
   - Simplified job structure

### Backward Compatibility

All existing features are preserved:
- ✅ DMAIC full cycle execution
- ✅ Knowledge package initialization
- ✅ PDF generation
- ✅ GLOOB bundles
- ✅ Scheduled execution

## 📞 Support

For issues or questions:
1. Check workflow logs in GitHub Actions
2. Review troubleshooting section above
3. Consult integration documentation
4. Contact CI/CD team

---

**Version**: 1.0.0  
**Last Updated**: 2025-01-19  
**Status**: Active
