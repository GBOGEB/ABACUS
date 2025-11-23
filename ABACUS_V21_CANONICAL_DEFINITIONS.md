# ABACUS v2.1 Canonical Definitions & Terminology

**Version:** 1.0.0  
**Generated:** 2025-11-23  
**Status:** CANONICAL REFERENCE

---

## 📚 Core Terminology

### PRE-CD (Pre-Continuous Deployment)

**Definition:**
The development phase where code is developed, tested, and validated in a **local environment** before integration with continuous deployment pipelines.

**Characteristics:**
- ✅ Local development environment
- ✅ Manual testing and validation
- ✅ Local Git repository
- ✅ No automated CI/CD pipelines
- ✅ Developer-controlled execution
- ✅ Workspace-based artifacts

**Synonyms:**
- Local Development Phase
- Pre-Integration Phase
- Development Phase
- Pre-Pipeline Phase

**NOT Synonymous With:**
- ❌ Production (requires POST-CD)
- ❌ Production-Ready (requires POST-CD validation)
- ❌ Deployed (requires POST-CD pipeline)

---

### POST-CD (Post-Continuous Deployment)

**Definition:**
The production phase where code is integrated with **GitHub**, automated through **CI/CD pipelines**, tested via **roundtrip workflows**, and deployed to **production environments**.

**Characteristics:**
- ✅ GitHub repository integration
- ✅ Automated CI/CD pipelines (GitHub Actions)
- ✅ Automated testing workflows
- ✅ Roundtrip validation (push → GitHub → pull → test)
- ✅ Production environment deployment
- ✅ Continuous monitoring and feedback

**Synonyms:**
- Production Phase
- CI/CD Integration Phase
- Pipeline-Enabled Phase
- GitHub-Integrated Phase

**NOT Synonymous With:**
- ❌ Local Development (PRE-CD phase)
- ❌ Manual Testing (PRE-CD phase)
- ❌ Workspace-Only (PRE-CD phase)

---

## 🔄 Phase Transition

### PRE-CD → POST-CD Transition

**Trigger Events:**
1. ✅ All PRE-CD validation complete (Stage 1)
2. ✅ GitHub repository created
3. ✅ CI/CD pipeline configured
4. ✅ First automated workflow executed

**Transition Criteria:**
```
PRE-CD Complete:
  ├─ Local tests: 100% pass
  ├─ Documentation: 100% aligned
  ├─ Knowledge: 100% preserved
  └─ Validation: All phases complete

POST-CD Ready:
  ├─ GitHub repo: Created
  ├─ CI/CD pipeline: Configured
  ├─ Workflows: Automated
  └─ Monitoring: Enabled
```

---

## 📊 ASCII Workflow Diagrams

### Overall Development Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    ABACUS v2.1 DEVELOPMENT WORKFLOW              │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                         PRE-CD PHASE                              │
│                    (Local Development)                            │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Stage 1.1      │
                    │  Environment    │
                    │  Setup          │
                    └────────┬────────┘
                             │ ✅ COMPLETE
                             ▼
                    ┌─────────────────┐
                    │  Stage 1.2      │
                    │  DOW            │
                    │  Integration    │
                    └────────┬────────┘
                             │ 🔄 IN PROGRESS (75%)
                             ▼
                    ┌─────────────────┐
                    │  Stage 1.3      │
                    │  Smoke Test     │
                    │  Validation     │
                    └────────┬────────┘
                             │ ⏳ PENDING
                             ▼
                    ┌─────────────────┐
                    │  Stage 1.4      │
                    │  Dry-Run        │
                    │  Validation     │
                    └────────┬────────┘
                             │ ⏳ PENDING
                             ▼
                    ┌─────────────────┐
                    │  Stage 1.5      │
                    │  Bridge         │
                    │  Validation     │
                    └────────┬────────┘
                             │ ⏳ PENDING
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    TRANSITION CHECKPOINT                          │
│              PRE-CD Complete → POST-CD Begin                      │
└──────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                         POST-CD PHASE                             │
│                  (GitHub Integration & CI/CD)                     │
└──────────────────────────────────────────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Stage 2        │
                    │  CI/CD          │
                    │  Integration    │
                    └────────┬────────┘
                             │ ⏳ PENDING
                             ▼
                    ┌─────────────────┐
                    │  Stage 3        │
                    │  Production     │
                    │  Deployment     │
                    └────────┬────────┘
                             │ ⏳ PENDING
                             ▼
                    ┌─────────────────┐
                    │  Stage 4        │
                    │  Iteration &    │
                    │  Monitoring     │
                    └────────┬────────┘
                             │ ⏳ PENDING
                             ▼
                    ┌─────────────────┐
                    │  Stage 5        │
                    │  Post-Impl &    │
                    │  Optimization   │
                    └────────┬────────┘
                             │ ⏳ PENDING
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    PRODUCTION READY                               │
│                  Maturity Level 3 Achieved                        │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🌳 Decision Trees

