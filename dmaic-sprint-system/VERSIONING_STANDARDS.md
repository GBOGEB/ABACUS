
# DMAIC VERSIONING STANDARDS

**Document Version:** 1.0  
**Last Updated:** November 14, 2025  
**Applies To:** All DMAIC project code, documentation, and data

---

## 📋 PURPOSE

This document defines version control practices and standards for the DMAIC project to ensure:
- Consistent version numbering across all artifacts
- Clear tracking of changes and iterations
- Easy rollback and recovery capabilities
- Proper handoff between development phases
- Comprehensive change history

---

## 🔢 SEMANTIC VERSIONING

### Version Format: MAJOR.MINOR.PATCH

Following [Semantic Versioning 2.0.0](https://semver.org/) principles:

```
MAJOR.MINOR.PATCH

MAJOR: Incompatible API/format changes
MINOR: Backward-compatible functionality additions
PATCH: Backward-compatible bug fixes
```

### Examples

**Code Versions:**
- `1.0.0` → Initial release (Sprint 3 completion)
- `1.1.0` → Sprint 5 data format fixes (backward compatible)
- `1.2.0` → Enhanced metrics addition (backward compatible)
- `2.0.0` → Breaking changes to phase output format (incompatible)

**Documentation Versions:**
- `1.0` → Finalized documentation (Sprint reports)
- `1.0-current` → Living documentation (tracking docs, updated regularly)

---

## 📦 VERSION CONTROL STRUCTURE

### Git Repository Structure

```
main (production-ready releases)
├── feature/sprint-6-testing (active development)
├── feature/sprint-6-metrics (active development)
├── feature/ci-cd-integration (planned)
├── hotfix/critical-bug-fix (as needed)
└── release/v1.3.0 (release preparation)
```

### Branch Naming Convention

| Branch Type | Format | Example | Purpose |
|-------------|--------|---------|---------|
| **Main** | `main` | `main` | Production releases |
| **Feature** | `feature/<sprint>-<name>` | `feature/sprint-6-testing` | Sprint development |
| **Hotfix** | `hotfix/<issue-id>-<desc>` | `hotfix/001-phase2-crash` | Critical fixes |
| **Release** | `release/v<version>` | `release/v1.3.0` | Release preparation |
| **Experiment** | `experiment/<name>` | `experiment/ml-integration` | Experimental features |

---

## 🏷️ TAGGING STRATEGY

### Sprint Completion Tags

Create annotated tags at sprint completion:

```bash
git tag -a v1.1.0-sprint5 -m "Sprint 5 completion: Data format fixes"
git tag -a v1.2.0-sprint6 -m "Sprint 6 completion: Iteration 3 & testing"
```

### Iteration Tags

Tag each DMAIC iteration execution:

```bash
git tag -a iteration-1 -m "Iteration 1: Baseline execution"
git tag -a iteration-2 -m "Iteration 2: Pre-Sprint 5 fixes"
git tag -a iteration-3 -m "Iteration 3: Post-Sprint 5 fixes validation"
```

### Release Tags

Major releases:

```bash
git tag -a v1.0.0 -m "Release 1.0: Initial DMAIC system"
git tag -a v2.0.0 -m "Release 2.0: Enhanced metrics & CI/CD"
```

---

## 📝 COMMIT MESSAGE STANDARDS

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Commit Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(phase2): Add file_metrics output` |
| `fix` | Bug fix | `fix(handoff): Correct Phase 2→3 file path` |
| `docs` | Documentation only | `docs(sprint5): Add completion report` |
| `refactor` | Code refactoring | `refactor(runner): Remove manual workarounds` |
| `test` | Adding/updating tests | `test(phase2): Add metrics collection tests` |
| `chore` | Maintenance tasks | `chore: Update dependencies` |
| `perf` | Performance improvement | `perf(phase1): Optimize file scanning` |
| `style` | Code style changes | `style: Format code with black` |

### Commit Message Examples

**Good:**
```
feat(phase2): Add file_metrics dictionary conversion

- Convert measurements array to file_metrics dict
- Save to dual locations for backward compatibility
- Enables Phase 3 to receive correct data format

Fixes: Sprint 5 critical finding
Related: DMAIC_SPRINT_5_CRITICAL_FINDINGS.md
```

**Bad:**
```
fixed stuff
```

---

## 🔖 FILE VERSIONING

### Code Files

#### Version Comment Header

```python
"""
Phase 2: Measure - Baseline Metrics Collection

Version: 1.1.0
Last Modified: 2025-11-13 17:39:00
Sprint: Sprint 5
Changes:
  - Added file_metrics dictionary conversion
  - Dual output locations for backward compatibility

Author: DMAIC Sprint System
"""
```

### Documentation Files

#### Version Footer

```markdown
---

**Document Version:** 1.0  
**Last Updated:** November 14, 2025  
**Sprint:** Sprint 6  
**Status:** Active  
**Changes:**
- Initial version
- Comprehensive workspace snapshot
```

### Data Files

#### Metadata in JSON

```json
{
  "version": "1.0.0",
  "iteration": 3,
  "phase": "MEASURE",
  "timestamp": "2025-11-14T10:30:00Z",
  "code_version": "1.2.0",
  "format_version": "2.0"
}
```

---

## 📊 VERSION TRACKING

### Current Versions Registry

| Component | Version | Date | Sprint | Status |
|-----------|---------|------|--------|--------|
| **DMAIC Core** | 1.2.0 | 2025-11-13 | Sprint 5 | ✅ Stable |
| **phase2_measure.py** | 1.1.0 | 2025-11-13 | Sprint 5 | ✅ Stable |
| **phase4_improve.py** | 1.1.0 | 2025-11-13 | Sprint 5 | ✅ Stable |
| **run_all_phases.py** | 1.1.0 | 2025-11-13 | Sprint 5 | ✅ Stable |
| **compare_iterations.py** | 1.0.0 | 2025-11-13 | Sprint 4 | ✅ Stable |
| **Test Suite** | 0.0.0 | N/A | Sprint 6 | ⏳ Pending |

### Iteration Data Versions

| Iteration | Data Version | Code Version | Date | Quality |
|-----------|--------------|--------------|------|---------|
| Iteration 1 | 1.0 | 1.0.0 | 2025-11-13 | ⚠️ Format issue |
| Iteration 2 | 1.0 | 1.0.0 (pre-fix) | 2025-11-13 | ⚠️ Pre-Sprint 5 |
| Iteration 3 | 2.0 | 1.2.0 (post-fix) | TBD | ✅ Expected good |

---

## 🔄 VERSION LIFECYCLE

### Development Lifecycle

```
Development → Testing → Staging → Production

feature/sprint-6-testing
    ↓ (PR review)
main (merge)
    ↓ (tag: v1.2.0-sprint6)
release/v1.2.0
    ↓ (validation)
main (production)
    ↓ (tag: v1.2.0)
Production Release
```

### Deprecation Policy

**Minor Version Deprecation:**
- Announce deprecation in version N
- Maintain support through version N+1
- Remove in version N+2

**Example:**
- v1.1.0: Announce old format deprecated
- v1.2.0: Both formats supported
- v1.3.0: Old format removed

**Major Version Deprecation:**
- Announce deprecation 2 major versions ahead
- Provide migration guide
- Maintain backward compatibility for 1 major version

---

## 📋 CHANGE LOG STANDARDS

### CHANGELOG.md Format

```markdown
# Changelog

All notable changes to the DMAIC project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Test framework setup (Sprint 6 Task 2)

### Changed
- Nothing yet

### Deprecated
- Nothing yet

### Removed
- Nothing yet

### Fixed
- Nothing yet

### Security
- Nothing yet

## [1.2.0] - 2025-11-13 - Sprint 5 Completion

### Added
- file_metrics dictionary in Phase 2 output
- Dual output locations for Phase 2 and Phase 4
- Backward compatibility support

### Changed
- Phase 2 output format (backward compatible)
- Phase 4 output location (backward compatible)

### Removed
- Manual phase handoff workarounds (28 lines)
- fix_phase_handoffs() method

### Fixed
- Phase 2 → Phase 3 data format mismatch
- Phase 4 → Phase 5 file path mismatch
- "11 problems" mystery (timing issue)

## [1.0.0] - 2025-11-13 - Sprint 3 Completion

### Added
- Initial DMAIC system release
- Phases 0-5 implementation
- Sprint orchestration system
- Comparison tool
- Comprehensive documentation

### Fixed
- UTF-8 encoding issues
- Module import conflicts
- Chunked processing for large codebases
```

---

## 🔐 VERSION ROLLBACK

### Rollback Procedures

**To Previous Sprint:**
```bash
# Checkout previous sprint tag
git checkout v1.1.0-sprint5

# Create hotfix branch if needed
git checkout -b hotfix/rollback-sprint6
```

**To Previous Iteration Data:**
```bash
# Restore from backup
cp -r backup/iteration_2/* DMAIC_V3_OUTPUT/sprints/iteration_2/

# Verify data integrity
python verify_data_integrity.py --iteration 2
```

**To Previous Code Version:**
```bash
# Checkout specific file version
git checkout v1.0.0 -- DMAIC_V3/phases/phase2_measure.py

# Test rollback
python run_all_phases.py --iteration test --validate
```

---

## 📊 VERSION METRICS

### Track Version Health

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| **Code Version Stability** | > 95% | 100% | ✅ |
| **Backward Compatibility** | 100% | 100% | ✅ |
| **Documentation Currency** | < 7 days old | Current | ✅ |
| **Test Coverage per Version** | > 70% | 0% | ⚠️ Pending |
| **Rollback Success Rate** | 100% | N/A | Not tested |

---

## 🎯 VERSIONING BEST PRACTICES

### DO's ✅

1. **Always tag sprint completions**
   ```bash
   git tag -a v1.2.0-sprint6 -m "Sprint 6: Iteration 3 validation"
   ```

2. **Maintain CHANGELOG.md**
   - Update with every significant change
   - Follow Keep a Changelog format
   - Link to related issues/PRs

3. **Version all artifacts**
   - Code: Header comments
   - Documentation: Version footers
   - Data: Metadata fields

4. **Use semantic versioning**
   - MAJOR: Breaking changes
   - MINOR: New features
   - PATCH: Bug fixes

5. **Create release branches**
   ```bash
   git checkout -b release/v1.3.0
   ```

### DON'Ts ❌

1. **Don't skip version numbers**
   - ❌ v1.0.0 → v1.2.0 (skipping 1.1.0)
   - ✅ v1.0.0 → v1.1.0 → v1.2.0

2. **Don't reuse version numbers**
   - ❌ Delete v1.1.0 and recreate
   - ✅ Create v1.1.1 for fixes

3. **Don't version without testing**
   - ❌ Tag before validation
   - ✅ Tag after successful testing

4. **Don't forget documentation**
   - ❌ Code changes without doc updates
   - ✅ Update docs with code changes

5. **Don't mix concerns in versions**
   - ❌ v1.1.0 with breaking changes
   - ✅ v2.0.0 for breaking changes

---

## 🔍 VERSION AUDITING

### Audit Checklist

**Pre-Release Audit:**
- [ ] All code changes documented
- [ ] CHANGELOG.md updated
- [ ] Version numbers updated in code
- [ ] Documentation versions updated
- [ ] Backward compatibility tested
- [ ] Migration guide created (if needed)
- [ ] Release notes prepared
- [ ] Tags created and pushed

**Post-Release Audit:**
- [ ] Tag verified in repository
- [ ] Version reflected in all components
- [ ] Documentation deployed
- [ ] Users notified (if applicable)
- [ ] Metrics collected
- [ ] Feedback gathered

---

## 📚 VERSION DOCUMENTATION

### Required Documentation per Version

1. **Release Notes**
   - What's new
   - What changed
   - What was fixed
   - Breaking changes (if any)
   - Migration guide (if needed)

2. **Version Manifest**
   ```json
   {
     "version": "1.2.0",
     "release_date": "2025-11-13",
     "sprint": "Sprint 5",
     "components": {
       "phase2_measure": "1.1.0",
       "phase4_improve": "1.1.0",
       "run_all_phases": "1.1.0"
     },
     "backward_compatible": true,
     "breaking_changes": false
   }
   ```

3. **Compatibility Matrix**
   | Version | Compatible With | Incompatible With |
   |---------|-----------------|-------------------|
   | 1.2.0 | 1.0.0, 1.1.0 | None |
   | 1.1.0 | 1.0.0 | None |
   | 1.0.0 | None (initial) | None |

---

## 🔗 RELATED DOCUMENTS

- [Workspace State](workspace/WORKSPACE_STATE.md)
- [Action Tracker](ACTION_TRACKER.md)
- [Operational Excellence](OPERATIONAL_EXCELLENCE.md)
- [Sprint Tracker](SPRINT_TRACKER.md)

---

## 📝 APPENDIX: VERSION HISTORY

### Version 1.2.0 - Sprint 5 Completion
**Date:** November 13, 2025, 17:39  
**Changes:**
- Added file_metrics to Phase 2
- Dual output locations for Phase 2 & 4
- Removed manual workarounds

**Files Changed:**
- phase2_measure.py (+11 lines)
- phase4_improve.py (+7 lines)
- run_all_phases.py (-28 lines)

**Impact:** Data format standardization, automated phase handoffs

---

### Version 1.0.0 - Sprint 3 Completion
**Date:** November 13, 2025  
**Changes:**
- Initial DMAIC system release
- All 6 phases implemented
- Sprint orchestration
- Comparison tool

**Files Created:**
- All core DMAIC files
- Sprint runner
- Phase executors
- Documentation

**Impact:** Full DMAIC cycle operational

---

**Document Version:** 1.0  
**Last Updated:** November 14, 2025  
**Maintained By:** DMAIC Sprint System  
**Review Frequency:** After each sprint completion
