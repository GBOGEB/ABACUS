# DOW Pipeline + Recursive DMAIC v0.4.0 Integration Plan

## 🎯 Integration Goal

Integrate the Recursive DMAIC v0.4.0 CI/CD workflows into the existing DOW (DMAIC + ABACUS) pipeline while maintaining backward compatibility and enhancing the deployment process.

## 📊 Current State Analysis

### Existing DOW Workflows

1. **cd.yml** - DMAIC V3.3 CD Pipeline
   - Triggers: push to main/develop, PR to main, daily schedule, manual
   - Python: 3.12
   - Features: Knowledge packages, PDF export, DMAIC phases

2. **dow-integration-ci-cd.yml** - ABACUS DOW Integration
   - Triggers: push/PR to main/develop/feature branches
   - Python: 3.11
   - Features: Linting (ruff, black, pylint), DOW phase testing

3. **dow-main-cicd.yml** - DOW Main CI/CD
   - Triggers: push/PR to main/develop/feat, scheduled every 6 hours
   - Python: 3.11
   - Features: Tests, DMAIC pipeline execution

### Recursive DMAIC v0.4.0 Workflows

1. **cd.yml** - Gated CD with Ubuntu + RHEL
   - Triggers: tags (v*.*.*)
   - Features: Multi-platform validation, release automation

2. **ci-workspace.yml** - Ubuntu CI
   - Python: 3.11
   - Features: Pre-commit, pytest, Phase0 smoke tests

3. **ci-rhel.yml** - RHEL 8/9 CI
   - Self-hosted runners
   - Features: FIPS compliance, private PyPI support

4. **ci-abacus.yml** - ABACUS-specific CI
5. **ci-codex.yml** - Codex-specific CI

## 🔄 Integration Strategy

### Phase 1: Merge and Enhance Existing Workflows

#### 1.1 Unified CD Workflow
**File**: `.github/workflows/cd-unified.yml`

Merge:
- Existing `cd.yml` (DMAIC V3.3)
- New `cd.yml` (Recursive DMAIC v0.4.0)

Features:
- Tag-based releases (v*.*.*)
- Multi-platform validation (Ubuntu + RHEL)
- DMAIC phase execution
- Knowledge package initialization
- PDF export capabilities
- Gated deployment

#### 1.2 Enhanced CI Workflow
**File**: `.github/workflows/ci-enhanced.yml`

Merge:
- `dow-integration-ci-cd.yml`
- `ci-workspace.yml`
- `ci-rhel.yml`

Features:
- Linting (ruff, black, pylint, mypy)
- Multi-platform testing (Ubuntu, RHEL 8, RHEL 9)
- Pre-commit hooks
- Pytest execution
- Phase0 smoke tests
- FIPS compliance checks
- Private PyPI support

#### 1.3 Specialized Workflows
Keep separate:
- `ci-abacus.yml` - ABACUS-specific testing
- `ci-codex.yml` - Codex-specific testing
- `dow-main-cicd.yml` - Scheduled pipeline execution

### Phase 2: Directory Structure Integration

```
.github/workflows/
├── cd-unified.yml              # Main CD pipeline (merged)
├── ci-enhanced.yml             # Main CI pipeline (merged)
├── ci-abacus.yml               # ABACUS-specific CI
├── ci-codex.yml                # Codex-specific CI
├── dow-scheduled.yml           # Scheduled DOW execution (renamed from dow-main-cicd.yml)
└── [legacy/]                   # Archive old workflows
    ├── cd.yml.old
    ├── dow-integration-ci-cd.yml.old
    └── dow-main-cicd.yml.old
```

### Phase 3: Configuration Files

#### 3.1 Merge Requirements
- Combine `requirements.txt` from both sources
- Ensure Python 3.11+ compatibility
- Add FIPS-compliant packages if needed

#### 3.2 Pre-commit Configuration
- Integrate `.pre-commit-config.yaml` from v0.4.0
- Add hooks for:
  - ruff
  - black
  - pylint
  - mypy
  - trailing whitespace
  - end-of-file fixer

#### 3.3 Project Configuration
- Merge `pyproject.toml` settings
- Ensure compatibility with both DMAIC and ABACUS

### Phase 4: Runner Configuration

#### 4.1 GitHub-Hosted Runners
- Ubuntu-latest for standard CI/CD
- Python 3.11 as baseline

#### 4.2 Self-Hosted Runners (Required)
- RHEL 8: `[self-hosted, linux, x64, rhel-8]`
- RHEL 9: `[self-hosted, linux, x64, rhel-9]`

#### 4.3 Runner Requirements
- Python 3.11+
- System packages: `python3-devel`, `gcc`, `git`
- Optional: FIPS mode enabled
- Optional: Private PyPI access

### Phase 5: Secret Management

#### 5.1 Required Secrets
- `GITHUB_TOKEN` (automatic)

#### 5.2 Optional Secrets
- `PIP_INDEX_URL` - Private PyPI mirror
- `PIP_EXTRA_INDEX_URL` - Additional PyPI sources
- `PIP_TRUSTED_HOST` - Trusted hosts for PyPI
- `PIP_CERT` - CA certificate for HTTPS
- `REQUIRE_FIPS` - FIPS compliance flag