### Phase Classification Decision Tree

```
┌─────────────────────────────────────────────────────────────────┐
│              PHASE CLASSIFICATION DECISION TREE                  │
└─────────────────────────────────────────────────────────────────┘

START: Classify Current Phase
    │
    ├─ Q1: Is GitHub repository created?
    │   │
    │   ├─ NO ──────────────────────────────────► PRE-CD PHASE
    │   │                                          (Local Development)
    │   │
    │   └─ YES
    │       │
    │       ├─ Q2: Is CI/CD pipeline configured?
    │       │   │
    │       │   ├─ NO ──────────────────────────► PRE-CD PHASE
    │       │   │                                  (Transition Pending)
    │       │   │
    │       │   └─ YES
    │       │       │
    │       │       ├─ Q3: Are automated workflows running?
    │       │       │   │
    │       │       │   ├─ NO ──────────────────► PRE-CD PHASE
    │       │       │   │                          (Configuration Only)
    │       │       │   │
    │       │       │   └─ YES
    │       │       │       │
    │       │       │       ├─ Q4: Has roundtrip testing been executed?
    │       │       │       │   │
    │       │       │       │   ├─ NO ──────────► POST-CD PHASE
    │       │       │       │   │                 (Initial Integration)
    │       │       │       │   │
    │       │       │       │   └─ YES
    │       │       │       │       │
    │       │       │       │       ├─ Q5: Is production deployed?
    │       │       │       │       │   │
    │       │       │       │       │   ├─ NO ──► POST-CD PHASE
    │       │       │       │       │   │         (Testing)
    │       │       │       │       │   │
    │       │       │       │       │   └─ YES ─► POST-CD PHASE
    │       │       │       │       │             (Production)
    │       │       │       │       │
    │       │       │       │       └─ RESULT: POST-CD PHASE
    │       │       │       │
    │       │       │       └─ RESULT: POST-CD PHASE
    │       │       │
    │       │       └─ RESULT: PRE-CD PHASE
    │       │
    │       └─ RESULT: PRE-CD PHASE
    │
    └─ RESULT: PRE-CD PHASE
```

---

### Deployment Readiness Decision Tree

```
┌─────────────────────────────────────────────────────────────────┐
│           DEPLOYMENT READINESS DECISION TREE                     │
└─────────────────────────────────────────────────────────────────┘

START: Assess Deployment Readiness
    │
    ├─ Q1: Are all PRE-CD tests passing?
    │   │
    │   ├─ NO ──────────────────────────────────► NOT READY
    │   │                                          (Fix Tests)
    │   │
    │   └─ YES
    │       │
    │       ├─ Q2: Is documentation 100% aligned?
    │       │   │
    │       │   ├─ NO ──────────────────────────► NOT READY
    │       │   │                                  (Update Docs)
    │       │   │
    │       │   └─ YES
    │       │       │
    │       │       ├─ Q3: Is knowledge preserved (0 loss)?
    │       │       │   │
    │       │       │   ├─ NO ──────────────────► NOT READY
    │       │       │   │                          (Preserve Knowledge)
    │       │       │   │
    │       │       │   └─ YES
    │       │       │       │
    │       │       │       ├─ Q4: Are all validation phases complete?
    │       │       │       │   │
    │       │       │       │   ├─ NO ──────────► NOT READY
    │       │       │       │   │                 (Complete Validation)
    │       │       │       │   │
    │       │       │       │   └─ YES
    │       │       │       │       │
    │       │       │       │       ├─ READY FOR: POST-CD Transition
    │       │       │       │       │
    │       │       │       │       └─ NEXT: Create GitHub Repository
    │       │       │       │
    │       │       │       └─ RESULT: PRE-CD READY
    │       │       │
    │       │       └─ RESULT: NOT READY
    │       │
    │       └─ RESULT: NOT READY
    │
    └─ RESULT: NOT READY
```

---

## 🎯 Validation Checkpoints

### PRE-CD Validation Checklist

```
┌─────────────────────────────────────────────────────────────────┐
│                  PRE-CD VALIDATION CHECKLIST                     │
└─────────────────────────────────────────────────────────────────┘

Stage 1.1: Environment Setup
  ✅ Python environment validated
  ✅ Dependencies installed
  ✅ Repository structure validated
  ✅ Output directories created

Stage 1.2: DOW Integration
  ✅ DOW components located
  ✅ DOW workflows validated
  ✅ DOW tracking system created
  🔄 Handover tarball integration (IN PROGRESS)

Stage 1.3: Smoke Test Validation
  ⏳ 6 smoke tests executed
  ⏳ Results validated
  ⏳ Reports generated

Stage 1.4: Dry-Run Validation
  ⏳ 6 dry-run tests executed
  ⏳ Results validated
  ⏳ Reports generated

Stage 1.5: Bridge Validation
  ⏳ 4 bridges validated
  ⏳ Integration tested
  ⏳ Reports generated

PRE-CD COMPLETE: ⏳ PENDING (33% complete)
```

### POST-CD Validation Checklist

```
┌─────────────────────────────────────────────────────────────────┐
│                  POST-CD VALIDATION CHECKLIST                    │
└─────────────────────────────────────────────────────────────────┘

Stage 2: CI/CD Integration
  ⏳ GitHub repository created
  ⏳ CI/CD pipeline configured
  ⏳ Automated workflows setup
  ⏳ Smoke tests integrated
  ⏳ Pipeline tested

Stage 3: Production Deployment
  ⏳ Bridges deployed
  ⏳ Runners deployed
  ⏳ DMAIC engine deployed
  ⏳ Integration tested
  ⏳ Deployment validated

Stage 4: Iteration & Monitoring
  ⏳ DMAIC phases executed
  ⏳ Iterations completed
  ⏳ Sprints executed
  ⏳ Performance monitored
  ⏳ Optimizations applied

Stage 5: Post-Implementation
  ⏳ Comprehensive validation
  ⏳ Reports generated
  ⏳ Documentation updated
  ⏳ Handover completed
  ⏳ Continuous improvement established

POST-CD COMPLETE: ⏳ PENDING (0% complete)
```

---

## 📋 Canonical Usage Examples

### ✅ CORRECT Usage

**Example 1: Describing Current Status**
```
"ABACUS v2.1 is currently in the PRE-CD phase (Stage 1.2.4), 
with local development 100% complete and GitHub integration pending."
```

**Example 2: Describing Transition**
```
"Upon completion of Stage 1.5, the system will transition from 
PRE-CD to POST-CD phase, beginning with GitHub repository creation."
```

**Example 3: Describing Deployment**
```
"Production deployment is a POST-CD activity that occurs in Stage 3, 
after CI/CD integration is complete."
```

### ❌ INCORRECT Usage

**Example 1: Premature Production Claim**
```
❌ "ABACUS v2.1 is production-ready"
✅ "ABACUS v2.1 local development is complete (PRE-CD), 
   with POST-CD production deployment pending"
```

**Example 2: Confusing Phases**
```
❌ "System is deployed to production"
✅ "System is deployed locally (PRE-CD), 
   with GitHub production deployment pending (POST-CD)"
```

**Example 3: Misusing Readiness**
```
❌ "100% deployment readiness means production-ready"
✅ "100% deployment readiness for local environment (PRE-CD), 
   POST-CD validation required for production"
```

---

## 🔍 Phase Identification Guide

### Quick Reference Table

| Indicator | PRE-CD | POST-CD |
|-----------|--------|---------|
| **Environment** | Local workspace | GitHub + Production |
| **Testing** | Manual execution | Automated CI/CD |
| **Repository** | Local Git | GitHub remote |
| **Workflows** | Manual scripts | GitHub Actions |
| **Deployment** | Local execution | Pipeline automation |
| **Monitoring** | Local logs | Production monitoring |
| **Validation** | Developer-driven | Automated + Manual |
| **Artifacts** | Local files | GitHub artifacts |

---

## 📊 Maturity Level Mapping

### PRE-CD Phase Maturity

```
Level 0 (Initial)     ──► PRE-CD Stage 1.1
Level 1 (Managed)     ──► PRE-CD Stage 1.2
Level 2 (Development) ──► PRE-CD Stage 1.3-1.5
```

### POST-CD Phase Maturity

```
Level 3 (Production)  ──► POST-CD Stage 2-3
Level 4 (Optimized)   ──► POST-CD Stage 4-5
```

---

## 🎯 Key Principles

### MANTRA: NO DOCUMENTATION BEFORE VALIDATION

**Principle:**
Documentation is created **AFTER** validation is complete, not before.

**Rationale:**
- Prevents documenting unvalidated features
- Ensures accuracy and reliability
- Reduces documentation rework
- Maintains documentation-code alignment

**Application:**
```
1. Develop feature (PRE-CD)
2. Test feature (PRE-CD)
3. Validate feature (PRE-CD)
4. Document feature (PRE-CD) ✅ ONLY AFTER VALIDATION
5. Integrate to GitHub (POST-CD)
6. Validate in CI/CD (POST-CD)
7. Update documentation (POST-CD) ✅ ONLY AFTER CI/CD VALIDATION
```

---

*Canonical Definitions v1.0.0*  
*Generated: 2025-11-23*  
*Status: AUTHORITATIVE REFERENCE*