## 📋 Implementation Checklist

### ✅ Phase 1: Preparation (CURRENT)
- [x] Analyze existing DOW workflows
- [x] Analyze Recursive DMAIC v0.4.0 workflows
- [x] Create integration plan
- [ ] Create backup of existing workflows
- [ ] Create integration branch

### ⏳ Phase 2: Workflow Integration
- [ ] Create `cd-unified.yml`
- [ ] Create `ci-enhanced.yml`
- [ ] Update `ci-abacus.yml` if needed
- [ ] Update `ci-codex.yml` if needed
- [ ] Rename `dow-main-cicd.yml` to `dow-scheduled.yml`
- [ ] Archive old workflows

### ⏳ Phase 3: Configuration Integration
- [ ] Merge `requirements.txt`
- [ ] Integrate `.pre-commit-config.yaml`
- [ ] Merge `pyproject.toml`
- [ ] Update `README.md` with CI/CD documentation

### ⏳ Phase 4: Testing
- [ ] Test unified CD workflow locally
- [ ] Test enhanced CI workflow locally
- [ ] Verify ABACUS-specific workflows
- [ ] Verify Codex-specific workflows
- [ ] Test scheduled workflow

### ⏳ Phase 5: Deployment
- [ ] Commit changes to integration branch
- [ ] Push to remote
- [ ] Create pull request
- [ ] Monitor CI/CD execution
- [ ] Address any failures
- [ ] Request code review
- [ ] Merge to main

### ⏳ Phase 6: Validation
- [ ] Create test release tag
- [ ] Verify CD workflow execution
- [ ] Verify artifact generation
- [ ] Verify GitHub Release creation
- [ ] Test RHEL runners
- [ ] Validate FIPS compliance (if applicable)

### ⏳ Phase 7: Documentation
- [ ] Update main README
- [ ] Create CI/CD documentation
- [ ] Document runner setup
- [ ] Document secret configuration
- [ ] Create troubleshooting guide

## 🔧 Technical Details

### Workflow Triggers

#### CD Unified
```yaml
on:
  push:
    tags: ["v*.*.*"]
  workflow_dispatch:
```

#### CI Enhanced
```yaml
on:
  push:
    branches: [main, develop, feature/*, feat/*]
  pull_request:
    branches: [main, develop]
  workflow_dispatch:
```

#### DOW Scheduled
```yaml
on:
  schedule:
    - cron: "0 */6 * * *"  # Every 6 hours
  workflow_dispatch:
```

### Python Version Strategy
- **Baseline**: Python 3.11 (compatible with both systems)
- **DMAIC V3.3**: Can upgrade from 3.12 to 3.11 (backward compatible)
- **Recursive DMAIC**: Already uses 3.11

### Job Dependencies
```
CI Enhanced:
  lint → test-ubuntu → test-rhel-8 → test-rhel-9 → smoke-tests

CD Unified:
  ci-ubuntu-mini → ci-rhel-mini → release
```

## 🚀 Rollout Plan

### Week 1: Integration Development
- Days 1-2: Create unified workflows
- Days 3-4: Test locally and in feature branch
- Day 5: Create PR and initial CI testing

### Week 2: Testing & Refinement
- Days 1-3: Address CI failures
- Days 4-5: Code review and refinements

### Week 3: Deployment
- Day 1: Merge to main
- Days 2-3: Monitor production CI/CD
- Days 4-5: Create first release with new CD

### Week 4: Documentation & Training
- Days 1-2: Complete documentation
- Days 3-4: Team training
- Day 5: Retrospective and improvements

## 📊 Success Metrics

### CI/CD Performance
- CI execution time: < 15 minutes
- CD execution time: < 20 minutes
- Success rate: > 95%

### Quality Metrics
- Code coverage: > 80%
- Linting pass rate: 100%
- Pre-commit hook compliance: 100%

### Deployment Metrics
- Release frequency: Weekly
- Deployment success rate: > 98%
- Rollback rate: < 2%

## 🐛 Risk Mitigation

### Risk 1: Workflow Conflicts
**Mitigation**: Archive old workflows, test thoroughly before merge

### Risk 2: Runner Availability
**Mitigation**: Ensure RHEL runners are configured and online before deployment

### Risk 3: Breaking Changes
**Mitigation**: Maintain backward compatibility, use feature flags

### Risk 4: Secret Management
**Mitigation**: Document all required secrets, use GitHub Environments

## 📞 Support & Contacts

### CI/CD Administrator
- **Name**: [To be assigned]
- **Contact**: [To be provided]

### RHEL Runner Admin
- **Name**: [To be assigned]
- **Contact**: [To be provided]

### Security/FIPS Contact
- **Name**: [To be assigned]
- **Contact**: [To be provided]

---

**Plan Version**: 1.0  
**Created**: 2025-01-19  
**Status**: In Progress - Phase 1  
**Next Review**: After Phase 2 completion
